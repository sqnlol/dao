import tkinter as tk
from tkinter import ttk
import queue
import sys 
import os 
import threading 

# --- POPRAWIONE IMPORTY ---
# Musimy odwoływać się z poziomu 'src'
from src.gui.login_view import LoginView
from src.gui.search_view import SearchView
from src.gui.results_view import ResultsView
from src import steam_market
# --- KONIEC POPRAWEK ---

SUGGESTIONS_FILE = "src/suggestions.txt"

class MarketApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Skin Analyzer")
        self.root.geometry("850x650") 
        self.root.minsize(width=800, height=600) 

        # Ustaw ikonę okna (Windows taskbar + tytuł)
        try:
            from PIL import Image, ImageTk
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img')
            icon_path = os.path.join(assets_dir, 'CS2SkinAnalyzer.png')
            ico_path = os.path.join(assets_dir, 'CS2SkinAnalyzer.ico')
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                # Dla ikony systemowej najlepiej zapewnić rozmiar 32x32 (zachowaj proporcje)
                try:
                    img_icon = img.copy()
                    img_icon.thumbnail((32, 32))
                    self._app_icon_img = ImageTk.PhotoImage(img_icon)
                    self.root.iconphoto(False, self._app_icon_img)
                except Exception:
                    pass
                # Spróbuj przygotować plik .ico dla pełnej zgodności na Windows
                try:
                    if not os.path.exists(ico_path):
                        # Utwórz kwadratowe płótno i wklej obrazek na środku dla każdego rozmiaru
                        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                        # Najprostsze: Pillow potrafi zapisać wielorozmiarowe ICO z listą sizes bez wcześniejszego ręcznego montażu
                        img.save(ico_path, format='ICO', sizes=sizes)
                    # Ustaw również iconbitmap, jeśli .ico istnieje
                    if os.path.exists(ico_path):
                        try:
                            self.root.iconbitmap(ico_path)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception as e:
            print(f"Nie udało się ustawić ikony aplikacji: {e}", file=sys.stderr)

        # Dane sesyjne
        self.steam_id = None
        self.steam_name = "Użytkowniku" 
        self.login_cookie = None 
        
        self.result_queue = queue.Queue()
        
        # Lista wszystkich przedmiotów do autouzupełniania
        self.all_suggestions = [] 
        
        # Słownik przechowujący instancje widoków
        self.views = {}
        self.current_view = None
        
        self._initialize_views()

        # Wczytanie sugestii z pliku (bez automatycznego pobierania). Pobieranie będzie na żądanie.
        self._load_existing_suggestions_only()

        # Event anulowania pobierania sugestii i flaga aktywnego wątku
        self._suggestions_cancel_event = threading.Event()
        self._suggestions_thread_active = False

        # Przechwyć zamknięcie okna aby przerwać pobieranie
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # --- Start aplikacji ---
        self.switch_view("login")
        self.process_queue()
        
    def _initialize_views(self):
        """Tworzy instancje wszystkich widoków."""
        
        self.container = ttk.Frame(self.root)
        self.container.pack(fill='both', expand=True)
        
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Inicjalizacja klas widoków
        self.views["login"] = LoginView(self.container, self)
        self.views["search"] = SearchView(self.container, self)
        self.views["results"] = ResultsView(self.container, self)

        # Ustawienie pozycji początkowej dla wszystkich widoków
        for name, view in self.views.items():
            view.frame.grid(row=0, column=0, sticky="nsew")

    def switch_view(self, view_name, **kwargs):
        """Przełącza aktualnie wyświetlany widok."""
        
        if view_name == "search":
            self.views["search"].update_welcome_label()
            
        elif view_name == "results":
            if 'item_name' in kwargs and 'history_data' in kwargs and 'listings_data' in kwargs:
                 self.views["results"].show_results(kwargs['item_name'], kwargs['history_data'], kwargs['listings_data'])
            
        view = self.views.get(view_name)
        if view:
            view.frame.tkraise()
            self.current_view = view
            
    # ------------------------------------------------------------------
    # OBSŁUGA SUGEROWANYCH PRZEDMIOTÓW
    # ------------------------------------------------------------------
    def _load_existing_suggestions_only(self):
        """Wczytuje sugestie wyłącznie z pliku (jeśli istnieje). Nie pobiera z sieci."""
        if os.path.exists(SUGGESTIONS_FILE):
            try:
                with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as f:
                    self.all_suggestions = [line.strip() for line in f if line.strip()]
                print(f"Wczytano {len(self.all_suggestions)} sugestii z pliku: {SUGGESTIONS_FILE}")
            except Exception as e:
                print(f"Błąd wczytywania sugestii z pliku: {e}.", file=sys.stderr)
        else:
            print("Brak pliku suggestions.txt – pobieranie dostępne z poziomu przycisku w UI.")

    def update_suggestions_async(self):
        """Pobiera/aktualizuje listę sugestii na żądanie użytkownika (w tle)."""
        import threading
        if self._suggestions_thread_active:
            return  # już trwa
        self._suggestions_cancel_event.clear()
        t = threading.Thread(target=self._run_suggestion_fetch, daemon=True)
        self._suggestions_thread_active = True
        t.start()

    def cancel_suggestions_fetch(self):
        """Ustawia flagę anulowania dla procesu pobierania sugestii."""
        if self._suggestions_thread_active:
            self._suggestions_cancel_event.set()
            try:
                self.result_queue.put({'status': 'log', 'message': 'Żądanie anulowania pobierania sugestii...'})
            except Exception:
                pass

    def _on_close(self):
        """Handler zamknięcia okna: przerwij ewentualne pobieranie i zamknij."""
        self.cancel_suggestions_fetch()
        # krótkie odczekanie aby wątek mógł się zakończyć łagodnie
        self.root.after(150, self.root.destroy)

    def _run_suggestion_fetch(self):
        """Logika wątku roboczego do pobierania i zapisywania sugestii (wznawialna)."""
        def cb(msg):
            try:
                if msg.startswith("PROGRESS "):
                    # Format: PROGRESS current total retries
                    parts = msg.split()
                    if len(parts) >= 4:
                        try:
                            current = int(parts[1])
                            total = int(parts[2])
                            retries = int(parts[3])
                            eta = int(parts[4]) if len(parts) >= 5 else -1
                        except ValueError:
                            current = 0; total = 0; retries = 0; eta = -1
                        self.result_queue.put({'status': 'progress', 'progress': {'current': current, 'total': total, 'retries': retries, 'eta': eta}})
                    # Ignoruj tekstowe logi postępu; UI odczytuje PROGRESS strukturalnie
                    else:
                        pass
                else:
                    # Przepuszczaj tylko przerwania/błędy/koniec
                    if any(k in msg.lower() for k in ["przerwano", "błąd", "zakończono", "gotowe", "niepowodzenie"]):
                        self.result_queue.put({'status': 'log', 'message': msg})
            except Exception:
                pass
        cb("Rozpoczynam aktualizację listy przedmiotów (może potrwać).")
        # dezaktywuj przycisk w UI
        try:
            if "search" in self.views:
                self.views["search"].set_update_button_state(active=False)
                self.views["search"].set_cancel_button_state(active=True)
        except Exception:
            pass
        suggestions = steam_market.fetch_all_csgo_items(
            output_file_path=SUGGESTIONS_FILE,
            page_size=100,
            resume=True,
            progress_path="src/suggestions.progress.json",
            partial_path="src/suggestions.partial.txt",
            log_callback=cb,
            cancel_event=self._suggestions_cancel_event,
        )
        if suggestions:
            self.all_suggestions = suggestions
            cb(f"Zakończono. Łącznie pozycji: {len(suggestions)}.")
            self.root.after(0, lambda: self._notify_search_view_suggestions_ready())
        else:
            cb("Przerwano/niepowodzenie pobierania sugestii. Możesz wznowić ponownie przyciskiem.")
        # ponownie aktywuj przycisk
        try:
            if "search" in self.views:
                self.views["search"].set_update_button_state(active=True)
                self.views["search"].set_cancel_button_state(active=False)
                self.views["search"].show_progress_bar(False)
                if hasattr(self.views["search"], 'clear_inline_progress'):
                    self.views["search"].clear_inline_progress()
        except Exception:
            pass
        self._suggestions_thread_active = False

    def _notify_search_view_suggestions_ready(self):
        """Przekazuje listę sugestii do SearchView po ich załadowaniu."""
        if "search" in self.views and hasattr(self.views["search"], 'set_suggestions'):
            self.views["search"].set_suggestions(self.all_suggestions)
            self.views["search"].log_message(f"Autouzupełnianie gotowe ({len(self.all_suggestions)} przedmiotów).")

    # ------------------------------------------------------------------
    # GŁÓWNA PĘTLA
    # ------------------------------------------------------------------
    def process_queue(self):
        """Sprawdza kolejkę wyników operacji wątkowych."""
        try:
            result = self.result_queue.get_nowait()
            
            status = result.get('status')
            
            if status == 'log':
                if "search" in self.views:
                    self.views["search"].log_message(result['message'])
            elif status == 'progress':
                # Jeśli anulowano, ignorujemy dalsze komunikaty PROGRESS aby nie odświeżać paska
                if self._suggestions_cancel_event.is_set():
                    pass
                else:
                    prog = result.get('progress') or {}
                    try:
                        current = int(prog.get('current', 0))
                        total = int(prog.get('total', 0))
                        retries = int(prog.get('retries', 0))
                        eta = int(prog.get('eta', -1)) if prog.get('eta', None) is not None else -1
                    except Exception:
                        current, total, retries, eta = 0, 0, 0, -1
                    if "search" in self.views:
                        self.views["search"].update_progress_bar(current, total, retries, eta)
            
            elif status == 'error':
                if "search" in self.views:
                    self.views["search"].log_message(f"BŁĄD: {result['message']}")
                    self.views["search"].search_button.config(state='normal') 
            
            elif status == 'success':
                if "search" in self.views:
                    self.views["search"].log_message("Pobieranie i zapisywanie zakończone pomyślnie.")
                    self.views["search"].search_button.config(state='normal')
                # Jeśli worker dołączył 'image_url' na najwyższym poziomie, wstaw go do listings_data
                listings = result.get('listings_data') or {}
                if 'image_url' in result and isinstance(listings, dict):
                    listings['image_url'] = result.get('image_url')

                self.switch_view(
                    "results",
                    item_name=result['item_name'],
                    history_data=result['history_data'],
                    listings_data=listings
                )
                
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
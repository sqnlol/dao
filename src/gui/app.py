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
from src.gui.cases_view import CasesView
from src.gui.case_detail_view import CaseDetailView
from src import steam_market
# --- KONIEC POPRAWEK ---

SUGGESTIONS_FILE = "src/suggestions.txt"

class MarketApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Skin Analyzer")
        self.root.geometry("850x650") 
        self.root.minsize(width=800, height=600) 
        # Zachowaj bazowy tytuł do aktualizacji taskbara o procenty
        self._base_title = self.root.title()

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
        
        # Ustawienia waluty (domyślnie PLN)
        self.currency = "PLN"  # Opcje: PLN, USD, EUR
        self.currency_code = 6  # Steam API: 6=PLN
        self.currency_symbol = "zł" 
        
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
        # Autologin jeśli pamiętany użytkownik
        self._attempt_auto_login()
        self.process_queue()
        # Auto-odświeżanie sugestii: domyślnie wyłączone; użytkownik włącza z SearchView
        self._auto_enabled = False
        self._auto_min_s = 600
        self._auto_max_s = 900
        self._auto_after_id = None
        self._next_auto_refresh_ts = None

    def set_taskbar_percent(self, percent: int | None):
        """Ustawia procent w tytule okna (widoczny jako tekst na pasku zadań).

        percent=None lub spoza [0,100] przywraca bazowy tytuł bez procentów.
        """
        try:
            if percent is None or not isinstance(percent, int) or percent < 0 or percent > 100:
                self.root.title(self._base_title)
            else:
                self.root.title(f"{self._base_title} [{percent}%]")
        except Exception:
            # Bezpieczny no-op na nieobsługiwanych platformach/sytuacjach
            pass

    # ------------------------------------------------------------------
    # PAMIĘTANIE SESJI
    # ------------------------------------------------------------------
    def _auth_state_path(self):
        """Zwraca ścieżkę do pliku auth_state w katalogu użytkownika (LocalAppData)."""
        try:
            # Windows: %LOCALAPPDATA% preferowane; fallback na HOME
            local_appdata = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
            target_dir = os.path.join(local_appdata, 'CS2SkinAnalyzer')
            os.makedirs(target_dir, exist_ok=True)
            return os.path.join(target_dir, 'auth_state.json')
        except Exception:
            # Ostateczny fallback: bieżący katalog (niezalecane, ale gwarantuje działanie)
            return 'auth_state.json'

    def _attempt_auto_login(self):
        """Jeśli istnieje zapamiętana sesja (remember me), wczytaj ją i przełącz do search."""
        path = self._auth_state_path()
        try:
            if os.path.exists(path):
                import json
                data = json.load(open(path, 'r', encoding='utf-8'))
                cookie = data.get('login_cookie')
                steam_name = data.get('steam_name') or 'Użytkowniku Steam'
                if cookie and isinstance(cookie, str) and len(cookie) > 10:
                    # Walidacja cookie: lekki ping do endpointu priceoverview (nie wymaga pełnej historii)
                    if self._validate_cookie(cookie):
                        self.login_cookie = cookie
                        self.steam_name = steam_name
                        print("Auto-login: przywrócono sesję zapamiętanego użytkownika (cookie OK).")
                        self.switch_view('search')
                        return
                    else:
                        print("Auto-login: zapisane cookie nieprawidłowe lub wygasłe.")
                        # Przekaż do login view z prefill cookie (ułatwia poprawę) + komunikat
                        self.switch_view('login')
                        lv = self.views.get('login')
                        if lv and hasattr(lv, 'cookie_entry'):
                            try:
                                lv.cookie_entry.delete(0, tk.END)
                                lv.cookie_entry.insert(0, cookie)
                                if hasattr(lv, 'login_status'):
                                    lv.login_status.config(text="Zapisane cookie wygasło – wprowadź nowe lub zaloguj przez przeglądarkę.", foreground='orange')
                            except Exception:
                                pass
                        return
        except Exception as e:
            print(f"Auto-login nieudany: {e}", file=sys.stderr)
        # jeśli brak auto-login -> ekran logowania
        self.switch_view('login')

    def _validate_cookie(self, cookie: str) -> bool:
        """Lekka walidacja cookie przez wywołanie prostego endpointu wymagającego zalogowania.

        Używamy pricehistory dla prostego, małego przedmiotu (szybki response) – jeśli success=False lub błąd, traktujemy jako nieważne.
        Chroni przed bezsensownym auto-loginem z wygasłym ciasteczkiem.
        """
        try:
            if not cookie or len(cookie) < 10:
                return False
            test_item = 'P250 | Sand Dune (Field-Tested)'  # tani, częsty przedmiot
            headers = steam_market.base_headers.copy()
            headers['Cookie'] = f'steamLoginSecure={cookie}'
            import requests
            url = f"https://steamcommunity.com/market/pricehistory/?appid=730&market_hash_name={requests.utils.quote(test_item)}"
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code != 200:
                return False
            data = resp.json()
            # Jeśli success True i ma pole prices (nawet pusta lista), uznaj cookie za ważne
            return bool(data.get('success'))
        except Exception:
            return False

    def persist_auth_state(self):
        """Zapisuje bieżącą sesję do pliku jeśli jest login_cookie (remember me)."""
        path = self._auth_state_path()
        try:
            if self.login_cookie and isinstance(self.login_cookie, str) and len(self.login_cookie) > 10:
                import json
                payload = {
                    'login_cookie': self.login_cookie,
                    'steam_name': self.steam_name
                }
                json.dump(payload, open(path, 'w', encoding='utf-8'))
        except Exception as e:
            print(f"Nie udało się zapisać auth_state: {e}", file=sys.stderr)

    def clear_auth_state(self):
        path = self._auth_state_path()
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Nie udało się usunąć auth_state: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # CYKLICZNE POBIERANIE SUGESTII (TYMCZASOWE)
    # ------------------------------------------------------------------
    def _schedule_next_auto_refresh(self, delay_seconds: int | None = None):
        """Planuje następny cykl auto-odświeżania wg bieżących ustawień.

        Jeśli wyłączone – anuluje istniejący timer. Gdy `delay_seconds` None, losuje z [min,max].
        """
        try:
            # Anuluj poprzedni timer jeśli istnieje
            if self._auto_after_id is not None:
                try:
                    self.root.after_cancel(self._auto_after_id)
                except Exception:
                    pass
                self._auto_after_id = None
            if not self._auto_enabled:
                self._next_auto_refresh_ts = None
                return
            import random, time
            min_s = max(1, int(self._auto_min_s))
            max_s = max(min_s, int(self._auto_max_s))
            delay = int(delay_seconds) if isinstance(delay_seconds, int) and delay_seconds >= 0 else random.randint(min_s, max_s)
            self._next_auto_refresh_ts = time.time() + delay
            # poinformuj widok o nowym ETA, jeśli istnieje
            if "search" in self.views and hasattr(self.views["search"], "_update_auto_next_label"):
                try:
                    self.views["search"]._update_auto_next_label()
                except Exception:
                    pass
            self._auto_after_id = self.root.after(delay * 1000, self._periodic_suggestions_tick)
        except Exception:
            pass

    def _periodic_suggestions_tick(self):
        try:
            if not self._auto_enabled:
                return
            # Nie dubluj – jeśli proces już trwa, przeskocz
            if getattr(self, '_suggestions_thread_active', False):
                self._enqueue_log("Auto-odświeżanie: poprzednia aktualizacja w toku — pomijam cykl.")
            else:
                self._enqueue_log("Auto-odświeżanie sugestii — uruchamiam w tle.")
                self.update_suggestions_async()
        except Exception:
            pass
        # Zaplanuj następny cykl
        self._schedule_next_auto_refresh()

    def _enqueue_log(self, message: str):
        try:
            self.result_queue.put({'status': 'log', 'message': message})
        except Exception:
            pass

    # Publiczne API: ustawienia auto-odświeżania z SearchView
    def set_auto_refresh_config(self, enabled: bool, min_seconds: int, max_seconds: int):
        try:
            self._auto_enabled = bool(enabled)
            # sanity clamp
            try:
                min_s = int(min_seconds)
                max_s = int(max_seconds)
            except Exception:
                min_s, max_s = 600, 900
            if min_s < 1:
                min_s = 1
            if max_s < min_s:
                max_s = min_s
            self._auto_min_s = min_s
            self._auto_max_s = max_s
            if self._auto_enabled:
                self._enqueue_log(f"Auto-odświeżanie: włączone ({min_s}-{max_s}s).")
                # Zaplanuj nowy cykl od teraz
                self._schedule_next_auto_refresh()
            else:
                self._enqueue_log("Auto-odświeżanie: wyłączone.")
                self._schedule_next_auto_refresh(delay_seconds=0)  # spowoduje anulowanie
        except Exception as e:
            print(f"Błąd set_auto_refresh_config: {e}", file=sys.stderr)
        
    def _initialize_views(self):
        """Tworzy instancje wszystkich widoków."""
        
        self.container = ttk.Frame(self.root)
        self.container.pack(fill='both', expand=True)
        
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=0)  # Sidebar - fixed width
        self.container.grid_columnconfigure(1, weight=1)  # Main content - expandable

        # Stwórz lewy panel boczny (sidebar)
        self._create_sidebar()

        # Kontener na główne widoki (po prawej od sidebaru)
        self.content_frame = ttk.Frame(self.container)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Inicjalizacja klas widoków w content_frame zamiast container
        self.views["login"] = LoginView(self.content_frame, self)
        self.views["search"] = SearchView(self.content_frame, self)
        self.views["results"] = ResultsView(self.content_frame, self)
        self.views["cases"] = CasesView(self.content_frame, self)
        self.views["case_detail"] = CaseDetailView(self.content_frame, self)

        # Ustawienie pozycji początkowej dla wszystkich widoków
        for name, view in self.views.items():
            view.frame.grid(row=0, column=0, sticky="nsew")
    
    def _create_sidebar(self):
        """Tworzy lewy panel boczny z menu nawigacyjnym."""
        # Główny frame sidebaru z ciemnym tłem
        self.sidebar = ttk.Frame(self.container, style='Sidebar.TFrame', width=200)
        self.sidebar.grid(row=0, column=0, sticky='ns')
        self.sidebar.grid_propagate(False)  # Zachowaj stałą szerokość
        
        # Styl dla sidebaru
        style = ttk.Style()
        style.configure('Sidebar.TFrame', background='#1a1a1a')
        style.configure('SidebarButton.TButton', 
                   background='#2a2a2a', 
                   foreground='white',
                   borderwidth=2,
                   focuscolor='none',
                   padding=12,
                   font=('Arial', 10))
        style.map('SidebarButton.TButton',
             background=[('active', '#3a3a3a'), ('pressed', '#4a4a4a')])
        # Styl przycisku na hover (pogrubienie + jaśniejsze tło)
        style.configure('SidebarButtonHover.TButton',
                background='#3a3a3a',
                foreground='white',
                borderwidth=2,
                padding=12,
                font=('Arial', 10, 'bold'))
        
        # Logo w górnej części
        logo_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        logo_frame.pack(side='top', fill='x', pady=20, padx=10)

        # Wczytaj i pokaż logo z zachowaniem spójnego wcięcia (naprawa IndentationError)
        try:
            from PIL import Image, ImageTk
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'CS2SkinAnalyzer.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img.thumbnail((80, 80))
                self._sidebar_logo_img = ImageTk.PhotoImage(img)
                logo_label = tk.Label(logo_frame, image=self._sidebar_logo_img, bg='#1a1a1a')
                logo_label.pack()
        except Exception as e:
            print(f"Nie udało się załadować logo sidebaru: {e}", file=sys.stderr)
        
        # Separator po logo
        sep = ttk.Frame(self.sidebar, height=2, style='Sidebar.TFrame')
        sep.pack(fill='x', pady=(0, 10))
        
        # Menu nawigacyjne
        menu_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        menu_frame.pack(side='top', fill='both', expand=True, padx=5)
        
        # Przycisk Główna
        self.btn_home = ttk.Button(menu_frame, text="🏠 Główna", 
                                   style='SidebarButton.TButton',
                                   command=lambda: self._sidebar_navigate('home'))
        self.btn_home.pack(fill='x', pady=2)
        
        # Przycisk Skrzynie
        self.btn_cases = ttk.Button(menu_frame, text="📦 Skrzynie", 
                                    style='SidebarButton.TButton',
                                    command=lambda: self._sidebar_navigate('cases'))
        self.btn_cases.pack(fill='x', pady=2)
        # Efekt hover dla przycisków w sidebarze
        try:
            self.btn_home.bind('<Enter>', lambda e: self.btn_home.configure(style='SidebarButtonHover.TButton'))
            self.btn_home.bind('<Leave>', lambda e: self.btn_home.configure(style='SidebarButton.TButton'))
            self.btn_cases.bind('<Enter>', lambda e: self.btn_cases.configure(style='SidebarButtonHover.TButton'))
            self.btn_cases.bind('<Leave>', lambda e: self.btn_cases.configure(style='SidebarButton.TButton'))
        except Exception:
            pass
        
        # Separator przed walutą
        ttk.Frame(menu_frame, height=20, style='Sidebar.TFrame').pack(fill='x', pady=10)
        
        # Sekcja waluty
        currency_label = tk.Label(menu_frame, text="💱 Waluta:", 
                                 bg='#1a1a1a', fg='white', 
                                 font=('Arial', 9))
        currency_label.pack(fill='x', pady=(5, 2))
        
        # Combobox wyboru waluty
        style.configure('Currency.TCombobox', fieldbackground='#2a2a2a', background='#2a2a2a')
        self.currency_combo = ttk.Combobox(menu_frame, 
                                          values=['PLN', 'USD', 'EUR'],
                                          state='readonly',
                                          width=15)
        self.currency_combo.set(self.currency)
        self.currency_combo.pack(fill='x', pady=2, padx=5)
        self.currency_combo.bind('<<ComboboxSelected>>', self._on_currency_change)
        
        # Sidebar ukryty domyślnie (widoczny dopiero po zalogowaniu)
        self.sidebar.grid_remove()
    
    def _sidebar_navigate(self, destination):
        """Obsługuje nawigację z sidebaru."""
        if destination == 'home':
            self.switch_view('search')
        elif destination == 'cases':
            self.switch_view('cases')
    
    def _on_currency_change(self, event=None):
        """Obsługuje zmianę waluty."""
        selected = self.currency_combo.get()
        
        # Mapowanie walut na kody Steam API i symbole
        currency_map = {
            'PLN': {'code': 6, 'symbol': 'zł'},
            'USD': {'code': 1, 'symbol': '$'},
            'EUR': {'code': 3, 'symbol': '€'}
        }
        
        if selected in currency_map:
            self.currency = selected
            self.currency_code = currency_map[selected]['code']
            self.currency_symbol = currency_map[selected]['symbol']
            
            # Loguj zmianę
            current_view = self.current_view
            if current_view and hasattr(current_view, 'log_message'):
                current_view.log_message(f"Waluta zmieniona na: {selected} ({self.currency_symbol})")
            
            # Odśwież bieżący widok jeśli to results (ponownie pobierz dane)
            if self.current_view == self.views.get('results'):
                # Informacja że trzeba ponownie wyszukać
                if hasattr(current_view, 'log_message'):
                    current_view.log_message("Wykonaj ponowne wyszukiwanie aby zobaczyć ceny w nowej walucie.")
    
    def _show_sidebar(self):
        """Pokazuje sidebar."""
        try:
            self.sidebar.grid()
        except Exception:
            pass
    
    def _hide_sidebar(self):
        """Ukrywa sidebar."""
        try:
            self.sidebar.grid_remove()
        except Exception:
            pass

    def switch_view(self, view_name, **kwargs):
        """Przełącza aktualnie wyświetlany widok."""
        
        # Pokaż/ukryj sidebar w zależności od widoku
        if view_name == "login":
            self._hide_sidebar()
        else:
            self._show_sidebar()
        
        if view_name == "search":
            self.views["search"].update_welcome_label()
            
        elif view_name == "results":
            if 'item_name' in kwargs and 'history_data' in kwargs and 'listings_data' in kwargs:
                 self.views["results"].show_results(
                     kwargs['item_name'], 
                     kwargs['history_data'], 
                     kwargs['listings_data'],
                     fresh_history=kwargs.get('fresh_history'),
                     currency_code=kwargs.get('currency_code')
                 )
        elif view_name == "case_detail":
            if 'case' in kwargs:
                self.views["case_detail"].show_case(kwargs['case'])
            
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
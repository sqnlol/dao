import tkinter as tk
from tkinter import ttk
import queue
import sys 
import os 
import threading 

# Import widoków z tego samego pakietu
from gui.login_view import LoginView
from gui.search_view import SearchView
from gui.results_view import ResultsView
import steam_market

SUGGESTIONS_FILE = "src/suggestions.txt"

class MarketApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CS2 Skin Analyzer")
        self.root.geometry("850x650") 
        self.root.minsize(width=650, height=500) 

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

        # Wczytanie/Pobranie sugestii
        self._load_or_fetch_suggestions() 
        
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
            # 🛑 Zmiana: Poprawne przekazywanie danych do show_results
            if 'item_name' in kwargs and 'history_data' in kwargs and 'listings_data' in kwargs:
                 self.views["results"].show_results(kwargs['item_name'], kwargs['history_data'], kwargs['listings_data'])
            
        view = self.views.get(view_name)
        if view:
            view.frame.tkraise()
            self.current_view = view
            
    # ------------------------------------------------------------------
    # OBSŁUGA SUGEROWANYCH PRZEDMIOTÓW
    # ------------------------------------------------------------------
    def _load_or_fetch_suggestions(self):
        """Wczytuje sugestie z pliku lub pobiera je z API."""
        if os.path.exists(SUGGESTIONS_FILE):
            try:
                with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as f:
                    self.all_suggestions = [line.strip() for line in f if line.strip()]
                print(f"Wczytano {len(self.all_suggestions)} sugestii z pliku: {SUGGESTIONS_FILE}")
            except Exception as e:
                print(f"Błąd wczytywania sugestii z pliku: {e}. Spróbuję pobrać z API.", file=sys.stderr)
                self._fetch_suggestions_async()
        else:
            self._fetch_suggestions_async()

    def _fetch_suggestions_async(self):
        """Uruchamia pobieranie sugestii z API w osobnym wątku."""
        print("Plik sugestii nie istnieje. Uruchamianie pobierania z API...")
        threading.Thread(target=self._run_suggestion_fetch, daemon=True).start()

    def _run_suggestion_fetch(self):
        """Logika wątku roboczego do pobierania i zapisywania sugestii."""
        suggestions = steam_market.fetch_all_csgo_items()
        
        if suggestions:
            self.all_suggestions = suggestions
            
            # Zapis do pliku
            try:
                # Używamy os.path.join, aby upewnić się, że ścieżka jest poprawna
                # Tworzymy katalog "src" jeśli nie istnieje
                os.makedirs(os.path.dirname(SUGGESTIONS_FILE) or '.', exist_ok=True)
                with open(SUGGESTIONS_FILE, 'w', encoding='utf-8') as f:
                    for item in suggestions:
                        f.write(item + '\n')
                print(f"Pomyślnie zapisano listę sugestii do pliku: {SUGGESTIONS_FILE}")
            except Exception as e:
                print(f"BŁĄD zapisu listy sugestii do pliku: {e}", file=sys.stderr)
                
            # Powiadamiamy widok wyszukiwania, że dane są gotowe
            self.root.after(0, lambda: self._notify_search_view_suggestions_ready())
            
        else:
             print("BŁĄD: Nie udało się pobrać sugestii z API.", file=sys.stderr)
             self.root.after(0, lambda: self.views["search"].log_message("OSTRZEŻENIE: Nie udało się pobrać listy autouzupełniania. Wyszukiwanie jest nadal możliwe."))

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
            
            elif status == 'error':
                if "search" in self.views:
                    self.views["search"].log_message(f"BŁĄD: {result['message']}")
                    self.views["search"].search_button.config(state='normal') 
            
            elif status == 'success':
                if "search" in self.views:
                    self.views["search"].log_message("Pobieranie i zapisywanie zakończone pomyślnie.")
                    self.views["search"].search_button.config(state='normal')
                
                # 🛑 Zmiana: Przekazujemy oba zestawy danych
                self.switch_view(
                    "results", 
                    item_name=result['item_name'], 
                    history_data=result['history_data'],
                    listings_data=result['listings_data']
                )
                
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
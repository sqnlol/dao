import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import threading
import sys 
import time # 🛑 Dodany import time

# Importy z głównego katalogu (za pomocą importu względnego)
from ..steam_market import get_price_history, parse_market_name, get_market_listings 
from .. import database


class SearchView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew") 
        
        self.frame.grid_rowconfigure(3, weight=1) 
        self.frame.grid_columnconfigure(0, weight=1) 

        self.item_name_var = tk.StringVar() 
        
        # Lokalna, filtrowana lista sugestii
        self.suggestions_list = [] 
        
        self._create_widgets()
        
    def _create_widgets(self):
        
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky='new', pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1) 

        ttk.Label(header_frame, text="CS2 Skin Analyzer", font=("Arial", 16, "bold")).pack(side='left', anchor='nw')
        
        self.welcome_label = ttk.Label(header_frame, text=f"Witaj, {self.controller.steam_name}")
        self.welcome_label.pack(side='right', anchor='ne')
        
        ttk.Separator(self.frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=5)

        input_frame = ttk.Frame(self.frame)
        input_frame.grid(row=2, column=0, sticky='ew', pady=(5, 10))
        
        input_frame.grid_columnconfigure(2, weight=1) 

        col = 0
        self.stattrack_var = tk.BooleanVar()
        self.stattrack_check = ttk.Checkbutton(input_frame, text="StatTrak™", variable=self.stattrack_var, onvalue=True, offvalue=False)
        self.stattrack_check.grid(row=0, column=col, padx=(0, 10), sticky='w'); col+=1

        ttk.Label(input_frame, text="Nazwa:").grid(row=0, column=col, padx=(0, 5), sticky='w'); col+=1
        
        self.item_combobox = ttk.Combobox(input_frame, textvariable=self.item_name_var)
        self.item_combobox.grid(row=0, column=col, sticky='ew', padx=5); col+=1
        self.item_combobox.set("AK-47 | Asiimov") 
        
        self.item_combobox.bind('<KeyRelease>', self.autocomplete)


        ttk.Label(input_frame, text="Jakość:").grid(row=0, column=col, padx=(5, 5), sticky='w'); col+=1
        self.wear_options = ["Brak", "(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)"]
        self.wear_combobox = ttk.Combobox(input_frame, values=self.wear_options, width=18, state='readonly')
        self.wear_combobox.grid(row=0, column=col, sticky='e'); col+=1
        self.wear_combobox.current(3) 

        self.search_button = ttk.Button(input_frame, text="Pobierz i zapisz", command=self.start_search_thread, state='normal')
        self.search_button.grid(row=0, column=col, padx=(5, 0), sticky='e'); col+=1

        self.status_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, state='disabled', height=10)
        self.status_text.grid(row=3, column=0, sticky='nsew', pady=(10, 0))
        
        # Logowanie statusu ładowania sugestii
        if not self.controller.all_suggestions:
            self.log_message("Trwa pobieranie pełnej listy przedmiotów z API Steam. Może to chwilę potrwać (1-2 minuty)...")
        else:
            self.set_suggestions(self.controller.all_suggestions)
            self.log_message(f"Autouzupełnianie gotowe ({len(self.suggestions_list)} przedmiotów). Gotowy do wyszukiwania.")


    # ------------------------------------------------------------------
    # METODY AUTOUZUPEŁNIANIA I KOMUNIKACJI
    # ------------------------------------------------------------------
    def autocomplete(self, event):
        """Filtruje lokalną listę sugestii na podstawie tekstu w polu."""
        
        current_text = self.item_name_var.get().strip().lower()
        
        if not self.suggestions_list:
            return 

        if not current_text:
            # Puste pole: wyświetlamy 6 pierwszych
            self.item_combobox['values'] = self.suggestions_list[:6]
        else:
            # Filtrujemy listę, szukając pasujących fragmentów
            matches = [
                name for name in self.suggestions_list
                if current_text in name.lower() 
            ]
            
            self.item_combobox['values'] = matches[:6]
            
            if matches and not self.item_combobox.winfo_ismapped():
                 self.item_combobox.event_generate('<Down>')

    def set_suggestions(self, suggestions):
        """Ustawia listę sugestii po ich załadowaniu z pliku lub API."""
        self.suggestions_list = suggestions
        self.item_combobox['values'] = self.suggestions_list[:6] # Ustawiamy początkowe 6

    def update_welcome_label(self):
        """Aktualizuje powitanie."""
        self.welcome_label.config(text=f"Witaj, {self.controller.steam_name}")

    def log_message(self, text):
        """Dodaje wiadomość do ScrolledText."""
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, text + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

    # ------------------------------------------------------------------
    # METODY WYSZUKIWANIA
    # ------------------------------------------------------------------
    def start_search_thread(self):
        
        base_name = self.item_name_var.get().strip() 
        selected_wear = self.wear_combobox.get()
        is_stattrack = self.stattrack_var.get()
        
        if not base_name:
            self.log_message("BŁĄD: Wpisz bazową nazwę przedmiotu!")
            return
            
        full_name_parts = []
        if is_stattrack:
            full_name_parts.append("StatTrak™")
        full_name_parts.append(base_name)
        if selected_wear != "Brak":
            full_name_parts.append(selected_wear)
            
        item_name = " ".join(full_name_parts)

        self.search_button.config(state='disabled')
        self.log_message(f"Rozpoczynanie pobierania dla: {item_name}...")
        
        login_cookie = self.controller.login_cookie
        
        threading.Thread(target=self._run_search_and_save, args=(item_name, login_cookie,), daemon=True).start()

    def _run_search_and_save(self, item_name, login_cookie):
        """Logika pobierania i zapisywania w wątku."""
        
        # 1. Pobieranie historii cen
        try:
            history = get_price_history(item_name, login_cookie)
            if history is None: 
                self.controller.result_queue.put({'status': 'error', 'message': 'Błąd API podczas pobierania historii. Sprawdź konsolę.'})
                return
            if not history: 
                self.controller.result_queue.put({'status': 'error', 'message': f'Brak danych historycznych dla {item_name}. Pamiętaj, że cookie może być nieaktualne lub przedmiot nie istnieje.'})
                return
        
            self.controller.result_queue.put({'status': 'log', 'message': f'Pobrano {len(history)} rekordów z API.'})

        except Exception as e:
            print(f"Krytyczny błąd w wątku (historia): {e}", file=sys.stderr)
            self.controller.result_queue.put({'status': 'error', 'message': f'Wystąpił krytyczny błąd podczas pobierania historii: {e}'})
            return

        # 🛑 DODANIE PAUZY MIĘDZY ZAPYTANIAMI
        time.sleep(1.5) 

        # 2. Pobieranie aktualnych ofert (Listings)
        try:
            # 🛑 Przekazujemy login_cookie do get_market_listings
            listings_data = get_market_listings(item_name, login_cookie, count=15)
            if listings_data is None:
                self.controller.result_queue.put({'status': 'log', 'message': 'Brak lub błąd pobierania aktualnych ofert rynkowych.'})
                listings_data = {'listings': [], 'total_count': 0, 'lowest_price': "N/A", 'highest_buy_order': "N/A"}
            else:
                self.controller.result_queue.put({'status': 'log', 'message': f'Pobrano {len(listings_data["listings"])} z {listings_data["total_count"]} ofert.'})

        except Exception as e:
            print(f"Krytyczny błąd w wątku (oferty): {e}", file=sys.stderr)
            listings_data = {'listings': [], 'total_count': 0, 'lowest_price': "N/A", 'highest_buy_order': "N/A"}


        # 3. Zapisywanie i przekazywanie danych
        try:
            parsed_name_parts = parse_market_name(item_name)

            records_to_save = []
            for entry in history:
                records_to_save.append({
                    'market_hash_name': item_name,
                    'item_type': parsed_name_parts['type'],
                    'item_name': parsed_name_parts['name'],
                    'item_wear': parsed_name_parts['wear'],
                    'price': entry['price'],
                    'sale_timestamp': entry['sale_timestamp'],
                    'sale_date_str': entry['sale_date_str']
                })
                
            added_count = database.add_sales(records_to_save)
            self.controller.result_queue.put({'status': 'log', 'message': f'Zapisano {added_count} nowych unikalnych rekordów w bazie.'})

            all_db_records = database.get_sales_for_item(item_name)
            
            self.controller.result_queue.put({
                'status': 'success',
                'item_name': item_name,
                'history_data': all_db_records,  
                'listings_data': listings_data    
            })
            
        except Exception as e:
            print(f"Krytyczny błąd w wątku (zapis/przekazanie): {e}", file=sys.stderr)
            self.controller.result_queue.put({'status': 'error', 'message': f'Wystąpił krytyczny błąd: {e}'})
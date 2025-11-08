import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import threading
import sys 
import time 

from src import steam_market
from src import database
from src.skin_list import SKIN_DATA


class SearchView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew") 
        
        self.frame.grid_rowconfigure(3, weight=1) 
        self.frame.grid_columnconfigure(0, weight=1) 

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
        
        input_frame.grid_columnconfigure(1, weight=1)
        input_frame.grid_columnconfigure(3, weight=1)
        
        self.stattrack_var = tk.BooleanVar()
        self.stattrack_check = ttk.Checkbutton(input_frame, text="StatTrak™", variable=self.stattrack_var, onvalue=True, offvalue=False)
        self.stattrack_check.grid(row=0, column=0, padx=(0, 10), pady=5, sticky='w')

        ttk.Label(input_frame, text="Jakość:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky='w')
        self.wear_options = ["(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)", "Brak"]
        self.wear_combobox = ttk.Combobox(input_frame, values=self.wear_options, width=18, state='readonly')
        self.wear_combobox.grid(row=0, column=3, sticky='ew', pady=5)
        self.wear_combobox.set("(Field-Tested)")

        ttk.Label(input_frame, text="Typ broni:").grid(row=1, column=0, padx=(0, 10), pady=5, sticky='w')
        weapon_list = sorted(list(SKIN_DATA.keys()))
        self.weapon_combo = ttk.Combobox(input_frame, values=weapon_list, state='readonly')
        self.weapon_combo.grid(row=1, column=1, sticky='ew', pady=5)
        self.weapon_combo.set("AK-47")

        ttk.Label(input_frame, text="Skin:").grid(row=1, column=2, padx=(10, 5), pady=5, sticky='w')
        self.skin_combo = ttk.Combobox(input_frame, state='disabled')
        self.skin_combo.grid(row=1, column=3, sticky='ew', pady=5)

        self.search_button = ttk.Button(input_frame, text="Pobierz i zapisz", command=self.start_search_thread, state='normal')
        self.search_button.grid(row=0, column=4, rowspan=2, padx=(10, 0), sticky='nsew')
        
        self.weapon_combo.bind("<<ComboboxSelected>>", self.on_weapon_select)

        self.status_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, state='disabled', height=10)
        self.status_text.grid(row=3, column=0, sticky='nsew', pady=(10, 0))
        
        if not self.controller.all_suggestions:
            self.log_message("Gotowy do wyszukiwania. (Autouzupełnianie zostanie naprawione później).")
        
        self.on_weapon_select(None)

    def on_weapon_select(self, event):
        """
        Aktualizuje listę "Skin" ORAZ stan listy "Jakość".
        """
        selected_weapon = self.weapon_combo.get()
        skin_list = SKIN_DATA.get(selected_weapon, [])
        
        if skin_list:
            self.skin_combo.config(state="readonly")
            self.skin_combo['values'] = skin_list
            self.skin_combo.set(skin_list[0])
            self.wear_combobox.config(state="readonly")
            self.wear_combobox.set("(Field-Tested)")
            self.stattrack_check.config(state="normal")
        else:
            self.skin_combo.config(state="disabled")
            self.skin_combo['values'] = []
            self.skin_combo.set("Brak")
            self.wear_combobox.config(state="disabled")
            self.wear_combobox.set("Brak")
            self.stattrack_check.config(state="disabled")
            self.stattrack_var.set(False)

    def update_welcome_label(self):
        self.welcome_label.config(text=f"Witaj, {self.controller.steam_name}")

    def log_message(self, text):
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, text + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

    def start_search_thread(self):
        
        weapon_name = self.weapon_combo.get()
        skin_variant = self.skin_combo.get()
        selected_wear = self.wear_combobox.get()
        is_stattrack = self.stattrack_var.get()
        
        if not weapon_name:
            self.log_message("BŁĄD: Wybierz typ broni!")
            return
            
        full_name_parts = []
        
        if is_stattrack:
            full_name_parts.append("StatTrak™")
        full_name_parts.append(weapon_name)
        if skin_variant and skin_variant != "Brak":
            full_name_parts.append(f"| {skin_variant}")
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
            history = steam_market.get_price_history(item_name, login_cookie)
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

        time.sleep(1.5) 

        # 2. Pobieranie aktualnych ofert (Listings)
        try:
            # Przekazujemy 'login_cookie'
            listings_data = steam_market.get_market_listings(item_name, login_cookie, count=10)
            
            if listings_data is None:
                self.controller.result_queue.put({'status': 'log', 'message': 'Brak lub błąd pobierania aktualnych ofert rynkowych.'})
                listings_data = {'listings': [], 'total_count': 0, 'lowest_price': "N/A"}
            else:
                fetched = len(listings_data.get("listings", []))
                total = listings_data.get("total_count", 0)
                self.controller.result_queue.put({'status': 'log', 'message': f'Pobrano {fetched} z {total} ofert.'})
                meta = listings_data.get('meta') or {}
                pages = meta.get('pages_loaded')
                retries = meta.get('retries')
                if pages is not None or retries is not None:
                    self.controller.result_queue.put({'status': 'log', 'message': f'Metryki: Strony: {pages or 0} | Retry: {retries or 0}.'})
        except Exception as e:
            print(f"Krytyczny błąd w wątku (oferty): {e}", file=sys.stderr)
            listings_data = {'listings': [], 'total_count': 0, 'lowest_price': "N/A", 'highest_buy_order': "N/A"}

        # 3. Zapisywanie i przekazywanie danych
        try:
            parsed_name_parts = steam_market.parse_market_name(item_name)

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
            
            # --- USUNIĘTO BŁĘDNE SORTOWANIE STĄD ---
            
            self.controller.result_queue.put({
                'status': 'success',
                'item_name': item_name,
                'history_data': all_db_records,  # Przekazujemy listę bez sortowania
                'listings_data': listings_data    
            })
            
        except Exception as e:
            print(f"Krytyczny błąd w wątku (zapis/przekazanie): {e}", file=sys.stderr)
            self.controller.result_queue.put({'status': 'error', 'message': f'Wystąpił krytyczny błąd: {e}'})
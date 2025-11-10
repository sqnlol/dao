import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import threading
import sys 
import time 

from src import steam_market
from src import database
from src.skin_list import SKIN_DATA, WEAPON_CATEGORIES


class SearchView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew") 
        
        self.frame.grid_rowconfigure(3, weight=1) 
        self.frame.grid_columnconfigure(0, weight=1) 

        self._create_widgets()
        
    def _create_widgets(self):
        # Ustaw styl ciemny dla kilku elementów
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('Dark.TFrame', background='#2E2E2E')
        style.configure('Dark.TLabel', background='#2E2E2E', foreground='white')
        style.configure('Dark.TButton', background='#3A3A3A', foreground='white')
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky='new', pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1) 

        left_header_group = ttk.Frame(header_frame, style='Dark.TFrame')
        left_header_group.pack(side='left', anchor='nw')
        ttk.Label(left_header_group, text="CS2 Skin Analyzer", font=("Arial", 16, "bold"), style='Dark.TLabel').pack(side='left')

        # Prawa strona nagłówka: przycisk Wyloguj (skrajnie po prawej),
        # po jego lewej komunikat o braku cookie, a jeszcze bardziej po lewej etykieta powitania
        right_header_group = ttk.Frame(header_frame)
        right_header_group.pack(side='right', anchor='ne')
        # Użyj grid wewnątrz grupy, aby precyzyjnie ustawić kolejność: [cookie msg] [Wyloguj] [Witaj, X]
        right_header_group.grid_columnconfigure(0, weight=0)
        right_header_group.grid_columnconfigure(1, weight=0)
        right_header_group.grid_columnconfigure(2, weight=0)

        # Komunikat o braku cookie (szary) – po lewej od Wyloguj
        self.cookie_mode_label = ttk.Label(right_header_group, text="Brak Cookie - funkcjonalność ograniczona", foreground='gray')
        self.cookie_mode_label.grid(row=0, column=0, padx=(0, 12))

        # Przycisk Wyloguj (środek)
        self.logout_button = ttk.Button(right_header_group, text="Wyloguj", command=self._go_back_to_login)
        self.logout_button.grid(row=0, column=1, padx=(0, 12))

        # Etykieta powitania (skrajnie prawa kolumna)
        self.welcome_label = ttk.Label(right_header_group, text=f"Witaj, {self.controller.steam_name}")
        self.welcome_label.grid(row=0, column=2, sticky='e')
        
        ttk.Separator(self.frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=5)

        input_frame = ttk.Frame(self.frame)
        input_frame.grid(row=2, column=0, sticky='ew', pady=(5, 10))
        
        input_frame.grid_columnconfigure(1, weight=1)
        input_frame.grid_columnconfigure(3, weight=1)
        
        self.stattrack_var = tk.BooleanVar()
        self.stattrack_check = ttk.Checkbutton(input_frame, text="StatTrak™", variable=self.stattrack_var, onvalue=True, offvalue=False)
        self.stattrack_check.grid(row=0, column=0, padx=(0, 10), pady=5, sticky='w')
        # Jakość (przeniesiona do wiersza 1, wyrównana z kategorią broni)
        ttk.Label(input_frame, text="Jakość:").grid(row=1, column=2, padx=(10, 5), pady=5, sticky='w')
        self.wear_options = ["(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)", "Brak"]
        self.wear_combobox = ttk.Combobox(input_frame, values=self.wear_options, width=18, state='readonly')
        self.wear_combobox.grid(row=1, column=3, sticky='ew', pady=5)
        self.wear_combobox.set("(Field-Tested)")

        # Kategoria broni (np. Karabiny, Pistolety, Noże)
        ttk.Label(input_frame, text="Kategoria broni:").grid(row=1, column=0, padx=(0, 10), pady=5, sticky='w')
        categories = sorted(list(WEAPON_CATEGORIES.keys()))
        self.category_combo = ttk.Combobox(input_frame, values=categories, state='readonly')
        self.category_combo.grid(row=1, column=1, sticky='ew', pady=5)
        if categories:
            self.category_combo.set(categories[0])

        # Typ broni (filtrowane przez wybraną kategorię)
        ttk.Label(input_frame, text="Typ broni:").grid(row=2, column=0, padx=(0, 10), pady=5, sticky='w')
        weapon_list = sorted(list(SKIN_DATA.keys()))
        # default readonly; for 'Noże' category we'll make it editable and blank
        self.weapon_combo = ttk.Combobox(input_frame, values=weapon_list, state='readonly')
        self.weapon_combo.grid(row=2, column=1, sticky='ew', pady=5)

        # Skin (wyrównany do Typ broni w tym samym wierszu)
        ttk.Label(input_frame, text="Skin:").grid(row=2, column=2, padx=(10, 5), pady=5, sticky='w')
        self.skin_combo = ttk.Combobox(input_frame, state='disabled')
        self.skin_combo.grid(row=2, column=3, sticky='ew', pady=5)
        self.skin_combo.bind("<<ComboboxSelected>>", self.on_skin_select)

        # Przycisk wyszukiwania po prawej stronie, zasięg na 3 wiersze
        self.search_button = ttk.Button(input_frame, text="Pobierz i zapisz", command=self.start_search_thread, state='normal')
        self.search_button.grid(row=0, column=4, rowspan=3, padx=(10, 0), sticky='nsew')
        
        self.weapon_combo.bind("<<ComboboxSelected>>", self.on_weapon_select)
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_select)

        # Dodatkowy pasek informacyjny (ciemny) pod nagłówkiem
        info_frame = ttk.Frame(self.frame, style='Dark.TFrame')
        info_frame.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        info_frame.grid_columnconfigure(0, weight=1)
        # Aktualizacja wersji aplikacji wyświetlanej w pasku informacyjnym
        self.version_label = ttk.Label(info_frame, text="Wersja: 0.4.5", style='Dark.TLabel')
        self.version_label.pack(side='left', padx=8)
        self.suggestions_label = ttk.Label(info_frame, text="Sugestie: ładowanie...", style='Dark.TLabel')
        self.suggestions_label.pack(side='left', padx=8)
        ttk.Button(info_frame, text="Odśwież autouzupełnianie", command=self._refresh_suggestions, style='Dark.TButton').pack(side='right', padx=8)

        self.status_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, state='disabled', height=10)
        self.status_text.grid(row=3, column=0, sticky='nsew', pady=(10, 0))
        # Kontrolki pobierania sugestii (aktualizacja + anulowanie)
        suggestions_controls = ttk.Frame(self.frame)
        suggestions_controls.grid(row=4, column=0, sticky='ew', pady=(6, 0))
        # 3 kolumny: [0]=Aktualizuj, [1]=etykieta postępu (rozszerza się), [2]=Przerwij
        suggestions_controls.grid_columnconfigure(1, weight=1)
        # Przycisk aktualizacji listy przedmiotów (on-demand)
        self.update_btn = ttk.Button(suggestions_controls, text="Zaktualizuj listę przedmiotów", command=self._update_suggestions)
        self.update_btn.grid(row=0, column=0, sticky='w')
        # Etykieta postępu między przyciskami
        self.inline_progress_var = tk.StringVar(value="")
        self.inline_progress_label = ttk.Label(suggestions_controls, textvariable=self.inline_progress_var, anchor='center')
        self.inline_progress_label.grid(row=0, column=1, sticky='ew', padx=8)
        # Przycisk anulowania pobierania (na starcie wyłączony)
        self.cancel_btn = ttk.Button(suggestions_controls, text="Przerwij", command=self._cancel_update, state='disabled')
        self.cancel_btn.grid(row=0, column=2, padx=(12,0))
        # Pasek postępu pobierania (ukryty na starcie)
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(self.frame, orient='horizontal', mode='determinate', maximum=100, variable=self.progress_var)
        self.progress_bar.grid(row=5, column=0, sticky='ew', pady=(4, 0))
        self.progress_bar.grid_remove()
        
        if not self.controller.all_suggestions:
            self.log_message("Gotowy do wyszukiwania. (Lista przedmiotów do pobrania przyciskiem).")

        # Wypełnij listę broni według wybranej kategorii
        self.on_category_select(None)

    def on_weapon_select(self, event):
        """
        Aktualizuje listę "Skin" ORAZ stan listy "Jakość".
        """
        selected_weapon = self.weapon_combo.get()
        skin_list = SKIN_DATA.get(selected_weapon, [])

        knife_models = {
            "Bayonet", "M9 Bayonet", "Karambit", "Flip Knife", "Gut Knife",
            "Huntsman Knife", "Falchion Knife", "Bowie Knife", "Shadow Daggers",
            "Navaja Knife", "Stiletto Knife", "Talon Knife", "Ursus Knife",
            "Classic Knife", "Paracord Knife", "Survival Knife", "Nomad Knife",
            "Skeleton Knife", "Butterfly Knife", "Kukri Knife"
        }
        is_knife = selected_weapon in knife_models

        if is_knife:
            # Dla noży pozwól na opcję "Vanilla" (goły nóż) jako pierwszy wybór
            values = ["Vanilla"] + list(skin_list)
            self.skin_combo.config(state="readonly")
            self.skin_combo['values'] = values
            self.skin_combo.set("Vanilla")
            # Vanilla nóż nie ma wear w nazwie – wyłącz wybór wear domyślnie
            self.wear_combobox.config(state="disabled")
            self.wear_combobox.set("Brak")
            self.stattrack_check.config(state="normal")
        else:
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

    def on_skin_select(self, event):
        """Dostosuj możliwość wyboru wear dla noży w zależności od tego, czy skin to 'Brak'."""
        try:
            selected_weapon = self.weapon_combo.get()
            selected_skin = self.skin_combo.get()
            knife_models = {
                "Bayonet", "M9 Bayonet", "Karambit", "Flip Knife", "Gut Knife",
                "Huntsman Knife", "Falchion Knife", "Bowie Knife", "Shadow Daggers",
                "Navaja Knife", "Stiletto Knife", "Talon Knife", "Ursus Knife",
                "Classic Knife", "Paracord Knife", "Survival Knife", "Nomad Knife",
                "Skeleton Knife", "Butterfly Knife", "Kukri Knife"
            }
            if selected_weapon in knife_models:
                if selected_skin.lower() == "vanilla":
                    self.wear_combobox.config(state="disabled")
                    self.wear_combobox.set("Brak")
                else:
                    self.wear_combobox.config(state="readonly")
                    if self.wear_combobox.get() == "Brak":
                        self.wear_combobox.set("(Field-Tested)")
        except Exception:
            pass

    def on_category_select(self, event):
        """
        Aktualizuje listę typów broni (weapon_combo) na podstawie wybranej kategorii.
        Jeśli kategoria jest pusta lub nie zawiera wpisów, pokaż wszystkie dostępne typy.
        """
        selected_cat = self.category_combo.get() if hasattr(self, 'category_combo') else None
        weapons = []
        if selected_cat:
            weapons = WEAPON_CATEGORIES.get(selected_cat, [])

        # Jeśli kategoria to Noże -> pozostaw pole 'Typ broni' puste i edytowalne (użytkownik wpisuje sam nazwe noża)
        if selected_cat == 'Noże':
            # Wyczyść listę wartości i pozwól wpisywać (state normal)
            self.weapon_combo.config(state='normal')
            self.weapon_combo['values'] = []
            try:
                self.weapon_combo.set('')
            except Exception:
                pass
            # wyłącz listę skinów — użytkownik wpisuje pełną nazwę (np. "★ Karambit | Doppler (Factory New)")
            self.skin_combo.config(state='disabled')
            self.skin_combo['values'] = []
            self.skin_combo.set('')
            # Ustaw stattrak/ wear dostępne
            self.wear_combobox.config(state='readonly')
            self.stattrack_check.config(state='normal')
            return

        if not weapons:
            # pokaż wszystkie dostępne typy
            weapons = sorted(list(SKIN_DATA.keys()))

        # filtruj tylko te, które istnieją w SKIN_DATA
        weapons = [w for w in weapons if w in SKIN_DATA]
        weapons = sorted(weapons)

        if weapons:
            self.weapon_combo.config(state='readonly')
            self.weapon_combo['values'] = weapons
            # ustaw domyślnie pierwszy element jeśli aktualnie nie ma wartości
            try:
                current = self.weapon_combo.get()
            except Exception:
                current = ''
            if not current or current not in weapons:
                self.weapon_combo.set(weapons[0])
        else:
            self.weapon_combo.config(state='disabled')
            self.weapon_combo['values'] = []
            self.weapon_combo.set('')

        # Zaktualizuj listę skinów dla aktualnie wybranej broni
        self.on_weapon_select(None)

    def update_welcome_label(self):
        # Aktualizuj etykietę powitania
        self.welcome_label.config(text=f"Witaj, {self.controller.steam_name}")
        # Pokaż/ukryj komunikat o braku cookie
        has_cookie = bool(getattr(self.controller, 'login_cookie', None))
        try:
            if has_cookie:
                # Ukryj etykietę o braku cookie, ale zachowaj layout grid
                if self.cookie_mode_label.winfo_ismapped():
                    self.cookie_mode_label.grid_remove()
            else:
                # Pokaż ponownie w tej samej komórce (row=0, col=0)
                if not self.cookie_mode_label.winfo_ismapped():
                    self.cookie_mode_label.grid()
        except Exception:
            pass

    def set_suggestions(self, suggestions):
        """Ustawia listę sugestii po pobraniu; aktualizuje etykietę i log."""
        try:
            self.controller.all_suggestions = suggestions or []
            self.suggestions_label.config(text=f"Sugestie: {len(self.controller.all_suggestions)}")
            self.log_message(f"Autouzupełnianie załadowane ({len(self.controller.all_suggestions)} pozycji).")
        except Exception as e:
            print(f"Błąd podczas ustawiania sugestii: {e}", file=sys.stderr)

    def _refresh_suggestions(self):
        """Uruchamia odświeżenie autouzupełniania przez kontroler w tle."""
        try:
            self.log_message("Uruchamianie odświeżania autouzupełniania...")
            if hasattr(self.controller, '_fetch_suggestions_async'):
                self.controller._fetch_suggestions_async()
                self.log_message("Pobieranie sugestii uruchomione w tle.")
            else:
                self.log_message("FUNKCJA: brak mechanizmu odświeżania w kontrolerze.")
        except Exception as e:
            self.log_message(f"Błąd podczas odświeżania sugestii: {e}")

    def _update_suggestions(self):
        """Rozpoczyna asynchroniczne pobieranie listy przedmiotów (wznowienie jeśli przerwane)."""
        try:
            self.log_message("Start aktualizacji listy przedmiotów...")
            # zresetuj i pokaż progressbar, zablokuj przycisk
            self.set_update_button_state(active=False)
            self.set_cancel_button_state(active=True)
            self.show_progress_bar(True)
            self.update_progress_bar(0, 0, 0)
            self.controller.update_suggestions_async()
        except Exception as e:
            print(f"Błąd aktualizacji sugestii: {e}", file=sys.stderr)
            self.log_message(f"BŁĄD: {e}")
            self.set_update_button_state(active=True)
            self.show_progress_bar(False)

    # API wywoływane przez kontroler: ustaw/zdjęcie blokady przycisku
    def set_update_button_state(self, active: bool):
        try:
            self.update_btn.config(state=('normal' if active else 'disabled'))
        except Exception:
            pass

    # API wywoływane przez kontroler: włącz/wyłącz przycisk anulowania
    def set_cancel_button_state(self, active: bool):
        try:
            self.cancel_btn.config(state=('normal' if active else 'disabled'))
        except Exception:
            pass

    # API wywoływane przez kontroler: aktualizacja paska postępu
    def update_progress_bar(self, current: int, total: int, retries: int, eta: int = -1):
        try:
            if total and total > 0:
                percent = max(0, min(100, int((current / float(total)) * 100)))
                self.progress_bar.config(mode='determinate', maximum=100)
                self.progress_var.set(percent)
            else:
                # nieznane total -> tryb indeterminate
                self.progress_bar.config(mode='indeterminate')
                self.progress_bar.start(80)
            self.show_progress_bar(True)
            # log bardziej czytelny dla retries
            # Sformatuj ETA jako HH:MM:SS
            if eta is None or eta < 0:
                eta_hms = "??:??:??"
            else:
                hours = eta // 3600
                minutes = (eta % 3600) // 60
                seconds = eta % 60
                eta_hms = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            # Ustaw etykietę postępu między przyciskami
            total_disp = (str(total) if (isinstance(total, int) and total > 0) else "?")
            self.inline_progress_var.set(f"[Postęp: {current} / {total_disp} | ETA: {eta_hms}]")
            # Nie logujemy postępu do logów – etykieta między przyciskami wystarcza
        except Exception:
            pass

    def show_progress_bar(self, visible: bool):
        try:
            if visible:
                self.progress_bar.grid()
            else:
                if self.progress_bar['mode'] == 'indeterminate':
                    self.progress_bar.stop()
                self.progress_bar.grid_remove()
        except Exception:
            pass

    def _cancel_update(self):
        """Wywołuje anulowanie pobierania sugestii po stronie kontrolera."""
        try:
            self.set_cancel_button_state(False)
            self.log_message("Żądanie anulowania wysłane...")
            if hasattr(self.controller, 'cancel_suggestions_fetch'):
                self.controller.cancel_suggestions_fetch()
            # Natychmiast ukryj pasek postępu i wyczyść etykietę między przyciskami
            self.show_progress_bar(False)
            self.clear_inline_progress()
        except Exception as e:
            print(f"Błąd anulowania: {e}", file=sys.stderr)

    # Pomocnicze API do czyszczenia etykiety postępu
    def clear_inline_progress(self):
        try:
            self.inline_progress_var.set("")
        except Exception:
            pass

    def _go_back_to_login(self):
        """Przełącza do ekranu logowania z zachowaniem obecnego cookie w polu, umożliwiając jego zmianę."""
        try:
            current_cookie = getattr(self.controller, 'login_cookie', '') or ''
            self.controller.switch_view('login')
            # wypełnij pole cookie jeśli login_view istnieje i ma cookie_entry
            login_view = self.controller.views.get('login')
            if login_view and hasattr(login_view, 'cookie_entry'):
                login_view.cookie_entry.delete(0, tk.END)
                login_view.cookie_entry.insert(0, current_cookie)
                login_view.login_status.config(text="Możesz zmienić wartość steamLoginSecure i ponownie połączyć.", foreground='gray')
        except Exception as e:
            print(f"Błąd powrotu do ekranu logowania: {e}", file=sys.stderr)

    def log_message(self, text):
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, text + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

    def start_search_thread(self):
        weapon_name = self.weapon_combo.get().strip()
        skin_variant = self.skin_combo.get().strip()
        selected_wear = self.wear_combobox.get().strip()
        is_stattrack = self.stattrack_var.get()

        if not weapon_name:
            self.log_message("BŁĄD: Wybierz typ broni!")
            return

        # Specjalne budowanie nazwy dla noży: "★ StatTrak™ <Nóż> | <Skin> (Wear)"
        is_knife = weapon_name in {
            "Bayonet", "M9 Bayonet", "Karambit", "Flip Knife", "Gut Knife",
            "Huntsman Knife", "Falchion Knife", "Bowie Knife", "Shadow Daggers",
            "Navaja Knife", "Stiletto Knife", "Talon Knife", "Ursus Knife",
            "Classic Knife", "Paracord Knife", "Survival Knife", "Nomad Knife",
            "Skeleton Knife", "Butterfly Knife"
        }

        parts = []
        if is_knife:
            parts.append("★")
            if is_stattrack:
                parts.append("StatTrak™")
            parts.append(weapon_name)
            # Noże: 'vanilla' traktujemy jak brak skina (bez separatora)
            if skin_variant and skin_variant.lower() != "vanilla":
                parts.append("|")
                parts.append(skin_variant)
            # Wear tylko jeśli jest skin (nie dla vanilla)
            if selected_wear != "Brak" and skin_variant and skin_variant.lower() != "vanilla":
                parts.append(selected_wear)
        else:
            if is_stattrack:
                parts.append("StatTrak™")
            parts.append(weapon_name)
            if skin_variant and skin_variant != "Brak":
                parts.append("|")
                parts.append(skin_variant)
            if selected_wear != "Brak":
                parts.append(selected_wear)

        item_name = " ".join(parts)

        self.search_button.config(state='disabled')
        # Komunikat o trybie
        if not getattr(self.controller, 'login_cookie', None):
            self.log_message(f"Tryb bez cookie – historia cen będzie niedostępna dla: {item_name}.")
        else:
            self.log_message(f"Rozpoczynanie pobierania dla: {item_name}...")
        
        login_cookie = self.controller.login_cookie
        
        threading.Thread(target=self._run_search_and_save, args=(item_name, login_cookie,), daemon=True).start()

    def _run_search_and_save(self, item_name, login_cookie):
        """Logika pobierania i zapisywania w wątku."""
        
        # 1. Pobieranie historii cen (tylko z cookie)
        try:
            if login_cookie:
                history = steam_market.get_price_history(item_name, login_cookie)
                if history is None:
                    self.controller.result_queue.put({'status': 'error', 'message': 'Błąd API podczas pobierania historii. Sprawdź konsolę.'})
                    return
                if not history:
                    self.controller.result_queue.put({'status': 'log', 'message': f'Brak danych historycznych dla {item_name}.'})
                else:
                    self.controller.result_queue.put({'status': 'log', 'message': f'Pobrano {len(history)} rekordów z API.'})
            else:
                history = []
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
                
            added_count = database.add_sales(records_to_save) if records_to_save else 0
            if added_count:
                self.controller.result_queue.put({'status': 'log', 'message': f'Zapisano {added_count} nowych unikalnych rekordów w bazie.'})

            all_db_records = database.get_sales_for_item(item_name)
            
            # --- USUNIĘTO BŁĘDNE SORTOWANIE STĄD ---
            
            self.controller.result_queue.put({
                'status': 'success',
                'item_name': item_name,
                'history_data': all_db_records,  # Przekazujemy listę bez sortowania
                'listings_data': listings_data,
                # Pobierz URL obrazka (jeśli dostępny) i przekaż dalej; nie blokujemy krytycznie jeśli brak
                'image_url': steam_market.get_item_image_url(item_name, login_cookie)
            })
            
        except Exception as e:
            print(f"Krytyczny błąd w wątku (zapis/przekazanie): {e}", file=sys.stderr)
            self.controller.result_queue.put({'status': 'error', 'message': f'Wystąpił krytyczny błąd: {e}'})
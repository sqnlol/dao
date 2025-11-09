import tkinter as tk
from tkinter import ttk
from src import steam_market
import sys
import operator # do sortowania listy
import datetime
from collections import defaultdict

# --- IMPORTY DLA WYKRESU (prosta wersja) ---
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
# --- KONIEC IMPORTÓW ---


class ResultsView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew") 
        self.frame.grid_rowconfigure(2, weight=1) 
        self.frame.grid_columnconfigure(0, weight=1) 

        # Dane do wyświetlenia
        self.current_item_name = ""
        self.history_data = []
        self.listings_data = {}
        # Stan sortowania historii (True = podstawowy kierunek: cena rosnąco, data malejąco -> najnowsze)
        self._history_sort_states = {
            'price': True,           # True => ascending, False => descending
            'sale_timestamp': True   # True => newest first (descending), False => oldest first (ascending)
        }
        self._history_last_sorted = None
        # Paginacja ofert
        self.page_size = 10
        self.current_page = 0  # indeks strony (0-based)
        self._all_listings = []  # pełna lista do paginacji
        self._page_cache = {}  # page_idx -> list of listings
        self._pages_loading = set()
        self._cache_item_key = None  # identyfikator aktualnego przedmiotu dla cache
        self._total_count = 0
        # stały rozmiar okna z listą, aby uniknąć skoków i umożliwić overlay
        self._listings_width = 780
        self._listings_height = 320
        self._overlay_canvas = None
        self._overlay_stipple = "gray50"  # intensywność bluru: gray12 (lekki) / gray50 (mocny)

        self._create_widgets()
        
    def _create_widgets(self):
        # 1. Nagłówek i przycisk powrotu
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky='new', pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1) 

        self.back_button = ttk.Button(header_frame, text="< Wyszukiwanie", command=lambda: self.controller.switch_view("search"))
        self.back_button.grid(row=0, column=0, sticky='w')

        self.title_label = ttk.Label(header_frame, text="[Nazwa Przedmiotu]", font=("Arial", 16, "bold"))
        self.title_label.grid(row=0, column=1, padx=10, sticky='w')
        # miejsce na obrazek przedmiotu w prawym górnym rogu
        header_frame.grid_columnconfigure(2, weight=0)
        self._header_image_label = tk.Label(header_frame, bd=0)
        self._header_image_label.grid(row=0, column=2, sticky='e')
        self._current_item_image = None
        
        ttk.Separator(self.frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=5)
        
        # 2. Główna przewijana sekcja
        self.main_content_frame = ttk.Frame(self.frame)
        self.main_content_frame.grid(row=2, column=0, sticky='nsew')
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)

        self.scrollable_content = tk.Canvas(self.main_content_frame, bd=0, highlightthickness=0)
        self.scrollable_content.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(self.main_content_frame, orient="vertical", command=self.scrollable_content.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.scrollable_content.configure(yscrollcommand=self.scrollbar.set)
        
        self.inner_frame = ttk.Frame(self.scrollable_content, padding="5")
        self.scrollable_content.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        self.inner_frame.bind("<Configure>", lambda e: self.scrollable_content.configure(scrollregion=self.scrollable_content.bbox("all")))
        self.inner_frame.grid_columnconfigure(0, weight=1)
        
        # --- SEKCJA WYKRESU (PROSTA WERSJA) ---
        self.chart_section = ttk.LabelFrame(self.inner_frame, text="📈 Wykres Cenowy")
        self.chart_section.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.chart_section.grid_columnconfigure(0, weight=1)
        self._create_chart_widgets(self.chart_section)
        
    # Sekcja Ofert
        self.listings_section = ttk.LabelFrame(self.inner_frame, text="📊 Aktualne Oferty Rynkowe")
        self.listings_section.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.listings_section.grid_columnconfigure(0, weight=1)
        
        # Sekcja Podsumowania
        self.summary_section = ttk.LabelFrame(self.inner_frame, text="📜 Podsumowanie Historyczne")
        self.summary_section.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.summary_section.grid_columnconfigure(0, weight=1)

        # Sekcja Tabeli Historii
        self.history_table_section = ttk.LabelFrame(self.inner_frame, text="⏳ Szczegóły Transakcji Historycznych")
        self.history_table_section.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        self.history_table_section.grid_columnconfigure(0, weight=1)
        
        self.history_expanded = tk.BooleanVar(value=False)
        self.history_toggle_button = ttk.Button(self.history_table_section, text="Rozwiń Tabela Danych", command=self._toggle_history_table)
        self.history_toggle_button.pack(pady=5, padx=5, fill='x')
        
        self.history_tree = self._create_history_treeview(self.history_table_section)
        
        
    def _clear_sections(self):
        """Czyści dynamiczną zawartość sekcji przed nowym wynikiem."""
        
        if hasattr(self, 'ax'):
            self.ax.clear()
            self.chart_canvas.draw()
        
        for widget in self.listings_section.winfo_children():
            widget.destroy()
            
        for widget in self.summary_section.winfo_children():
            widget.destroy()
            
        self.history_tree.delete(*self.history_tree.get_children())
        self.history_tree.pack_forget() 
        self.history_expanded.set(False)
        self.history_toggle_button.config(text="Rozwiń Tabela Danych")
        self.history_toggle_button.pack(pady=5, padx=5, fill='x')

    # ------------------------------------------------------------------
    # --- FUNKCJE DLA WYKRESU (PROSTA WERSJA) ---
    # ------------------------------------------------------------------

    def _create_chart_widgets(self, master):
        """Tworzy płótno Matplotlib i przyciski filtrowania."""
        
        button_frame = ttk.Frame(master)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="Tydzień", command=lambda: self._plot_chart('week')).pack(side='left', padx=2)
        ttk.Button(button_frame, text="Miesiąc", command=lambda: self._plot_chart('month')).pack(side='left', padx=2)
        ttk.Button(button_frame, text="Ogółem", command=lambda: self._plot_chart('all')).pack(side='left', padx=2)

        # Czarne tło
        self.fig = Figure(figsize=(8, 3), dpi=100)
        self.fig.patch.set_facecolor('#2E2E2E')

        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1C1C1C')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.yaxis.label.set_color('white')
        self.ax.xaxis.label.set_color('white')
        self.ax.title.set_color('white')

        for spine in self.ax.spines.values():
            spine.set_edgecolor('white')

    # (Obrazek zostanie wyświetlany w nagłówku jako header image)

        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=master)
        self.chart_canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)
        self.chart_canvas.draw()

    def _plot_chart(self, time_range='all'):
        """Wersja Opcja A: Rysuje każdą pojedynczą transakcję."""
        
        if not self.history_data:
            self.ax.clear()
            self.ax.text(0.5, 0.5, 'Brak danych historycznych', 
                         horizontalalignment='center', verticalalignment='center', 
                         transform=self.ax.transAxes, color='white')
            self.chart_canvas.draw()
            return
            
        now = datetime.datetime.now()
        limit_date = None
        
        if time_range == 'week':
            limit_date = now - datetime.timedelta(days=7)
        elif time_range == 'month':
            limit_date = now - datetime.timedelta(days=30)
        
        x_dates = []
        y_prices = []
        
        try:
            for record in self.history_data:
                record_date = datetime.datetime.fromtimestamp(record['sale_timestamp'])
                if time_range == 'all':
                    x_dates.append(record_date)
                    y_prices.append(record['price'])
                elif limit_date is not None and record_date > limit_date:
                    x_dates.append(record_date)
                    y_prices.append(record['price'])
        except Exception as e:
            print(f"Błąd przetwarzania daty dla wykresu: {e}", file=sys.stderr)
            return

        if not x_dates:
            self.ax.clear()
            self.ax.text(0.5, 0.5, f'Brak danych historycznych dla zakresu: {time_range}', 
                         horizontalalignment='center', verticalalignment='center', 
                         transform=self.ax.transAxes, color='white')
            self.chart_canvas.draw()
            return

        self.ax.clear()
        
        # --- KLUCZOWA ZMIANA ---
        # Zmieniono 'o' (kropki) na '.-' (linia z kropkami)
        self.ax.plot(x_dates, y_prices, '.-', markersize=4, color='#3498db', alpha=0.7)
        # --- KONIEC ZMIANY ---
        
        self.ax.set_title(f"Historia transakcji ({time_range})", color='white')
        self.ax.set_ylabel("Cena (PLN)", color='white')
        self.ax.grid(True, linestyle='--', alpha=0.2, color='white')
        
        self.fig.autofmt_xdate()
        date_format = mdates.DateFormatter('%Y-%m-%d')
        self.ax.xaxis.set_major_formatter(date_format)
        
        self.ax.set_facecolor('#1C1C1C')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('white')
        
        self.chart_canvas.draw()
        
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))

    # ------------------------------------------------------------------
    # FUNKCJE BUDOWANIA WIDOKU (BEZ ZMIAN)
    # ------------------------------------------------------------------
    def _create_history_treeview(self, parent_frame):
        # Wersja bez 'quantity'
        columns = ("Typ", "Jakość", "Skórka", "Cena", "Data")
        tree = ttk.Treeview(parent_frame, columns=columns, show='headings', height=10)
        
        tree.column("Typ", width=80, anchor=tk.W)
        tree.column("Jakość", width=100, anchor=tk.W)
        tree.column("Skórka", width=250, anchor=tk.W)
        tree.column("Cena", width=100, anchor=tk.E)
        tree.column("Data", width=150, anchor=tk.W)

        tree.heading("Typ", text="Typ")
        tree.heading("Jakość", text="Jakość")
        tree.heading("Skórka", text="Nazwa skórki")
        tree.heading("Cena", text="Cena Sprzedaży", command=lambda: self._sort_history('price'))
        tree.heading("Data", text="Data Sprzedaży", command=lambda: self._sort_history('sale_timestamp'))
        
        return tree
        
    def _fill_listings(self):
        for widget in self.listings_section.winfo_children():
            widget.destroy()
        # Ustal cache i bieżącą stronę/dane
        if not self._page_cache:
            initial = self.listings_data.get('listings', [])
            self._page_cache[0] = initial
            self._all_listings = initial
        else:
            self._all_listings = self._page_cache.get(self.current_page, [])
        # Używaj bieżącej wartości z listings_data aby uniknąć rozjazdu z etykietami/metadanymi
        total_count = self.listings_data.get('total_count', len(self._all_listings))

        info_frame = ttk.Frame(self.listings_section)
        info_frame.pack(fill='x', padx=5, pady=5)

        if total_count == 0 or not self._all_listings:
            ttk.Label(info_frame, text="⛔ Brak aktualnych ofert sprzedaży na rynku.", foreground='red').pack(fill='x')
            # Pokaż ostatnią zarejestrowaną sprzedaż z historii, jeśli dostępna
            try:
                if self.history_data:
                    latest_sale = max(self.history_data, key=lambda r: r.get('sale_timestamp', 0))
                    sale_date = latest_sale.get('sale_date_str', '-')
                    sale_price = latest_sale.get('price', None)
                    if sale_price is not None:
                        ttk.Label(info_frame, text=f"Ostatnia sprzedaż: {sale_date}, cena: {sale_price:.2f} PLN", foreground='gray').pack(anchor='w')
                    else:
                        ttk.Label(info_frame, text=f"Ostatnia sprzedaż: {sale_date}", foreground='gray').pack(anchor='w')
                else:
                    ttk.Label(info_frame, text="Brak danych o ostatniej sprzedaży.", foreground='gray').pack(anchor='w')
            except Exception as e:
                print(f"Błąd prezentacji ostatniej sprzedaży: {e}", file=sys.stderr)
            return

        ttk.Label(info_frame, text=f"Łącznie ofert: {total_count}.").pack(anchor='w')
        lp = self.listings_data.get('lowest_price')
        lp_float = self.listings_data.get('lowest_price_float')
        if lp_float is not None:
            ttk.Label(info_frame, text=f"Najniższa oferta: {lp_float:.2f} PLN", foreground='green').pack(anchor='w')
        elif lp:
            ttk.Label(info_frame, text=f"Najniższa oferta: {lp}", foreground='green').pack(anchor='w')

        # Nawigacja stron
        nav_frame = ttk.Frame(self.listings_section)
        nav_frame.pack(fill='x', padx=5)
        first_btn = ttk.Button(nav_frame, text="⏮ Pierwsza", command=lambda: self._goto_page(0))
        prev_btn = ttk.Button(nav_frame, text="◀ Poprzednie", command=self._prev_page)
        next_btn = ttk.Button(nav_frame, text="Następne ▶", command=self._next_page)
        last_btn = ttk.Button(nav_frame, text="Ostatnia ⏭", command=self._goto_last_page)
        first_btn.pack(side='left')
        prev_btn.pack(side='left', padx=(5,0))
        last_btn.pack(side='right')
        next_btn.pack(side='right', padx=(0,5))
        self.page_label = ttk.Label(nav_frame, text="Strona 1")
        self.page_label.pack(side='top', pady=2)

        ttk.Separator(self.listings_section, orient='horizontal').pack(fill='x', padx=5, pady=4)
        # Stały obszar listy ofert + overlay
        container = tk.Frame(self.listings_section, width=self._listings_width, height=self._listings_height)
        container.pack_propagate(False)
        container.pack(fill='x', padx=5)
        listings_frame = ttk.Frame(container)
        listings_frame.pack(fill='both', expand=True)
        # zapamiętaj kontener do overlay
        self._listings_container = container
        listings_frame.grid_columnconfigure(0, weight=1)
        listings_frame.grid_columnconfigure(1, weight=1)
        listings_frame.grid_columnconfigure(2, weight=1)
        ttk.Label(listings_frame, text="Lp.", font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=5, sticky='w')
        ttk.Label(listings_frame, text="Cena Końcowa", font=('Arial', 9, 'bold')).grid(row=0, column=1, padx=5, sticky='e')
        ttk.Label(listings_frame, text="Prowizja Steam", font=('Arial', 9, 'bold')).grid(row=0, column=2, padx=5, sticky='e')

        self._render_current_page_rows(listings_frame)
        # Prefetch kolejnej strony jeśli istnieje
        self._maybe_prefetch_next()
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))

    def _maybe_prefetch_next(self):
        """Prefetch kolejnej strony jeśli jej nie ma w cache i istnieje."""
        try:
            item_key = self._cache_item_key or self.current_item_name
            total_count = self.listings_data.get('total_count', 0)
            next_start = (self.current_page + 1) * self.page_size
            if next_start >= total_count:
                return
            next_page = self.current_page + 1
            if next_page in self._page_cache or next_page in self._pages_loading:
                return
            self._pages_loading.add(next_page)
            def worker():
                data = steam_market.get_market_listings_page(self.current_item_name, self.controller.login_cookie, start=next_start, count=self.page_size)
                # Zapis tylko jeśli nadal oglądamy ten sam przedmiot
                if data and data.get('listings') and self._cache_item_key == item_key:
                    self._page_cache[next_page] = data['listings']
                    try:
                        self.controller.result_queue.put({'status': 'log', 'message': f'Prefetch: strona {next_page + 1} gotowa.'})
                    except Exception:
                        pass
                self._pages_loading.discard(next_page)
            import threading
            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            print(f"Prefetch błąd: {e}", file=sys.stderr)

    def _render_current_page_rows(self, parent):
        # Usuń stare wiersze (zostaw nagłówek row=0)
        for child in parent.winfo_children():
            info = child.grid_info()
            if info.get('row') and info.get('row') != 0:
                child.destroy()
        # Wyświetlamy bieżącą załadowaną stronę (self._all_listings reprezentuje stronę)
        subset = self._all_listings
        for idx, listing in enumerate(subset, start=1):
            price = listing.get('price_float')
            fee = listing.get('fee')
            price_text = f"{price:.2f} PLN" if price is not None else "N/A"
            fee_text = f"{fee:.2f} PLN" if fee is not None else "N/A"
            base_index = self.current_page * self.page_size
            ttk.Label(parent, text=str(base_index + idx)).grid(row=idx, column=0, padx=5, sticky='w')
            ttk.Label(parent, text=price_text, foreground='green').grid(row=idx, column=1, padx=5, sticky='e')
            ttk.Label(parent, text=fee_text).grid(row=idx, column=2, padx=5, sticky='e')
        total_count = self.listings_data.get('total_count', len(self._all_listings))
        total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        self.page_label.config(text=f"Strona {self.current_page + 1} / {total_pages}")
        # Aktualizacja etykiety "Łącznie ofert" następuje przy pełnym przeładowaniu (_fill_listings)

    def _next_page(self):
        if getattr(self, '_loading_page', False):
            return
        total_count = self.listings_data.get('total_count', len(self._all_listings))
        target_page = self.current_page + 1
        start = target_page * self.page_size
        if start >= total_count:
            return  # brak dalszych stron
        # Preferuj cache – jeśli mamy, przełącz lokalnie
        if target_page in self._page_cache:
            self._goto_page(target_page)
        else:
            self._fetch_page(start)

    def _prev_page(self):
        if getattr(self, '_loading_page', False):
            return
        if self.current_page > 0:
            target_page = self.current_page - 1
            # Preferuj cache
            if target_page in self._page_cache:
                self._goto_page(target_page)
            else:
                start = target_page * self.page_size
                self._fetch_page(start)

    def _goto_last_page(self):
        if getattr(self, '_loading_page', False):
            return
        total_count = self.listings_data.get('total_count', len(self._all_listings))
        last_page = max(0, (total_count - 1) // self.page_size)
        if last_page == self.current_page:
            return
        # Preferuj cache jeśli już pobrana
        if last_page in self._page_cache:
            self._goto_page(last_page)
        else:
            self._fetch_page(last_page * self.page_size)

    def _goto_page(self, page_idx):
        if getattr(self, '_loading_page', False):
            return
        total_count = self.listings_data.get('total_count', len(self._all_listings))
        max_page = max(0, (total_count - 1) // self.page_size)
        if page_idx < 0 or page_idx > max_page:
            return
        if page_idx == self.current_page:
            return
        # Jeśli mamy cache — przełącz lokalnie, bez sieci
        if page_idx in self._page_cache:
            self.current_page = page_idx
            self._all_listings = self._page_cache.get(self.current_page, [])
            try:
                # log: przejście na stronę z cache
                next_page = self.current_page + 1
                prefetch_ready = next_page in self._page_cache
                self.controller.result_queue.put({'status': 'log', 'message': f'Oferty: strona {self.current_page + 1} z cache. Prefetch następnej: {"TAK" if prefetch_ready else "NIE"}.'})
            except Exception:
                pass
            self._fill_listings()
        else:
            self._fetch_page(page_idx * self.page_size)

    def _fetch_page(self, start):
        self._loading_page = True
        self._show_overlay("Ładowanie…")
        item_key = self._cache_item_key

        def worker():
            data = None
            try:
                data = steam_market.get_market_listings_page(self.current_item_name, self.controller.login_cookie, start=start, count=self.page_size)
            except Exception as e:
                print(f"Błąd pobierania strony ofert: {e}", file=sys.stderr)
            def apply():
                self._loading_page = False
                # Jeśli użytkownik przełączył przedmiot w trakcie pobierania strony – porzuć
                if self._cache_item_key != item_key:
                    self._hide_overlay()
                    return
                if data is None:
                    ttk.Label(self.listings_section, text="Błąd pobierania strony.", foreground='red').pack(pady=5)
                    return
                page_idx = start // self.page_size
                self._all_listings = data.get('listings', [])
                # log do SearchView: strona pobrana z sieci
                try:
                    self.controller.result_queue.put({'status': 'log', 'message': f'Oferty: załadowano stronę { (start // self.page_size) + 1 } z sieci.'})
                except Exception:
                    pass
                # zapis do cache tej strony
                self._page_cache[page_idx] = self._all_listings
                self.listings_data['listings'] = self._all_listings
                self.listings_data['total_count'] = data.get('total_count', self.listings_data.get('total_count', len(self._all_listings)))
                self.listings_data['lowest_price'] = data.get('lowest_price', self.listings_data.get('lowest_price'))
                self.listings_data['lowest_price_float'] = data.get('lowest_price_float', self.listings_data.get('lowest_price_float'))
                self.current_page = page_idx
                self._hide_overlay()
                self._fill_listings()
            self.controller.root.after(0, apply)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _show_overlay(self, text="Ładowanie…"):
        try:
            if getattr(self, '_listings_container', None) is None:
                return
            if self._overlay_canvas is not None:
                try:
                    self._overlay_canvas.destroy()
                except Exception:
                    pass
            canvas = tk.Canvas(self._listings_container, width=self._listings_width, height=self._listings_height, highlightthickness=0, bd=0)
            canvas.place(x=0, y=0)
            # prostokąt z wzorem stipple, efekt "przyciemnienia"
            canvas.create_rectangle(0, 0, self._listings_width, self._listings_height, fill="gray", stipple=self._overlay_stipple, outline="")
            canvas.create_text(self._listings_width//2, self._listings_height//2, text=text, fill="white", font=("Arial", 12, "bold"))
            self._overlay_canvas = canvas
        except Exception as e:
            print(f"Overlay błąd: {e}", file=sys.stderr)

    def _hide_overlay(self):
        try:
            if self._overlay_canvas is not None:
                self._overlay_canvas.destroy()
                self._overlay_canvas = None
        except Exception:
            pass

    def _fill_summary(self):
        history = self.history_data
        if not history:
            ttk.Label(self.summary_section, text="Brak danych historycznych do podsumowania.").pack(pady=5, padx=5)
            return
            
        lowest_record = min(history, key=operator.itemgetter('price'))
        highest_record = max(history, key=operator.itemgetter('price'))
        
        summary_grid = ttk.Frame(self.summary_section, padding=5)
        summary_grid.pack(fill='x', padx=5, pady=5)
        summary_grid.grid_columnconfigure(1, weight=1)
        summary_grid.grid_columnconfigure(3, weight=1)
        row = 0
        
        ttk.Label(summary_grid, text="Najniższa cena historyczna:").grid(row=row, column=0, sticky='w', padx=5)
        ttk.Label(summary_grid, text=f"{lowest_record['price']:.2f} PLN", font=('Arial', 10, 'bold'), foreground='green').grid(row=row, column=1, sticky='w')
        ttk.Label(summary_grid, text=f"Data: {lowest_record['sale_date_str']}").grid(row=row, column=2, padx=10, sticky='w')
        row += 1

        ttk.Label(summary_grid, text="Najwyższa cena historyczna:").grid(row=row, column=0, sticky='w', padx=5)
        ttk.Label(summary_grid, text=f"{highest_record['price']:.2f} PLN", font=('Arial', 10, 'bold'), foreground='red').grid(row=row, column=1, sticky='w')
        ttk.Label(summary_grid, text=f"Data: {highest_record['sale_date_str']}").grid(row=row, column=2, padx=10, sticky='w')
        row += 1
        
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))


    def _fill_history_table(self):
        """Wypełnia Treeview danymi historycznymi."""
        self.history_tree.delete(*self.history_tree.get_children())
        
        for record in self.history_data:
            # Wersja bez 'quantity'
            self.history_tree.insert("", tk.END, values=(
                f"{record['item_type']}",
                record['item_wear'] or 'Brak',
                record['market_hash_name'],
                f"{record['price']:.2f}",
                record['sale_date_str']
            ))
            
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))
        
    def _toggle_history_table(self):
        """Przełącza widoczność tabeli historycznej."""
        if self.history_expanded.get():
            self.history_tree.pack_forget()
            self.history_expanded.set(False)
            self.history_toggle_button.config(text="Rozwiń Tabela Danych")
        else:
            if not self.history_tree.get_children():
                self._initial_history_sort()
                self._fill_history_table()
                
            self.history_tree.pack(fill='both', expand=True, padx=5, pady=5)
            self.history_expanded.set(True)
            self.history_toggle_button.config(text="Zwiń Tabela Danych")
            
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))

    # ------------------------------------------------------------------
    # GŁÓWNA METODA POKAZUJĄCA WYNIKI
    # ------------------------------------------------------------------
    def show_results(self, item_name, history_data, listings_data):
        """Aktualizuje widok po pomyślnym pobraniu danych."""
        # Reset cache dla nowego przedmiotu (uniknięcie przenikania ofert starego)
        self._cache_item_key = item_name
        self._page_cache.clear()
        self._pages_loading.clear()
        self._all_listings = []
        self._total_count = 0
        if getattr(self, '_overlay_canvas', None) is not None:
            try:
                self._overlay_canvas.destroy()
            except Exception:
                pass
            self._overlay_canvas = None
        self.current_item_name = item_name
        self.history_data = history_data
        self.listings_data = listings_data
        self.current_page = 0
        
        self.title_label.config(text=f"Wyniki dla: {item_name}")
        
        # --- POPRAWKA: Sprawdzamy czy listings_data nie jest None ---
        if listings_data is None:
            listings_data = {} # Zapewnij pusty słownik, aby .get() nie crashował
        # --- KONIEC POPRAWKI ---

        lowest_price = listings_data.get('lowest_price')
        lowest_price_float = listings_data.get('lowest_price_float')
        lp_text = f"{lowest_price_float:.2f} PLN" if lowest_price_float is not None else (lowest_price or "N/A")
        
        self._clear_sections()
        
        # Tworzymy etykietę podsumowania tutaj, po wyczyszczeniu
        self._create_summary_label(lp_text)
        
        self._plot_chart('all') # Narysuj wykres "Ogółem"
        self._fill_listings()
        self._fill_summary()
        # Spróbuj pobrać i wyświetlić obrazek jeśli został przekazany
        image_url = listings_data.get('image_url') if isinstance(listings_data, dict) else None
        if image_url:
            # Pobierz obraz asynchronicznie i ustaw w UI w wątku głównym
            def download_and_set():
                try:
                    import requests
                    from PIL import Image, ImageTk
                    from io import BytesIO
                    resp = requests.get(image_url, timeout=15)
                    if resp.status_code == 200 and resp.content:
                        img = Image.open(BytesIO(resp.content))
                        # Zmień rozmiar na sensowną wysokość i powiększ (np. 180px) zachowując proporcje
                        max_h = 180
                        w, h = img.size
                        if h > max_h:
                            new_w = int(w * (max_h / float(h)))
                            img = img.resize((new_w, max_h), Image.LANCZOS)
                        # Jeśli obraz ma jasne (białe) tło - dopasuj tło GUI do bieli, aby się "skleiło"
                        try:
                            rgb = img.convert('RGB')
                            w2, h2 = rgb.size
                            # próbkuj rogi
                            corners = [rgb.getpixel((0,0)), rgb.getpixel((w2-1,0)), rgb.getpixel((0,h2-1)), rgb.getpixel((w2-1,h2-1))]
                            avg = tuple(sum(c[i] for c in corners)//len(corners) for i in range(3))
                            if avg[0] >= 230 and avg[1] >= 230 and avg[2] >= 230:
                                hex_bg = '#ffffff'
                                try:
                                    self.scrollable_content.config(bg=hex_bg)
                                except Exception:
                                    pass
                                try:
                                    self._header_image_label.config(bg=hex_bg)
                                except Exception:
                                    pass
                                try:
                                    style = ttk.Style()
                                    style.configure('Results.TFrame', background=hex_bg)
                                    try:
                                        self.frame.configure(style='Results.TFrame')
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                                try:
                                    # również dostosuj tło wykresu do jasnego motywu (lekko szare osie)
                                    import matplotlib
                                    norm_rgb = (1.0, 1.0, 1.0)
                                    darker = (0.95, 0.95, 0.95)
                                    self.fig.patch.set_facecolor(norm_rgb)
                                    self.ax.set_facecolor(darker)
                                    try:
                                        self.chart_canvas.draw()
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        tkimg = ImageTk.PhotoImage(img)
                        def apply():
                            try:
                                # Ustaw obrazek w nagłówku (prawy górny róg)
                                self._current_item_image = tkimg
                                self._header_image_label.config(image=self._current_item_image)
                                # Przesuń widok do góry, aby użytkownik zobaczył nagłówek
                                try:
                                    self.scrollable_content.yview_moveto(0)
                                except Exception:
                                    pass
                            except Exception as e:
                                print(f"Błąd ustawiania obrazka: {e}", file=sys.stderr)
                        self.controller.root.after(0, apply)
                except Exception as e:
                    print(f"Ostrzeżenie: nie udało się pobrać obrazka: {e}", file=sys.stderr)
            import threading
            threading.Thread(target=download_and_set, daemon=True).start()
        # Przygotuj tabelę historii (nie pokazujemy dopóki użytkownik nie rozwinie)
        self._initial_history_sort()
        
        self.scrollable_content.yview_moveto(0)

    # --- PRZYWRÓCONA FUNKCJA ---
    def _create_summary_label(self, lowest_price_text):
        """Tworzy etykietę podsumowania (tylko najniższa oferta)."""
        for widget in self.summary_section.winfo_children():
            widget.destroy()
        summary_label = ttk.Label(self.summary_section, text=f"Najniższa oferta: {lowest_price_text}")
        summary_label.pack(side='left', padx=5, pady=5)

    # --- SORTOWANIE HISTORII ---
    def _initial_history_sort(self):
        """Ustaw wstępne sortowanie: daty malejąco (najnowsze)."""
        if not self.history_data:
            return
        # daty malejąco (najnowsze pierwsze)
        self.history_data.sort(key=lambda r: r.get('sale_timestamp', 0), reverse=True)
        self._history_last_sorted = 'sale_timestamp'
        # zaktualizuj nagłówek daty
        self._update_history_headers(active='sale_timestamp', ascending=False)  # descending = newest first

    def _sort_history(self, field):
        """Sortuje historię po wskazanym polu. Kliknięcie przełącza kierunek."""
        if not self.history_data:
            return
        if field not in ('price', 'sale_timestamp'):
            return
        ascending = self._history_sort_states[field]
        if field == 'price':
            # cena: ascending True => rosnąco (najniższa pierwsza)
            self.history_data.sort(key=lambda r: r.get('price', 0), reverse=not ascending)
        else:  # sale_timestamp
            # data: ascending True => newest first (timestamp descending)
            self.history_data.sort(key=lambda r: r.get('sale_timestamp', 0), reverse=ascending)
        # toggle kierunek na następną interakcję
        self._history_sort_states[field] = not ascending
        self._history_last_sorted = field
        # aktualizuj nagłówki strzałkami
        # dla daty: ascending True oznacza że PREVIOUS click zrobił newest first, aktualny sort jest zrobiony według poprzedniego ascending flagi
        # po sortowaniu chcemy wyświetlić kierunek użyty, czyli 'ascending' variable
        self._update_history_headers(active=field, ascending=ascending if field=='price' else (not ascending))
        self._fill_history_table()

    def _update_history_headers(self, active=None, ascending=True):
        """Aktualizuje tekst nagłówków z symbolami kierunku sortowania."""
        try:
            price_arrow = ''
            date_arrow = ''
            if active == 'price':
                price_arrow = ' ↑' if ascending else ' ↓'
            elif active == 'sale_timestamp':
                # ascending (for display) = chronologicznie rosnąco (starsze -> nowsze); descending = najnowsze pierwsze
                date_arrow = ' ↑' if ascending else ' ↓'
            self.history_tree.heading("Cena", text=f"Cena Sprzedaży{price_arrow}", command=lambda: self._sort_history('price'))
            self.history_tree.heading("Data", text=f"Data Sprzedaży{date_arrow}", command=lambda: self._sort_history('sale_timestamp'))
        except Exception as e:
            print(f"Błąd aktualizacji nagłówków sortowania: {e}", file=sys.stderr)
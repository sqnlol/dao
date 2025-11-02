import tkinter as tk
from tkinter import ttk
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
        
        self.current_listing_display_limit = 15 

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
        tree.heading("Cena", text="Cena Sprzedaży")
        tree.heading("Data", text="Data Sprzedaży")
        
        return tree
        
    def _fill_listings(self):
        for widget in self.listings_section.winfo_children():
            widget.destroy()
        listings = self.listings_data.get('listings', [])
        total_count = self.listings_data.get('total_count', 0)
        info_frame = ttk.Frame(self.listings_section)
        info_frame.pack(fill='x', padx=5, pady=5)
        
        if total_count == 0 or not listings:
            ttk.Label(info_frame, text="⛔ Brak aktualnych ofert sprzedaży na rynku.", foreground='red').pack(fill='x')
            if self.listings_data.get('highest_buy_order'):
                ttk.Label(info_frame, text=f"Najwyższe zlecenie kupna (Buy Order): {self.listings_data['highest_buy_order']}").pack(fill='x')
            return
        
        ttk.Label(info_frame, text=f"Liczba ofert: {total_count}.").pack(anchor='w')
        ttk.Separator(self.listings_section, orient='horizontal').pack(fill='x', padx=5, pady=2)
        listings_frame = ttk.Frame(self.listings_section)
        listings_frame.pack(fill='x', padx=5)
        
        listings_frame.grid_columnconfigure(0, weight=1)
        listings_frame.grid_columnconfigure(1, weight=1)
        listings_frame.grid_columnconfigure(2, weight=1)
        
        ttk.Label(listings_frame, text="Lp.", font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=5, sticky='w')
        ttk.Label(listings_frame, text="Cena Końcowa", font=('Arial', 9, 'bold')).grid(row=0, column=1, padx=5, sticky='e')
        ttk.Label(listings_frame, text="Prowizja Steam", font=('Arial', 9, 'bold')).grid(row=0, column=2, padx=5, sticky='e')
        
        row_num = 1
        for i, listing in enumerate(listings[:self.current_listing_display_limit]):
            price = listing.get('price_float')
            fee = listing.get('fee')
            
            ttk.Label(listings_frame, text=f"{i + 1}.", anchor='w').grid(row=row_num, column=0, padx=5, sticky='w')
            price_text = f"{price:.2f} PLN" if price is not None else "N/A"
            fee_text = f"{fee:.2f} PLN" if fee is not None else "N/A"
            
            ttk.Label(listings_frame, text=price_text, anchor='e', foreground='green').grid(row=row_num, column=1, padx=5, sticky='e')
            ttk.Label(listings_frame, text=fee_text, anchor='e').grid(row=row_num, column=2, padx=5, sticky='e')
            row_num += 1
            
        if total_count > self.current_listing_display_limit and len(listings) >= self.current_listing_display_limit:
            more_button = ttk.Button(self.listings_section, text=f"Pokaż kolejne 15 ofert (Wyświetlono: {self.current_listing_display_limit}/{total_count})", command=self._load_more_listings)
            more_button.pack(pady=5, padx=5, fill='x')
        
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))

    def _load_more_listings(self):
        self.current_listing_display_limit += 10
        self._fill_listings()

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
        
        if self.history_data:
            # Sortujemy dane tutaj (od najnowszych)
            self.history_data.sort(key=lambda x: x['sale_timestamp'], reverse=True)

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
        
        self.current_item_name = item_name
        self.history_data = history_data
        self.listings_data = listings_data
        self.current_listing_display_limit = 15 
        
        self.title_label.config(text=f"Wyniki dla: {item_name}")
        
        # --- POPRAWKA: Sprawdzamy czy listings_data nie jest None ---
        if listings_data is None:
            listings_data = {} # Zapewnij pusty słownik, aby .get() nie crashował
        # --- KONIEC POPRAWKI ---
        
        lowest_price = listings_data.get('lowest_price', "N/A")
        buy_order = listings_data.get('highest_buy_order', "N/A")
        
        self._clear_sections()
        
        # Tworzymy etykietę podsumowania tutaj, po wyczyszczeniu
        self._create_summary_label(lowest_price, buy_order) # Przywrócone
        
        self._plot_chart('all') # Narysuj wykres "Ogółem"
        self._fill_listings()
        self._fill_summary()
        
        self.scrollable_content.yview_moveto(0)

    # --- PRZYWRÓCONA FUNKCJA ---
    def _create_summary_label(self, lowest_price, buy_order):
        """Tworzy etykietę podsumowania w odpowiedniej ramce."""
        # Usuń starą etykietę, jeśli istnieje
        for widget in self.summary_section.winfo_children():
            widget.destroy()
            
        summary_text = f"Najniższa oferta: {lowest_price} | Najwyższe zlecenie kupna: {buy_order}"
        
        summary_label = ttk.Label(self.summary_section, text=summary_text)
        summary_label.pack(side='left', padx=5, pady=5)
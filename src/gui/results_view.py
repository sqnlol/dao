import tkinter as tk
from tkinter import ttk
import sys
import operator # do sortowania listy

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
        
        self.current_listing_display_limit = 15 # Limit wyświetlanych ofert

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

        # Używamy Canvas i Scrollbar dla przewijania wewnętrznej ramki
        self.scrollable_content = tk.Canvas(self.main_content_frame, bd=0, highlightthickness=0)
        self.scrollable_content.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(self.main_content_frame, orient="vertical", command=self.scrollable_content.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.scrollable_content.configure(yscrollcommand=self.scrollbar.set)
        
        # Frame, w którym umieścimy całą treść
        self.inner_frame = ttk.Frame(self.scrollable_content, padding="5")
        self.scrollable_content.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        self.inner_frame.bind("<Configure>", lambda e: self.scrollable_content.configure(scrollregion=self.scrollable_content.bbox("all")))
        self.inner_frame.grid_columnconfigure(0, weight=1)
        
        # Sekcje widoku (będą wypełniane dynamicznie w show_results)
        self.listings_section = ttk.LabelFrame(self.inner_frame, text="📊 Aktualne Oferty Rynkowe")
        self.listings_section.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.listings_section.grid_columnconfigure(0, weight=1)
        
        self.summary_section = ttk.LabelFrame(self.inner_frame, text="📜 Podsumowanie Historyczne")
        self.summary_section.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.summary_section.grid_columnconfigure(0, weight=1)

        self.history_table_section = ttk.LabelFrame(self.inner_frame, text="⏳ Szczegóły Transakcji Historycznych")
        self.history_table_section.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.history_table_section.grid_columnconfigure(0, weight=1)
        
        # Przycisk Rozwiń/Zwiń
        self.history_expanded = tk.BooleanVar(value=False)
        self.history_toggle_button = ttk.Button(self.history_table_section, text="Rozwiń Tabela Danych", command=self._toggle_history_table)
        self.history_toggle_button.pack(pady=5, padx=5, fill='x')
        
        self.history_tree = self._create_history_treeview(self.history_table_section)
        # self.history_tree jest początkowo ukryty (pack_forget)
        
        
    def _clear_sections(self):
        """Czyści dynamiczną zawartość sekcji przed nowym wynikiem."""
        
        # Czyścimy sekcję ofert, ale zostawiamy miejsce na nagłówek
        for widget in self.listings_section.winfo_children():
            widget.destroy()
            
        # Czyścimy sekcję podsumowania
        for widget in self.summary_section.winfo_children():
            widget.destroy()
            
        # Resetujemy stan tabeli historycznej
        self.history_tree.delete(*self.history_tree.get_children())
        self.history_tree.pack_forget() # Upewnij się, że jest ukryta
        self.history_expanded.set(False)
        self.history_toggle_button.config(text="Rozwiń Tabela Danych")
        self.history_toggle_button.pack(pady=5, padx=5, fill='x')


    # ------------------------------------------------------------------
    # FUNKCJE BUDOWANIA WIDOKU
    # ------------------------------------------------------------------
    def _create_history_treeview(self, parent_frame):
        """Tworzy widżet Treeview dla danych historycznych."""
        
        columns = ("Data", "Cena", "Market Hash Name", "Typ Jakości")
        tree = ttk.Treeview(parent_frame, columns=columns, show='headings', height=10)
        
        tree.column("Data", width=150, anchor=tk.W)
        tree.column("Cena", width=100, anchor=tk.E)
        tree.column("Market Hash Name", width=250, anchor=tk.W)
        tree.column("Typ Jakości", width=120, anchor=tk.W)

        tree.heading("Data", text="Data Sprzedaży")
        tree.heading("Cena", text="Cena Sprzedaży")
        tree.heading("Market Hash Name", text="Nazwa Rynkowa")
        tree.heading("Typ Jakości", text="Typ / Jakość")
        
        return tree
        
    def _fill_listings(self):
        """Wypełnia sekcję aktualnych ofert."""
        
        # 1. Usuń istniejącą zawartość
        for widget in self.listings_section.winfo_children():
            widget.destroy()

        listings = self.listings_data.get('listings', [])
        total_count = self.listings_data.get('total_count', 0)
        
        info_frame = ttk.Frame(self.listings_section)
        info_frame.pack(fill='x', padx=5, pady=5)
        
        if total_count == 0:
            ttk.Label(info_frame, text="⛔ Brak aktualnych ofert sprzedaży na rynku.", foreground='red').pack(fill='x')
            if self.listings_data.get('highest_buy_order'):
                ttk.Label(info_frame, text=f"Najwyższe zlecenie kupna (Buy Order): {self.listings_data['highest_buy_order']}").pack(fill='x')
            return

        # Podsumowanie cen
        lowest_price_str = self.listings_data.get('lowest_price')
        highest_buy_str = self.listings_data.get('highest_buy_order')
        
        ttk.Label(info_frame, text=f"Liczba ofert: {total_count}. Najniższa cena rynkowa: {lowest_price_str}").pack(anchor='w')
        if highest_buy_str:
            ttk.Label(info_frame, text=f"Najwyższe zlecenie kupna: {highest_buy_str}").pack(anchor='w')
            
        ttk.Separator(self.listings_section, orient='horizontal').pack(fill='x', padx=5, pady=2)

        # 2. Tabela ofert
        listings_frame = ttk.Frame(self.listings_section)
        listings_frame.pack(fill='x', padx=5)
        
        # Nagłówki tabeli
        listings_frame.grid_columnconfigure(0, weight=1)
        listings_frame.grid_columnconfigure(1, weight=1)
        listings_frame.grid_columnconfigure(2, weight=1)
        
        ttk.Label(listings_frame, text="Lp.", font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=5, sticky='w')
        ttk.Label(listings_frame, text="Cena Końcowa", font=('Arial', 9, 'bold')).grid(row=0, column=1, padx=5, sticky='e')
        ttk.Label(listings_frame, text="Prowizja Steam", font=('Arial', 9, 'bold')).grid(row=0, column=2, padx=5, sticky='e')
        
        row_num = 1
        # Wyświetlamy do aktualnie ustalonego limitu
        for i, listing in enumerate(listings[:self.current_listing_display_limit]):
            price = listing.get('price_float')
            fee = listing.get('fee')
            
            ttk.Label(listings_frame, text=f"{i + 1}.", anchor='w').grid(row=row_num, column=0, padx=5, sticky='w')
            
            # Cena może być None, jeśli API zwróciło niepełne dane
            price_text = f"{price:.2f} PLN" if price is not None else "N/A"
            fee_text = f"{fee:.2f}" if fee is not None else "N/A"
            
            ttk.Label(listings_frame, text=price_text, anchor='e', foreground='green').grid(row=row_num, column=1, padx=5, sticky='e')
            ttk.Label(listings_frame, text=fee_text, anchor='e').grid(row=row_num, column=2, padx=5, sticky='e')
            
            row_num += 1
            
        # 3. Przycisk "Więcej"
        if total_count > self.current_listing_display_limit and len(listings) >= self.current_listing_display_limit:
            more_button = ttk.Button(self.listings_section, text=f"Pokaż kolejne 15 ofert (Wyświetlono: {self.current_listing_display_limit}/{total_count})", command=self._load_more_listings)
            more_button.pack(pady=5, padx=5, fill='x')
        
        # Wymuś aktualizację przewijania
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))

    def _load_more_listings(self):
        """Zwiększa limit wyświetlanych ofert (zakładając, że dane są już załadowane)."""
        
        # Zwiększamy limit wyświetlania
        self.current_listing_display_limit += 15
        
        # W realistycznej aplikacji, tutaj byłoby zapytanie do API o kolejne 15 ofert
        # W tej implementacji zakładamy, że tylko zwiększamy widoczność, dopóki lista się nie skończy.
        
        self._fill_listings() # Odśwież widok

    def _fill_summary(self):
        """Wypełnia sekcję podsumowania historycznego."""
        
        history = self.history_data
        
        if not history:
            ttk.Label(self.summary_section, text="Brak danych historycznych do podsumowania.").pack(pady=5, padx=5)
            return
            
        # 1. Znajdź najtańszą i najdroższą cenę historyczną
        lowest_record = min(history, key=operator.itemgetter('price'))
        highest_record = max(history, key=operator.itemgetter('price'))
        
        # 2. Formatowanie i wyświetlanie
        
        summary_grid = ttk.Frame(self.summary_section, padding=5)
        summary_grid.pack(fill='x', padx=5, pady=5)
        summary_grid.grid_columnconfigure(1, weight=1)
        summary_grid.grid_columnconfigure(3, weight=1)

        row = 0
        
        # Najtańsza cena
        ttk.Label(summary_grid, text="Najniższa cena historyczna:").grid(row=row, column=0, sticky='w', padx=5)
        ttk.Label(summary_grid, text=f"{lowest_record['price']:.2f} PLN", font=('Arial', 10, 'bold'), foreground='green').grid(row=row, column=1, sticky='w')
        ttk.Label(summary_grid, text=f"Data: {lowest_record['sale_date_str']}").grid(row=row, column=2, padx=10, sticky='w')
        row += 1

        # Najdroższa cena
        ttk.Label(summary_grid, text="Najwyższa cena historyczna:").grid(row=row, column=0, sticky='w', padx=5)
        ttk.Label(summary_grid, text=f"{highest_record['price']:.2f} PLN", font=('Arial', 10, 'bold'), foreground='red').grid(row=row, column=1, sticky='w')
        ttk.Label(summary_grid, text=f"Data: {highest_record['sale_date_str']}").grid(row=row, column=2, padx=10, sticky='w')
        row += 1
        
        # Wymuś aktualizację przewijania
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))


    def _fill_history_table(self):
        """Wypełnia Treeview danymi historycznymi."""
        
        # Usuń starą zawartość
        self.history_tree.delete(*self.history_tree.get_children())
        
        # Wypełnij nowymi danymi
        for record in self.history_data:
            self.history_tree.insert("", tk.END, values=(
                record['sale_date_str'],
                f"{record['price']:.2f}",
                record['market_hash_name'],
                f"{record['item_type']} / {record['item_wear'] or 'Brak'}"
            ))
            
        # Wymuś aktualizację przewijania
        self.inner_frame.update_idletasks()
        self.scrollable_content.config(scrollregion=self.scrollable_content.bbox("all"))
        
    def _toggle_history_table(self):
        """Przełącza widoczność tabeli historycznej."""
        if self.history_expanded.get():
            self.history_tree.pack_forget()
            self.history_expanded.set(False)
            self.history_toggle_button.config(text="Rozwiń Tabela Danych")
        else:
            # Wypełniamy dane przy pierwszym rozwinięciu, aby zaoszczędzić czas na starcie
            if not self.history_tree.get_children():
                self._fill_history_table()
                
            self.history_tree.pack(fill='both', expand=True, padx=5, pady=5)
            self.history_expanded.set(True)
            self.history_toggle_button.config(text="Zwiń Tabela Danych")
            
        # Wymuś aktualizację przewijania
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
        self.current_listing_display_limit = 15 # Resetujemy limit wyświetlanych ofert
        
        self.title_label.config(text=f"Wyniki dla: {item_name}")
        
        self._clear_sections()
        self._fill_listings()
        self._fill_summary()
        
        # Upewnij się, że okno przewijane jest na górze
        self.scrollable_content.yview_moveto(0)
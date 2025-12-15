import tkinter as tk
from tkinter import ttk
from src import steam_market
import sys
import datetime
from collections import OrderedDict
import threading
import os

# --- IMPORTY DLA WYKRESU ---
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

try:
    from PIL import Image, ImageTk
    from io import BytesIO
    import requests
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Kursy walut względem PLN
EXCHANGE_RATES = {
    'PLN': 1.0,
    'USD': 0.25,
    'EUR': 0.23
}


class ResultsView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        # Główny frame z ciemnym tłem
        self.frame = tk.Frame(master, bg='#1e1e1e')
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # Dane
        self.current_item_name = ""
        self.history_data = []
        self.listings_data = {}
        self._history_from_api = False
        
        # Paginacja ofert z cache
        self.page_size = 10
        self.current_page = 0
        self._all_listings = []
        self._page_cache = {}  # page_idx -> list of listings
        self._pages_loading = set()  # strony aktualnie pobierane
        self._cache_item_key = None  # identyfikator aktualnego przedmiotu dla cache
        self._loading_page = False
        
        # Paginacja historii
        self.history_page_size = 50
        self.history_current_page = 0
        self.history_expanded = False
        
        # Stan sortowania historii
        self._history_sort_states = {
            'price': True,  # True = rosnąco
            'sale_timestamp': True  # True = najnowsze pierwsze (desc)
        }
        self._history_last_sorted = None
        
        # Cache obrazków
        self._image_cache = OrderedDict()
        self._image_cache_limit = 50
        self._current_item_image = None

        self._create_widgets()

    def _create_widgets(self):
        """Tworzy wszystkie widgety."""
        # ===================== HEADER BAR =====================
        self._create_header()
        
        # ===================== GŁÓWNA ZAWARTOŚĆ (scrollowalna) =====================
        self.main_canvas = tk.Canvas(self.frame, bg='#1e1e1e', highlightthickness=0)
        self.main_canvas.grid(row=1, column=0, sticky='nsew')
        
        self.scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.main_canvas.yview)
        self.scrollbar.grid(row=1, column=1, sticky='ns')
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.content_frame = tk.Frame(self.main_canvas, bg='#1e1e1e')
        self.canvas_window = self.main_canvas.create_window((0, 0), window=self.content_frame, anchor='nw')
        
        self.content_frame.bind('<Configure>', self._on_content_configure)
        self.main_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Bind scroll - tylko gdy kursor nad canvas
        self.main_canvas.bind('<Enter>', self._bind_mousewheel)
        self.main_canvas.bind('<Leave>', self._unbind_mousewheel)
        self.content_frame.bind('<Enter>', self._bind_mousewheel)
        self.content_frame.bind('<Leave>', self._unbind_mousewheel)
        
        # ===================== SEKCJA GÓRNA: Obrazek + Info + Wykres =====================
        self._create_top_section()
        
        # ===================== SEKCJA OFERT =====================
        self._create_listings_section()
        
        # ===================== SEKCJA HISTORII =====================
        self._create_history_section()

    def _create_header(self):
        """Tworzy header bar z logo, zakładkami i użytkownikiem."""
        self.header = tk.Frame(self.frame, bg='#1e1e1e', height=60)
        self.header.grid(row=0, column=0, columnspan=2, sticky='ew')
        
        # Konfiguracja kolumn dla wyśrodkowania tytułu
        # col 0: logo, col 1: wyszukiwarka, col 2: skrzynie, col 3: SPACER (weight), col 4: tytuł (center), col 5: SPACER (weight), col 6: user
        self.header.grid_columnconfigure(3, weight=1)  # lewy spacer
        self.header.grid_columnconfigure(5, weight=1)  # prawy spacer
        
        # Logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'CS2SkinAnalyzer.png')
            if os.path.exists(logo_path) and HAS_PIL:
                img = Image.open(logo_path)
                img.thumbnail((48, 48))
                self._header_logo = ImageTk.PhotoImage(img)
                logo_lbl = tk.Label(self.header, image=self._header_logo, bg='#1e1e1e')
                logo_lbl.grid(row=0, column=0, padx=(12, 12), pady=6)
        except Exception:
            pass

        # Zakładki
        search_lbl = tk.Label(self.header, text="Wyszukiwarka", bg='#1e1e1e', fg='#888888', 
                              font=('Segoe UI', 14), cursor='hand2')
        search_lbl.grid(row=0, column=1, padx=(0, 24))
        search_lbl.bind('<Button-1>', lambda e: self.controller.switch_view('search'))
        
        cases_lbl = tk.Label(self.header, text="Skrzynie", bg='#1e1e1e', fg='#888888',
                             font=('Segoe UI', 14), cursor='hand2')
        cases_lbl.grid(row=0, column=2)
        cases_lbl.bind('<Button-1>', lambda e: self.controller.switch_view('cases'))

        # Tytuł przedmiotu (wyśrodkowany)
        self.title_label = tk.Label(self.header, text="", bg='#1e1e1e', fg='#ffffff',
                                    font=('Segoe UI', 14, 'bold'))
        self.title_label.grid(row=0, column=4)

        # Prawa strona: użytkownik + dropdown + avatar
        right_frame = tk.Frame(self.header, bg='#1e1e1e')
        right_frame.grid(row=0, column=6, sticky='e', padx=(0, 12))
        
        # Kontener na nazwę i strzałkę (dropdown)
        self.user_dropdown_frame = tk.Frame(right_frame, bg='#1e1e1e', cursor='hand2')
        self.user_dropdown_frame.pack(side='left', padx=(0, 8))
        
        steam_name = getattr(self.controller, 'steam_name', None) or 'Użytkownik'
        self.welcome_label = tk.Label(self.user_dropdown_frame, text=f"Witaj,\n{steam_name}", 
                                      bg='#1e1e1e', fg='#ffffff', font=('Segoe UI', 10), justify='right')
        self.welcome_label.pack(side='left')
        
        # Strzałka w dół
        self.dropdown_arrow = tk.Label(self.user_dropdown_frame, text="▼", bg='#1e1e1e', fg='#888888', 
                                       font=('Segoe UI', 8), cursor='hand2')
        self.dropdown_arrow.pack(side='left', padx=(4, 0))
        
        # Menu dropdown (ukryte domyślnie)
        self.dropdown_menu = None
        self.dropdown_visible = False
        
        # Bindowanie kliknięcia na cały obszar dropdown
        for widget in (self.user_dropdown_frame, self.welcome_label, self.dropdown_arrow):
            widget.bind('<Button-1>', self._toggle_dropdown_menu)
        
        # Avatar canvas
        self.avatar_canvas = tk.Canvas(right_frame, width=52, height=52, bg='#1e1e1e', 
                                       highlightthickness=0, cursor='hand2')
        self.avatar_canvas.pack(side='left')
        self._setup_avatar()
        
        # Separator pod headerem
        separator = tk.Frame(self.frame, bg='#5588cc', height=2)
        separator.grid(row=0, column=0, columnspan=2, sticky='sew', pady=(60, 0))

    def _setup_avatar(self):
        """Ustawia avatar użytkownika."""
        cached_avatar = getattr(self.controller, '_cached_avatar_photo', None)
        cached_frame = getattr(self.controller, '_cached_frame_photo', None)
        
        if cached_avatar:
            self.avatar_canvas.create_image(26, 26, image=cached_avatar, tags='avatar')
            if cached_frame:
                self.avatar_canvas.create_image(26, 26, image=cached_frame, tags='frame')
        else:
            self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1)
            self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', 
                                           font=('Segoe UI', 7), justify='center')

    def _create_top_section(self):
        """Tworzy górną sekcję: przycisk powrotu, obrazek, info, wykres."""
        top_frame = tk.Frame(self.content_frame, bg='#1e1e1e')
        top_frame.pack(fill='x', padx=20, pady=(10, 20))
        
        # Lewa kolumna: przycisk powrotu + obrazek + info
        left_col = tk.Frame(top_frame, bg='#1e1e1e')
        left_col.pack(side='left', anchor='n')
        
        # Przycisk powrotu (niebieski kwadrat ze strzałką)
        back_btn = tk.Canvas(left_col, width=40, height=40, bg='#2a5a8a', highlightthickness=0, cursor='hand2')
        back_btn.pack(anchor='w', pady=(0, 15))
        back_btn.create_text(20, 20, text="◀", fill='white', font=('Segoe UI', 16, 'bold'))
        back_btn.bind('<Button-1>', lambda e: self.controller.switch_view('search'))
        
        # Obrazek przedmiotu
        self.image_frame = tk.Frame(left_col, bg='#1e1e1e', width=280, height=200)
        self.image_frame.pack(pady=(0, 15))
        self.image_frame.pack_propagate(False)
        
        self.image_label = tk.Label(self.image_frame, bg='#1e1e1e', text='(Ładowanie obrazka...)', 
                                    fg='#888888', font=('Segoe UI', 10))
        self.image_label.pack(expand=True)
        
        # Ramka z informacjami o cenach
        info_frame = tk.Frame(left_col, bg='#2a2a2a', highlightbackground='#5588cc', highlightthickness=1)
        info_frame.pack(fill='x', pady=(0, 10))
        
        self.lowest_offer_label = tk.Label(info_frame, text="Najniższa aktualna oferta:", 
                                           bg='#2a2a2a', fg='#88bbff', font=('Segoe UI', 10), anchor='w')
        self.lowest_offer_label.pack(fill='x', padx=10, pady=(10, 5))
        
        self.lowest_offer_value = tk.Label(info_frame, text="-", 
                                           bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 11, 'bold'), anchor='w')
        self.lowest_offer_value.pack(fill='x', padx=10, pady=(0, 10))
        
        # Najniższa/najwyższa cena historyczna
        hist_frame = tk.Frame(info_frame, bg='#2a2a2a')
        hist_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        tk.Label(hist_frame, text="Najniższa cena historyczna:", bg='#2a2a2a', fg='#888888', 
                 font=('Segoe UI', 9)).grid(row=0, column=0, sticky='w')
        self.min_hist_price = tk.Label(hist_frame, text="-", bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 9))
        self.min_hist_price.grid(row=0, column=1, sticky='w', padx=(10, 0))
        tk.Label(hist_frame, text="Data:", bg='#2a2a2a', fg='#888888', font=('Segoe UI', 9)).grid(row=0, column=2, sticky='w', padx=(20, 0))
        self.min_hist_date = tk.Label(hist_frame, text="-", bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 9))
        self.min_hist_date.grid(row=0, column=3, sticky='w', padx=(5, 0))
        
        tk.Label(hist_frame, text="Najwyższa cena historyczna:", bg='#2a2a2a', fg='#888888', 
                 font=('Segoe UI', 9)).grid(row=1, column=0, sticky='w')
        self.max_hist_price = tk.Label(hist_frame, text="-", bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 9))
        self.max_hist_price.grid(row=1, column=1, sticky='w', padx=(10, 0))
        tk.Label(hist_frame, text="Data:", bg='#2a2a2a', fg='#888888', font=('Segoe UI', 9)).grid(row=1, column=2, sticky='w', padx=(20, 0))
        self.max_hist_date = tk.Label(hist_frame, text="-", bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 9))
        self.max_hist_date.grid(row=1, column=3, sticky='w', padx=(5, 0))
        
        # Prawa kolumna: wykres + przyciski filtrowania
        right_col = tk.Frame(top_frame, bg='#1e1e1e')
        right_col.pack(side='left', fill='both', expand=True, padx=(30, 0))
        
        # Wykres i przyciski w jednym kontenerze
        chart_container = tk.Frame(right_col, bg='#1e1e1e')
        chart_container.pack(fill='both', expand=True)
        
        # Wykres - z paddingiem górnym żeby daty kończyły się równo z info box
        self._create_chart(chart_container)
        
        # Przyciski filtrowania po prawej stronie wykresu - z paddingiem górnym 
        # żeby pierwszy przycisk był na równi z "Historia transakcji"
        filter_frame = tk.Frame(chart_container, bg='#1e1e1e')
        filter_frame.pack(side='right', anchor='n', padx=(10, 0), pady=(75, 0))
        
        filter_buttons = [
            ("Ogółem", 'all'),
            ("Rok", 'year'),
            ("Pół roku", 'half_year'),
            ("Trzy miesiące", '3months'),
            ("Miesiąc", 'month'),
            ("Tydzień", 'week')
        ]
        
        for text, range_val in filter_buttons:
            btn = tk.Button(filter_frame, text=text, bg='#3a3a3a', fg='white', 
                           font=('Segoe UI', 9), width=12, cursor='hand2',
                           activebackground='#5588cc', activeforeground='white',
                           relief='flat', bd=0)
            btn.pack(pady=2)
            btn.config(command=lambda r=range_val: self._plot_chart(r))
        
        # Separator
        tk.Frame(filter_frame, bg='#444444', height=1).pack(fill='x', pady=10)
        
        # Pola Od/Do z selektorami daty (rok-miesiąc-dzień)
        tk.Label(filter_frame, text="Od:", bg='#1e1e1e', fg='#888888', font=('Segoe UI', 9)).pack(anchor='w')
        
        from_frame = tk.Frame(filter_frame, bg='#1e1e1e')
        from_frame.pack(pady=(0, 5))
        
        # Generowanie list lat, miesięcy
        current_year = datetime.datetime.now().year
        years = [str(y) for y in range(2012, current_year + 1)]
        months = [str(m).zfill(2) for m in range(1, 13)]
        
        self.from_year = ttk.Combobox(from_frame, width=5, values=years, state='readonly')
        self.from_year.set('2012')
        self.from_year.pack(side='left')
        self.from_year.bind('<<ComboboxSelected>>', lambda e: self._update_days_combobox('from'))
        tk.Label(from_frame, text="-", bg='#1e1e1e', fg='#888888').pack(side='left')
        
        self.from_month = ttk.Combobox(from_frame, width=3, values=months, state='readonly')
        self.from_month.set('08')
        self.from_month.pack(side='left')
        self.from_month.bind('<<ComboboxSelected>>', lambda e: self._update_days_combobox('from'))
        tk.Label(from_frame, text="-", bg='#1e1e1e', fg='#888888').pack(side='left')
        
        # Dni - początkowo 31, będą aktualizowane dynamicznie
        self.from_day = ttk.Combobox(from_frame, width=3, values=[str(d).zfill(2) for d in range(1, 32)], state='readonly')
        self.from_day.set('21')
        self.from_day.pack(side='left')
        
        tk.Label(filter_frame, text="Do:", bg='#1e1e1e', fg='#888888', font=('Segoe UI', 9)).pack(anchor='w')
        
        to_frame = tk.Frame(filter_frame, bg='#1e1e1e')
        to_frame.pack(pady=(0, 5))
        
        today = datetime.datetime.now()
        
        self.to_year = ttk.Combobox(to_frame, width=5, values=years, state='readonly')
        self.to_year.set(str(today.year))
        self.to_year.pack(side='left')
        self.to_year.bind('<<ComboboxSelected>>', lambda e: self._update_days_combobox('to'))
        tk.Label(to_frame, text="-", bg='#1e1e1e', fg='#888888').pack(side='left')
        
        self.to_month = ttk.Combobox(to_frame, width=3, values=months, state='readonly')
        self.to_month.set(str(today.month).zfill(2))
        self.to_month.pack(side='left')
        self.to_month.bind('<<ComboboxSelected>>', lambda e: self._update_days_combobox('to'))
        tk.Label(to_frame, text="-", bg='#1e1e1e', fg='#888888').pack(side='left')
        
        self.to_day = ttk.Combobox(to_frame, width=3, values=[str(d).zfill(2) for d in range(1, 32)], state='readonly')
        self.to_day.set(str(today.day).zfill(2))
        self.to_day.pack(side='left')
        
        # Zaktualizuj dostępne dni na starcie
        self._update_days_combobox('from')
        self._update_days_combobox('to')
        
        check_btn = tk.Button(filter_frame, text="Sprawdź", bg='#3a3a3a', fg='white',
                             font=('Segoe UI', 9), cursor='hand2', relief='flat')
        check_btn.pack(pady=5)
        check_btn.config(command=self._filter_by_date_range)

    def _create_chart(self, parent):
        """Tworzy wykres matplotlib."""
        # Padding górny żeby wykres był niżej i daty kończyły się równo z info box
        chart_frame = tk.Frame(parent, bg='#1e1e1e')
        chart_frame.pack(side='left', fill='both', expand=True, pady=(55, 0))
        
        self.fig = Figure(figsize=(8, 3.5), dpi=100)
        self.fig.patch.set_facecolor('#1e1e1e')
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1a1a1a')
        self.ax.tick_params(axis='x', colors='white', labelsize=8)
        self.ax.tick_params(axis='y', colors='white', labelsize=8)
        self.ax.set_title("Historia transakcji (all)", color='white', fontsize=10)
        
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#444444')
        
        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.chart_canvas.get_tk_widget().pack(fill='both', expand=True)
        self.chart_canvas.draw()
        
        # Hover tooltip - przygotuj adnotację
        try:
            self._hover_annot = self.ax.annotate(
                "",
                xy=(0, 0),
                xytext=(12, 12),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.3", fc="#2a2a2a", ec="#5588cc", alpha=0.95),
                color="white",
                fontsize=9
            )
            self._hover_annot.set_visible(False)
            self._hover_threshold_px = 15
            self._chart_points = []
            self._chart_records = []
            self.chart_canvas.mpl_connect("motion_notify_event", self._on_chart_hover)
        except Exception:
            self._hover_annot = None
            self._hover_threshold_px = 0
            self._hover_dot = None

    def _create_listings_section(self):
        """Tworzy sekcję aktualnych ofert."""
        # Tytuł sekcji - klikalny link do Steam Market
        title_frame = tk.Frame(self.content_frame, bg='#1e1e1e')
        title_frame.pack(fill='x', padx=20, pady=(10, 5))
        
        self.listings_title_link = tk.Label(title_frame, text="Aktualne oferty na rynku Steam: 🔗", 
                                            bg='#1e1e1e', fg='#5588cc',
                                            font=('Segoe UI', 12), cursor='hand2')
        self.listings_title_link.pack(anchor='center')
        self.listings_title_link.bind('<Button-1>', lambda e: self._open_steam_market_page())
        self.listings_title_link.bind('<Enter>', lambda e: self.listings_title_link.config(fg='#77aaee'))
        self.listings_title_link.bind('<Leave>', lambda e: self.listings_title_link.config(fg='#5588cc'))
        
        # Nagłówki tabeli
        header_frame = tk.Frame(self.content_frame, bg='#1e1e1e')
        header_frame.pack(fill='x', padx=20)
        
        # Linie poziome
        tk.Frame(header_frame, bg='#5588cc', height=1).pack(fill='x')
        
        cols_frame = tk.Frame(header_frame, bg='#1e1e1e')
        cols_frame.pack(fill='x')
        
        tk.Label(cols_frame, text="", width=5, bg='#1e1e1e', fg='#888888').pack(side='left')
        tk.Label(cols_frame, text="Nazwa", width=40, bg='#1e1e1e', fg='#888888', 
                font=('Segoe UI', 10), anchor='center').pack(side='left', expand=True)
        tk.Label(cols_frame, text="Cena", width=15, bg='#1e1e1e', fg='#888888',
                font=('Segoe UI', 10), anchor='center').pack(side='left')
        tk.Label(cols_frame, text="Prowizja Steam", width=15, bg='#1e1e1e', fg='#888888',
                font=('Segoe UI', 10), anchor='center').pack(side='left')
        
        tk.Frame(header_frame, bg='#5588cc', height=1).pack(fill='x')
        
        # Kontener na listingi
        self.listings_container = tk.Frame(self.content_frame, bg='#1e1e1e')
        self.listings_container.pack(fill='x', padx=20)
        
        # Paginacja ofert
        self.listings_nav_frame = tk.Frame(self.content_frame, bg='#1e1e1e')
        self.listings_nav_frame.pack(fill='x', padx=20, pady=10)
        
        # Strzałki nawigacji
        nav_inner = tk.Frame(self.listings_nav_frame, bg='#1e1e1e')
        nav_inner.pack()
        
        self.first_btn = tk.Label(nav_inner, text="◀◀", bg='#1e1e1e', fg='#5588cc', 
                                  font=('Segoe UI', 16), cursor='hand2')
        self.first_btn.pack(side='left', padx=10)
        self.first_btn.bind('<Button-1>', lambda e: self._goto_listings_page(0))
        
        self.prev_btn = tk.Label(nav_inner, text="◀", bg='#1e1e1e', fg='#5588cc',
                                 font=('Segoe UI', 16), cursor='hand2')
        self.prev_btn.pack(side='left', padx=10)
        self.prev_btn.bind('<Button-1>', lambda e: self._prev_listings_page())
        
        self.listings_page_info = tk.Label(nav_inner, text="[10 najtańszych ofert]\nStrona 1/x", 
                                           bg='#1e1e1e', fg='#ffffff', font=('Segoe UI', 12),
                                           justify='center')
        self.listings_page_info.pack(side='left', padx=30)
        
        self.next_btn = tk.Label(nav_inner, text="▶", bg='#1e1e1e', fg='#5588cc',
                                 font=('Segoe UI', 16), cursor='hand2')
        self.next_btn.pack(side='left', padx=10)
        self.next_btn.bind('<Button-1>', lambda e: self._next_listings_page())
        
        self.last_btn = tk.Label(nav_inner, text="▶▶", bg='#1e1e1e', fg='#5588cc',
                                 font=('Segoe UI', 16), cursor='hand2')
        self.last_btn.pack(side='left', padx=10)
        self.last_btn.bind('<Button-1>', lambda e: self._goto_listings_last_page())

    def _create_history_section(self):
        """Tworzy sekcję danych historycznych."""
        # Separator
        tk.Frame(self.content_frame, bg='#5588cc', height=1).pack(fill='x', padx=20, pady=(20, 10))
        
        # Tytuł z przyciskiem rozwijania
        title_frame = tk.Frame(self.content_frame, bg='#1e1e1e')
        title_frame.pack(fill='x', padx=20)
        
        self.history_toggle_label = tk.Label(title_frame, text="Dane historyczne  (Rozwiń/zwiń)", 
                                             bg='#1e1e1e', fg='#ffffff', font=('Segoe UI', 12),
                                             cursor='hand2')
        self.history_toggle_label.pack(anchor='center')
        self.history_toggle_label.bind('<Button-1>', lambda e: self._toggle_history())
        
        # Kontener na tabelę historii (domyślnie ukryty)
        self.history_frame = tk.Frame(self.content_frame, bg='#1e1e1e')
        # Nie pakujemy - będzie pokazany po kliknięciu
        
        # Nagłówki tabeli historii
        self.history_header = tk.Frame(self.history_frame, bg='#1e1e1e')
        self.history_header.pack(fill='x', padx=20, pady=(10, 0))
        
        tk.Frame(self.history_header, bg='#5588cc', height=1).pack(fill='x')
        
        h_cols = tk.Frame(self.history_header, bg='#1e1e1e')
        h_cols.pack(fill='x')
        
        tk.Label(h_cols, text="Typ", width=12, bg='#1e1e1e', fg='#888888', font=('Segoe UI', 10)).pack(side='left')
        tk.Label(h_cols, text="Nazwa", width=20, bg='#1e1e1e', fg='#888888', font=('Segoe UI', 10)).pack(side='left', expand=True)
        tk.Label(h_cols, text="Jakość", width=15, bg='#1e1e1e', fg='#888888', font=('Segoe UI', 10)).pack(side='left')
        
        # Kolumna Cena - klikalna do sortowania
        self.history_price_header = tk.Label(h_cols, text="Cena Sprzedaży", width=15, bg='#1e1e1e', 
                                              fg='#5588cc', font=('Segoe UI', 10), cursor='hand2')
        self.history_price_header.pack(side='left')
        self.history_price_header.bind('<Button-1>', lambda e: self._sort_history('price'))
        
        # Kolumna Data - klikalna do sortowania
        self.history_date_header = tk.Label(h_cols, text="Data sprzedaży", width=18, bg='#1e1e1e', 
                                             fg='#5588cc', font=('Segoe UI', 10), cursor='hand2')
        self.history_date_header.pack(side='left')
        self.history_date_header.bind('<Button-1>', lambda e: self._sort_history('sale_timestamp'))
        
        tk.Frame(self.history_header, bg='#5588cc', height=1).pack(fill='x')
        
        # Kontener na wiersze historii
        self.history_rows_container = tk.Frame(self.history_frame, bg='#1e1e1e')
        self.history_rows_container.pack(fill='x', padx=20)
        
        # Paginacja historii
        self.history_nav = tk.Frame(self.history_frame, bg='#1e1e1e')
        self.history_nav.pack(fill='x', padx=20, pady=10)
        
        nav_h = tk.Frame(self.history_nav, bg='#1e1e1e')
        nav_h.pack()
        
        self.history_first_btn = tk.Label(nav_h, text="◀◀", bg='#1e1e1e', fg='#5588cc', font=('Segoe UI', 14), 
                cursor='hand2')
        self.history_first_btn.pack(side='left', padx=5)
        self.history_first_btn.bind('<Button-1>', lambda e: self._history_goto_first())
        
        self.history_prev_btn = tk.Label(nav_h, text="◀", bg='#1e1e1e', fg='#5588cc', font=('Segoe UI', 14),
                cursor='hand2')
        self.history_prev_btn.pack(side='left', padx=5)
        self.history_prev_btn.bind('<Button-1>', lambda e: self._history_goto_prev())
        
        self.history_page_label = tk.Label(nav_h, text="Strona 1/1", bg='#1e1e1e', fg='#ffffff',
                                           font=('Segoe UI', 10))
        self.history_page_label.pack(side='left', padx=20)
        
        self.history_next_btn = tk.Label(nav_h, text="▶", bg='#1e1e1e', fg='#5588cc', font=('Segoe UI', 14),
                cursor='hand2')
        self.history_next_btn.pack(side='left', padx=5)
        self.history_next_btn.bind('<Button-1>', lambda e: self._history_goto_next())
        
        self.history_last_btn = tk.Label(nav_h, text="▶▶", bg='#1e1e1e', fg='#5588cc', font=('Segoe UI', 14),
                cursor='hand2')
        self.history_last_btn.pack(side='left', padx=5)
        self.history_last_btn.bind('<Button-1>', lambda e: self._history_goto_last())

    # ===================== EVENT HANDLERS =====================
    
    def _on_content_configure(self, event):
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        self.main_canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _bind_mousewheel(self, event=None):
        """Binduje scroll gdy kursor wchodzi na canvas."""
        # Użyj bind_all ale tylko gdy ResultsView jest aktywny
        self._scroll_active = True
        self.frame.bind_all('<MouseWheel>', self._on_mousewheel_safe)
    
    def _unbind_mousewheel(self, event=None):
        """Odbindowuje scroll gdy kursor opuszcza canvas."""
        self._scroll_active = False
    
    def _on_mousewheel_safe(self, event):
        """Obsługuje scroll myszką z warunkiem aktywności."""
        if getattr(self, '_scroll_active', False):
            self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ===================== CHART METHODS =====================
    
    def _plot_chart(self, time_range='all'):
        """Rysuje wykres historii cen."""
        if not self.history_data:
            self.ax.clear()
            self.ax.text(0.5, 0.5, 'Brak danych historycznych', 
                        ha='center', va='center', transform=self.ax.transAxes, color='white')
            self.ax.set_facecolor('#1a1a1a')
            self.chart_canvas.draw()
            return
        
        now = datetime.datetime.now()
        limit_date = None
        
        range_names = {
            'week': 'Tydzień',
            'month': 'Miesiąc',
            '3months': 'Trzy miesiące',
            'half_year': 'Pół roku',
            'year': 'Rok',
            'all': 'Ogółem'
        }
        
        if time_range == 'week':
            limit_date = now - datetime.timedelta(days=7)
        elif time_range == 'month':
            limit_date = now - datetime.timedelta(days=30)
        elif time_range == '3months':
            limit_date = now - datetime.timedelta(days=90)
        elif time_range == 'half_year':
            limit_date = now - datetime.timedelta(days=180)
        elif time_range == 'year':
            limit_date = now - datetime.timedelta(days=365)
        
        x_dates = []
        y_prices = []
        plotted_records = []
        
        currency_symbol = getattr(self.controller, 'currency_symbol', 'zł')
        
        for record in self.history_data:
            try:
                record_date = datetime.datetime.fromtimestamp(record['sale_timestamp'])
                price = record['price']
                if not self._history_from_api:
                    price = self._convert_price(price)
                
                if limit_date is None or record_date > limit_date:
                    x_dates.append(record_date)
                    y_prices.append(price)
                    plotted_records.append(record)
            except Exception:
                continue
        
        self.ax.clear()
        
        if not x_dates:
            self.ax.text(0.5, 0.5, f'Brak danych dla zakresu: {range_names.get(time_range, time_range)}',
                        ha='center', va='center', transform=self.ax.transAxes, color='white')
            self._chart_points = []
            self._chart_records = []
        else:
            self.ax.plot(x_dates, y_prices, '-', color='#5588cc', linewidth=1.5)
            self.ax.fill_between(x_dates, y_prices, alpha=0.3, color='#5588cc')
            # Zapisz punkty do hover
            self._chart_points = list(zip(x_dates, y_prices))
            self._chart_records = plotted_records
        
        self.ax.set_title(f"Historia transakcji ({range_names.get(time_range, time_range)})", 
                         color='white', fontsize=10)
        self.ax.set_ylabel(f"Cena ({currency_symbol})", color='white', fontsize=9)
        self.ax.set_facecolor('#1a1a1a')
        self.ax.tick_params(axis='x', colors='white', labelsize=8)
        self.ax.tick_params(axis='y', colors='white', labelsize=8)
        self.ax.grid(True, linestyle='--', alpha=0.2, color='white')
        
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#444444')
        
        # Odtwórz adnotację hover po wyczyszczeniu
        try:
            if hasattr(self, '_hover_annot') and self._hover_annot is not None:
                try:
                    self._hover_annot.remove()
                except Exception:
                    pass
            self._hover_annot = self.ax.annotate(
                "",
                xy=(0, 0),
                xytext=(12, 12),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.3", fc="#2a2a2a", ec="#5588cc", alpha=0.95),
                color="white",
                fontsize=9
            )
            self._hover_annot.set_visible(False)
            
            # Zielona kropka podświetlająca punkt
            if hasattr(self, '_hover_dot') and self._hover_dot is not None:
                try:
                    self._hover_dot.remove()
                except Exception:
                    pass
            self._hover_dot = self.ax.scatter([], [], s=80, color='#00ff00', zorder=5, marker='o', edgecolors='white', linewidths=1.5)
            self._hover_dot.set_visible(False)
        except Exception:
            pass
        
        self.fig.autofmt_xdate()
        self.chart_canvas.draw()

    def _update_days_combobox(self, which):
        """Aktualizuje listę dni w combobox na podstawie wybranego roku i miesiąca."""
        import calendar
        try:
            if which == 'from':
                year = int(self.from_year.get())
                month = int(self.from_month.get())
                day_combo = self.from_day
            else:
                year = int(self.to_year.get())
                month = int(self.to_month.get())
                day_combo = self.to_day
            
            # Pobierz liczbę dni w danym miesiącu
            max_days = calendar.monthrange(year, month)[1]
            
            # Aktualne zaznaczenie
            current_day = day_combo.get()
            try:
                current_day_int = int(current_day)
            except:
                current_day_int = 1
            
            # Zaktualizuj listę dni
            new_days = [str(d).zfill(2) for d in range(1, max_days + 1)]
            day_combo['values'] = new_days
            
            # Jeśli aktualny dzień jest większy niż max, ustaw na max
            if current_day_int > max_days:
                day_combo.set(str(max_days).zfill(2))
        except Exception:
            pass

    def _filter_by_date_range(self):
        """Filtruje wykres według zakresu dat z selektorów."""
        try:
            # Pobierz daty z selektorów
            from_year = int(self.from_year.get())
            from_month = int(self.from_month.get())
            from_day = int(self.from_day.get())
            
            to_year = int(self.to_year.get())
            to_month = int(self.to_month.get())
            to_day = int(self.to_day.get())
            
            # Walidacja i korekta dnia (np. 31 luty -> ostatni dzień miesiąca)
            import calendar
            from_day = min(from_day, calendar.monthrange(from_year, from_month)[1])
            to_day = min(to_day, calendar.monthrange(to_year, to_month)[1])
            
            from_date = datetime.datetime(from_year, from_month, from_day)
            to_date = datetime.datetime(to_year, to_month, to_day, 23, 59, 59)
            
            if from_date > to_date:
                return
            
            # Filtruj dane
            x_dates = []
            y_prices = []
            plotted_records = []
            
            currency_symbol = getattr(self.controller, 'currency_symbol', 'zł')
            
            for record in self.history_data:
                try:
                    record_date = datetime.datetime.fromtimestamp(record['sale_timestamp'])
                    if from_date <= record_date <= to_date:
                        price = record['price']
                        if not self._history_from_api:
                            price = self._convert_price(price)
                        x_dates.append(record_date)
                        y_prices.append(price)
                        plotted_records.append(record)
                except Exception:
                    continue
            
            # Rysuj wykres
            self.ax.clear()
            
            if not x_dates:
                self.ax.text(0.5, 0.5, f'Brak danych dla zakresu: {from_date.strftime("%Y-%m-%d")} - {to_date.strftime("%Y-%m-%d")}',
                            ha='center', va='center', transform=self.ax.transAxes, color='white')
                self._chart_points = []
                self._chart_records = []
            else:
                self.ax.plot(x_dates, y_prices, '-', color='#5588cc', linewidth=1.5)
                self.ax.fill_between(x_dates, y_prices, alpha=0.3, color='#5588cc')
                self._chart_points = list(zip(x_dates, y_prices))
                self._chart_records = plotted_records
            
            range_str = f"{from_date.strftime('%Y-%m-%d')} - {to_date.strftime('%Y-%m-%d')}"
            self.ax.set_title(f"Historia transakcji ({range_str})", color='white', fontsize=10)
            self.ax.set_ylabel(f"Cena ({currency_symbol})", color='white', fontsize=9)
            self.ax.set_facecolor('#1a1a1a')
            self.ax.tick_params(axis='x', colors='white', labelsize=8)
            self.ax.tick_params(axis='y', colors='white', labelsize=8)
            self.ax.grid(True, linestyle='--', alpha=0.2, color='white')
            
            for spine in self.ax.spines.values():
                spine.set_edgecolor('#444444')
            
            # Odtwórz hover
            try:
                if hasattr(self, '_hover_annot') and self._hover_annot is not None:
                    try:
                        self._hover_annot.remove()
                    except Exception:
                        pass
                self._hover_annot = self.ax.annotate(
                    "",
                    xy=(0, 0),
                    xytext=(12, 12),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.3", fc="#2a2a2a", ec="#5588cc", alpha=0.95),
                    color="white",
                    fontsize=9
                )
                self._hover_annot.set_visible(False)
            except Exception:
                pass
            
            self.fig.autofmt_xdate()
            self.chart_canvas.draw()
        except Exception as e:
            print(f"Błąd filtrowania dat: {e}", file=sys.stderr)

    def _on_chart_hover(self, event):
        """Obsługuje najechanie myszą na wykres - pokazuje tooltip z informacjami."""
        try:
            if not hasattr(self, '_chart_points') or not self._chart_points:
                return
            if event.inaxes != self.ax:
                if self._hover_annot and self._hover_annot.get_visible():
                    self._hover_annot.set_visible(False)
                    self.chart_canvas.draw_idle()
                return
            
            import numpy as np
            
            # Konwersja X do wartości numerycznych
            if isinstance(self._chart_points[0][0], datetime.datetime):
                xs = [mdates.date2num(x) for x, _ in self._chart_points]
            else:
                xs = [x for x, _ in self._chart_points]
            ys = [y for _, y in self._chart_points]
            
            pts_data = np.column_stack([xs, ys])
            xys_disp = self.ax.transData.transform(pts_data)
            ex, ey = event.x, event.y
            
            # Oblicz odległość do każdego punktu
            dists = np.hypot(xys_disp[:, 0] - ex, xys_disp[:, 1] - ey)
            idx = int(np.argmin(dists))
            min_dist = float(dists[idx])
            
            if min_dist <= self._hover_threshold_px:
                x, y = self._chart_points[idx]
                rec = None
                try:
                    rec = self._chart_records[idx]
                except Exception:
                    pass
                
                currency_symbol = getattr(self.controller, 'currency_symbol', 'zł')
                price_txt = f"{y:.2f} {currency_symbol}" if y is not None else "N/A"
                
                # Data
                if isinstance(x, datetime.datetime):
                    dt_str = x.strftime('%Y-%m-%d %H:%M')
                else:
                    try:
                        dt = mdates.num2date(x)
                        dt_str = dt.strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        dt_str = str(x)
                
                # Użyj sale_date_str z rekordu jeśli dostępne
                if rec and isinstance(rec, dict):
                    dt_str = rec.get('sale_date_str', dt_str)
                
                text = f"Data: {dt_str}\nCena: {price_txt}"
                
                # Ustaw pozycję bazową
                self._hover_annot.xy = (x, y)
                off_x, off_y = 12, 12
                ha, va = 'left', 'bottom'
                self._hover_annot.set_position((off_x, off_y))
                try:
                    self._hover_annot.set_ha(ha)
                    self._hover_annot.set_va(va)
                except Exception:
                    pass
                
                # Sprawdź czy tooltip wychodzi poza canvas i odbij jeśli tak
                try:
                    canvas = self.chart_canvas.get_tk_widget()
                    canvas_w = max(1, int(canvas.winfo_width()))
                    canvas_h = max(1, int(canvas.winfo_height()))
                    pad_px = 4
                    
                    renderer = None
                    try:
                        renderer = self.fig.canvas.get_renderer()
                    except Exception:
                        pass
                    if renderer is None:
                        try:
                            self.chart_canvas.draw()
                            renderer = self.fig.canvas.get_renderer()
                        except Exception:
                            renderer = None
                    
                    if renderer is not None:
                        self._hover_annot.set_text(text)
                        bbox = self._hover_annot.get_window_extent(renderer=renderer)
                        need_flip_x = bbox.x1 > canvas_w - pad_px
                        need_flip_y_top = bbox.y1 > canvas_h - pad_px
                        need_flip_y_bottom = bbox.y0 < pad_px
                        
                        # Odbij w poziomie jeśli wychodzi za prawą krawędź
                        if need_flip_x:
                            off_x = -12
                            ha = 'right'
                        # Odbij w pionie
                        if need_flip_y_top:
                            off_y = -12
                            va = 'top'
                        elif need_flip_y_bottom:
                            off_y = 12
                            va = 'bottom'
                        
                        try:
                            self._hover_annot.set_position((off_x, off_y))
                            self._hover_annot.set_ha(ha)
                            self._hover_annot.set_va(va)
                        except Exception:
                            pass
                except Exception:
                    pass
                
                self._hover_annot.set_text(text)
                self._hover_annot.set_visible(True)
                
                # Pokaż zieloną kropkę na punkcie
                try:
                    if hasattr(self, '_hover_dot') and self._hover_dot is not None:
                        import matplotlib.dates as mdates_inner
                        sx = mdates.date2num(x) if isinstance(x, datetime.datetime) else x
                        self._hover_dot.set_offsets([[sx, y]])
                        self._hover_dot.set_visible(True)
                except Exception:
                    pass
                
                self.chart_canvas.draw_idle()
            else:
                if self._hover_annot and self._hover_annot.get_visible():
                    self._hover_annot.set_visible(False)
                    # Ukryj kropkę
                    try:
                        if hasattr(self, '_hover_dot') and self._hover_dot is not None and self._hover_dot.get_visible():
                            self._hover_dot.set_visible(False)
                    except Exception:
                        pass
                    self.chart_canvas.draw_idle()
        except Exception as e:
            pass

    def _convert_price(self, price_pln):
        """Konwertuje cenę z PLN na wybraną walutę."""
        if price_pln is None:
            return None
        currency = getattr(self.controller, 'currency', 'PLN')
        rate = EXCHANGE_RATES.get(currency, 1.0)
        return price_pln * rate

    # ===================== HISTORY SORTING =====================
    
    def _initial_history_sort(self):
        """Ustaw wstępne sortowanie: daty malejąco (najnowsze)."""
        if not self.history_data:
            return
        # daty malejąco (najnowsze pierwsze)
        self.history_data.sort(key=lambda r: r.get('sale_timestamp', 0), reverse=True)
        self._history_last_sorted = 'sale_timestamp'
        self._update_history_headers(active='sale_timestamp', ascending=False)
    
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
            # data: ascending True => najnowsze pierwsze (timestamp malejąco)
            self.history_data.sort(key=lambda r: r.get('sale_timestamp', 0), reverse=ascending)
        
        # toggle kierunek na następną interakcję
        self._history_sort_states[field] = not ascending
        self._history_last_sorted = field
        
        # aktualizuj nagłówki strzałkami
        self._update_history_headers(active=field, ascending=ascending if field=='price' else (not ascending))
        
        # Reset do pierwszej strony i odśwież
        self.history_current_page = 0
        self._fill_history()
    
    def _update_history_headers(self, active=None, ascending=True):
        """Aktualizuje tekst nagłówków z symbolami kierunku sortowania."""
        try:
            price_text = "Cena Sprzedaży"
            date_text = "Data sprzedaży"
            
            if active == 'price':
                price_text += ' ↑' if ascending else ' ↓'
            elif active == 'sale_timestamp':
                date_text += ' ↑' if ascending else ' ↓'
            
            self.history_price_header.config(text=price_text)
            self.history_date_header.config(text=date_text)
        except Exception as e:
            print(f"Błąd aktualizacji nagłówków sortowania: {e}", file=sys.stderr)

    # ===================== LISTINGS METHODS =====================
    
    def _fill_listings(self):
        """Wypełnia sekcję ofert."""
        for widget in self.listings_container.winfo_children():
            widget.destroy()
        
        # Inicjalizacja cache dla nowego przedmiotu
        if not self._page_cache:
            initial = self.listings_data.get('listings', [])
            self._page_cache[0] = initial
            self._all_listings = initial
        else:
            self._all_listings = self._page_cache.get(self.current_page, [])
        
        total_count = self.listings_data.get('total_count', len(self._all_listings))
        currency_symbol = getattr(self.controller, 'currency_symbol', 'zł')
        currency = getattr(self.controller, 'currency', 'PLN')
        rate = EXCHANGE_RATES.get(currency, 1.0)
        
        if not self._all_listings:
            no_data = tk.Label(self.listings_container, text="Brak aktualnych ofert", 
                              bg='#1e1e1e', fg='#888888', font=('Segoe UI', 10))
            no_data.pack(pady=20)
            self.listings_page_info.config(text="[Brak ofert]")
            return
        
        # Wyświetl oferty z bieżącej strony
        for i, listing in enumerate(self._all_listings):
            row_bg = '#1e1e1e' if i % 2 == 0 else '#252525'
            row = tk.Frame(self.listings_container, bg=row_bg)
            row.pack(fill='x')
            
            # Numer
            base_index = self.current_page * self.page_size
            tk.Label(row, text=f"{base_index + i + 1}.", width=5, bg=row_bg, fg='#888888',
                    font=('Segoe UI', 10)).pack(side='left')
            
            # Nazwa
            name = self.current_item_name
            tk.Label(row, text=name, width=40, bg=row_bg, fg='#ffffff',
                    font=('Segoe UI', 10), anchor='center').pack(side='left', expand=True)
            
            # Cena - konwersja waluty
            price_float = listing.get('price_float', 0) or 0
            price_converted = price_float * rate
            tk.Label(row, text=f"{price_converted:.2f}{currency_symbol}", width=15, bg=row_bg, fg='#ffffff',
                    font=('Segoe UI', 10), anchor='center').pack(side='left')
            
            # Prowizja - konwersja waluty
            fee = listing.get('fee', 0) or 0
            fee_converted = fee * rate
            tk.Label(row, text=f"{fee_converted:.2f}{currency_symbol}", width=15, bg=row_bg, fg='#888888',
                    font=('Segoe UI', 10), anchor='center').pack(side='left')
        
        # Aktualizuj info o stronie
        total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        self.listings_page_info.config(text=f"[Łącznie {total_count} ofert]\nStrona {self.current_page + 1}/{total_pages}")
        
        # Prefetch następnej strony
        self._maybe_prefetch_next()

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
                data = steam_market.get_market_listings_page(
                    self.current_item_name, 
                    self.controller.login_cookie, 
                    start=next_start, 
                    count=self.page_size
                )
                # Zapis tylko jeśli nadal oglądamy ten sam przedmiot
                if data and data.get('listings') and self._cache_item_key == item_key:
                    self._page_cache[next_page] = data['listings']
                    try:
                        self.controller.result_queue.put({
                            'status': 'log', 
                            'message': f'Prefetch: strona {next_page + 1} gotowa.'
                        })
                    except Exception:
                        pass
                self._pages_loading.discard(next_page)
            
            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            print(f"Prefetch błąd: {e}", file=sys.stderr)

    def _prev_listings_page(self):
        if self._loading_page:
            return
        if self.current_page > 0:
            target_page = self.current_page - 1
            if target_page in self._page_cache:
                self._goto_listings_page(target_page)
            else:
                self._fetch_page(target_page * self.page_size)
    
    def _next_listings_page(self):
        if self._loading_page:
            return
        total_count = self.listings_data.get('total_count', len(self._all_listings))
        target_page = self.current_page + 1
        start = target_page * self.page_size
        if start >= total_count:
            return
        if target_page in self._page_cache:
            self._goto_listings_page(target_page)
        else:
            self._fetch_page(start)
    
    def _goto_listings_page(self, page):
        if self._loading_page:
            return
        total_count = self.listings_data.get('total_count', len(self._all_listings))
        max_page = max(0, (total_count - 1) // self.page_size)
        if page < 0 or page > max_page:
            return
        if page == self.current_page:
            return
        if page in self._page_cache:
            self.current_page = page
            self._all_listings = self._page_cache.get(self.current_page, [])
            self._fill_listings()
        else:
            self._fetch_page(page * self.page_size)
    
    def _goto_listings_last_page(self):
        if self._loading_page:
            return
        total_count = self.listings_data.get('total_count', len(self._all_listings))
        last_page = max(0, (total_count - 1) // self.page_size)
        if last_page == self.current_page:
            return
        if last_page in self._page_cache:
            self._goto_listings_page(last_page)
        else:
            self._fetch_page(last_page * self.page_size)

    def _fetch_page(self, start):
        """Pobiera stronę ofert z API."""
        self._loading_page = True
        self._show_loading_overlay()
        item_key = self._cache_item_key
        
        def worker():
            data = None
            try:
                data = steam_market.get_market_listings_page(
                    self.current_item_name, 
                    self.controller.login_cookie, 
                    start=start, 
                    count=self.page_size
                )
            except Exception as e:
                print(f"Błąd pobierania strony ofert: {e}", file=sys.stderr)
            
            def apply():
                self._loading_page = False
                self._hide_loading_overlay()
                
                # Jeśli użytkownik przełączył przedmiot w trakcie pobierania strony – porzuć
                if self._cache_item_key != item_key:
                    return
                
                if data is None:
                    return
                
                page_idx = start // self.page_size
                self._all_listings = data.get('listings', [])
                
                # Log do SearchView
                try:
                    self.controller.result_queue.put({
                        'status': 'log', 
                        'message': f'Oferty: załadowano stronę {page_idx + 1} z sieci.'
                    })
                except Exception:
                    pass
                
                # Zapis do cache
                self._page_cache[page_idx] = self._all_listings
                self.listings_data['listings'] = self._all_listings
                self.listings_data['total_count'] = data.get('total_count', self.listings_data.get('total_count', len(self._all_listings)))
                self.current_page = page_idx
                self._fill_listings()
            
            self.controller.root.after(0, apply)
        
        threading.Thread(target=worker, daemon=True).start()

    def _show_loading_overlay(self):
        """Pokazuje overlay ładowania na liście ofert."""
        try:
            if hasattr(self, '_loading_overlay') and self._loading_overlay:
                self._loading_overlay.destroy()
            
            self._loading_overlay = tk.Frame(self.listings_container, bg='#1e1e1e')
            self._loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            
            tk.Label(self._loading_overlay, text="⏳ Ładowanie...", 
                    bg='#1e1e1e', fg='#5588cc', font=('Segoe UI', 12)).pack(expand=True)
        except Exception as e:
            print(f"Overlay błąd: {e}", file=sys.stderr)

    def _hide_loading_overlay(self):
        """Ukrywa overlay ładowania."""
        try:
            if hasattr(self, '_loading_overlay') and self._loading_overlay:
                self._loading_overlay.destroy()
                self._loading_overlay = None
        except Exception:
            pass

    # ===================== HISTORY METHODS =====================
    
    def _toggle_history(self):
        """Przełącza widoczność sekcji historii."""
        if self.history_expanded:
            self.history_frame.pack_forget()
            self.history_expanded = False
        else:
            self.history_frame.pack(fill='x', after=self.history_toggle_label.master)
            self.history_expanded = True
            self._fill_history()
    
    def _fill_history(self):
        """Wypełnia tabelę historii."""
        for widget in self.history_rows_container.winfo_children():
            widget.destroy()
        
        if not self.history_data:
            no_data = tk.Label(self.history_rows_container, text="Brak danych historycznych",
                              bg='#1e1e1e', fg='#888888')
            no_data.pack(pady=10)
            return
        
        currency_symbol = getattr(self.controller, 'currency_symbol', 'zł')
        
        # Parsuj nazwę przedmiotu
        parts = self._parse_item_name(self.current_item_name)
        
        # Paginacja
        start = self.history_current_page * self.history_page_size
        end = start + self.history_page_size
        page_data = self.history_data[start:end]
        
        for i, record in enumerate(page_data):
            row_bg = '#1e1e1e' if i % 2 == 0 else '#252525'
            row = tk.Frame(self.history_rows_container, bg=row_bg)
            row.pack(fill='x')
            
            # Typ (broń)
            tk.Label(row, text=parts.get('weapon', '-'), width=12, bg=row_bg, fg='#ffffff',
                    font=('Segoe UI', 10)).pack(side='left')
            
            # Nazwa (skin)
            tk.Label(row, text=parts.get('skin', '-'), width=20, bg=row_bg, fg='#ffffff',
                    font=('Segoe UI', 10)).pack(side='left', expand=True)
            
            # Jakość
            tk.Label(row, text=parts.get('wear', '-'), width=15, bg=row_bg, fg='#ffffff',
                    font=('Segoe UI', 10)).pack(side='left')
            
            # Cena
            price = record.get('price', 0)
            if not self._history_from_api:
                price = self._convert_price(price)
            tk.Label(row, text=f"{price:.2f}{currency_symbol}", width=15, bg=row_bg, fg='#ffffff',
                    font=('Segoe UI', 10)).pack(side='left')
            
            # Data
            date_str = record.get('sale_date_str', '-')
            tk.Label(row, text=date_str, width=18, bg=row_bg, fg='#ffffff',
                    font=('Segoe UI', 10)).pack(side='left')
        
        # Aktualizuj etykietę strony
        total_pages = max(1, (len(self.history_data) + self.history_page_size - 1) // self.history_page_size)
        self.history_page_label.config(text=f"Strona {self.history_current_page + 1}/{total_pages}")

    def _history_goto_first(self):
        """Przechodzi do pierwszej strony historii."""
        if self.history_current_page > 0:
            self.history_current_page = 0
            self._fill_history()
    
    def _history_goto_prev(self):
        """Przechodzi do poprzedniej strony historii."""
        if self.history_current_page > 0:
            self.history_current_page -= 1
            self._fill_history()
    
    def _history_goto_next(self):
        """Przechodzi do następnej strony historii."""
        total_pages = max(1, (len(self.history_data) + self.history_page_size - 1) // self.history_page_size)
        if self.history_current_page < total_pages - 1:
            self.history_current_page += 1
            self._fill_history()
    
    def _history_goto_last(self):
        """Przechodzi do ostatniej strony historii."""
        total_pages = max(1, (len(self.history_data) + self.history_page_size - 1) // self.history_page_size)
        if self.history_current_page < total_pages - 1:
            self.history_current_page = total_pages - 1
            self._fill_history()

    def _parse_item_name(self, name):
        """Parsuje nazwę przedmiotu na komponenty."""
        result = {'weapon': '-', 'skin': '-', 'wear': '-'}
        
        if not name:
            return result
        
        # Usuń prefiks StatTrak/Souvenir
        clean_name = name
        if name.startswith('StatTrak™ '):
            clean_name = name[10:]
        elif name.startswith('Souvenir '):
            clean_name = name[9:]
        
        # Szukaj jakości w nawiasie
        import re
        wear_match = re.search(r'\((Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)', clean_name)
        if wear_match:
            result['wear'] = f"({wear_match.group(1)})"
            clean_name = clean_name[:wear_match.start()].strip()
        
        # Podziel na broń i skin
        if ' | ' in clean_name:
            parts = clean_name.split(' | ', 1)
            result['weapon'] = parts[0]
            result['skin'] = parts[1] if len(parts) > 1 else '-'
        else:
            result['weapon'] = clean_name
        
        return result

    # ===================== MAIN SHOW METHOD =====================
    
    def show_results(self, item_name, history_data, listings_data, fresh_history=None, currency_code=None):
        """Główna metoda wyświetlająca wyniki."""
        self.current_item_name = item_name
        self.history_data = fresh_history if fresh_history else (history_data or [])
        self._history_from_api = bool(fresh_history)
        self.listings_data = listings_data or {}
        self.current_page = 0
        self.history_current_page = 0
        self.history_expanded = False
        
        # Reset cache dla nowego przedmiotu
        self._page_cache = {}
        self._pages_loading = set()
        self._cache_item_key = item_name
        self._loading_page = False
        
        # Ukryj sekcję historii
        self.history_frame.pack_forget()
        
        # Tytuł
        self.title_label.config(text=item_name)
        
        # Aktualizuj avatar
        self._setup_avatar()
        steam_name = getattr(self.controller, 'steam_name', None) or 'Użytkownik'
        self.welcome_label.config(text=f"Witaj,\n{steam_name}")
        
        # Ceny
        currency_symbol = getattr(self.controller, 'currency_symbol', 'zł')
        currency = getattr(self.controller, 'currency', 'PLN')
        rate = EXCHANGE_RATES.get(currency, 1.0)
        
        lowest_price_float = self.listings_data.get('lowest_price_float')
        if lowest_price_float is not None:
            converted_lowest = lowest_price_float * rate
            self.lowest_offer_value.config(text=f"{converted_lowest:.2f} {currency_symbol}")
        else:
            self.lowest_offer_value.config(text="-")
        
        # Min/max historyczne
        if self.history_data:
            min_rec = min(self.history_data, key=lambda r: r.get('price', float('inf')))
            max_rec = max(self.history_data, key=lambda r: r.get('price', 0))
            
            min_price = min_rec.get('price', 0)
            max_price = max_rec.get('price', 0)
            if not self._history_from_api:
                min_price = self._convert_price(min_price)
                max_price = self._convert_price(max_price)
            
            self.min_hist_price.config(text=f"{min_price:.2f} {currency_symbol}")
            self.min_hist_date.config(text=min_rec.get('sale_date_str', '-'))
            self.max_hist_price.config(text=f"{max_price:.2f} {currency_symbol}")
            self.max_hist_date.config(text=max_rec.get('sale_date_str', '-'))
        else:
            self.min_hist_price.config(text="-")
            self.min_hist_date.config(text="-")
            self.max_hist_price.config(text="-")
            self.max_hist_date.config(text="-")
        
        # Obrazek
        self._load_item_image()
        
        # Wykres
        self._plot_chart('all')
        
        # Sortuj historię (najnowsze pierwsze)
        self._initial_history_sort()
        
        # Oferty
        self._fill_listings()
        
        # Scroll na górę
        self.main_canvas.yview_moveto(0)

    def _load_item_image(self):
        """Ładuje obrazek przedmiotu."""
        image_url = self.listings_data.get('image_url') if isinstance(self.listings_data, dict) else None
        
        if not image_url or not HAS_PIL:
            self.image_label.config(image='', text='(Brak obrazka)')
            return
        
        # Sprawdź cache
        cached = self._image_cache.get(image_url)
        if cached:
            self._current_item_image = cached
            self.image_label.config(image=self._current_item_image, text='')
            return
        
        # Pobierz asynchronicznie
        def download():
            try:
                resp = requests.get(image_url, timeout=15)
                if resp.status_code == 200:
                    img = Image.open(BytesIO(resp.content))
                    # Skaluj do 250px szerokości zachowując proporcje
                    max_w = 250
                    w, h = img.size
                    if w > max_w:
                        new_h = int(h * (max_w / float(w)))
                        img = img.resize((max_w, new_h), Image.LANCZOS)
                    
                    def apply():
                        try:
                            tkimg = ImageTk.PhotoImage(img)
                            self._image_cache[image_url] = tkimg
                            if len(self._image_cache) > self._image_cache_limit:
                                self._image_cache.popitem(last=False)
                            self._current_item_image = tkimg
                            self.image_label.config(image=self._current_item_image, text='')
                        except Exception:
                            pass
                    self.controller.root.after(0, apply)
            except Exception:
                pass
        
        threading.Thread(target=download, daemon=True).start()

    # ===================== DROPDOWN MENU UŻYTKOWNIKA =====================
    def _toggle_dropdown_menu(self, event=None):
        """Pokazuje lub ukrywa menu dropdown."""
        if self.dropdown_visible:
            self._hide_dropdown_menu()
        else:
            self._show_dropdown_menu()
        return "break"  # Zapobiega propagacji zdarzenia

    def _show_dropdown_menu(self):
        """Wyświetla menu dropdown pod strzałką."""
        if self.dropdown_menu:
            self._hide_dropdown_menu()

        # Utwórz menu jako Toplevel
        self.dropdown_menu = tk.Toplevel(self.controller.root)
        self.dropdown_menu.overrideredirect(True)  # Bez ramki okna
        self.dropdown_menu.configure(bg='#2a2a2a')
        self.dropdown_menu.attributes('-topmost', True)

        # Pozycja menu - pod strzałką
        try:
            x = self.dropdown_arrow.winfo_rootx()
            y = self.dropdown_arrow.winfo_rooty() + self.dropdown_arrow.winfo_height() + 5
        except Exception:
            x, y = 100, 100

        # Ramka menu
        menu_frame = tk.Frame(self.dropdown_menu, bg='#2a2a2a', highlightbackground='#5588cc', highlightthickness=1)
        menu_frame.pack(fill='both', expand=True)

        # Aktualna waluta
        current_currency = getattr(self.controller, 'currency', 'PLN')

        # Opcja: Zmień walutę
        currency_btn = tk.Label(
            menu_frame, text=f"💱 Zmień walutę: {current_currency}",
            bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 10),
            padx=16, pady=8, cursor='hand2', anchor='w'
        )
        currency_btn.pack(fill='x')
        currency_btn.bind('<Enter>', lambda e: currency_btn.config(bg='#3a3a3a'))
        currency_btn.bind('<Leave>', lambda e: currency_btn.config(bg='#2a2a2a'))
        currency_btn.bind('<Button-1>', lambda e: self._on_currency_option_click())

        # Separator
        sep = tk.Frame(menu_frame, bg='#444444', height=1)
        sep.pack(fill='x', padx=8)

        # Opcja: Wyloguj
        logout_btn = tk.Label(
            menu_frame, text="🚪 Wyloguj",
            bg='#2a2a2a', fg='#ff6666', font=('Segoe UI', 10),
            padx=16, pady=8, cursor='hand2', anchor='w'
        )
        logout_btn.pack(fill='x')
        logout_btn.bind('<Enter>', lambda e: logout_btn.config(bg='#3a3a3a'))
        logout_btn.bind('<Leave>', lambda e: logout_btn.config(bg='#2a2a2a'))
        logout_btn.bind('<Button-1>', lambda e: self._on_logout_click())

        self.dropdown_menu.geometry(f"+{x}+{y}")
        self.dropdown_visible = True

        # Opóźnione bindowanie - zamknij menu po kliknięciu poza nim
        self.controller.root.after(100, self._bind_outside_click)

    def _bind_outside_click(self):
        """Binduje kliknięcie poza menu z opóźnieniem."""
        try:
            self.controller.root.bind('<Button-1>', self._on_click_outside_dropdown, add='+')
        except Exception:
            pass

    def _hide_dropdown_menu(self):
        """Ukrywa menu dropdown."""
        if self.dropdown_menu:
            try:
                self.dropdown_menu.destroy()
            except Exception:
                pass
            self.dropdown_menu = None
        self.dropdown_visible = False
        try:
            self.controller.root.unbind('<Button-1>')
        except Exception:
            pass

    def _on_click_outside_dropdown(self, event):
        """Zamyka dropdown jeśli kliknięto poza nim."""
        if not self.dropdown_menu:
            return
        try:
            # Sprawdź czy kliknięto w menu
            if self.dropdown_menu.winfo_exists():
                menu_x = self.dropdown_menu.winfo_rootx()
                menu_y = self.dropdown_menu.winfo_rooty()
                menu_w = self.dropdown_menu.winfo_width()
                menu_h = self.dropdown_menu.winfo_height()
                click_x = event.x_root
                click_y = event.y_root
                if not (menu_x <= click_x <= menu_x + menu_w and menu_y <= click_y <= menu_y + menu_h):
                    # Sprawdź czy nie kliknięto w strzałkę/nazwę (toggle)
                    arrow_x = self.dropdown_arrow.winfo_rootx()
                    arrow_y = self.dropdown_arrow.winfo_rooty()
                    arrow_w = self.dropdown_arrow.winfo_width() + self.welcome_label.winfo_width() + 20
                    arrow_h = max(self.dropdown_arrow.winfo_height(), self.welcome_label.winfo_height())
                    if not (arrow_x - 10 <= click_x <= arrow_x + arrow_w and arrow_y <= click_y <= arrow_y + arrow_h):
                        self._hide_dropdown_menu()
        except Exception:
            self._hide_dropdown_menu()

    def _on_currency_option_click(self):
        """Obsługuje kliknięcie opcji zmiany waluty."""
        self._hide_dropdown_menu()
        self._show_currency_modal()

    def _on_logout_click(self):
        """Obsługuje kliknięcie opcji wylogowania."""
        self._hide_dropdown_menu()
        # Wyczyść dane sesji
        self.controller.clear_auth_state()
        # Zresetuj lokalny avatar canvas do placeholdera
        try:
            self.avatar_canvas.delete('all')
            self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1, tags='default_frame')
            self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', font=('Segoe UI', 7), justify='center', tags='placeholder')
        except Exception:
            pass
        # Przejdź do ekranu logowania
        self.controller.switch_view('login')

    # ===================== MODAL ZMIANY WALUTY =====================
    def _show_currency_modal(self):
        """Wyświetla modal do zmiany waluty."""
        # Overlay - przyciemnione tło (bez alpha całego okna!)
        self.currency_overlay = tk.Frame(self.controller.root, bg='#1a1a1a')
        self.currency_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.currency_overlay.lift()
        
        # Tło overlay z bindowaniem kliknięcia
        overlay_bg = tk.Frame(self.currency_overlay, bg='#1a1a1a')
        overlay_bg.place(x=0, y=0, relwidth=1, relheight=1)
        overlay_bg.bind('<Button-1>', lambda e: self._close_currency_modal())

        # Modal - okienko na środku
        self.currency_modal = tk.Frame(self.currency_overlay, bg='#2a2a2a', highlightbackground='#5588cc', highlightthickness=2)
        self.currency_modal.place(relx=0.5, rely=0.5, anchor='center')

        # Tytuł
        tk.Label(self.currency_modal, text="Zmień walutę", bg='#2a2a2a', fg='#ffffff',
                 font=('Segoe UI', 14, 'bold')).pack(pady=(20, 16), padx=40)

        # Aktualna waluta
        current_currency = getattr(self.controller, 'currency', 'PLN')
        info_label = tk.Label(self.currency_modal, text=f"Aktualna waluta: {current_currency}", 
                              bg='#2a2a2a', fg='#888888', font=('Segoe UI', 10))
        info_label.pack(pady=(0, 16))

        # Przyciski walut
        currencies = [('PLN', 'zł'), ('USD', '$'), ('EUR', '€')]
        btn_frame = tk.Frame(self.currency_modal, bg='#2a2a2a')
        btn_frame.pack(pady=(0, 20))
        
        for curr, symbol in currencies:
            is_selected = curr == current_currency
            btn_bg = '#5588cc' if is_selected else '#3a3a3a'
            btn = tk.Label(
                btn_frame, text=f"{curr} ({symbol})",
                bg=btn_bg, fg='#ffffff', font=('Segoe UI', 12),
                padx=20, pady=10, cursor='hand2',
                relief='flat', borderwidth=0
            )
            btn.pack(side='left', padx=8)
            if not is_selected:
                btn.bind('<Enter>', lambda e, b=btn: b.config(bg='#4a4a4a'))
                btn.bind('<Leave>', lambda e, b=btn: b.config(bg='#3a3a3a'))
            btn.bind('<Button-1>', lambda e, c=curr: self._select_currency(c))

        # Przycisk Anuluj
        cancel_btn = tk.Label(
            self.currency_modal, text="Anuluj",
            bg='#2a2a2a', fg='#888888', font=('Segoe UI', 10),
            cursor='hand2'
        )
        cancel_btn.pack(pady=(0, 20))
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(fg='#ffffff'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(fg='#888888'))
        cancel_btn.bind('<Button-1>', lambda e: self._close_currency_modal())

    def _select_currency(self, currency):
        """Wybiera walutę i zamyka modal."""
        # Mapowanie walut na symbole
        currency_symbols = {
            'PLN': 'zł',
            'USD': '$',
            'EUR': '€'
        }
        
        self.controller.currency = currency
        self.controller.currency_symbol = currency_symbols.get(currency, 'zł')
        self._close_currency_modal()
        # Odśwież widok z nową walutą
        self._refresh_with_currency()

    def _close_currency_modal(self):
        """Zamyka modal zmiany waluty."""
        try:
            if hasattr(self, 'currency_overlay') and self.currency_overlay:
                self.currency_overlay.destroy()
                self.currency_overlay = None
            if hasattr(self, 'currency_modal') and self.currency_modal:
                self.currency_modal = None
        except Exception:
            pass

    def _refresh_with_currency(self):
        """Odświeża dane z nową walutą."""
        if self.history_data and self.current_item_name:
            self.show_results(self.current_item_name, self.history_data, self.listings_data)

    def _open_steam_market_page(self):
        """Otwiera stronę Steam Market z aktualnym przedmiotem w przeglądarce."""
        import webbrowser
        import urllib.parse
        
        if not self.current_item_name:
            return
        
        # Zakoduj nazwę przedmiotu dla URL
        encoded_name = urllib.parse.quote(self.current_item_name)
        url = f"https://steamcommunity.com/market/listings/730/{encoded_name}"
        
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Błąd otwierania przeglądarki: {e}", file=sys.stderr)

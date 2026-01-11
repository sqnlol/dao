import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import threading
import sys 
import time 
import importlib

from src import steam_market
from src import database
from src.debug_logger import logger
from src.skin_list import (
    SKIN_DATA, WEAPON_CATEGORIES,
    GLOVES, STICKERS, ZEUS_SKINS, GRAFFITI, AGENTS, CONTAINERS, OTHER_TYPES,
    ZEUS_WEAR_MAP, WEAPON_WEAR_MAP, WEAPON_SOUVENIR_MAP, WEAPON_STATTRAK_MAP,
    KNIVES, MUSIC_KITS, MUSIC_KITS_STATTRAK, KEY_ITEMS, CHARM_ITEMS,
    VIEWER_PASSES, OPERATION_PASSES, COLLECTIBLE_PINS, GIFT_ITEMS, PATCH_ITEMS,
    TOOL_ITEMS
)


class SearchView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        # Główna ramka – ciemne tło
        self.frame = tk.Frame(master, bg='#1e1e1e')
        self.frame.grid(row=0, column=0, sticky="nsew") 
        
        self.frame.grid_rowconfigure(1, weight=1)  # środek rozciągalny
        self.frame.grid_columnconfigure(0, weight=1)

        self._create_widgets()
        # Dane rozszerzonych kategorii dostarczane przez skin_list.py (brak lokalnych struktur)
        
    def _create_widgets(self):
        # ===================== STYLE =====================
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass

        # Ciemne tło ramek i etykiet
        style.configure('Search.TFrame', background='#1e1e1e')
        style.configure('Search.TLabel', background='#1e1e1e', foreground='#ffffff')
        style.configure('SearchGray.TLabel', background='#1e1e1e', foreground='#888888')
        style.configure('SearchHeader.TLabel', background='#1e1e1e', foreground='#ffffff', font=('Segoe UI', 14))
        style.configure('SearchTab.TLabel', background='#1e1e1e', foreground='#ffffff', font=('Segoe UI', 12))

        # Ciemne LabelFrame z niebieskim obramowaniem
        style.configure('SearchLF.TLabelframe', background='#1e1e1e', bordercolor='#5588cc', relief='solid')
        style.configure('SearchLF.TLabelframe.Label', background='#1e1e1e', foreground='#88bbff', font=('Segoe UI', 10))

        # Ciemne Combobox – ciemne pole, biały tekst
        style.configure('Dark.TCombobox', fieldbackground='#3a3a3a', background='#3a3a3a', foreground='#ffffff', arrowcolor='#ffffff')
        style.map('Dark.TCombobox', fieldbackground=[('readonly', '#3a3a3a')], foreground=[('readonly', '#ffffff')])

        # Checkboxy w odpowiednich kolorach
        style.configure('SearchCheck.TCheckbutton', background='#1e1e1e', foreground='#00cccc', font=('Segoe UI', 10))
        style.map('SearchCheck.TCheckbutton', background=[('active', '#1e1e1e')])

        # Przycisk Szukaj – niebieskofioletowy
        style.configure('Search.TButton', background='#6688cc', foreground='#1e1e1e', font=('Segoe UI', 14, 'bold'), padding=(24, 12))
        style.map('Search.TButton', background=[('active', '#7799dd')])

        # Przycisk akcji (mniejszy)
        style.configure('Action.TButton', borderwidth=2, padding=8)

        # ===================== NAGŁÓWEK (row 0) =====================
        header = tk.Frame(self.frame, bg='#1e1e1e')
        header.grid(row=0, column=0, sticky='ew', padx=0)
        header.grid_columnconfigure(2, weight=1)

        # Logo placeholder (możesz zastąpić własnym obrazkiem)
        try:
            import os
            from PIL import Image, ImageTk
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'CS2SkinAnalyzer.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img.thumbnail((48, 48))
                self._header_logo = ImageTk.PhotoImage(img)
                logo_lbl = tk.Label(header, image=self._header_logo, bg='#1e1e1e')
                logo_lbl.grid(row=0, column=0, padx=(12, 12), pady=6)
        except Exception:
            pass

        # Zakładki
        tk.Label(header, text="Wyszukiwarka", bg='#1e1e1e', fg='#ffffff', font=('Segoe UI', 14)).grid(row=0, column=1, padx=(0, 24))
        cases_lbl = tk.Label(header, text="Skrzynie", bg='#1e1e1e', fg='#888888', font=('Segoe UI', 14), cursor='hand2')
        cases_lbl.grid(row=0, column=2, sticky='w')
        cases_lbl.bind('<Button-1>', lambda e: self.controller.switch_view('cases'))

        # Prawa strona: powitanie + dropdown + avatar
        right_group = tk.Frame(header, bg='#1e1e1e')
        right_group.grid(row=0, column=3, sticky='e')

        # Kontener na nazwę i strzałkę
        user_dropdown_frame = tk.Frame(right_group, bg='#1e1e1e', cursor='hand2')
        user_dropdown_frame.pack(side='left', padx=(0, 8))

        self.welcome_label = tk.Label(user_dropdown_frame, text=f"Witaj,\n{self.controller.steam_name}", bg='#1e1e1e', fg='#ffffff', font=('Segoe UI', 10), justify='right')
        self.welcome_label.pack(side='left')

        # Strzałka w dół
        self.dropdown_arrow = tk.Label(user_dropdown_frame, text="▼", bg='#1e1e1e', fg='#888888', font=('Segoe UI', 8), cursor='hand2')
        self.dropdown_arrow.pack(side='left', padx=(4, 0))

        # Menu dropdown (ukryte domyślnie)
        self.dropdown_menu = None
        self.dropdown_visible = False

        # Bindowanie kliknięcia na cały obszar
        for widget in (user_dropdown_frame, self.welcome_label, self.dropdown_arrow):
            widget.bind('<Button-1>', self._toggle_dropdown_menu)

        # Avatar (canvas dla obrazka i ramki Steam)
        self.avatar_canvas = tk.Canvas(right_group, width=52, height=52, bg='#1e1e1e', highlightthickness=0)
        self.avatar_canvas.pack(side='left')
        self._avatar_photo = None  # Przechowuje referencję do PhotoImage avatara
        self._frame_photo = None   # Przechowuje referencję do PhotoImage ramki
        # Domyślna ramka (niebieska)
        self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1, tags='default_frame')
        self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', font=('Segoe UI', 7), justify='center', tags='placeholder')
        # Spróbuj załadować avatar z URL
        self._load_avatar_async()

        # Niebieska linia pozioma pod headerem
        separator = tk.Frame(self.frame, bg='#5588cc', height=2)
        separator.grid(row=0, column=0, sticky='sew', padx=0, pady=(60, 0))

        # Ukryte elementy interfejsu starego (zachowane do kompatybilności)
        self.cookie_mode_label = tk.Label(self.frame, text="", bg='#1e1e1e', fg='#888888')
        self.logout_button = None  # placeholder – usunięty z widoku

        # ===================== ŚRODKOWA SEKCJA FORMULARZA (row 1) =====================
        center_wrapper = tk.Frame(self.frame, bg='#1e1e1e')
        center_wrapper.grid(row=1, column=0, sticky='nsew')
        center_wrapper.grid_rowconfigure(0, weight=1)
        center_wrapper.grid_columnconfigure(0, weight=1)

        form_container = tk.Frame(center_wrapper, bg='#1e1e1e')
        form_container.place(relx=0.5, rely=0.45, anchor='center')

        # --- Wiersz 1: Kategoria przedmiotu + Opcje ---
        self.row1 = tk.Frame(form_container, bg='#1e1e1e')
        self.row1.pack(pady=(0, 16))

        # Kategoria przedmiotu (LabelFrame)
        self.cat_lf = ttk.LabelFrame(self.row1, text="Kategoria przedmiotu", style='SearchLF.TLabelframe', padding=(12, 8))
        self.cat_lf.pack(side='left', padx=(0, 24))

        categories = sorted(list(WEAPON_CATEGORIES.keys()))
        if 'Skrzynki' in categories and 'Pojemnik' not in categories:
            categories = [c for c in categories if c != 'Skrzynki'] + ['Pojemnik']
        extra_cats = ['Rękawice', 'Naklejka', 'Zeus x27', 'Graffiti', 'Agent', 'Inne']
        for ec in extra_cats:
            if ec not in categories:
                categories.append(ec)
        categories = sorted(categories)

        self.category_combo = ttk.Combobox(self.cat_lf, values=categories, state='readonly', width=36, style='Dark.TCombobox')
        self.category_combo.pack()
        if categories:
            self.category_combo.set(categories[0])

        # Opcje (StatTrak / Souvenir)
        self.opt_lf = ttk.LabelFrame(self.row1, text="Opcje", style='SearchLF.TLabelframe', padding=(12, 8))
        self.opt_lf.pack(side='left')

        self.stattrack_var = tk.BooleanVar(value=False)
        self.souvenir_var = tk.BooleanVar(value=False)
        self.stattrack_check = ttk.Checkbutton(self.opt_lf, text="StatTrak™", variable=self.stattrack_var, style='SearchCheck.TCheckbutton', command=self._on_stattrak_toggle)
        self.stattrack_check.pack(anchor='w')
        self.souvenir_check = ttk.Checkbutton(self.opt_lf, text="Souvenir", variable=self.souvenir_var, style='SearchCheck.TCheckbutton', command=self._on_souvenir_toggle)
        self.souvenir_check.pack(anchor='w')

        # --- Wiersz 2: Typ przedmiotu (może być ukryty dla niektórych kategorii) ---
        self.row2 = tk.Frame(form_container, bg='#1e1e1e')
        self.row2.pack(pady=(0, 24))

        self.type_lf = ttk.LabelFrame(self.row2, text="Typ przedmiotu", style='SearchLF.TLabelframe', padding=(12, 8))
        self.type_lf.pack()

        weapon_list = sorted(list(SKIN_DATA.keys()))
        self.weapon_combo = ttk.Combobox(self.type_lf, values=weapon_list, state='readonly', width=36, style='Dark.TCombobox')
        self.weapon_combo.pack()

        # --- Wiersz 3: Nazwa + Jakość ---
        row3 = tk.Frame(form_container, bg='#1e1e1e')
        row3.pack(pady=(0, 24))

        self.name_lf = ttk.LabelFrame(row3, text="Nazwa", style='SearchLF.TLabelframe', padding=(12, 8))
        self.name_lf.pack(side='left', padx=(0, 24))
        self.skin_combo = ttk.Combobox(self.name_lf, state='disabled', width=28, style='Dark.TCombobox')
        self.skin_combo.pack()

        self.qual_lf = ttk.LabelFrame(row3, text="Jakość", style='SearchLF.TLabelframe', padding=(12, 8))
        self.qual_lf.pack(side='left')
        self.wear_options = ["(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)", "Brak"]
        self.wear_combobox = ttk.Combobox(self.qual_lf, values=self.wear_options, state='readonly', width=28, style='Dark.TCombobox')
        self.wear_combobox.pack()
        self.wear_combobox.set("(Field-Tested)")

        # --- Przycisk Szukaj ---
        search_btn_frame = tk.Frame(form_container, bg='#1e1e1e')
        search_btn_frame.pack(pady=(8, 0))

        self.search_button = tk.Button(
            search_btn_frame, text="🔍  Szukaj", bg='#6688cc', fg='#ffffff',
            font=('Segoe UI', 14, 'bold'), relief='flat', cursor='hand2',
            activebackground='#7799dd', activeforeground='#ffffff', padx=32, pady=10,
            command=self.start_search_thread
        )
        self.search_button.pack()

        # Aliasy starych etykiet (kompatybilność wsteczna)
        self.label_category = tk.Label(self.frame, text="", bg='#1e1e1e')
        self.label_weapon_type = tk.Label(self.frame, text="Typ przedmiotu:", bg='#1e1e1e', fg='#88bbff')
        self.label_skin = tk.Label(self.frame, text="Nazwa:", bg='#1e1e1e', fg='#88bbff')
        self.label_quality = tk.Label(self.frame, text="Jakość:", bg='#1e1e1e', fg='#88bbff')

        # ===================== DOLNY PASEK (row 2) =====================
        bottom = tk.Frame(self.frame, bg='#1e1e1e')
        bottom.grid(row=2, column=0, sticky='sew', pady=(0, 12))
        bottom.grid_columnconfigure(0, weight=1)

        # Kontener na autouzupełnianie z dropdown
        auto_frame = tk.Frame(bottom, bg='#1e1e1e')
        auto_frame.pack()
        
        # Status kółko (zielone/czerwone)
        self.auto_status_indicator = tk.Label(auto_frame, text="●", bg='#1e1e1e', fg='#ff4444', font=('Segoe UI', 10))
        self.auto_status_indicator.pack(side='left', padx=(0, 6))
        
        self.suggestions_label = tk.Label(auto_frame, text="Autouzupełnianie wyłączone", bg='#1e1e1e', fg='#888888', font=('Segoe UI', 9), cursor='hand2')
        self.suggestions_label.pack(side='left')
        
        self.auto_dropdown_arrow = tk.Label(auto_frame, text="▼", bg='#1e1e1e', fg='#888888', font=('Segoe UI', 7), cursor='hand2')
        self.auto_dropdown_arrow.pack(side='left', padx=(4, 0))
        
        # Menu autouzupełniania (ukryte domyślnie)
        self.auto_dropdown_menu = None
        self.auto_dropdown_visible = False
        
        # Bindowanie kliknięcia - wszystkie elementy otwierają dropdown
        for widget in (self.auto_status_indicator, self.suggestions_label, self.auto_dropdown_arrow):
            widget.bind('<Button-1>', self._toggle_auto_dropdown)

        # ===================== UKRYTE ELEMENTY (kompatybilność) =====================
        # Zachowane jako atrybuty klasy, ale nie wyświetlane
        self.version_label = tk.Label(self.frame, text="", bg='#1e1e1e')
        self.status_text = None  # brak widocznego logu – można dodać później w rozsuwanym panelu
        self.update_btn = None
        self.backfill_btn = None
        self.cancel_btn = None
        self.inline_progress_var = tk.StringVar(value="")
        self.inline_progress_label = None
        self.auto_refresh_enabled = tk.BooleanVar(value=False)
        # Wczytaj zapisane ustawienia interwału z kontrolera
        saved_min = getattr(self.controller, '_auto_min_s', 600)
        saved_max = getattr(self.controller, '_auto_max_s', 900)
        self.auto_from_var = tk.StringVar(value=str(saved_min))
        self.auto_to_var = tk.StringVar(value=str(saved_max))
        self.auto_next_var = tk.StringVar(value="")
        self.force_cycle_btn = None
        self.auto_refresh_check = None
        self.auto_from_entry = None
        self.auto_to_entry = None
        self.auto_next_label = None
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = None
        
        # Zaktualizuj wyświetlanie statusu autouzupełniania na starcie
        self._update_auto_status_display()

        # ===================== BINDINGI =====================
        self.weapon_combo.bind("<<ComboboxSelected>>", self.on_weapon_select)
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_select)
        self.skin_combo.bind("<<ComboboxSelected>>", self.on_skin_select)

        try:
            self.frame.bind_all('<Control-Return>', lambda e: self.start_search_thread())
        except Exception:
            pass

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
            # Souvenir nie dotyczy noży
            self.souvenir_check.config(state="disabled")
            self.souvenir_var.set(False)
        else:
            if skin_list:
                self.skin_combo.config(state="readonly")
                self.skin_combo['values'] = skin_list
                self.skin_combo.set(skin_list[0])
                # Ustaw jakości w oparciu o WEAPON_WEAR_MAP (jeśli dostępne)
                try:
                    first_skin = self.skin_combo.get()
                    wear_map = WEAPON_WEAR_MAP.get(selected_weapon, {})
                    wears = wear_map.get(first_skin)
                    if not wears:
                        wears = [w for w in self.wear_options if w != 'Brak']
                    self.wear_combobox.config(state='readonly')
                    self.wear_combobox['values'] = wears
                    if wears:
                        self.wear_combobox.set(wears[0])
                except Exception:
                    self.wear_combobox.config(state="readonly")
                    self.wear_combobox.set("(Field-Tested)")
                # StatTrak dostępny tylko jeśli skin wspiera StatTrak wg sugestii
                try:
                    weapon = selected_weapon
                    first_skin = self.skin_combo.get()
                    st_skins = WEAPON_STATTRAK_MAP.get(weapon, [])
                    if first_skin in st_skins:
                        self.stattrack_check.config(state='normal')
                    else:
                        self.stattrack_check.config(state='disabled')
                        self.stattrack_var.set(False)
                except Exception:
                    self.stattrack_check.config(state='disabled')
                    self.stattrack_var.set(False)
                # Souvenir tylko jeśli pierwszy skin ma wariant Souvenir
                try:
                    weapon = selected_weapon
                    first_skin = self.skin_combo.get()
                    souvenir_skins = WEAPON_SOUVENIR_MAP.get(weapon, [])
                    if first_skin in souvenir_skins:
                        self.souvenir_check.config(state='normal')
                    else:
                        self.souvenir_check.config(state='disabled')
                        self.souvenir_var.set(False)
                except Exception:
                    self.souvenir_check.config(state='disabled')
                    self.souvenir_var.set(False)
            else:
                self.skin_combo.config(state="disabled")
                self.skin_combo['values'] = []
                self.skin_combo.set("Brak")
                self.wear_combobox.config(state="disabled")
                self.wear_combobox.set("Brak")
                self.stattrack_check.config(state="disabled")
                self.stattrack_var.set(False)
                # Brak skinów – wyłącz Souvenir
                self.souvenir_check.config(state="disabled")
                self.souvenir_var.set(False)

    def on_skin_select(self, event):
        """Dostosuj możliwość wyboru wear dla noży w zależności od tego, czy skin to 'Brak'."""
        try:
            selected_weapon = self.weapon_combo.get()
            selected_skin = self.skin_combo.get()
            # Obsługa Zeus x27: odśwież jakości przy zmianie skina
            current_cat = self.category_combo.get()
            if current_cat == 'Zeus x27':
                self._refresh_zeus_wears(selected_skin)
                return
            # Obsługa standardowych broni – per-skin wears z WEAPON_WEAR_MAP
            if selected_weapon in WEAPON_WEAR_MAP:
                try:
                    wears = WEAPON_WEAR_MAP.get(selected_weapon, {}).get(selected_skin)
                    if wears:
                        self.wear_combobox.config(state='readonly')
                        self.wear_combobox['values'] = wears
                        self.wear_combobox.set(wears[0])
                    else:
                        # Fallback – pełen zestaw jeśli brak danych
                        fallback = [w for w in self.wear_options if w != 'Brak']
                        self.wear_combobox.config(state='readonly')
                        self.wear_combobox['values'] = fallback
                        if fallback:
                            self.wear_combobox.set(fallback[0])
                except Exception:
                    pass
            # Aktualizacja dostępności Souvenir po zmianie skina
            if selected_weapon in WEAPON_SOUVENIR_MAP:
                try:
                    souvenir_skins = WEAPON_SOUVENIR_MAP.get(selected_weapon, [])
                    if selected_skin in souvenir_skins:
                        self.souvenir_check.config(state='normal')
                    else:
                        self.souvenir_check.config(state='disabled')
                        self.souvenir_var.set(False)
                except Exception:
                    pass
            # Aktualizacja dostępności StatTrak po zmianie skina
            if selected_weapon in WEAPON_STATTRAK_MAP:
                try:
                    st_skins = WEAPON_STATTRAK_MAP.get(selected_weapon, [])
                    if selected_skin in st_skins:
                        self.stattrack_check.config(state='normal')
                    else:
                        self.stattrack_check.config(state='disabled')
                        self.stattrack_var.set(False)
                except Exception:
                    pass
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

    def _on_zeus_skin_select(self, event):
        try:
            skin = self.skin_combo.get()
            self._refresh_zeus_wears(skin)
        except Exception:
            pass

    def _on_knives_type_select(self, event):
        try:
            ktype_disp = self.weapon_combo.get()
            ktype = ktype_disp[2:] if ktype_disp.startswith('★ ') else ktype_disp
            from src.skin_list import KNIVES as _KN
            skins = (_KN.get('skins', {}) or {}).get(ktype, [])
            if not skins:
                from src.skin_list import SKIN_DATA as _SK
                skins = _SK.get(ktype, [])
            values = (["Vanilla"] + skins) if skins else ["Vanilla"]
            self.skin_combo.config(state='readonly')
            self.skin_combo['values'] = values
            if values:
                self.skin_combo.set(values[0])
            self._refresh_knives_wears()
        except Exception:
            pass

    def _on_knives_skin_select(self, event):
        try:
            self._refresh_knives_wears()
        except Exception:
            pass

    def _on_gloves_type_select(self, event):
        try:
            gtype = self.weapon_combo.get()
            from src.skin_list import GLOVES as _GL
            skins = _GL.get('skins', {}).get(gtype, [])
            self.skin_combo.config(state=('readonly' if skins else 'disabled'))
            self.skin_combo['values'] = skins
            if skins:
                self.skin_combo.set(skins[0])
            self._refresh_gloves_wears()
        except Exception:
            pass

    def _on_gloves_skin_select(self, event):
        try:
            self._refresh_gloves_wears()
        except Exception:
            pass

    def _refresh_zeus_wears(self, skin):
        try:
            from src.skin_list import ZEUS_WEAR_MAP as _ZWM
            wears = _ZWM.get(skin) or [w for w in self.wear_options if w != 'Brak']
            if wears:
                self.wear_combobox.config(state='readonly')
                self.wear_combobox['values'] = wears
                self.wear_combobox.set(wears[0])
            else:
                self.wear_combobox['values'] = []
                self.wear_combobox.set('')
                self.wear_combobox.config(state='disabled')
        except Exception:
            pass

    def _refresh_knives_wears(self):
        try:
            ktype_disp = self.weapon_combo.get()
            ktype = ktype_disp[2:] if ktype_disp.startswith('★ ') else ktype_disp
            skin = self.skin_combo.get()
            if skin and skin.lower() == 'vanilla':
                self.wear_combobox.config(state='disabled')
                self.wear_combobox.set('Brak')
                return
            from src.skin_list import KNIVES as _KN
            wear_map = _KN.get('wear_map', {}) or {}
            wears = (wear_map.get(ktype, {}) or {}).get(skin)
            if not wears:
                wears = [w for w in self.wear_options if w != 'Brak']
            self.wear_combobox.config(state=('readonly' if wears else 'disabled'))
            self.wear_combobox['values'] = wears or []
            if wears:
                self.wear_combobox.set(wears[0])
            else:
                self.wear_combobox.set('')
        except Exception:
            pass

    def _refresh_gloves_wears(self):
        try:
            gtype = self.weapon_combo.get()
            skin = self.skin_combo.get()
            from src.skin_list import GLOVES as _GL
            wear_map = _GL.get('wear_map', {}) or {}
            wears = (wear_map.get(gtype, {}) or {}).get(skin)
            if not wears:
                wears = _GL.get('wear') or [w for w in self.wear_options if w != 'Brak']
            self.wear_combobox.config(state=('readonly' if wears else 'disabled'))
            self.wear_combobox['values'] = wears or []
            if wears:
                self.wear_combobox.set(wears[0])
            else:
                self.wear_combobox.set('')
        except Exception:
            pass

    def on_category_select(self, event):
        """
        Aktualizuje listę typów broni (weapon_combo) na podstawie wybranej kategorii.
        Jeśli kategoria jest pusta lub nie zawiera wpisów, pokaż wszystkie dostępne typy.
        """
        selected_cat = self.category_combo.get() if hasattr(self, 'category_combo') else None
        # Reset base state before applying specialized rules
        self._reset_base_ui()
        # Wyczyść ewentualne poprzednie bindowania specyficzne dla kategorii
        try:
            self.wear_combobox.unbind("<<ComboboxSelected>>")
        except Exception:
            pass
        try:
            self.weapon_combo.unbind("<<ComboboxSelected>>")
        except Exception:
            pass
        # Krytyczne: upewnij się, że combobox skina nie niesie poprzednich handlerów
        # (np. z kategorii Zeus/Graffiti), które zastępowały domyślny on_skin_select.
        try:
            self.skin_combo.unbind("<<ComboboxSelected>>")
        except Exception:
            pass
        # Przywróć domyślny handler skórek
        self.skin_combo.bind("<<ComboboxSelected>>", self.on_skin_select)
        # Przywróć domyślny handler typu broni
        self.weapon_combo.bind("<<ComboboxSelected>>", self.on_weapon_select)
        weapons = []
        if selected_cat:
            weapons = WEAPON_CATEGORIES.get(selected_cat, [])

            # Kategoria noży – wyświetl typy z prefiksem '★ '
            if selected_cat in ('Noże', 'Nóż'):
                # Zmień nazwy LabelFrame'ów
                try:
                    self.type_lf.config(text='Typ noża')
                    self.name_lf.config(text='Nazwa')
                    self.qual_lf.config(text='Jakość')
                except Exception:
                    pass
                self.label_weapon_type.config(text='Typ noża:')
                self.label_skin.config(text='Nazwa:')
                k_types_raw = KNIVES.get('types', [])
                k_types_display = ["★ " + t if not t.startswith('★ ') else t for t in k_types_raw]
                self.weapon_combo.config(state='readonly')
                self.weapon_combo['values'] = k_types_display
                first_disp = k_types_display[0] if k_types_display else ''
                self.weapon_combo.set(first_disp)
                raw_type = first_disp[2:] if first_disp.startswith('★ ') else first_disp
                skins = (KNIVES.get('skins', {}) or {}).get(raw_type, [])
                if not skins:
                    skins = SKIN_DATA.get(raw_type, [])
                values = (["Vanilla"] + skins) if skins else ["Vanilla"]
                self.skin_combo.config(state='readonly')
                self.skin_combo['values'] = values
                self.skin_combo.set(values[0])
                self._refresh_knives_wears()
                try:
                    self.weapon_combo.unbind("<<ComboboxSelected>>")
                except Exception:
                    pass
                self.weapon_combo.bind("<<ComboboxSelected>>", self._on_knives_type_select)
                try:
                    self.skin_combo.unbind("<<ComboboxSelected>>")
                except Exception:
                    pass
                self.skin_combo.bind("<<ComboboxSelected>>", self._on_knives_skin_select)
                self.stattrack_check.config(state='normal')
                self.souvenir_check.config(state='disabled')
                self.souvenir_var.set(False)
                return
        if selected_cat == 'Rękawice':
            # Zmień nazwy LabelFrame'ów
            try:
                self.type_lf.config(text='Typ rękawic')
                self.name_lf.config(text='Nazwa')
                self.qual_lf.config(text='Jakość')
            except Exception:
                pass
            self.label_weapon_type.config(text='Typ rękawic:')
            self.label_skin.config(text='Nazwa:')
            # Typy rękawic i nazwy z suggestions (GLOVES)
            types = GLOVES.get('types', [])
            self.weapon_combo.config(state='readonly')
            self.weapon_combo['values'] = types
            first_glove_type = types[0] if types else ''
            self.weapon_combo.set(first_glove_type)
            skins = GLOVES.get('skins', {}).get(first_glove_type, [])
            self.skin_combo.config(state='readonly')
            self.skin_combo['values'] = skins
            if skins:
                self.skin_combo.set(skins[0])
            # Jakości tylko dostępne dla danych rękawic (per-skin)
            try:
                self._refresh_gloves_wears()
            except Exception:
                wears = GLOVES.get('wear') or [w for w in self.wear_options if w != 'Brak']
                self.wear_combobox.config(state='readonly')
                self.wear_combobox['values'] = wears
                if wears:
                    self.wear_combobox.set(wears[0])
            # Bind: zmiana typu -> skiny + jakości; zmiana nazwy -> jakości
            try:
                self.weapon_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.weapon_combo.bind("<<ComboboxSelected>>", self._on_gloves_type_select)
            try:
                self.skin_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.skin_combo.bind("<<ComboboxSelected>>", self._on_gloves_skin_select)
            # Rękawice nie mają wariantów StatTrak ani Souvenir
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)
            return
        if selected_cat == 'Naklejka':
            # Zmień nazwy LabelFrame'ów
            try:
                self.type_lf.config(text='Typ naklejki')
                self.name_lf.config(text='Nazwa')
                self.qual_lf.config(text='Event')
            except Exception:
                pass
            self.label_weapon_type.config(text='Typ naklejki:')
            self.label_skin.config(text='Nazwa:')
            sticker_types = STICKERS.get('types', ['Esportowa', 'Zwykła'])
            self.weapon_combo.config(state='readonly')
            self.weapon_combo['values'] = sticker_types
            current_type = sticker_types[0] if sticker_types else ''
            if current_type:
                self.weapon_combo.set(current_type)
            # Zastosuj logikę dla domyślnego typu naklejki
            self._configure_sticker_ui(current_type)
            try:
                self.weapon_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.weapon_combo.bind("<<ComboboxSelected>>", self._on_sticker_type_select)
            return
        if selected_cat == 'Zeus x27':
            # Ukryj pole typu broni; Zeus ma tylko skiny
            try:
                self.row2.pack_forget()
            except Exception:
                pass
            try:
                self.type_lf.config(text='Typ przedmiotu')
                self.name_lf.config(text='Skin')
                self.qual_lf.config(text='Jakość')
            except Exception:
                pass
            self.label_weapon_type.grid_remove()
            self.weapon_combo.grid_remove()
            # Skórki Zeus z suggestions.txt
            self.skin_combo.config(state='readonly')
            self.skin_combo['values'] = ZEUS_SKINS
            if ZEUS_SKINS:
                self.skin_combo.set(ZEUS_SKINS[0])
            self.label_skin.config(text='Skin:')
            # Jakości zależne od wybranego skina (jeśli dostępne w suggestions)
            current_zeus_skin = self.skin_combo.get()
            zeus_wears = ZEUS_WEAR_MAP.get(current_zeus_skin) or [w for w in self.wear_options if w != 'Brak']
            self.wear_combobox.config(state='readonly')
            self.wear_combobox['values'] = zeus_wears
            if zeus_wears:
                self.wear_combobox.set(zeus_wears[0])
            else:
                self.wear_combobox.set('')
                self.wear_combobox.config(state='disabled')
            # Bind: zmiana skina -> odśwież jakości (najpierw wyczyść poprzednie)
            try:
                self.skin_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.skin_combo.bind("<<ComboboxSelected>>", self._on_zeus_skin_select)
            # StatTrak/Souvenir wyłączone
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)
            return
        if selected_cat == 'Graffiti':
            # Zmień nazwy LabelFrame'ów
            try:
                self.type_lf.config(text='Typ graffiti')
                self.name_lf.config(text='Nazwa')
                self.qual_lf.config(text='Event')
            except Exception:
                pass
            # Typ graffiti (Esportowe / Zwykłe)
            self.label_weapon_type.config(text='Typ graffiti:')
            self.weapon_combo.config(state='readonly')
            self.weapon_combo['values'] = GRAFFITI.get('types', [])
            if GRAFFITI.get('types'):
                self.weapon_combo.set(GRAFFITI['types'][0])
            self.label_skin.config(text='Nazwa graffiti:')
            # Domyślnie tryb Esportowe: blokuj nazwy do czasu wyboru eventu
            self.skin_combo.config(state='disabled')
            self.skin_combo['values'] = []
            self.skin_combo.set('')
            self.label_quality.config(text='Event:')
            self.wear_combobox.config(state='readonly')
            self.wear_combobox['values'] = GRAFFITI.get('events', [])
            if GRAFFITI.get('events'):
                self.wear_combobox.set(GRAFFITI['events'][0])
            else:
                self.skin_combo['values'] = []
                self.skin_combo.set('')
            # bindy do dynamicznej zmiany
            # Bindy specyficzne dla graffiti (najpierw wyczyść poprzednie)
            try:
                self.weapon_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.weapon_combo.bind("<<ComboboxSelected>>", self._on_graffiti_type_select)
            try:
                self.wear_combobox.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.wear_combobox.bind("<<ComboboxSelected>>", self._on_graffiti_event_select)
            try:
                self.skin_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.skin_combo.bind("<<ComboboxSelected>>", self._on_graffiti_name_select)
            # wyłącz StatTrak/Souvenir
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)
            return
        if selected_cat == 'Agent':
            # Ukryj wiersz z typem przedmiotu
            try:
                self.row2.pack_forget()
            except Exception:
                pass
            try:
                self.type_lf.config(text='Typ przedmiotu')
                self.name_lf.config(text='Agent')
                self.qual_lf.config(text='Kolekcja')
            except Exception:
                pass
            # wear_combobox -> kolekcja, skin_combo -> agent
            self.label_weapon_type.grid_remove()
            self.weapon_combo.grid_remove()
            self.label_quality.config(text='Kolekcja:')
            collections = AGENTS.get('collections', [])
            self.wear_combobox.config(state='readonly')
            self.wear_combobox['values'] = collections
            if collections:
                self.wear_combobox.set(collections[0])
            current_collection = self.wear_combobox.get()
            agent_list = AGENTS.get('map', {}).get(current_collection, AGENTS.get('names', []))
            self.label_skin.config(text='Agent:')
            self.skin_combo.config(state='readonly')
            self.skin_combo['values'] = agent_list
            if agent_list:
                self.skin_combo.set(agent_list[0])
            self.wear_combobox.bind("<<ComboboxSelected>>", self._on_agent_collection_select)
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)
            return
        if selected_cat == 'Inne':
            # Zmień nazwy LabelFrame'ów
            try:
                self.type_lf.config(text='Typ przedmiotu')
                self.name_lf.config(text='Nazwa')
                self.qual_lf.config(text='Jakość')
            except Exception:
                pass
            # Ukryj pole jakości domyślnie - będzie pokazane tylko jeśli potrzebne
            try:
                self.qual_lf.pack_forget()
            except Exception:
                pass
            self.label_weapon_type.config(text='Typ przedmiotu:')
            other_types = OTHER_TYPES or []
            self.weapon_combo.config(state='readonly')
            self.weapon_combo['values'] = other_types
            if other_types:
                self.weapon_combo.set(other_types[0])
            else:
                self.weapon_combo.set('')
            try:
                self.weapon_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.weapon_combo.bind("<<ComboboxSelected>>", self._on_other_type_select)
            self._configure_other_type_ui(self.weapon_combo.get())
            return
        if selected_cat == 'Pojemnik':
            # Ukryj wiersz z typem przedmiotu
            try:
                self.row2.pack_forget()
            except Exception:
                pass
            try:
                self.type_lf.config(text='Typ przedmiotu')
                self.name_lf.config(text='Nazwa')
                self.qual_lf.config(text='Rodzaj')
            except Exception:
                pass
            # Ukryj Typ broni; używamy pola "Rodzaj" (wear_combobox) do wyboru podkategorii
            self.label_weapon_type.grid_remove()
            self.weapon_combo.grid_remove()
            # Ustaw "Rodzaj" i możliwe wartości
            rodzaje = [
                'Skrzynia',
                'Pojemnik z naklejkami',
                'Zestaw (Package)',
                'Terminal',
                'Paczka z naszywką',
                'Skrzynia z zestawem utworów'
            ]
            # Jeśli parsowane typy dostarczone – użyj ich (dla spójności z suggestions)
            try:
                c_types = CONTAINERS.get('types') or []
                # Normalizuj do nowych nazw
                mapped = []
                for t in c_types:
                    if t == 'Pojemnik':
                        mapped.append('Pojemnik z naklejkami')
                    elif t == 'Zestaw':
                        mapped.append('Zestaw (Package)')
                    else:
                        mapped.append(t)
                if mapped:
                    rodzaje = mapped
            except Exception:
                pass
            self.label_quality.config(text='Rodzaj:')
            self.wear_combobox.config(state='readonly')
            self.wear_combobox['values'] = rodzaje
            if rodzaje:
                self.wear_combobox.set(rodzaje[0])
            # Nazwa listowana w polu Skin (przemianowanym na "Nazwa")
            self.label_skin.config(text='Nazwa:')
            self.skin_combo.config(state='readonly')
            # Ustaw nazwy dla pierwszego rodzaju
            self._set_container_names_for_kind(self.wear_combobox.get())
            # Bind zmiany rodzaju
            try:
                self.wear_combobox.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            self.wear_combobox.bind("<<ComboboxSelected>>", self._on_container_type_select)
            # Nazwy pojemników nie wymagają obsługi on_skin_select – odwiąż handler
            try:
                self.skin_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            # StatTrak/Souvenir wyłączone
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)
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
            # Ustaw poprawny wybór: jeśli obecny nie należy do listy, wybierz pierwszy
            try:
                current = (self.weapon_combo.get() or '').strip()
                if current not in weapons and weapons:
                    self.weapon_combo.set(weapons[0])
            except Exception:
                pass
        self.skin_combo.bind("<<ComboboxSelected>>", self.on_skin_select)

        # Zaktualizuj listę skinów dla aktualnie wybranej broni
        self.on_weapon_select(None)

    def _on_container_type_select(self, event):
        try:
            kind = (self.wear_combobox.get() or '').strip()
            self._set_container_names_for_kind(kind)
        except Exception:
            pass

    def _set_container_names_for_kind(self, kind: str):
        """Ustaw listę nazw (skin_combo) w zależności od wybranego rodzaju pojemnika."""
        try:
            # Zbierz listy z CONTAINERS
            cases = CONTAINERS.get('cases', []) or []
            stickers_common = CONTAINERS.get('common', []) or []
            stickers_event = CONTAINERS.get('event_containers', []) or []
            sets_col = CONTAINERS.get('sets_collection', []) or []
            sets_souv = CONTAINERS.get('sets_souvenir', []) or []
            sets_other = CONTAINERS.get('sets_other', []) or []
            terminals = CONTAINERS.get('terminals', []) or []
            patch_packs = CONTAINERS.get('patch_packs', []) or []
            music_kit_boxes = CONTAINERS.get('music_kit_boxes', []) or []

            names = []
            if kind == 'Skrzynia':
                names = cases
            elif kind == 'Pojemnik z naklejkami':
                # Połącz eventowe i zwykłe kapsuły
                names = sorted(list({*stickers_common, *stickers_event}))
            elif kind == 'Zestaw (Package)':
                names = sorted(list({*sets_col, *sets_souv, *sets_other}))
            elif kind == 'Terminal':
                names = terminals
            elif kind == 'Paczka z naszywką':
                names = patch_packs
            elif kind == 'Skrzynia z zestawem utworów':
                names = music_kit_boxes
            else:
                names = []
            self.skin_combo.config(state=('readonly' if names else 'disabled'))
            self.skin_combo['values'] = names
            if names:
                self.skin_combo.set(names[0])
            else:
                self.skin_combo.set('')
        except Exception:
            pass

    def _configure_sticker_ui(self, sticker_type: str):
        try:
            try:
                self.skin_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            try:
                self.wear_combobox.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            if sticker_type == 'Esportowa':
                self.label_quality.config(text='Event:')
                self.label_quality.grid()
                self.wear_combobox.grid()
                events = STICKERS.get('events', [])
                self.wear_combobox.config(state='readonly')
                self.wear_combobox['values'] = events
                if events:
                    self.wear_combobox.set(events[0])
                else:
                    self.wear_combobox.set('')
                self._set_sticker_names_for_event(self.wear_combobox.get())
                self.wear_combobox.bind("<<ComboboxSelected>>", self._on_sticker_event_select)
            else:
                self.label_quality.grid_remove()
                self.wear_combobox.grid_remove()
                names = STICKERS.get('normal_names', [])
                self.skin_combo.config(state=('readonly' if names else 'disabled'))
                self.skin_combo['values'] = names
                if names:
                    self.skin_combo.set(names[0])
                else:
                    self.skin_combo.set('')
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)
        except Exception:
            pass

    def _set_sticker_names_for_event(self, event_name: str):
        try:
            if not event_name:
                self.skin_combo.config(state='disabled')
                self.skin_combo['values'] = []
                self.skin_combo.set('')
                return
            names = (STICKERS.get('event_to_names', {}) or {}).get(event_name, [])
            self.skin_combo.config(state=('readonly' if names else 'disabled'))
            self.skin_combo['values'] = names
            if names:
                self.skin_combo.set(names[0])
            else:
                self.skin_combo.set('')
        except Exception:
            pass

    def _on_sticker_type_select(self, event):
        sticker_type = (self.weapon_combo.get() or '').strip()
        self._configure_sticker_ui(sticker_type)

    def _on_sticker_event_select(self, event):
        event_name = self.wear_combobox.get()
        self._set_sticker_names_for_event(event_name)

    def _reset_base_ui(self):
        """Przywraca podstawowe etykiety i widoczność dla klasycznej broni."""
        # Pokaż wiersz z typem przedmiotu (po row1)
        try:
            self.row2.pack_forget()
            self.row2.pack(after=self.row1, pady=(0, 24))
        except Exception:
            pass
        # Pokaż pole Jakość (mogło być ukryte dla kategorii Inne)
        try:
            self.qual_lf.pack_forget()
            self.qual_lf.pack(side='left')
        except Exception:
            pass
        # Resetuj nazwy LabelFrame'ów
        try:
            self.type_lf.config(text='Typ przedmiotu')
            self.name_lf.config(text='Nazwa')
            self.qual_lf.config(text='Jakość')
        except Exception:
            pass
        # Stare aliasy (kompatybilność)
        self.label_weapon_type.config(text='Typ broni:')
        self.label_skin.config(text='Skin:')
        self.label_quality.config(text='Jakość:')
        # Re-enable wear default set
        self.wear_combobox.config(state='readonly')
        self.wear_combobox['values'] = self.wear_options
        if '(Field-Tested)' in self.wear_options:
            self.wear_combobox.set('(Field-Tested)')
        # Enable StatTrak by default (actual enabling for category handled elsewhere)
        self.stattrack_check.config(state='normal')
        # Souvenir base reset (will be toggled off for knives etc.)
        self.souvenir_check.config(state='normal')

    def update_welcome_label(self):
        # Aktualizuj etykietę powitania
        steam_name = getattr(self.controller, 'steam_name', None) or 'Gość'
        try:
            self.welcome_label.config(text=f"Witaj,\n{steam_name}")
        except Exception:
            pass
        
        is_logged = getattr(self.controller, 'is_logged_in', lambda: False)()
        
        # Pokaż/ukryj komunikat o braku cookie – w nowym UI nie ma tego elementu, safe skip
        has_cookie = bool(getattr(self.controller, 'login_cookie', None))
        try:
            if self.cookie_mode_label is not None:
                if has_cookie:
                    self.cookie_mode_label.grid_remove()
                else:
                    self.cookie_mode_label.grid()
        except Exception:
            pass
        
        # Wyczyść i odśwież avatar
        self.avatar_canvas.delete('all')
        
        if not is_logged:
            # Użytkownik wylogowany - pokaż placeholder
            self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1, tags='default_frame')
            self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', font=('Segoe UI', 7), justify='center', tags='placeholder')
            self._avatar_photo = None
            self._frame_photo = None
            return
        
        # Użytkownik zalogowany - sprawdź cache lub załaduj
        cached_avatar = getattr(self.controller, '_cached_avatar_photo', None)
        cached_frame = getattr(self.controller, '_cached_frame_photo', None)
        
        if cached_avatar:
            # Użyj cache'owanego avatara
            self.avatar_canvas.create_image(26, 26, image=cached_avatar, tags='avatar')
            if cached_frame:
                self.avatar_canvas.create_image(26, 26, image=cached_frame, tags='frame')
        else:
            # Brak cache - załaduj asynchronicznie
            self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1, tags='default_frame')
            self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', font=('Segoe UI', 7), justify='center', tags='placeholder')
            self._load_avatar_async()

    def _load_avatar_async(self):
        """Ładuje avatar i ramkę Steam w tle."""
        avatar_url = getattr(self.controller, 'steam_avatar_url', None)
        frame_url = getattr(self.controller, 'steam_frame_url', None)
        if avatar_url or frame_url:
            threading.Thread(target=self._fetch_and_set_avatar, args=(avatar_url, frame_url), daemon=True).start()

    def _fetch_and_set_avatar(self, avatar_url, frame_url=None):
        """Pobiera obrazek avatara i ramki z URL i ustawia je w UI."""
        try:
            import requests
            from io import BytesIO
            try:
                from PIL import Image, ImageTk
            except ImportError:
                return  # Brak PIL - zostaw placeholder
            
            avatar_img = None
            frame_img = None
            
            # Pobierz avatar
            if avatar_url:
                try:
                    response = requests.get(avatar_url, timeout=10)
                    if response.status_code == 200:
                        img_data = BytesIO(response.content)
                        avatar_img = Image.open(img_data)
                        avatar_img = avatar_img.resize((46, 46), Image.Resampling.LANCZOS)
                except Exception:
                    pass
            
            # Pobierz ramkę Steam
            if frame_url:
                try:
                    response = requests.get(frame_url, timeout=10)
                    if response.status_code == 200:
                        img_data = BytesIO(response.content)
                        frame_img = Image.open(img_data)
                        # Ramki Steam są zwykle większe, skalujemy do 52x52
                        frame_img = frame_img.resize((52, 52), Image.Resampling.LANCZOS)
                except Exception:
                    pass
            
            # Ustaw w UI (musi być w wątku głównym)
            def _set_images():
                try:
                    # Sprawdź czy użytkownik nadal jest zalogowany
                    if not getattr(self.controller, 'is_logged_in', lambda: False)():
                        return
                    
                    # Usuń domyślne elementy
                    self.avatar_canvas.delete('default_frame')
                    self.avatar_canvas.delete('placeholder')
                    self.avatar_canvas.delete('avatar')
                    self.avatar_canvas.delete('frame')
                    
                    # Ustaw avatar
                    if avatar_img:
                        self._avatar_photo = ImageTk.PhotoImage(avatar_img)
                        # Zapisz też w kontrolerze dla innych widoków
                        self.controller._cached_avatar_photo = self._avatar_photo
                        self.avatar_canvas.create_image(26, 26, image=self._avatar_photo, tags='avatar')
                    
                    # Ustaw ramkę Steam (na wierzchu)
                    if frame_img:
                        self._frame_photo = ImageTk.PhotoImage(frame_img)
                        # Zapisz też w kontrolerze
                        self.controller._cached_frame_photo = self._frame_photo
                        self.avatar_canvas.create_image(26, 26, image=self._frame_photo, tags='frame')
                    elif avatar_img:
                        # Jeśli nie ma ramki Steam, użyj domyślnej niebieskiej
                        self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1, tags='default_frame')
                except Exception:
                    pass
            
            self.controller.root.after(0, _set_images)
        except Exception as e:
            print(f"Błąd ładowania avatara: {e}", file=sys.stderr)

    # ===================== DROPDOWN MENU UŻYTKOWNIKA =====================
    def _toggle_dropdown_menu(self, event=None):
        """Pokazuje lub ukrywa menu dropdown."""
        if self.dropdown_visible:
            self._hide_dropdown_menu()
        else:
            self._show_dropdown_menu()

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

        # Zamknij menu po kliknięciu poza nim
        self.controller.root.bind('<Button-1>', self._on_click_outside_dropdown, add='+')

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
            widget = event.widget
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
        # Wyczyść dane sesji (metoda kontrolera czyści wszystko)
        self.controller.clear_auth_state()
        # Zresetuj lokalny avatar canvas do placeholdera
        try:
            self.avatar_canvas.delete('all')
            self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1, tags='default_frame')
            self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', font=('Segoe UI', 7), justify='center', tags='placeholder')
            self._avatar_photo = None
            self._frame_photo = None
        except Exception:
            pass
        # Przejdź do ekranu logowania (wywoła _refresh_all_headers)
        self.controller.switch_view('login')

    # ===================== MODAL ZMIANY WALUTY =====================
    def _show_currency_modal(self):
        """Wyświetla modal do zmiany waluty."""
        # Overlay - przyciemnione tło
        self.currency_overlay = tk.Frame(self.controller.root, bg='black')
        self.currency_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.currency_overlay.configure(bg='#000000')
        # Ustawienie przezroczystości przez nakładkę
        self.currency_overlay.lift()

        # Przyciemnienie (symulowane przez czarny kolor z alpha przez wiele warstw lub stipple)
        # Tkinter nie obsługuje alpha, więc użyjemy ciemnego koloru
        overlay_bg = tk.Frame(self.currency_overlay, bg='#1a1a1a')
        overlay_bg.place(x=0, y=0, relwidth=1, relheight=1)
        overlay_bg.bind('<Button-1>', lambda e: self._close_currency_modal())

        # Modal - okienko na środku
        modal = tk.Frame(self.currency_overlay, bg='#2a2a2a', highlightbackground='#5588cc', highlightthickness=2)
        modal.place(relx=0.5, rely=0.5, anchor='center')

        # Tytuł
        title = tk.Label(modal, text="Zmień walutę", bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 14, 'bold'))
        title.pack(pady=(20, 16), padx=40)

        # Aktualna waluta
        current_currency = getattr(self.controller, 'currency', 'PLN')
        info_label = tk.Label(modal, text=f"Aktualna waluta: {current_currency}", bg='#2a2a2a', fg='#888888', font=('Segoe UI', 10))
        info_label.pack(pady=(0, 16))

        # Przyciski walut
        currencies = [('PLN', 'zł'), ('USD', '$'), ('EUR', '€')]
        btn_frame = tk.Frame(modal, bg='#2a2a2a')
        btn_frame.pack(pady=(0, 20))

        for curr, symbol in currencies:
            is_selected = curr == current_currency
            btn_bg = '#5588cc' if is_selected else '#3a3a3a'
            btn_fg = '#ffffff'
            btn = tk.Label(
                btn_frame, text=f"{curr} ({symbol})",
                bg=btn_bg, fg=btn_fg, font=('Segoe UI', 12),
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
            modal, text="Anuluj",
            bg='#2a2a2a', fg='#888888', font=('Segoe UI', 10),
            cursor='hand2'
        )
        cancel_btn.pack(pady=(0, 20))
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(fg='#ffffff'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(fg='#888888'))
        cancel_btn.bind('<Button-1>', lambda e: self._close_currency_modal())

        # Zapisz referencję do modala
        self.currency_modal = modal

    def _close_currency_modal(self):
        """Zamyka modal zmiany waluty."""
        try:
            self.currency_overlay.destroy()
        except Exception:
            pass
        self.currency_overlay = None
        self.currency_modal = None

    def _select_currency(self, currency):
        """Wybiera nową walutę i przeładowuje widok."""
        currency_map = {
            'PLN': {'code': 6, 'symbol': 'zł'},
            'USD': {'code': 1, 'symbol': '$'},
            'EUR': {'code': 3, 'symbol': '€'}
        }
        if currency in currency_map:
            self.controller.currency = currency
            self.controller.currency_code = currency_map[currency]['code']
            self.controller.currency_symbol = currency_map[currency]['symbol']
            self.log_message(f"Waluta zmieniona na: {currency} ({currency_map[currency]['symbol']})")

        self._close_currency_modal()
        
        # Przeładuj aktualny widok
        self.controller.switch_view('search')

    # ===================== DROPDOWN AUTOUZUPEŁNIANIA =====================
    def _toggle_auto_dropdown(self, event=None):
        """Pokazuje lub ukrywa menu dropdown autouzupełniania."""
        if self.auto_dropdown_visible:
            self._hide_auto_dropdown()
        else:
            self._show_auto_dropdown()
        return "break"  # Zatrzymaj propagację eventu

    def _show_auto_dropdown(self):
        """Wyświetla menu dropdown autouzupełniania."""
        if self.auto_dropdown_menu:
            self._hide_auto_dropdown()
            return

        # Utwórz menu jako Toplevel
        self.auto_dropdown_menu = tk.Toplevel(self.controller.root)
        self.auto_dropdown_menu.overrideredirect(True)
        self.auto_dropdown_menu.configure(bg='#2a2a2a')
        self.auto_dropdown_menu.attributes('-topmost', True)

        # Pozycja menu - nad etykietą
        try:
            x = self.suggestions_label.winfo_rootx()
            y = self.suggestions_label.winfo_rooty() - 5
        except Exception:
            x, y = 100, 100

        # Ramka menu
        menu_frame = tk.Frame(self.auto_dropdown_menu, bg='#2a2a2a', highlightbackground='#5588cc', highlightthickness=1)
        menu_frame.pack(fill='both', expand=True)

        # Opcja: Włącz/Wyłącz autouzupełnianie
        is_enabled = self.auto_refresh_enabled.get()
        toggle_text = "🔴 Wyłącz autouzupełnianie" if is_enabled else "🟢 Włącz autouzupełnianie"
        toggle_btn = tk.Label(
            menu_frame, text=toggle_text,
            bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 10),
            padx=16, pady=8, cursor='hand2', anchor='w'
        )
        toggle_btn.pack(fill='x')
        toggle_btn.bind('<Enter>', lambda e: toggle_btn.config(bg='#3a3a3a'))
        toggle_btn.bind('<Leave>', lambda e: toggle_btn.config(bg='#2a2a2a'))
        toggle_btn.bind('<Button-1>', lambda e: self._toggle_auto_refresh())

        # Separator
        sep0 = tk.Frame(menu_frame, bg='#444444', height=1)
        sep0.pack(fill='x', padx=8)

        # Opcja: Ustawienia interwału
        interval_btn = tk.Label(
            menu_frame, text="⏱ Ustawienia interwału",
            bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 10),
            padx=16, pady=8, cursor='hand2', anchor='w'
        )
        interval_btn.pack(fill='x')
        interval_btn.bind('<Enter>', lambda e: interval_btn.config(bg='#3a3a3a'))
        interval_btn.bind('<Leave>', lambda e: interval_btn.config(bg='#2a2a2a'))
        interval_btn.bind('<Button-1>', lambda e: self._show_interval_modal())

        # Separator
        sep1 = tk.Frame(menu_frame, bg='#444444', height=1)
        sep1.pack(fill='x', padx=8)

        # Opcja: Przeładuj sugestie (odświeża wyszukiwarkę z aktualnej listy)
        reload_btn = tk.Label(
            menu_frame, text="📂 Przeładuj sugestie",
            bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 10),
            padx=16, pady=8, cursor='hand2', anchor='w'
        )
        reload_btn.pack(fill='x')
        reload_btn.bind('<Enter>', lambda e: reload_btn.config(bg='#3a3a3a'))
        reload_btn.bind('<Leave>', lambda e: reload_btn.config(bg='#2a2a2a'))
        reload_btn.bind('<Button-1>', lambda e: self._reload_suggestions_from_file())

        # Oblicz pozycję (nad przyciskiem)
        self.auto_dropdown_menu.update_idletasks()
        menu_height = self.auto_dropdown_menu.winfo_reqheight()
        y = y - menu_height

        self.auto_dropdown_menu.geometry(f"+{x}+{y}")
        self.auto_dropdown_visible = True

        # Zamknij menu po kliknięciu poza nim (po krótkim opóźnieniu)
        self._auto_bind_id = self.controller.root.after(100, self._bind_auto_outside_click)

    def _bind_auto_outside_click(self):
        """Binduje handler kliknięcia poza dropdown."""
        self._auto_outside_click_bind_id = self.controller.root.bind('<Button-1>', self._on_click_outside_auto_dropdown, add='+')

    def _reload_suggestions_from_file(self):
        """Przeładowuje sugestie z pliku i odświeża wyszukiwarkę."""
        self._hide_auto_dropdown()
        try:
            # Wczytaj sugestie z pliku przez kontroler
            if hasattr(self.controller, '_load_existing_suggestions_only'):
                self.controller._load_existing_suggestions_only()
            # Odśwież taksomonię
            self._reload_taxonomy()
            # Zaktualizuj wyświetlanie
            self._update_auto_status_display()
            self.log_message(f"Przeładowano {len(self.controller.all_suggestions)} sugestii z pliku.")
        except Exception as e:
            self.log_message(f"Błąd przeładowywania sugestii: {e}")

    def _hide_auto_dropdown(self):
        """Ukrywa menu dropdown autouzupełniania."""
        # Usuń binding kliknięcia poza menu
        try:
            if hasattr(self, '_auto_outside_click_bind_id') and self._auto_outside_click_bind_id:
                self.controller.root.unbind('<Button-1>', self._auto_outside_click_bind_id)
                self._auto_outside_click_bind_id = None
        except Exception:
            pass
        
        if self.auto_dropdown_menu:
            try:
                self.auto_dropdown_menu.destroy()
            except Exception:
                pass
            self.auto_dropdown_menu = None
        self.auto_dropdown_visible = False

    def _on_click_outside_auto_dropdown(self, event):
        """Zamyka dropdown autouzupełniania jeśli kliknięto poza nim."""
        if not self.auto_dropdown_menu or not self.auto_dropdown_visible:
            return
        try:
            # Sprawdź czy kliknięto na elementy toggle (kółko, napis, strzałka)
            for widget in (self.auto_status_indicator, self.suggestions_label, self.auto_dropdown_arrow):
                try:
                    wx = widget.winfo_rootx()
                    wy = widget.winfo_rooty()
                    ww = widget.winfo_width()
                    wh = widget.winfo_height()
                    if wx <= event.x_root <= wx + ww and wy <= event.y_root <= wy + wh:
                        return  # Kliknięto na toggle - nie zamykaj (toggle obsłuży)
                except Exception:
                    pass
            
            if self.auto_dropdown_menu.winfo_exists():
                menu_x = self.auto_dropdown_menu.winfo_rootx()
                menu_y = self.auto_dropdown_menu.winfo_rooty()
                menu_w = self.auto_dropdown_menu.winfo_width()
                menu_h = self.auto_dropdown_menu.winfo_height()
                if not (menu_x <= event.x_root <= menu_x + menu_w and menu_y <= event.y_root <= menu_y + menu_h):
                    self._hide_auto_dropdown()
        except Exception:
            self._hide_auto_dropdown()

    def _update_auto_status_display(self):
        """Aktualizuje wyświetlanie statusu autouzupełniania."""
        is_enabled = self.auto_refresh_enabled.get()
        count = len(getattr(self.controller, 'all_suggestions', []))
        
        if is_enabled:
            self.auto_status_indicator.config(fg='#44ff44')  # Zielone
            self.suggestions_label.config(text=f"Autouzupełnianie ({count} sugestii)")
        else:
            self.auto_status_indicator.config(fg='#ff4444')  # Czerwone
            self.suggestions_label.config(text="Autouzupełnianie wyłączone")

    def _toggle_auto_refresh(self):
        """Włącza/wyłącza automatyczne odświeżanie."""
        self._hide_auto_dropdown()
        current = self.auto_refresh_enabled.get()
        self.auto_refresh_enabled.set(not current)
        if not current:
            self.log_message("Automatyczne uzupełnianie WŁĄCZONE")
            self._schedule_auto_refresh()
        else:
            self.log_message("Automatyczne uzupełnianie WYŁĄCZONE")
            self._cancel_auto_refresh()
        self._update_auto_status_display()

    def _start_auto_refresh_now(self):
        """Uruchamia automatyczne pobieranie natychmiast."""
        self._hide_auto_dropdown()
        # Włącz automatyczne odświeżanie jeśli nie jest włączone
        if not self.auto_refresh_enabled.get():
            self.auto_refresh_enabled.set(True)
            self._update_auto_status_display()
        self.log_message("Rozpoczynam pobieranie sugestii...")
        # Anuluj poprzednie zaplanowane i rozpocznij od razu
        self._cancel_auto_refresh()
        self._update_suggestions()
        # Zaplanuj następne pobranie
        self._schedule_auto_refresh()

    def _manual_refresh_suggestions(self):
        """Ręczne jednorazowe pobranie sugestii."""
        self._hide_auto_dropdown()
        self._update_suggestions()

    def _show_interval_modal(self):
        """Wyświetla modal do ustawienia interwału."""
        self._hide_auto_dropdown()
        
        # Overlay - przyciemnione tło
        self.interval_overlay = tk.Frame(self.controller.root, bg='black')
        self.interval_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.interval_overlay.configure(bg='#000000')
        self.interval_overlay.lift()

        overlay_bg = tk.Frame(self.interval_overlay, bg='#1a1a1a')
        overlay_bg.place(x=0, y=0, relwidth=1, relheight=1)
        overlay_bg.bind('<Button-1>', lambda e: self._close_interval_modal())

        # Modal
        modal = tk.Frame(self.interval_overlay, bg='#2a2a2a', highlightbackground='#5588cc', highlightthickness=2)
        modal.place(relx=0.5, rely=0.5, anchor='center')

        # Tytuł
        title = tk.Label(modal, text="Ustawienia interwału", bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 14, 'bold'))
        title.pack(pady=(20, 16), padx=40)

        # Opis
        desc = tk.Label(modal, text="Interwał losowy między pobieraniami (w sekundach):", bg='#2a2a2a', fg='#888888', font=('Segoe UI', 10))
        desc.pack(pady=(0, 12))

        # Pola wejściowe
        input_frame = tk.Frame(modal, bg='#2a2a2a')
        input_frame.pack(pady=(0, 16))

        tk.Label(input_frame, text="Od:", bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 10)).pack(side='left', padx=(0, 8))
        self.interval_from_entry = ttk.Entry(input_frame, width=8)
        self.interval_from_entry.pack(side='left')
        self.interval_from_entry.insert(0, self.auto_from_var.get())

        tk.Label(input_frame, text="Do:", bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 10)).pack(side='left', padx=(16, 8))
        self.interval_to_entry = ttk.Entry(input_frame, width=8)
        self.interval_to_entry.pack(side='left')
        self.interval_to_entry.insert(0, self.auto_to_var.get())

        tk.Label(input_frame, text="sek.", bg='#2a2a2a', fg='#888888', font=('Segoe UI', 10)).pack(side='left', padx=(8, 0))

        # Przyciski
        btn_frame = tk.Frame(modal, bg='#2a2a2a')
        btn_frame.pack(pady=(0, 20))

        save_btn = tk.Label(
            btn_frame, text="Zapisz",
            bg='#5588cc', fg='#ffffff', font=('Segoe UI', 11),
            padx=24, pady=8, cursor='hand2'
        )
        save_btn.pack(side='left', padx=8)
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg='#6699dd'))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg='#5588cc'))
        save_btn.bind('<Button-1>', lambda e: self._save_interval_settings())

        cancel_btn = tk.Label(
            btn_frame, text="Anuluj",
            bg='#3a3a3a', fg='#ffffff', font=('Segoe UI', 11),
            padx=24, pady=8, cursor='hand2'
        )
        cancel_btn.pack(side='left', padx=8)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg='#4a4a4a'))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg='#3a3a3a'))
        cancel_btn.bind('<Button-1>', lambda e: self._close_interval_modal())

        self.interval_modal = modal

    def _close_interval_modal(self):
        """Zamyka modal ustawień interwału."""
        try:
            self.interval_overlay.destroy()
        except Exception:
            pass
        self.interval_overlay = None
        self.interval_modal = None

    def _save_interval_settings(self):
        """Zapisuje ustawienia interwału."""
        try:
            from_val = int(self.interval_from_entry.get())
            to_val = int(self.interval_to_entry.get())
            if from_val > 0 and to_val > 0 and to_val >= from_val:
                self.auto_from_var.set(str(from_val))
                self.auto_to_var.set(str(to_val))
                # Zapisz do pliku ustawień
                if hasattr(self.controller, 'persist_interval_settings'):
                    self.controller.persist_interval_settings(from_val, to_val)
                self.log_message(f"Interwał ustawiony: {from_val}-{to_val} sekund")
            else:
                self.log_message("Błąd: nieprawidłowe wartości interwału")
        except ValueError:
            self.log_message("Błąd: wprowadź liczby całkowite")
        self._close_interval_modal()

    def _schedule_auto_refresh(self):
        """Planuje następne automatyczne odświeżenie."""
        if not self.auto_refresh_enabled.get():
            return
        try:
            import random
            from_sec = int(self.auto_from_var.get())
            to_sec = int(self.auto_to_var.get())
            delay = random.randint(from_sec, to_sec)
            self._auto_refresh_job = self.controller.root.after(delay * 1000, self._auto_refresh_cycle)
            self.log_message(f"Następne automatyczne pobranie za {delay} sekund")
        except Exception as e:
            self.log_message(f"Błąd planowania: {e}")

    def _cancel_auto_refresh(self):
        """Anuluje zaplanowane automatyczne odświeżenie."""
        if hasattr(self, '_auto_refresh_job') and self._auto_refresh_job:
            try:
                self.controller.root.after_cancel(self._auto_refresh_job)
            except Exception:
                pass
            self._auto_refresh_job = None

    def _auto_refresh_cycle(self):
        """Wykonuje cykl automatycznego odświeżania."""
        if not self.auto_refresh_enabled.get():
            return
        self.log_message("Automatyczne pobieranie sugestii...")
        self._update_suggestions()
        # Zaplanuj następny cykl
        self._schedule_auto_refresh()

    def set_suggestions(self, suggestions):
        """Ustawia listę sugestii po pobraniu; aktualizuje etykietę i log."""
        try:
            self.controller.all_suggestions = suggestions or []
            self._update_auto_status_display()
            self.log_message(f"Autouzupełnianie załadowane ({len(self.controller.all_suggestions)} pozycji).")
            # aktualizacja zaplanowanego cyklu
            self._update_auto_next_label()
            # przeładuj taksonomię (gloves/stickers/agents itp.) z aktualnego suggestions.txt
            self._reload_taxonomy()
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
            self._update_auto_next_label()
        except Exception as e:
            print(f"Błąd aktualizacji sugestii: {e}", file=sys.stderr)
            self.log_message(f"BŁĄD: {e}")
            self.set_update_button_state(active=True)
            self.show_progress_bar(False)

    def _backfill_suggestions(self):
        """Uruchamia szybki backfill brakujących pozycji bez pełnego skanowania."""
        try:
            self.log_message("Backfill: start uzupełniania brakujących pozycji...")
            # Zablokuj akcje na czas backfill
            self.set_update_button_state(active=False)
            self.set_cancel_button_state(active=True)
            # Backfill działa w osobnym wątku po stronie kontrolera
            if hasattr(self.controller, 'backfill_suggestions_async'):
                self.controller.backfill_suggestions_async()
            else:
                self.log_message("Backfill: funkcja niedostępna w kontrolerze.")
        except Exception as e:
            print(f"Błąd backfill: {e}", file=sys.stderr)
            self.log_message(f"BŁĄD backfill: {e}")
            self.set_update_button_state(active=True)
            self.set_cancel_button_state(active=False)

    # API wywoływane przez kontroler: ustaw/zdjęcie blokady przycisku
    def set_update_button_state(self, active: bool):
        try:
            if self.update_btn is not None:
                self.update_btn.config(state=('normal' if active else 'disabled'))
        except Exception:
            pass

    # API wywoływane przez kontroler: włącz/wyłącz przycisk anulowania
    def set_cancel_button_state(self, active: bool):
        try:
            if self.cancel_btn is not None:
                self.cancel_btn.config(state=('normal' if active else 'disabled'))
        except Exception:
            pass

    # API wywoływane przez kontroler: aktualizacja paska postępu
    def update_progress_bar(self, current: int, total: int, retries: int, eta: int = -1):
        if self.progress_bar is None:
            return  # brak widocznego paska w nowym UI
        try:
            if total and total > 0:
                # Pasek postępu pokazuje realny X/TOTAL (maksimum = total, wartość = current)
                safe_total = max(1, int(total))
                safe_current = max(0, min(int(current), safe_total))
                self.progress_bar.config(mode='determinate', maximum=safe_total)
                self.progress_var.set(safe_current)
                # Ustaw procent na pasku zadań (taskbar) poprzez tytuł okna
                try:
                    percent_val = int((safe_current / float(safe_total)) * 100)
                    if hasattr(self.controller, 'set_taskbar_percent'):
                        self.controller.set_taskbar_percent(percent_val)
                except Exception:
                    pass
            else:
                # nieznane total -> tryb indeterminate
                self.progress_bar.config(mode='indeterminate')
                self.progress_bar.start(80)
                # Przy nieznanym total usuń procent z tytułu
                try:
                    if hasattr(self.controller, 'set_taskbar_percent'):
                        self.controller.set_taskbar_percent(None)
                except Exception:
                    pass
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
            # Dodatkowo procent do etykiety (obliczany tylko gdy znamy total)
            # Usunięty procent z etykiety (widoczny tylko w tytule okna)
            self.inline_progress_var.set(f"[Postęp: {current} / {total_disp} | ETA: {eta_hms}]")
            # Nie logujemy postępu do logów – etykieta między przyciskami wystarcza
        except Exception:
            pass

    def show_progress_bar(self, visible: bool):
        if self.progress_bar is None:
            return
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

    # ------------------------------------------------------------------
    # AUTO REFRESH HOOKS
    # ------------------------------------------------------------------
    def _on_auto_toggle(self):
        enabled = self.auto_refresh_enabled.get()
        if self.force_cycle_btn is not None:
            try:
                self.force_cycle_btn.config(state=('normal' if enabled else 'disabled'))
            except Exception:
                pass
        if hasattr(self.controller, 'set_auto_refresh_config'):
            try:
                from_val = int(self.auto_from_var.get())
                to_val = int(self.auto_to_var.get())
            except Exception:
                from_val, to_val = 600, 900
            self.controller.set_auto_refresh_config(enabled, from_val, to_val)
        # aktualizuj etykietę z następnym cyklem
        self._update_auto_next_label()

    def _update_auto_next_label(self):
        try:
            if not self.auto_refresh_enabled.get():
                self.auto_next_var.set("Auto: wyłączone")
                return
            # Jeśli kontroler zaplanował następny czas, pobierz go
            ts = getattr(self.controller, '_next_auto_refresh_ts', None)
            import time
            if ts and ts > time.time():
                remaining = int(ts - time.time())
                mins = remaining // 60
                secs = remaining % 60
                self.auto_next_var.set(f"Następny cykl za {mins:02d}:{secs:02d}")
            else:
                self.auto_next_var.set("Planowanie...")
        except Exception:
            pass

    def _force_auto_cycle(self):
        # Wymuszenie natychmiastowego cyklu niezależnie od planowania
        if self.auto_refresh_enabled.get():
            self.log_message("Wymuszony cykl auto-odświeżania sugestii.")
            self._update_suggestions()
    def _go_back_to_login(self):
        """Przełącza do ekranu logowania z zachowaniem obecnego cookie w polu, umożliwiając jego zmianę."""
        try:
            # Wyczyść zapamiętaną sesję ('remember me') przy ręcznym wylogowaniu
            try:
                if hasattr(self.controller, 'clear_auth_state'):
                    self.controller.clear_auth_state()
            except Exception:
                pass
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
        """Loguje komunikat – jeśli status_text istnieje wyświetla tam, inaczej print."""
        if self.status_text is not None:
            try:
                self.status_text.config(state='normal')
                self.status_text.insert(tk.END, text + "\n")
                self.status_text.see(tk.END)
                self.status_text.config(state='disabled')
                return
            except Exception:
                pass
        print(f"[SearchView] {text}")

    def start_search_thread(self):
        # Zbuduj nazwę przedmiotu na podstawie wybranej kategorii za pomocą mapowanych builderów
        item_name = self._build_item_name()
        if not item_name:
            # Builder mógł zalogować przyczynę; bez konkretnej nazwy nie kontynuujemy
            return

        self.search_button.config(state='disabled')
        # Komunikat o trybie
        if not getattr(self.controller, 'login_cookie', None):
            self.log_message(f"Tryb bez cookie – historia cen będzie niedostępna dla: {item_name}.")
        else:
            self.log_message(f"Rozpoczynanie pobierania dla: {item_name}...")
        
        login_cookie = self.controller.login_cookie
        
        threading.Thread(target=self._run_search_and_save, args=(item_name, login_cookie,), daemon=True).start()

    # ------------------------ NAME BUILDERS ------------------------
    def _get_selected_category(self) -> str:
        try:
            return (self.category_combo.get() or '').strip()
        except Exception:
            return ''

    def _build_item_name(self) -> str:
        cat = self._get_selected_category()
        # Mapowanie kategoria -> funkcja budująca nazwę
        builders = {
            'Noże': self._build_name_knives,
            'Nóż': self._build_name_knives,
            'Rękawice': self._build_name_gloves,
            'Naklejka': self._build_name_sticker,
            'Zeus x27': self._build_name_zeus,
            'Graffiti': self._build_name_graffiti,
            'Agent': self._build_name_agent,
            'Inne': self._build_name_other,
            'Pojemnik': self._build_name_container,
            'Skrzynki': self._build_name_container,
        }
        builder = builders.get(cat, self._build_name_default)
        return builder()

    def _reload_taxonomy(self):
        """Reload skin_list to pick up new parsed suggestions and refresh current category UI."""
        try:
            import src.skin_list as skin_list_mod
            importlib.reload(skin_list_mod)
            global GLOVES, STICKERS, ZEUS_SKINS, GRAFFITI, AGENTS, CONTAINERS, OTHER_TYPES
            GLOVES = skin_list_mod.GLOVES
            STICKERS = skin_list_mod.STICKERS
            ZEUS_SKINS = skin_list_mod.ZEUS_SKINS
            GRAFFITI = skin_list_mod.GRAFFITI
            AGENTS = skin_list_mod.AGENTS
            CONTAINERS = skin_list_mod.CONTAINERS
            OTHER_TYPES = skin_list_mod.OTHER_TYPES
            global KNIVES, MUSIC_KITS, MUSIC_KITS_STATTRAK, KEY_ITEMS, CHARM_ITEMS
            global VIEWER_PASSES, OPERATION_PASSES, COLLECTIBLE_PINS, GIFT_ITEMS, PATCH_ITEMS, TOOL_ITEMS
            KNIVES = skin_list_mod.KNIVES
            MUSIC_KITS = skin_list_mod.MUSIC_KITS
            MUSIC_KITS_STATTRAK = skin_list_mod.MUSIC_KITS_STATTRAK
            KEY_ITEMS = skin_list_mod.KEY_ITEMS
            CHARM_ITEMS = skin_list_mod.CHARM_ITEMS
            VIEWER_PASSES = skin_list_mod.VIEWER_PASSES
            OPERATION_PASSES = skin_list_mod.OPERATION_PASSES
            COLLECTIBLE_PINS = skin_list_mod.COLLECTIBLE_PINS
            GIFT_ITEMS = skin_list_mod.GIFT_ITEMS
            PATCH_ITEMS = skin_list_mod.PATCH_ITEMS
            TOOL_ITEMS = skin_list_mod.TOOL_ITEMS
            # jeśli jesteśmy w kategorii Agent – odśwież listy
            current_cat = self.category_combo.get()
            if current_cat == 'Agent':
                self.on_category_select(None)
            self.log_message("Przeładowano dane taksonomii.")
        except Exception as e:
            self.log_message(f"BŁĄD przeładowania taksonomii: {e}")

    def _common_inputs(self):
        weapon = (self.weapon_combo.get() or '').strip()
        skin = (self.skin_combo.get() or '').strip()
        wear = (self.wear_combobox.get() or '').strip()
        return weapon, skin, wear

    def _build_name_default(self) -> str:
        weapon, skin, wear = self._common_inputs()
        if not weapon:
            self.log_message("BŁĄD: Wybierz typ broni!")
            return ''
        parts = []
        # Souvenir vs StatTrak (wzajemnie wykluczające)
        if self.souvenir_var.get():
            parts.append("Souvenir")
        elif self.stattrack_var.get():
            parts.append("StatTrak™")
        parts.append(weapon)
        if skin and skin != 'Brak':
            parts.append("|")
            parts.append(skin)
        if wear and wear != 'Brak':
            parts.append(wear)
        return " ".join(parts)

    def _build_name_knives(self) -> str:
        weapon, skin, wear = self._common_inputs()
        if not weapon:
            self.log_message("BŁĄD: Wpisz nazwę noża!")
            return ''
        raw_weapon = weapon[2:] if weapon.startswith('★ ') else weapon
        parts = ["★"]
        if self.stattrack_var.get():
            parts.append("StatTrak™")
        parts.append(raw_weapon)
        if skin and skin.lower() != 'vanilla':
            parts.extend(["|", skin])
            if wear and wear != 'Brak':
                parts.append(wear)
        return " ".join(parts)

    def _build_name_gloves(self) -> str:
        weapon, skin, wear = self._common_inputs()
        if not weapon or not skin:
            self.log_message("BŁĄD: Wybierz typ rękawic i skina.")
            return ''
        parts = [weapon, "|", skin]
        if wear and wear != 'Brak':
            parts.append(wear)
        return " ".join(parts)

    def _build_name_sticker(self) -> str:
        sticker_type = (self.weapon_combo.get() or '').strip()
        skin = (self.skin_combo.get() or '').strip()
        event_or_quality = (self.wear_combobox.get() or '').strip()
        if not skin:
            self.log_message("BŁĄD: Wybierz nazwę naklejki.")
            return ''
        if sticker_type == 'Esportowa':
            if not event_or_quality:
                self.log_message("BŁĄD: Wybierz event dla naklejki esportowej.")
                return ''
            return f"Sticker | {skin} | {event_or_quality}"
        # Zwykła – brak pola jakości
        return f"Sticker | {skin}"

    def _build_name_zeus(self) -> str:
        _weapon, skin, wear = self._common_inputs()
        if not skin:
            self.log_message("BŁĄD: Wybierz skina dla Zeus x27.")
            return ''
        # Zeus używa formatu jak broń: "Zeus x27 | Skin (Wear)" gdy wear wybrany
        if wear and wear != 'Brak':
            # Jeśli wear nie zawiera nawiasów, dodaj je
            wear_str = wear if wear.startswith('(') else f"({wear})"
            return f"Zeus x27 | {skin} {wear_str}"
        return f"Zeus x27 | {skin}"

    def _build_name_graffiti(self) -> str:
        # Graffiti ma dwa tryby: Esportowe (event->name) i Zwykłe (name->color)
        g_type = (self.weapon_combo.get() or '').strip()
        event_or_color = (self.wear_combobox.get() or '').strip()
        name = (self.skin_combo.get() or '').strip()
        if g_type == 'Esportowe':
            if not event_or_color:
                self.log_message("BŁĄD: Wybierz event.")
                return ''
            if not name:
                self.log_message("BŁĄD: Wybierz nazwę graffiti (event).")
                return ''
            # Steam market_hash_name dla esport: "Sealed Graffiti | Nazwa | Event"
            return f"Sealed Graffiti | {name} | {event_or_color}"
        # Zwykłe
        if not name:
            self.log_message("BŁĄD: Wybierz nazwę graffiti.")
            return ''
        if event_or_color:
            return f"Sealed Graffiti | {name} ({event_or_color})"
        return f"Sealed Graffiti | {name}"

    def _on_graffiti_type_select(self, event):
        try:
            g_type = self.weapon_combo.get()
            if g_type == 'Esportowe':
                self.label_quality.config(text='Event:')
                events = GRAFFITI.get('events', [])
                self.wear_combobox.config(state='readonly')
                self.wear_combobox['values'] = events
                # Nie wybieraj automatycznie eventu – użytkownik wybiera, a nazwy odblokujemy po wyborze
                self.wear_combobox.set('')
                self.skin_combo['values'] = []
                self.skin_combo.set('')
                self.skin_combo.config(state='disabled')
                # W trybie Esportowe wiąż handler wyboru eventu
                try:
                    self.wear_combobox.bind("<<ComboboxSelected>>", self._on_graffiti_event_select)
                except Exception:
                    pass
            else:  # Zwykłe
                self.label_quality.config(text='Kolor:')
                normal_names = GRAFFITI.get('normal_names', [])
                self.skin_combo['values'] = normal_names
                self.skin_combo.config(state='readonly')
                if normal_names:
                    self.skin_combo.set(normal_names[0])
                    first = self.skin_combo.get()
                    colors = GRAFFITI.get('name_to_colors', {}).get(first, [])
                    # Ustaw stan pola kolorów zależnie od dostępności wariantów
                    if colors:
                        self.wear_combobox.config(state='readonly')
                    else:
                        self.wear_combobox.config(state='disabled')
                    self.wear_combobox['values'] = colors
                    if colors:
                        self.wear_combobox.set(colors[0])
                    else:
                        self.wear_combobox.set('')
                        self.log_message("Wybrane graffiti nie ma wariantów kolorystycznych.")
                else:
                    self.skin_combo.set('')
                    self.wear_combobox['values'] = []
                    self.wear_combobox.set('')
                    self.skin_combo.config(state='disabled')
                    self.wear_combobox.config(state='disabled')
                # W trybie Zwykłe – odwiąż handler eventu, bo pole oznacza 'Kolor'
                try:
                    self.wear_combobox.unbind("<<ComboboxSelected>>")
                except Exception:
                    pass
        except Exception as e:
            self.log_message(f"BŁĄD wyboru typu graffiti: {e}")

    def _on_graffiti_event_select(self, event):
        try:
            # Gdy tryb to 'Zwykłe', zmiany w polu 'Kolor' nie powinny wpływać na listę nazw
            if (self.weapon_combo.get() or '').strip() == 'Zwykłe':
                return
            event_name = self.wear_combobox.get()
            names = GRAFFITI.get('event_to_names', {}).get(event_name, [])
            self.skin_combo['values'] = names
            if names:
                self.skin_combo.config(state='readonly')
                self.skin_combo.set(names[0])
            else:
                self.skin_combo.config(state='disabled')
                self.skin_combo.set('')
                self.log_message("Brak nazw graffiti dla wybranego eventu.")
        except Exception as e:
            self.log_message(f"BŁĄD wyboru eventu: {e}")

    def _on_graffiti_name_select(self, event):
        try:
            g_type = self.weapon_combo.get()
            if g_type == 'Zwykłe':
                name = self.skin_combo.get()
                colors = GRAFFITI.get('name_to_colors', {}).get(name, [])
                self.wear_combobox['values'] = colors
                if colors:
                    self.wear_combobox.set(colors[0])
                    self.wear_combobox.config(state='readonly')
                else:
                    self.wear_combobox.set('')
                    self.wear_combobox.config(state='disabled')
                    self.log_message("Wybrane graffiti nie ma wariantów kolorystycznych.")
        except Exception as e:
            self.log_message(f"BŁĄD wyboru nazwy graffiti: {e}")

    def _build_name_agent(self) -> str:
        collection = (self.wear_combobox.get() or '').strip()
        agent_name = (self.skin_combo.get() or '').strip()
        if not collection:
            self.log_message("BŁĄD: Wybierz kolekcję agenta.")
            return ''
        if not agent_name:
            self.log_message("BŁĄD: Wybierz nazwę agenta.")
            return ''
        placeholders = {"Operator X", "Specialist Y", "Trooper Z"}
        if agent_name in placeholders:
            self.log_message("BŁĄD: Placeholder – wybierz prawdziwego agenta.")
            return ''
        return f"{agent_name} | {collection}"

    def _on_agent_collection_select(self, event):
        try:
            collection = self.wear_combobox.get()
            from src.skin_list import AGENTS as _AG
            agent_list = _AG.get('map', {}).get(collection, _AG.get('names', []))
            self.skin_combo['values'] = agent_list
            if agent_list:
                self.skin_combo.set(agent_list[0])
            self.log_message(f"Zmieniono kolekcję agenta na: {collection}")
        except Exception as e:
            self.log_message(f"BŁĄD zmiany kolekcji agenta: {e}")

    def _on_other_type_select(self, event):
        other_type = (self.weapon_combo.get() or '').strip()
        self._configure_other_type_ui(other_type)

    def _configure_other_type_ui(self, other_type: str):
        """Konfiguruje UI dla kategorii 'Inne' - używa LabelFrame'ów z pack()."""
        try:
            try:
                self.skin_combo.unbind("<<ComboboxSelected>>")
            except Exception:
                pass
            # Ukryj pole Jakość domyślnie dla kategorii Inne
            try:
                self.qual_lf.pack_forget()
            except Exception:
                pass
            # Zresetuj combobox'y
            self.skin_combo.config(state='disabled')
            self.skin_combo['values'] = []
            self.skin_combo.set('')
            self.wear_combobox.config(state='disabled')
            self.wear_combobox['values'] = []
            self.wear_combobox.set('')
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)

            if other_type == 'Zestaw utworów':
                # Nazwa zestawu
                try:
                    self.name_lf.config(text='Nazwa')
                except Exception:
                    pass
                kits = MUSIC_KITS or []
                self.skin_combo.config(state='readonly' if kits else 'disabled')
                self.skin_combo['values'] = kits
                if kits:
                    self.skin_combo.set(kits[0])
                else:
                    self.skin_combo.set('')
                self.skin_combo.bind("<<ComboboxSelected>>", self._on_music_kit_select)
                self._refresh_music_kit_stattrak()
                return

            if other_type == 'Klucz':
                try:
                    self.name_lf.config(text='Nazwa')
                except Exception:
                    pass
                keys = KEY_ITEMS or []
                self.skin_combo.config(state='readonly' if keys else 'disabled')
                self.skin_combo['values'] = keys
                if keys:
                    self.skin_combo.set(keys[0])
                else:
                    self.skin_combo.set('')
                return

            if other_type == 'Przywieszka':
                try:
                    self.name_lf.config(text='Nazwa')
                except Exception:
                    pass
                charms = CHARM_ITEMS or []
                self.skin_combo.config(state='readonly' if charms else 'disabled')
                self.skin_combo['values'] = charms
                if charms:
                    self.skin_combo.set(charms[0])
                else:
                    self.skin_combo.set('')
                return

            if other_type == 'Przepustka':
                # Pokaż pole Jakość jako Typ przepustki
                try:
                    self.qual_lf.config(text='Typ przepustki')
                    self.qual_lf.pack(side='left')
                except Exception:
                    pass
                pass_types = ['Przepustka widza', 'Przepustka operacji']
                self.wear_combobox.config(state='readonly')
                self.wear_combobox['values'] = pass_types
                selected_type = pass_types[0] if pass_types else ''
                if selected_type:
                    self.wear_combobox.set(selected_type)
                else:
                    self.wear_combobox.set('')
                try:
                    self.name_lf.config(text='Nazwa')
                except Exception:
                    pass
                self._set_pass_names(selected_type)
                self.wear_combobox.bind("<<ComboboxSelected>>", self._on_pass_type_select)
                return

            if other_type == 'Przedmiot kolekcjonerski':
                try:
                    self.name_lf.config(text='Nazwa')
                except Exception:
                    pass
                pins = COLLECTIBLE_PINS or []
                self.skin_combo.config(state='readonly' if pins else 'disabled')
                self.skin_combo['values'] = pins
                if pins:
                    self.skin_combo.set(pins[0])
                else:
                    self.skin_combo.set('')
                return

            if other_type == 'Prezent':
                try:
                    self.name_lf.config(text='Nazwa')
                except Exception:
                    pass
                gifts = GIFT_ITEMS or []
                self.skin_combo.config(state='readonly' if gifts else 'disabled')
                self.skin_combo['values'] = gifts
                if gifts:
                    self.skin_combo.set(gifts[0])
                else:
                    self.skin_combo.set('')
                return

            if other_type == 'Naszywka':
                try:
                    self.name_lf.config(text='Nazwa')
                except Exception:
                    pass
                patches = PATCH_ITEMS or []
                self.skin_combo.config(state='readonly' if patches else 'disabled')
                self.skin_combo['values'] = patches
                if patches:
                    self.skin_combo.set(patches[0])
                else:
                    self.skin_combo.set('')
                return

            if other_type == 'Narzędzie':
                try:
                    self.name_lf.config(text='Nazwa')
                except Exception:
                    pass
                tools = TOOL_ITEMS or []
                self.skin_combo.config(state='readonly' if tools else 'disabled')
                self.skin_combo['values'] = tools
                if tools:
                    self.skin_combo.set(tools[0])
                else:
                    self.skin_combo.set('')
                return

            if other_type:
                self.log_message(f"INFO: Kategoria 'Inne' nie ma jeszcze konfiguracji dla typu '{other_type}'.")
        except Exception as exc:
            self.log_message(f"BŁĄD konfiguracji typu '{other_type}': {exc}")

    def _on_music_kit_select(self, event):
        self._refresh_music_kit_stattrak()

    def _refresh_music_kit_stattrak(self):
        try:
            kit_name = (self.skin_combo.get() or '').strip()
            if kit_name and kit_name in MUSIC_KITS_STATTRAK:
                self.stattrack_check.config(state='normal')
            else:
                self.stattrack_check.config(state='disabled')
                self.stattrack_var.set(False)
        except Exception:
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)

    def _on_pass_type_select(self, event):
        pass_label = self.wear_combobox.get()
        self._set_pass_names(pass_label)

    def _set_pass_names(self, pass_label: str):
        try:
            mapping = {
                'Przepustka widza': VIEWER_PASSES or [],
                'Przepustka operacji': OPERATION_PASSES or [],
            }
            names = mapping.get(pass_label, [])
            self.skin_combo.config(state='readonly' if names else 'disabled')
            self.skin_combo['values'] = names
            if names:
                self.skin_combo.set(names[0])
            else:
                self.skin_combo.set('')
        except Exception:
            self.skin_combo.config(state='disabled')
            self.skin_combo['values'] = []
            self.skin_combo.set('')

    def _build_name_other(self) -> str:
        weapon, _skin, _wear = self._common_inputs()
        # Na razie brak wsparcia detali – tylko typ
        if weapon == 'Zestaw utworów':
            kit_name = (self.skin_combo.get() or '').strip()
            if not kit_name:
                self.log_message("BŁĄD: Wybierz nazwę zestawu utworów.")
                return ''
            prefix = "StatTrak™ " if self.stattrack_var.get() else ''
            return f"{prefix}Music Kit | {kit_name}"
        if weapon == 'Klucz':
            key_name = (self.skin_combo.get() or '').strip()
            if not key_name:
                self.log_message("BŁĄD: Wybierz nazwę klucza.")
                return ''
            return key_name
        if weapon == 'Przywieszka':
            charm_name = (self.skin_combo.get() or '').strip()
            if not charm_name:
                self.log_message("BŁĄD: Wybierz nazwę przywieszki.")
                return ''
            return f"Charm | {charm_name}"
        if weapon == 'Przepustka':
            pass_name = (self.skin_combo.get() or '').strip()
            if not pass_name:
                self.log_message("BŁĄD: Wybierz nazwę przepustki.")
                return ''
            return pass_name
        if weapon == 'Przedmiot kolekcjonerski':
            pin_name = (self.skin_combo.get() or '').strip()
            if not pin_name:
                self.log_message("BŁĄD: Wybierz nazwę pinu kolekcjonerskiego.")
                return ''
            return pin_name
        if weapon == 'Prezent':
            gift_name = (self.skin_combo.get() or '').strip()
            if not gift_name:
                self.log_message("BŁĄD: Wybierz nazwę prezentu.")
                return ''
            return gift_name
        if weapon == 'Naszywka':
            patch_name = (self.skin_combo.get() or '').strip()
            if not patch_name:
                self.log_message("BŁĄD: Wybierz nazwę naszywki.")
                return ''
            return f"Patch | {patch_name}"
        if weapon == 'Narzędzie':
            tool_name = (self.skin_combo.get() or '').strip()
            if not tool_name:
                self.log_message("BŁĄD: Wybierz nazwę narzędzia.")
                return ''
            return tool_name
        self.log_message("INFO: Kategoria 'Inne' nie ma jeszcze pełnego wsparcia budowania nazw.")
        return weapon

    def _build_name_container(self) -> str:
        # W nowym układzie "Rodzaj" wybierany jest w wear_combobox, a "Nazwa" w skin_combo
        kind = (self.wear_combobox.get() or '').strip()
        name = (self.skin_combo.get() or '').strip()
        if not kind:
            self.log_message("BŁĄD: Wybierz rodzaj pojemnika.")
            return ''
        if not name:
            self.log_message("BŁĄD: Wybierz nazwę.")
            return ''
        return name

    # Handlery wzajemnego wykluczania
    def _on_stattrak_toggle(self):
        try:
            if self.stattrack_var.get():
                # Odznacz Souvenir
                if self.souvenir_var.get():
                    self.souvenir_var.set(False)
        except Exception:
            pass

    def _on_souvenir_toggle(self):
        try:
            if self.souvenir_var.get():
                # Odznacz StatTrak
                if self.stattrack_var.get():
                    self.stattrack_var.set(False)
        except Exception:
            pass

    def _run_search_and_save(self, item_name, login_cookie):
        """Logika pobierania i zapisywania w wątku."""
        
        # Debug logging
        if logger.enabled:
            logger.info(f"Starting search for: {item_name}")
            logger.debug(f"Cookie present: {bool(login_cookie)}")
        
        search_start = time.time()
        
        # 1. Pobieranie historii cen (tylko z cookie)
        try:
            if login_cookie:
                if logger.enabled:
                    logger.debug("Fetching price history...")
                
                history = steam_market.get_price_history(item_name, login_cookie)
                
                if history is None:
                    if logger.enabled:
                        logger.error(f"Price history API error for {item_name}")
                    self.controller.result_queue.put({'status': 'error', 'message': 'Błąd API podczas pobierania historii. Sprawdź konsolę.'})
                    return
                if not history:
                    if logger.enabled:
                        logger.warning(f"No history data for {item_name}")
                    self.controller.result_queue.put({'status': 'log', 'message': f'Brak danych historycznych dla {item_name}.'})
                else:
                    if logger.enabled:
                        logger.info(f"Fetched {len(history)} history records")
                    self.controller.result_queue.put({'status': 'log', 'message': f'Pobrano {len(history)} rekordów z API.'})
            else:
                if logger.enabled:
                    logger.debug("No cookie - skipping price history")
                history = []
        except Exception as e:
            if logger.enabled:
                logger.exception(f"Critical error fetching history: {e}")
            print(f"Krytyczny błąd w wątku (historia): {e}", file=sys.stderr)
            self.controller.result_queue.put({'status': 'error', 'message': f'Wystąpił krytyczny błąd podczas pobierania historii: {e}'})
            return

        time.sleep(1.5) 

        # 2. Pobieranie aktualnych ofert (Listings)
        try:
            if logger.enabled:
                logger.debug("Fetching market listings...")
            
            # Przekazujemy 'login_cookie'
            listings_data = steam_market.get_market_listings(item_name, login_cookie, count=10)
            
            if listings_data is None:
                if logger.enabled:
                    logger.warning("No listings data returned")
                self.controller.result_queue.put({'status': 'log', 'message': 'Brak lub błąd pobierania aktualnych ofert rynkowych.'})
                listings_data = {'listings': [], 'total_count': 0, 'lowest_price': "N/A"}
            else:
                fetched = len(listings_data.get("listings", []))
                total = listings_data.get("total_count", 0)
                if logger.enabled:
                    logger.info(f"Fetched {fetched}/{total} listings")
                self.controller.result_queue.put({'status': 'log', 'message': f'Pobrano {fetched} z {total} ofert.'})
                meta = listings_data.get('meta') or {}
                pages = meta.get('pages_loaded')
                retries = meta.get('retries')
                if pages is not None or retries is not None:
                    if logger.enabled:
                        logger.debug(f"Listings meta: pages={pages}, retries={retries}")
                    self.controller.result_queue.put({'status': 'log', 'message': f'Metryki: Strony: {pages or 0} | Retry: {retries or 0}.'})
        except Exception as e:
            if logger.enabled:
                logger.exception(f"Critical error fetching listings: {e}")
            print(f"Krytyczny błąd w wątku (oferty): {e}", file=sys.stderr)
            listings_data = {'listings': [], 'total_count': 0, 'lowest_price': "N/A", 'highest_buy_order': "N/A"}

        # 3. Zapisywanie i przekazywanie danych
        try:
            parsed_name_parts = steam_market.parse_market_name(item_name)
            if logger.enabled:
                logger.debug(f"Parsed name: type={parsed_name_parts['type']}, name={parsed_name_parts['name']}, wear={parsed_name_parts['wear']}")

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
                if logger.enabled:
                    logger.info(f"Saved {added_count} new records to database")
                self.controller.result_queue.put({'status': 'log', 'message': f'Zapisano {added_count} nowych unikalnych rekordów w bazie.'})

            all_db_records = database.get_sales_for_item(item_name)
            
            # Oblicz czas całkowity
            total_time = time.time() - search_start
            if logger.enabled:
                logger.perf(f"Search '{item_name[:30]}...'", total_time)
                logger.info(f"Search complete: {len(all_db_records)} total records in DB")
            
            self.controller.result_queue.put({
                'status': 'success',
                'item_name': item_name,
                'history_data': all_db_records,  # Przekazujemy listę bez sortowania
                'listings_data': listings_data,
                # Pobierz URL obrazka (jeśli dostępny) i przekaż dalej; nie blokujemy krytycznie jeśli brak
                'image_url': steam_market.get_item_image_url(item_name, login_cookie)
            })
            
        except Exception as e:
            if logger.enabled:
                logger.exception(f"Critical error saving/passing data: {e}")
            print(f"Krytyczny błąd w wątku (zapis/przekazanie): {e}", file=sys.stderr)
            self.controller.result_queue.put({'status': 'error', 'message': f'Wystąpił krytyczny błąd: {e}'})
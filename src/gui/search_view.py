import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import threading
import sys 
import time 
import importlib

from src import steam_market
from src import database
from src.skin_list import (
    SKIN_DATA, WEAPON_CATEGORIES,
    GLOVES, STICKERS, ZEUS_SKINS, GRAFFITI, AGENTS, CONTAINERS, OTHER_TYPES,
    ZEUS_WEAR_MAP, WEAPON_WEAR_MAP, WEAPON_SOUVENIR_MAP, WEAPON_STATTRAK_MAP,
    KNIVES
)


class SearchView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew") 
        
        self.frame.grid_rowconfigure(3, weight=1) 
        self.frame.grid_columnconfigure(0, weight=1) 

        self._create_widgets()
        # Dane rozszerzonych kategorii dostarczane przez skin_list.py (brak lokalnych struktur)
        
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
        
        # StatTrak / Souvenir
        self.stattrack_var = tk.BooleanVar(value=False)
        self.souvenir_var = tk.BooleanVar(value=False)
        self.stattrack_check = ttk.Checkbutton(input_frame, text="StatTrak™", variable=self.stattrack_var,
                                               onvalue=True, offvalue=False, command=self._on_stattrak_toggle)
        self.stattrack_check.grid(row=0, column=0, padx=(0, 10), pady=5, sticky='w')
        self.souvenir_check = ttk.Checkbutton(input_frame, text="Souvenir", variable=self.souvenir_var,
                                              onvalue=True, offvalue=False, command=self._on_souvenir_toggle)
        self.souvenir_check.grid(row=0, column=1, padx=(0, 10), pady=5, sticky='w')
        # Jakość (domyślnie); dla kategorii Pojemnik zmieniana na "Rodzaj"
        self.label_quality = ttk.Label(input_frame, text="Jakość:")
        self.label_quality.grid(row=1, column=2, padx=(10, 5), pady=5, sticky='w')
        self.wear_options = ["(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)", "Brak"]
        self.wear_combobox = ttk.Combobox(input_frame, values=self.wear_options, width=18, state='readonly')
        self.wear_combobox.grid(row=1, column=3, sticky='ew', pady=5)
        self.wear_combobox.set("(Field-Tested)")

        # Kategoria broni (np. Karabiny, Pistolety, Noże)
        self.label_category = ttk.Label(input_frame, text="Kategoria broni:")
        self.label_category.grid(row=1, column=0, padx=(0, 10), pady=5, sticky='w')
        categories = sorted(list(WEAPON_CATEGORIES.keys()))
        # Rozszerzenia kategorii i rename Skrzynki->Pojemnik
        if 'Skrzynki' in categories and 'Pojemnik' not in categories:
            categories = [c for c in categories if c != 'Skrzynki'] + ['Pojemnik']
        extra_cats = ['Rękawice', 'Naklejka', 'Zeus x27', 'Graffiti', 'Agent', 'Inne']
        for ec in extra_cats:
            if ec not in categories:
                categories.append(ec)
        categories = sorted(categories)
        self.category_combo = ttk.Combobox(input_frame, values=categories, state='readonly')
        self.category_combo.grid(row=1, column=1, sticky='ew', pady=5)
        if categories:
            self.category_combo.set(categories[0])

        # Typ broni (filtrowane przez wybraną kategorię)
        self.label_weapon_type = ttk.Label(input_frame, text="Typ broni:")
        self.label_weapon_type.grid(row=2, column=0, padx=(0, 10), pady=5, sticky='w')
        weapon_list = sorted(list(SKIN_DATA.keys()))
        # default readonly; for 'Noże' category we'll make it editable and blank
        self.weapon_combo = ttk.Combobox(input_frame, values=weapon_list, state='readonly')
        self.weapon_combo.grid(row=2, column=1, sticky='ew', pady=5)

        # Skin (wyrównany do Typ broni w tym samym wierszu)
        self.label_skin = ttk.Label(input_frame, text="Skin:")
        self.label_skin.grid(row=2, column=2, padx=(10, 5), pady=5, sticky='w')
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
        # Przycisk backfill – szybki przebieg po offsetach, żeby domknąć brakujące pozycje
        self.backfill_btn = ttk.Button(suggestions_controls, text="Backfill braków", command=self._backfill_suggestions)
        # Umieść poniżej głównego przycisku, aby nie kolidować z etykietą postępu i Anuluj
        self.backfill_btn.grid(row=1, column=0, sticky='w', pady=(4,0))
        # Etykieta postępu między przyciskami
        self.inline_progress_var = tk.StringVar(value="")
        self.inline_progress_label = ttk.Label(suggestions_controls, textvariable=self.inline_progress_var, anchor='center')
        self.inline_progress_label.grid(row=0, column=1, sticky='ew', padx=8)
        # Przycisk anulowania pobierania (na starcie wyłączony)
        self.cancel_btn = ttk.Button(suggestions_controls, text="Przerwij", command=self._cancel_update, state='disabled')
        self.cancel_btn.grid(row=0, column=2, padx=(12,0))
        # --- AUTO REFRESH CONFIG ---
        auto_frame = ttk.Frame(self.frame)
        auto_frame.grid(row=6, column=0, sticky='ew', pady=(8,0))
        auto_frame.grid_columnconfigure(7, weight=1)
        self.auto_refresh_enabled = tk.BooleanVar(value=False)
        self.auto_refresh_check = ttk.Checkbutton(auto_frame, text="Auto-odświeżanie sugestii", variable=self.auto_refresh_enabled, command=self._on_auto_toggle)
        self.auto_refresh_check.grid(row=0, column=0, padx=(0,8))
        ttk.Label(auto_frame, text="Interwał od (s):").grid(row=0, column=1)
        self.auto_from_var = tk.StringVar(value="600")
        self.auto_from_entry = ttk.Entry(auto_frame, width=6, textvariable=self.auto_from_var)
        self.auto_from_entry.grid(row=0, column=2, padx=(4,8))
        ttk.Label(auto_frame, text="do (s):").grid(row=0, column=3)
        self.auto_to_var = tk.StringVar(value="900")
        self.auto_to_entry = ttk.Entry(auto_frame, width=6, textvariable=self.auto_to_var)
        self.auto_to_entry.grid(row=0, column=4, padx=(4,8))
        self.auto_next_var = tk.StringVar(value="")
        self.auto_next_label = ttk.Label(auto_frame, textvariable=self.auto_next_var, foreground='gray')
        self.auto_next_label.grid(row=0, column=5, padx=(4,0))
        # przycisk wymuszenia natychmiastowego cyklu
        self.force_cycle_btn = ttk.Button(auto_frame, text="Cykl teraz", command=self._force_auto_cycle, state='disabled')
        self.force_cycle_btn.grid(row=0, column=6, padx=(12,0))
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
            # Zmienione etykiety
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
            return
        if selected_cat == 'Naklejka':
            self.weapon_combo.config(state='readonly')
            self.weapon_combo['values'] = STICKERS['types']
            self.weapon_combo.set(STICKERS['types'][0])
            self.label_skin.config(text='Naklejka:')
            self.skin_combo.config(state='readonly')
            # Start od naklejek eventowych
            self.skin_combo['values'] = STICKERS['events']
            if STICKERS['events']:
                self.skin_combo.set(STICKERS['events'][0])
            self.wear_combobox.config(state='readonly')
            self.wear_combobox['values'] = STICKERS['qualities']
            if STICKERS['qualities']:
                self.wear_combobox.set(STICKERS['qualities'][0])
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)
            return
        if selected_cat == 'Zeus x27':
            # Ukryj pole typu broni; Zeus ma tylko skiny
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
            self.weapon_combo.config(state='readonly')
            self.weapon_combo['values'] = OTHER_TYPES
            if OTHER_TYPES:
                self.weapon_combo.set(OTHER_TYPES[0])
            # Ukryj skórkę i jakość – placeholder
            self.label_skin.grid_remove()
            self.skin_combo.grid_remove()
            self.label_quality.grid_remove()
            self.wear_combobox.grid_remove()
            self.stattrack_check.config(state='disabled')
            self.stattrack_var.set(False)
            self.souvenir_check.config(state='disabled')
            self.souvenir_var.set(False)
            return
        if selected_cat == 'Pojemnik':
            # Ukryj Typ broni; używamy pola "Rodzaj" (wear_combobox) do wyboru podkategorii
            self.label_weapon_type.grid_remove()
            self.weapon_combo.grid_remove()
            # Ustaw "Rodzaj" i możliwe wartości
            rodzaje = [
                'Skrzynia',
                'Pojemnik z naklejkami',
                'Zestaw (Package)',
                'Terminal'
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

    def _reset_base_ui(self):
        """Przywraca podstawowe etykiety i widoczność dla klasycznej broni."""
        # Show all labels/combos
        self.label_weapon_type.config(text='Typ broni:')
        self.label_weapon_type.grid()
        self.weapon_combo.grid()
        self.label_skin.config(text='Skin:')
        self.label_skin.grid()
        self.skin_combo.grid()
        self.label_quality.config(text='Jakość:')
        self.label_quality.grid()
        self.wear_combobox.grid()
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
        self.welcome_label.config(text=f"Witaj, {self.controller.steam_name}")
        # Pokaż/ukryj komunikat o braku cookie
        has_cookie = bool(getattr(self.controller, 'login_cookie', None))
        try:
            if has_cookie:
                # Ukryj etykietę niezależnie od aktualnego stanu mapowania (ważne przy pierwszym wyświetleniu)
                self.cookie_mode_label.grid_remove()
            else:
                # Pokaż ponownie w tej samej komórce (row=0, col=0)
                self.cookie_mode_label.grid()
        except Exception:
            pass

    def set_suggestions(self, suggestions):
        """Ustawia listę sugestii po pobraniu; aktualizuje etykietę i log."""
        try:
            self.controller.all_suggestions = suggestions or []
            self.suggestions_label.config(text=f"Sugestie: {len(self.controller.all_suggestions)}")
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
        self.force_cycle_btn.config(state=('normal' if enabled else 'disabled'))
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
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, text + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

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
            global KNIVES
            KNIVES = skin_list_mod.KNIVES
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
        _weapon, skin, wear = self._common_inputs()
        if not skin:
            self.log_message("BŁĄD: Wybierz naklejkę.")
            return ''
        # Wzorzec: "Sticker | <Nazwa> (Jakość)"
        base = ["Sticker", "|", skin]
        if wear:
            base.append(f"({wear})")
        return " ".join(base)

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

    def _build_name_other(self) -> str:
        weapon, _skin, _wear = self._common_inputs()
        # Na razie brak wsparcia detali – tylko typ
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
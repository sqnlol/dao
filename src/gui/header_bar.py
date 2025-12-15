"""
Współdzielony komponent nagłówka (header bar) dla wszystkich widoków.
Dane użytkownika są przechowywane centralnie w kontrolerze aplikacji.
"""
import tkinter as tk
from tkinter import ttk
import os
import sys
import threading
import requests
from io import BytesIO
from PIL import Image, ImageTk


class HeaderBar:
    """Komponent nagłówka z logo, zakładkami i informacjami o użytkowniku."""
    
    # Współdzielone dane avatara (statyczne, ładowane raz)
    _avatar_photo = None
    _frame_photo = None
    _avatar_loaded = False
    
    def __init__(self, parent_frame, controller, active_tab='search'):
        """
        Tworzy header bar.
        
        Args:
            parent_frame: Ramka nadrzędna (tk.Frame)
            controller: Kontroler aplikacji (MarketApp)
            active_tab: Aktywna zakładka ('search', 'cases', 'case_detail')
        """
        self.controller = controller
        self.active_tab = active_tab
        self.parent = parent_frame
        
        # Menu dropdown
        self.dropdown_menu = None
        self.dropdown_visible = False
        
        self._create_header()
    
    def _create_header(self):
        """Tworzy nagłówek."""
        self.header = tk.Frame(self.parent, bg='#1e1e1e')
        self.header.grid(row=0, column=0, sticky='ew', padx=16, pady=(12, 0))
        self.header.grid_columnconfigure(2, weight=1)

        # Logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'CS2SkinAnalyzer.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img.thumbnail((48, 48))
                self._header_logo = ImageTk.PhotoImage(img)
                logo_lbl = tk.Label(self.header, image=self._header_logo, bg='#1e1e1e')
                logo_lbl.grid(row=0, column=0, padx=(0, 12))
        except Exception:
            pass

        # Zakładki
        search_fg = '#ffffff' if self.active_tab == 'search' else '#888888'
        cases_fg = '#ffffff' if self.active_tab in ('cases', 'case_detail') else '#888888'
        
        search_lbl = tk.Label(self.header, text="Wyszukiwarka", bg='#1e1e1e', fg=search_fg, 
                              font=('Segoe UI', 14), cursor='hand2' if self.active_tab != 'search' else '')
        search_lbl.grid(row=0, column=1, padx=(0, 24))
        if self.active_tab != 'search':
            search_lbl.bind('<Button-1>', lambda e: self.controller.switch_view('search'))
        
        cases_lbl = tk.Label(self.header, text="Skrzynie", bg='#1e1e1e', fg=cases_fg,
                             font=('Segoe UI', 14), cursor='hand2' if self.active_tab not in ('cases', 'case_detail') else '')
        cases_lbl.grid(row=0, column=2, sticky='w')
        if self.active_tab not in ('cases', 'case_detail'):
            cases_lbl.bind('<Button-1>', lambda e: self.controller.switch_view('cases'))

        # Prawa strona: powitanie + dropdown + avatar
        right_group = tk.Frame(self.header, bg='#1e1e1e')
        right_group.grid(row=0, column=3, sticky='e')

        # Kontener na nazwę i strzałkę
        user_dropdown_frame = tk.Frame(right_group, bg='#1e1e1e', cursor='hand2')
        user_dropdown_frame.pack(side='left', padx=(0, 8))

        steam_name = getattr(self.controller, 'steam_name', None) or 'Użytkownik'
        self.welcome_label = tk.Label(user_dropdown_frame, text=f"Witaj,\n{steam_name}", 
                                       bg='#1e1e1e', fg='#ffffff', font=('Segoe UI', 10), justify='right')
        self.welcome_label.pack(side='left')

        # Strzałka w dół
        self.dropdown_arrow = tk.Label(user_dropdown_frame, text="▼", bg='#1e1e1e', fg='#888888', 
                                        font=('Segoe UI', 8), cursor='hand2')
        self.dropdown_arrow.pack(side='left', padx=(4, 0))

        # Bindowanie kliknięcia na cały obszar
        for widget in (user_dropdown_frame, self.welcome_label, self.dropdown_arrow):
            widget.bind('<Button-1>', self._toggle_dropdown_menu)

        # Avatar (canvas dla obrazka i ramki Steam)
        self.avatar_canvas = tk.Canvas(right_group, width=52, height=52, bg='#1e1e1e', highlightthickness=0)
        self.avatar_canvas.pack(side='left')
        
        # Użyj współdzielonych danych avatara lub załaduj
        self._setup_avatar()

        # Niebieska linia pozioma
        separator = tk.Frame(self.parent, bg='#5588cc', height=2)
        separator.grid(row=0, column=0, sticky='sew', padx=0, pady=(70, 0))

    def _setup_avatar(self):
        """Ustawia avatar - używa cache lub ładuje nowy."""
        # Sprawdź czy avatar jest już załadowany w kontrolerze
        cached_avatar = getattr(self.controller, '_cached_avatar_photo', None)
        cached_frame = getattr(self.controller, '_cached_frame_photo', None)
        
        if cached_avatar:
            # Użyj cache'owanego avatara
            self.avatar_canvas.create_image(26, 26, image=cached_avatar, tags='avatar')
            if cached_frame:
                self.avatar_canvas.create_image(26, 26, image=cached_frame, tags='frame')
        else:
            # Domyślna ramka (niebieska) i placeholder
            self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1, tags='default_frame')
            self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', 
                                           font=('Segoe UI', 7), justify='center', tags='placeholder')
            # Załaduj avatar asynchronicznie
            self._load_avatar_async()

    def _load_avatar_async(self):
        """Asynchronicznie ładuje avatar użytkownika i zapisuje w kontrolerze."""
        def load():
            try:
                avatar_url = getattr(self.controller, 'steam_avatar_url', None)
                frame_url = getattr(self.controller, 'steam_frame_url', None)
                
                if avatar_url:
                    resp = requests.get(avatar_url, timeout=10)
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content))
                        img = img.resize((46, 46), Image.Resampling.LANCZOS)
                        
                        def set_avatar():
                            try:
                                # Sprawdź czy użytkownik nadal jest zalogowany
                                if not getattr(self.controller, 'is_logged_in', lambda: False)():
                                    return
                                photo = ImageTk.PhotoImage(img)
                                # Zapisz w kontrolerze dla innych widoków
                                self.controller._cached_avatar_photo = photo
                                self.avatar_canvas.delete('placeholder')
                                self.avatar_canvas.delete('default_frame')
                                self.avatar_canvas.create_image(26, 26, image=photo, tags='avatar')
                            except Exception:
                                pass
                        self.avatar_canvas.after(0, set_avatar)
                
                if frame_url:
                    resp = requests.get(frame_url, timeout=10)
                    if resp.status_code == 200:
                        frame_img = Image.open(BytesIO(resp.content))
                        frame_img = frame_img.resize((52, 52), Image.Resampling.LANCZOS)
                        
                        def set_frame():
                            try:
                                # Sprawdź czy użytkownik nadal jest zalogowany
                                if not getattr(self.controller, 'is_logged_in', lambda: False)():
                                    return
                                frame_photo = ImageTk.PhotoImage(frame_img)
                                # Zapisz w kontrolerze
                                self.controller._cached_frame_photo = frame_photo
                                self.avatar_canvas.create_image(26, 26, image=frame_photo, tags='frame')
                            except Exception:
                                pass
                        self.avatar_canvas.after(0, set_frame)
            except Exception as e:
                print(f"Błąd ładowania avatara: {e}", file=sys.stderr)
        
        threading.Thread(target=load, daemon=True).start()

    def _toggle_dropdown_menu(self, event=None):
        """Pokazuje/ukrywa menu dropdown użytkownika."""
        if self.dropdown_visible:
            self._hide_dropdown()
        else:
            self._show_dropdown()
        return "break"  # Zatrzymaj propagację eventu

    def _show_dropdown(self):
        """Wyświetla menu dropdown."""
        if self.dropdown_menu:
            self._hide_dropdown()
            return
        
        # Utwórz menu jako Toplevel
        self.dropdown_menu = tk.Toplevel(self.controller.root)
        self.dropdown_menu.overrideredirect(True)
        self.dropdown_menu.configure(bg='#2a2a2a')
        self.dropdown_menu.attributes('-topmost', True)

        # Pozycja menu - pod strzałką
        try:
            x = self.dropdown_arrow.winfo_rootx() - 80
            y = self.dropdown_arrow.winfo_rooty() + self.dropdown_arrow.winfo_height() + 5
        except Exception:
            x, y = 100, 100

        # Ramka menu
        menu_frame = tk.Frame(self.dropdown_menu, bg='#2a2a2a', highlightbackground='#5588cc', highlightthickness=1)
        menu_frame.pack(fill='both', expand=True)

        # Opcja: Wyloguj
        logout_btn = tk.Label(
            menu_frame, text="🚪 Wyloguj",
            bg='#2a2a2a', fg='#ffffff', font=('Segoe UI', 10),
            padx=16, pady=8, cursor='hand2', anchor='w'
        )
        logout_btn.pack(fill='x')
        logout_btn.bind('<Enter>', lambda e: logout_btn.config(bg='#3a3a3a'))
        logout_btn.bind('<Leave>', lambda e: logout_btn.config(bg='#2a2a2a'))
        logout_btn.bind('<Button-1>', lambda e: self._on_logout_click())

        self.dropdown_menu.geometry(f"+{x}+{y}")
        self.dropdown_visible = True

        # Zamknij menu po kliknięciu poza nim (po krótkim opóźnieniu aby uniknąć natychmiastowego zamknięcia)
        self._bind_id = self.controller.root.after(100, self._bind_outside_click)

    def _bind_outside_click(self):
        """Binduje handler kliknięcia poza dropdown."""
        self._outside_click_bind_id = self.controller.root.bind('<Button-1>', self._on_click_outside_dropdown, add='+')

    def _hide_dropdown(self):
        """Ukrywa menu dropdown."""
        # Usuń binding kliknięcia poza menu
        try:
            if hasattr(self, '_outside_click_bind_id') and self._outside_click_bind_id:
                self.controller.root.unbind('<Button-1>', self._outside_click_bind_id)
                self._outside_click_bind_id = None
        except Exception:
            pass
        
        if self.dropdown_menu:
            try:
                self.dropdown_menu.destroy()
            except Exception:
                pass
            self.dropdown_menu = None
        self.dropdown_visible = False

    def _on_click_outside_dropdown(self, event):
        """Zamyka dropdown jeśli kliknięto poza nim."""
        if not self.dropdown_menu or not self.dropdown_visible:
            return
        try:
            # Sprawdź czy kliknięto na strzałkę (toggle) - jeśli tak, nie rób nic (toggle obsłuży)
            arrow_x = self.dropdown_arrow.winfo_rootx()
            arrow_y = self.dropdown_arrow.winfo_rooty()
            arrow_w = self.dropdown_arrow.winfo_width()
            arrow_h = self.dropdown_arrow.winfo_height()
            click_x = event.x_root
            click_y = event.y_root
            
            if arrow_x <= click_x <= arrow_x + arrow_w and arrow_y <= click_y <= arrow_y + arrow_h:
                return  # Kliknięto na strzałkę - toggle obsłuży
            
            if self.dropdown_menu.winfo_exists():
                menu_x = self.dropdown_menu.winfo_rootx()
                menu_y = self.dropdown_menu.winfo_rooty()
                menu_w = self.dropdown_menu.winfo_width()
                menu_h = self.dropdown_menu.winfo_height()
                if not (menu_x <= click_x <= menu_x + menu_w and menu_y <= click_y <= menu_y + menu_h):
                    self._hide_dropdown()
        except Exception:
            self._hide_dropdown()

    def _on_logout_click(self):
        """Obsługa wylogowania."""
        self._hide_dropdown()
        # Wyczyść dane sesji (metoda kontrolera czyści wszystko)
        self.controller.clear_auth_state()
        self.controller.switch_view('login')

    def update_user_info(self):
        """Aktualizuje informacje o użytkowniku w nagłówku."""
        is_logged = getattr(self.controller, 'is_logged_in', lambda: False)()
        steam_name = getattr(self.controller, 'steam_name', None) or 'Gość'
        self.welcome_label.config(text=f"Witaj,\n{steam_name}")
        
        # Wyczyść canvas całkowicie
        self.avatar_canvas.delete('all')
        
        if not is_logged:
            # Użytkownik wylogowany - pokaż placeholder
            self.avatar_canvas.create_rectangle(2, 2, 50, 50, outline='#5588cc', width=1, tags='default_frame')
            self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', 
                                           font=('Segoe UI', 7), justify='center', tags='placeholder')
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
            self.avatar_canvas.create_text(26, 26, text="steam\nprofile", fill='#888888', 
                                           font=('Segoe UI', 7), justify='center', tags='placeholder')
            self._load_avatar_async()

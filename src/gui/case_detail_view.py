import tkinter as tk
from tkinter import ttk
import sys
import os
from PIL import Image, ImageTk
from urllib.parse import quote
import webbrowser
from src.gui.header_bar import HeaderBar


class CaseDetailView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        # Główna ramka – ciemne tło
        self.frame = tk.Frame(master, bg='#1e1e1e')
        self.frame.grid(row=0, column=0, sticky="nsew")

        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # Nagłówek (współdzielony komponent)
        self.header_bar = HeaderBar(self.frame, self.controller, active_tab='case_detail')

        # ===================== GŁÓWNA ZAWARTOŚĆ (row 1) =====================
        self.content = tk.Frame(self.frame, bg='#1e1e1e')
        self.content.grid(row=1, column=0, sticky='nsew', padx=32, pady=24)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(1, weight=1)

        # Sekcja obrazka (lewa strona)
        self.image_panel = tk.Frame(self.content, bg='#2a2a2a', highlightthickness=1, highlightbackground='#5588cc')
        self.image_panel.grid(row=0, column=0, sticky='n', padx=(0, 24))
        
        self.image_label = tk.Label(self.image_panel, text='(Brak obrazka)', bg='#2a2a2a', fg='#888888')
        self.image_label.pack(padx=16, pady=16)
        self._current_photo = None

        # Sekcja informacji i akcji (prawa strona)
        info_panel = tk.Frame(self.content, bg='#1e1e1e')
        info_panel.grid(row=0, column=1, sticky='nsew')

        # Tytuł skrzyni
        self.title_label = tk.Label(info_panel, text="Szczegóły skrzyni", bg='#1e1e1e', fg='#ffffff',
                                     font=('Segoe UI', 18, 'bold'), anchor='w')
        self.title_label.pack(anchor='w', pady=(0, 16))

        # Informacje
        info_grid = tk.Frame(info_panel, bg='#1e1e1e')
        info_grid.pack(anchor='w', fill='x')

        tk.Label(info_grid, text="Nazwa:", bg='#1e1e1e', fg='#88bbff', font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky='w')
        self.name_value = tk.Label(info_grid, text="-", bg='#1e1e1e', fg='#ffffff', font=('Segoe UI', 11))
        self.name_value.grid(row=0, column=1, sticky='w', padx=(12, 0))

        tk.Label(info_grid, text="Plik:", bg='#1e1e1e', fg='#88bbff', font=('Segoe UI', 11, 'bold')).grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.path_value = tk.Label(info_grid, text="-", bg='#1e1e1e', fg='#888888', font=('Segoe UI', 10))
        self.path_value.grid(row=1, column=1, sticky='w', padx=(12, 0), pady=(8, 0))

        # Przyciski akcji
        actions = tk.Frame(info_panel, bg='#1e1e1e')
        actions.pack(anchor='w', pady=(24, 0))

        self._create_action_button(actions, "📂 Otwórz plik", self._open_file).pack(side='left')
        self._create_action_button(actions, "📁 Pokaż w folderze", self._reveal_in_folder).pack(side='left', padx=(12, 0))
        self._create_action_button(actions, "🔍 Szukaj na Steam", self._open_steam_search).pack(side='left', padx=(12, 0))

        # Przycisk powrotu
        back_frame = tk.Frame(info_panel, bg='#1e1e1e')
        back_frame.pack(anchor='w', pady=(32, 0))
        self._create_action_button(back_frame, "← Wróć do skrzyń", lambda: self.controller.switch_view('cases'), 
                                   bg='#5588cc', fg='#ffffff').pack()

        self.current_case = None

    def _create_action_button(self, parent, text, command, bg='#3a3a3a', fg='#ffffff'):
        """Tworzy stylowany przycisk akcji."""
        btn = tk.Label(parent, text=text, bg=bg, fg=fg, font=('Segoe UI', 10),
                       padx=16, pady=8, cursor='hand2')
        btn.bind('<Button-1>', lambda e: command())
        btn.bind('<Enter>', lambda e: btn.config(bg='#4a4a4a' if bg == '#3a3a3a' else '#6699dd'))
        btn.bind('<Leave>', lambda e: btn.config(bg=bg))
        return btn

    def show_case(self, case: dict):
        """Aktualizuje widok dla wybranej skrzyni."""
        self.current_case = case or {}
        name = case.get('name') or 'Skrzynia'
        self.title_label.config(text=name)
        self.name_value.config(text=name)
        
        # Pokaż ścieżkę cache
        cache_path = case.get('cache_path') or '-'
        # Skróć ścieżkę dla lepszego wyświetlania
        if len(cache_path) > 60:
            cache_path = '...' + cache_path[-57:]
        self.path_value.config(text=cache_path)
        
        # Załaduj obrazek z cache (jeśli dostępny)
        if case.get('cache_path') and os.path.exists(case['cache_path']):
            self._load_image_async(case['cache_path'])
        else:
            try:
                self.image_label.config(image='', text='(Brak w cache)', fg='#888888')
                self._current_photo = None
            except Exception:
                pass

    # -------------------------
    # AKCJE
    # -------------------------
    def _open_file(self):
        try:
            p = (self.current_case or {}).get('cache_path')
            if p and os.path.exists(p):
                os.startfile(p)
        except Exception as e:
            print(f"Nie udało się otworzyć pliku: {e}", file=sys.stderr)

    def _reveal_in_folder(self):
        try:
            p = (self.current_case or {}).get('cache_path')
            if p and os.path.exists(p):
                folder = os.path.dirname(p)
                os.startfile(folder)
        except Exception as e:
            print(f"Nie udało się otworzyć folderu: {e}", file=sys.stderr)

    def _open_steam_search(self):
        try:
            name = (self.current_case or {}).get('name') or ''
            if name:
                url = f"https://steamcommunity.com/market/search?appid=730&q={quote(name)}"
                webbrowser.open(url)
        except Exception as e:
            print(f"Nie udało się otworzyć przeglądarki: {e}", file=sys.stderr)

    # -------------------------
    # ŁADOWANIE OBRAZKA
    # -------------------------
    def _load_image_async(self, image_path: str):
        import threading
        def worker():
            try:
                img = Image.open(image_path)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                
                # Skaluj do sensownej wysokości
                max_h = 280
                w, h = img.size
                if h > max_h:
                    new_w = int(w * (max_h / float(h)))
                    img = img.resize((new_w, max_h), Image.Resampling.LANCZOS)
                
                def apply(pil_img):
                    try:
                        photo = ImageTk.PhotoImage(pil_img)
                        self.image_label.config(image=photo, text='')
                        self._current_photo = photo
                    except Exception as e:
                        print(f"Błąd PhotoImage w CaseDetail: {e}", file=sys.stderr)
                        self.image_label.config(image='', text='(Błąd obrazka)', fg='#888888')
                self.frame.after(0, lambda im=img: apply(im))
            except Exception as e:
                print(f"Błąd ładowania obrazka skrzyni: {e}", file=sys.stderr)
                self.frame.after(0, lambda: self.image_label.config(image='', text='(Błąd obrazka)', fg='#888888'))
        threading.Thread(target=worker, daemon=True).start()

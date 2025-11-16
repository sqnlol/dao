import tkinter as tk
from tkinter import ttk
import sys
import os
from PIL import Image, ImageTk
from urllib.parse import quote
import webbrowser

class CaseDetailView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew")

        self.frame.grid_rowconfigure(2, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # Header
        header = ttk.Frame(self.frame)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ttk.Label(header, text="Szczegóły skrzyni", font=("Arial", 16, "bold"))
        self.title_label.pack(side='left')

        self.back_btn = ttk.Button(header, text="← Wróć", command=lambda: self.controller.switch_view('cases'))
        self.back_btn.pack(side='right')

        ttk.Separator(self.frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=5)

        # Content
        self.content = ttk.Frame(self.frame)
        self.content.grid(row=2, column=0, sticky='nsew')
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # Główna siatka: obraz po lewej, dane + akcje po prawej
        body = ttk.Frame(self.content)
        body.grid(row=0, column=0, sticky='nsew')
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)

        # Sekcja obrazka
        self.image_panel = ttk.Frame(body)
        self.image_panel.grid(row=0, column=0, sticky='n', padx=(0, 16))
        self.image_label = ttk.Label(self.image_panel, text='(Brak obrazka)')
        self.image_label.pack()
        self._current_photo = None

        # Sekcja informacji i akcji
        info_panel = ttk.Frame(body)
        info_panel.grid(row=0, column=1, sticky='nsew')
        info_panel.grid_columnconfigure(1, weight=1)

        ttk.Label(info_panel, text="Nazwa:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky='w')
        self.name_value = ttk.Label(info_panel, text="-")
        self.name_value.grid(row=0, column=1, sticky='w', padx=(6,0))

        ttk.Label(info_panel, text="Plik:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky='w', pady=(6,0))
        self.path_value = ttk.Label(info_panel, text="-", foreground='gray')
        self.path_value.grid(row=1, column=1, sticky='w', padx=(6,0), pady=(6,0))

        # Przyciski akcji
        actions = ttk.Frame(info_panel)
        actions.grid(row=2, column=0, columnspan=2, sticky='w', pady=(10,0))
        ttk.Button(actions, text="Otwórz plik", command=self._open_file).pack(side='left')
        ttk.Button(actions, text="Pokaż w folderze", command=self._reveal_in_folder).pack(side='left', padx=(8,0))
        ttk.Button(actions, text="Szukaj na Steam", command=self._open_steam_search).pack(side='left', padx=(8,0))

        self.current_case = None

    def show_case(self, case: dict):
        """Aktualizuje widok dla wybranej skrzyni."""
        self.current_case = case or {}
        name = case.get('name') or case.get('path') or 'Skrzynia'
        self.title_label.config(text=f"Skrzynia: {name}")
        self.name_value.config(text=name)
        self.path_value.config(text=case.get('path') or '-')
        # Załaduj obrazek (jeśli dostępny)
        img_path = case.get('path')
        if img_path and os.path.exists(img_path):
            self._load_image_async(img_path)
        else:
            try:
                self.image_label.config(image='', text='(Brak obrazka)')
                self._current_photo = None
            except Exception:
                pass

    # -------------------------
    # AKCJE
    # -------------------------
    def _open_file(self):
        try:
            p = (self.current_case or {}).get('path')
            if p and os.path.exists(p):
                os.startfile(p)
        except Exception as e:
            print(f"Nie udało się otworzyć pliku: {e}", file=sys.stderr)

    def _reveal_in_folder(self):
        try:
            p = (self.current_case or {}).get('path')
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
                if img.mode == "RGBA":
                    try:
                        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                        img = Image.alpha_composite(bg, img).convert("RGB")
                    except Exception:
                        img = img.convert("RGB")
                # Skaluj do sensownej wysokości
                max_h = 240
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
                        self.image_label.config(image='', text='(Błąd obrazka)')
                self.frame.after(0, lambda im=img: apply(im))
            except Exception as e:
                print(f"Błąd ładowania obrazka skrzyni: {e}", file=sys.stderr)
                self.frame.after(0, lambda: self.image_label.config(image='', text='(Błąd obrazka)'))
        threading.Thread(target=worker, daemon=True).start()

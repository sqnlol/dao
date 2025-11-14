import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import sys
import os
from PIL import Image, ImageTk
from collections import OrderedDict
import requests
from io import BytesIO
from steam_market import get_item_image_url


class CasesView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew") 
        
        self.frame.grid_rowconfigure(2, weight=1) 
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Cache obrazków
        self._image_cache = OrderedDict()
        self._max_cache_size = 50
        
        # Dane skrzyń CS2
        self.cases_data = self._get_cases_data()

        self._create_widgets()
        
    def _derive_name_from_path(self, path: str) -> str:
        try:
            from urllib.parse import unquote
            base = os.path.basename(path)
            name, _ = os.path.splitext(base)
            name = unquote(name)
            name = name.replace('_', ' ').strip()
            return name
        except Exception:
            return os.path.basename(path)

    def _get_cases_data(self):
        """Wczytuje listę obrazów skrzyń z lokalnego folderu src/img/cases.

        Preferuje .png nad .webp oraz jpg. Deduplikuje po nazwie bazowej pliku.
        Zwraca listę słowników: {"path": absolute_path, "name": friendly_name}.
        """
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "img", "cases"))
            if not os.path.isdir(base_dir):
                print(f"Brak folderu z obrazami skrzyń: {base_dir}", file=sys.stderr)
                return []

            preferred = {".png": 3, ".webp": 2, ".jpg": 1, ".jpeg": 1}
            choose = {}
            exclude = {"chroma_new", "chroma", "skrzynia_chroma_test", "test_resized"}

            for name in os.listdir(base_dir):
                lower = name.lower()
                stem, ext = os.path.splitext(lower)
                if ext not in (".png", ".webp", ".jpg", ".jpeg"):
                    continue
                if stem in exclude:
                    continue
                cur = choose.get(stem)
                if cur is None or preferred.get(ext, 0) > preferred.get(os.path.splitext(cur)[1], 0):
                    choose[stem] = name

            data = []
            for stem in sorted(choose.keys()):
                filename = choose[stem]
                full = os.path.join(base_dir, filename)
                data.append({"path": full, "name": self._derive_name_from_path(full)})

            if not data:
                print("Nie znaleziono obrazów skrzyń w src/img/cases", file=sys.stderr)
            return data
        except Exception as e:
            print(f"Błąd skanowania folderu skrzyń: {e}", file=sys.stderr)
            return []
    
    def _create_widgets(self):
        # Nagłówek
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1) 

        ttk.Label(header_frame, text="Skrzynie CS2", font=("Arial", 16, "bold")).pack(side='left')
        
        # Pasek informacyjny
        info_label = ttk.Label(header_frame, text="Przeglądaj dostępne skrzynie", foreground='gray')
        info_label.pack(side='right', padx=10)

        # Separator
        ttk.Separator(self.frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=5)

        # Główna zawartość - przewijany canvas z siatką skrzyń
        main_container = ttk.Frame(self.frame)
        main_container.grid(row=2, column=0, sticky='nsew')
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Canvas ze scrollbarem
        self.canvas = tk.Canvas(main_container, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Włącz przewijanie kółkiem myszy
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Stwórz siatkę kafelków ze skrzyniami
        self._create_cases_grid()

    def _on_mousewheel(self, event):
        """Obsługa przewijania kółkiem myszy."""
        try:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except Exception:
            pass

    def _create_cases_grid(self):
        """Tworzy siatkę z kafelkami skrzyń (obrazy z lokalnego folderu)."""
        columns = 4  # 4 skrzynie w rzędzie
        
        for idx, case in enumerate(self.cases_data):
            row = idx // columns
            col = idx % columns
            
            # Biały kafelek z lekkim obramowaniem
            tile = tk.Frame(self.scrollable_frame, bg='#ffffff', highlightthickness=1, highlightbackground='#dddddd')
            tile.grid(row=row, column=col, padx=10, pady=10, sticky='n')

            # Obrazek na białym tle
            img_label = tk.Label(tile, bg='#ffffff')
            img_label.pack(padx=12, pady=(12, 6))

            # Podpis z nazwą skrzyni
            name_text = case.get('name') or 'Skrzynia'
            name_label = tk.Label(tile, text=name_text, bg='#ffffff', fg='#333333', font=("Arial", 10))
            name_label.configure(wraplength=160, justify='center')
            name_label.pack(padx=8, pady=(0, 12))

            # Kliknięcie w kafelek lub elementy w środku przechodzi do szczegółów
            tile.bind("<Button-1>", lambda e, c=case: self._on_case_click(c))
            img_label.bind("<Button-1>", lambda e, c=case: self._on_case_click(c))
            name_label.bind("<Button-1>", lambda e, c=case: self._on_case_click(c))

            # Załaduj obrazek z dysku
            self._load_case_image_local(case['path'], img_label)

    def _load_case_image_local(self, image_path, label):
        """Ładuje obraz lokalnie i skaluje proporcjonalnie do maksymalnej wysokości."""
        import threading

        def load_and_set():
            try:
                img = Image.open(image_path)
                # Jeśli obraz ma kanał alfa, wypełnij tło na biało dla spójnego wyglądu
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                if img.mode == "RGBA":
                    try:
                        white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                        img = Image.alpha_composite(white_bg, img).convert("RGB")
                    except Exception:
                        img = img.convert("RGB")

                max_h = 180
                w, h = img.size
                if h > max_h:
                    new_w = int(w * (max_h / float(h)))
                    img = img.resize((new_w, max_h), Image.Resampling.LANCZOS)

                def apply():
                    try:
                        photo = ImageTk.PhotoImage(img)
                        label.config(image=photo, text='')
                        label.image = photo
                    except Exception as e:
                        print(f"Błąd PhotoImage (local): {e}", file=sys.stderr)
                        label.config(text="Błąd")

                label.after(0, apply)
            except Exception as e:
                print(f"Błąd ładowania pliku {image_path}: {e}", file=sys.stderr)
                label.after(0, lambda: label.config(text="Błąd"))

        threading.Thread(target=load_and_set, daemon=True).start()

    def _load_case_image(self, market_name, label):
        """Ładuje obrazek skrzyni przez Steam Market API."""
        import threading
        
        def download_and_set():
            try:
                # Pobierz URL obrazka z Steam Market
                login_cookie = getattr(self.controller, 'login_cookie', None)
                image_url = get_item_image_url(market_name, login_cookie, currency_code=6, timeout=10)
                
                if not image_url:
                    label.after(0, lambda: label.config(text="Brak URL"))
                    return
                
                # Pobierz obrazek
                resp = requests.get(image_url, timeout=10)
                if resp.status_code == 200 and resp.content:
                    img = Image.open(BytesIO(resp.content))
                    # Skaluj zachowując proporcje (jak w results_view)
                    max_h = 180
                    w, h = img.size
                    if h > max_h:
                        new_w = int(w * (max_h / float(h)))
                        img = img.resize((new_w, max_h), Image.Resampling.LANCZOS)
                    
                    def apply():
                        try:
                            photo = ImageTk.PhotoImage(img)
                            label.config(image=photo, text='')
                            label.image = photo
                        except Exception as e:
                            print(f"Błąd PhotoImage: {e}", file=sys.stderr)
                    
                    label.after(0, apply)
                else:
                    label.after(0, lambda: label.config(text=f"HTTP {resp.status_code}"))
            except Exception as e:
                print(f"Błąd pobierania {market_name}: {e}", file=sys.stderr)
                label.after(0, lambda: label.config(text="Błąd"))
        
        threading.Thread(target=download_and_set, daemon=True).start()

    def _set_image(self, label, photo):
        """Ustawia obrazek w label (musi być wywołane w głównym wątku)."""
        try:
            label.config(image=photo, text='')
            label.image = photo  # Zachowaj referencję
        except Exception:
            pass

    def _on_case_click(self, case):
        """Obsługuje kliknięcie na skrzynię."""
        try:
            # Przełącz do widoku szczegółów skrzyni (na razie pusty)
            self.controller.switch_view('case_detail', case=case)
        except Exception as e:
            print(f"Nie udało się przejść do widoku skrzyni: {e}", file=sys.stderr)

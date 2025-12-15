import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import sys
import os
from PIL import Image, ImageTk
from collections import OrderedDict
import requests
from io import BytesIO
from src import steam_market
from src.case_images_cache import get_all_cases_list, download_all_cases_async, is_cached
from src.gui.header_bar import HeaderBar


class CasesView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        # Główna ramka – ciemne tło
        self.frame = tk.Frame(master, bg='#1e1e1e')
        self.frame.grid(row=0, column=0, sticky="nsew") 
        
        self.frame.grid_rowconfigure(1, weight=1)  # główna zawartość rozciągalna
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Cache obrazków
        self._image_cache = OrderedDict()
        self._max_cache_size = 50
        
        # Dane skrzyń CS2 - teraz z cache
        self.cases_data = get_all_cases_list()
        
        # Sprawdź czy wszystkie obrazki są w cache
        self._check_and_download_missing_images()

        self._create_widgets()
        
    def _check_and_download_missing_images(self):
        """Sprawdza czy wszystkie obrazki są w cache i pobiera brakujące."""
        missing = [case for case in self.cases_data if not case["cached"]]
        
        if missing:
            print(f"Brakuje {len(missing)} obrazków w cache. Rozpoczynam pobieranie...")
            
            # Pobierz cookie z controllera jeśli dostępne
            login_cookie = getattr(self.controller, 'login_cookie', None)
            
            def progress(current, total, case_name, success):
                status = "✓" if success else "✗"
                print(f"[{current}/{total}] {status} {case_name}")
            
            def completion(results):
                print(f"\nPobieranie zakończone: {results['success']}/{results['total']} sukcesów")
                # Odśwież listę skrzyń
                self.cases_data = get_all_cases_list()
                # Odśwież widok jeśli okno jest wciąż aktywne
                try:
                    self.frame.after(0, self._refresh_cases_grid)
                except Exception:
                    pass
            
            # Uruchom pobieranie w tle
            download_all_cases_async(
                login_cookie=login_cookie,
                delay=1.5,
                progress_callback=progress,
                completion_callback=completion
            )
    
    def _refresh_cases_grid(self):
        """Odświeża siatkę skrzyń (usuwa starą i tworzy nową)."""
        try:
            # Usuń wszystkie widgety z scrollable_frame
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            # Stwórz siatkę na nowo
            self._create_cases_grid()
        except Exception as e:
            print(f"Błąd odświeżania siatki: {e}", file=sys.stderr)

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

    def _create_widgets(self):
        # ===================== NAGŁÓWEK (współdzielony komponent) =====================
        self.header_bar = HeaderBar(self.frame, self.controller, active_tab='cases')

        # ===================== GŁÓWNA ZAWARTOŚĆ (row 1) =====================
        main_container = tk.Frame(self.frame, bg='#1e1e1e')
        main_container.grid(row=1, column=0, sticky='nsew', padx=16, pady=16)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Canvas ze scrollbarem
        self.canvas = tk.Canvas(main_container, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#1e1e1e')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self._update_scroll_region()
        )
        
        # Wyśrodkuj zawartość w canvas
        self._canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind do zmiany rozmiaru canvas, aby centrować zawartość
        self.canvas.bind('<Configure>', self._center_scrollable_frame)
        
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Włącz przewijanie kółkiem myszy
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Stwórz siatkę kafelków ze skrzyniami
        self._create_cases_grid()

    def _update_scroll_region(self):
        """Aktualizuje region przewijania canvas."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _center_scrollable_frame(self, event=None):
        """Centruje zawartość siatki w canvas."""
        try:
            canvas_width = self.canvas.winfo_width()
            frame_width = self.scrollable_frame.winfo_reqwidth()
            
            # Jeśli zawartość jest węższa niż canvas, wycentruj ją
            if frame_width < canvas_width:
                x_offset = (canvas_width - frame_width) // 2
            else:
                x_offset = 0
            
            self.canvas.coords(self._canvas_window, x_offset, 0)
            self._update_scroll_region()
        except Exception:
            pass

    def _on_mousewheel(self, event):
        """Obsługa przewijania kółkiem myszy."""
        try:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except Exception:
            pass

    def _create_cases_grid(self):
        """Tworzy siatkę z kafelkami skrzyń (obrazy z cache)."""
        columns = 6  # 6 skrzyń na szerokim układzie 1600 px
        try:
            current_width = max(self.controller.root.winfo_width(), 0)
            if current_width and current_width < 1200:
                columns = 4
            elif current_width and current_width < 1400:
                columns = 5
        except Exception:
            columns = 6
        
        for idx, case in enumerate(self.cases_data):
            row = idx // columns
            col = idx % columns
            
            # Ciemny kafelek z niebieskim obramowaniem
            tile = tk.Frame(self.scrollable_frame, bg='#2a2a2a', highlightthickness=1, highlightbackground='#5588cc')
            tile.grid(row=row, column=col, padx=10, pady=10, sticky='n')

            # Obrazek na ciemnym tle
            img_label = tk.Label(tile, bg='#2a2a2a')
            img_label.pack(padx=12, pady=(12, 6))

            # Podpis z nazwą skrzyni
            name_text = case.get('name') or 'Skrzynia'
            name_label = tk.Label(tile, text=name_text, bg='#2a2a2a', fg='#ffffff', font=("Segoe UI", 10))
            name_label.configure(wraplength=160, justify='center')
            name_label.pack(padx=8, pady=(0, 12))

            # Kliknięcie w kafelek lub elementy w środku przechodzi do szczegółów
            tile.bind("<Button-1>", lambda e, c=case: self._on_case_click(c))
            img_label.bind("<Button-1>", lambda e, c=case: self._on_case_click(c))
            name_label.bind("<Button-1>", lambda e, c=case: self._on_case_click(c))

            # Załaduj obrazek z cache
            if case.get('cache_path'):
                self._load_case_image_from_cache(case['cache_path'], img_label)
            else:
                # Jeśli nie ma w cache, pokaż placeholder
                img_label.config(text="Pobieranie...", font=("Segoe UI", 9), fg='#888888')

    def _load_case_image_from_cache(self, cache_path, label):
        """Ładuje obraz z cache i skaluje proporcjonalnie do maksymalnej wysokości."""
        import threading

        def load_and_set():
            try:
                img = Image.open(cache_path)
                # Zachowaj przezroczystość dla ciemnego tła
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")

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
                        print(f"Błąd PhotoImage (cache): {e}", file=sys.stderr)
                        label.config(text="Błąd", fg='#888888')

                label.after(0, apply)
            except Exception as e:
                print(f"Błąd ładowania z cache {cache_path}: {e}", file=sys.stderr)
                label.after(0, lambda: label.config(text="Błąd", fg='#888888'))

        threading.Thread(target=load_and_set, daemon=True).start()

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

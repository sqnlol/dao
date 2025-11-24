import os
import tkinter as tk
from tkinter import ttk
import threading
import time
import sys


class RoundedButton(tk.Frame):
    """Simple canvas-based button with rounded corners and hover states."""

    def __init__(
        self,
        master,
        text,
        command,
        bg_color,
        hover_color=None,
        active_color=None,
        text_color='#DBDBDB',
        height=52,
        radius=12,
        font=("Arial", 16, "bold"),
        icon_image=None,
        icon_size=(24, 24),
        icon_gap=8,
    ):
        super().__init__(master, bg=master.cget('bg'))
        self.command = command
        self.text = text
        self.bg_color = bg_color
        self.hover_color = hover_color or self._shade_color(bg_color, 1.08)
        self.active_color = active_color or self._shade_color(bg_color, 0.92)
        self.text_color = text_color
        self.height = height
        self.radius = radius
        self.font = font
        self.icon_image = icon_image
        self.icon_size = icon_size
        self.icon_gap = icon_gap
        self._current_color = self.bg_color
        self._hover = False

        self.canvas = tk.Canvas(self, bg=self['bg'], highlightthickness=0, bd=0, height=self.height)
        self.canvas.pack(fill='x', expand=True)
        self.canvas.configure(cursor="hand2")
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _shade_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw(self):
        self.canvas.delete('all')
        width = max(self.canvas.winfo_width(), 40)
        height = self.height
        radius = min(self.radius, height // 2, width // 2)
        fill = self._current_color
        self.canvas.create_rectangle(radius, 0, width - radius, height, fill=fill, outline=fill)
        self.canvas.create_rectangle(0, radius, width, height - radius, fill=fill, outline=fill)
        self.canvas.create_oval(0, 0, radius * 2, radius * 2, fill=fill, outline=fill)
        self.canvas.create_oval(width - radius * 2, 0, width, radius * 2, fill=fill, outline=fill)
        self.canvas.create_oval(0, height - radius * 2, radius * 2, height, fill=fill, outline=fill)
        self.canvas.create_oval(width - radius * 2, height - radius * 2, width, height, fill=fill, outline=fill)
        text_x = width / 2
        if self.icon_image:
            icon_w, _ = self.icon_size
            try:
                icon_w = int(self.icon_image.width())
            except Exception:
                pass
            text_id = self.canvas.create_text(0, 0, text=self.text, font=self.font, anchor='w')
            bbox = self.canvas.bbox(text_id) or (0, 0, 0, 0)
            self.canvas.delete(text_id)
            text_width = bbox[2] - bbox[0]
            total_width = icon_w + self.icon_gap + text_width
            start_x = (width - total_width) / 2
            self.canvas.create_image(start_x + icon_w / 2, height / 2, image=self.icon_image)
            text_x = start_x + icon_w + self.icon_gap
            self.canvas.create_text(text_x, height / 2, text=self.text, fill=self.text_color, font=self.font, anchor='w')
        else:
            self.canvas.create_text(text_x, height / 2, text=self.text, fill=self.text_color, font=self.font, anchor='center')

    def _on_enter(self, _event):
        self._hover = True
        self._current_color = self.hover_color
        self._draw()

    def _on_leave(self, _event):
        self._hover = False
        self._current_color = self.bg_color
        self._draw()

    def _on_press(self, _event):
        self._current_color = self.active_color
        self._draw()

    def _on_release(self, event):
        self._current_color = self.hover_color if self._hover else self.bg_color
        self._draw()
        if self.command and self._pointer_inside(event):
            self.command()

    def _pointer_inside(self, event):
        width = self.canvas.winfo_width()
        height = self.height
        return 0 <= event.x <= width and 0 <= event.y <= height


class LoginView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        self._bg_color = '#1F1F20'
        self._card_bg = '#0F111A'
        self._accent = '#78A3D7'
        self._button_dark = '#2B2B2B'
        self._button_green = '#71A031'
        self._assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img')

        self._steam_icon_image = None

        self.frame = tk.Frame(master, bg=self._bg_color)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        self._build_styles()
        self._create_widgets()

    def _load_icon(self, filename, size=None):
        try:
            from PIL import Image, ImageTk
        except ImportError:
            print("Brak Pillow - pomijam ikonę", file=sys.stderr)
            return None

        path = os.path.join(self._assets_dir, filename)
        if not os.path.exists(path):
            return None

        try:
            with Image.open(path) as img:
                img = img.convert("RGBA")
                if size:
                    resample = getattr(Image, 'LANCZOS', getattr(Image, 'BICUBIC', Image.NEAREST))
                    img = img.resize(size, resample)
                return ImageTk.PhotoImage(img)
        except Exception as exc:
            print(f"Nie udało się załadować {filename}: {exc}", file=sys.stderr)
            return None

    def _create_widgets(self):
        container = tk.Frame(self.frame, bg=self._bg_color)
        container.grid(row=0, column=0, sticky='nsew')
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Use the newly provided Steam logo asset, scaled down to fit the button nicely.
        self._steam_icon_image = self._load_icon('steamlogo.png', (26, 18))

        logo_frame = tk.Frame(container, bg=self._bg_color)
        logo_frame.grid(row=0, column=0, sticky='n', pady=(60, 30))
        try:
            from PIL import Image, ImageTk
            logo_path = os.path.join(self._assets_dir, 'CS2SkinAnalyzer.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                ratio = img.width / img.height if img.height else 1
                target_h = 120
                target_w = int(target_h * ratio)
                img_big = img.resize((target_w, target_h))
                self._login_logo_img = ImageTk.PhotoImage(img_big)
                tk.Label(logo_frame, image=self._login_logo_img, bg=self._bg_color).pack()
        except Exception as e:
            print(f"Logo niezaładowane: {e}", file=sys.stderr)

        card_wrapper = tk.Frame(container, bg=self._bg_color)
        card_wrapper.grid(row=1, column=0, sticky='n')

        card_border = tk.Frame(
            card_wrapper,
            bg=self._card_bg,
            highlightbackground=self._accent,
            highlightcolor=self._accent,
            highlightthickness=2,
            bd=0,
            relief='flat'
        )
        card_border.pack()
        card_border.configure(width=560, height=300)
        card_border.pack_propagate(False)

        card = tk.Frame(card_border, bg=self._card_bg, padx=48, pady=32)
        card.pack(fill='both', expand=True)

        title_row = tk.Frame(card, bg=self._card_bg)
        title_row.pack(fill='x', pady=(0, 24))
        tk.Label(title_row, text="Logowanie", font=("Arial", 18, "bold"), fg='#DBDBDB', bg=self._card_bg).pack(side='left')
        tk.Frame(title_row, bg=self._accent, height=2).pack(side='left', fill='x', expand=True, padx=(12, 0), pady=(14, 0))

        self.remember_me_var = tk.BooleanVar(value=False)

        self.guest_button = RoundedButton(
            card,
            text="Wejdź jako Gość",
            command=self.connect_guest,
            bg_color=self._button_dark,
            hover_color='#3A3A3A',
            active_color='#242424',
            radius=12,
            text_color='#DBDBDB'
        )
        self.guest_button.pack(fill='x', pady=(0, 14))

        self.browser_login_button = RoundedButton(
            card,
            text="Zaloguj przez Steam",
            command=self.start_steam_login_flow,
            bg_color=self._button_green,
            hover_color='#7FB636',
            active_color='#5C8727',
            radius=12,
            text_color='#DBDBDB',
            icon_image=self._steam_icon_image,
            icon_size=(26, 18),
            icon_gap=10
        )
        self.browser_login_button.pack(fill='x', pady=(0, 18))

        remember_frame = tk.Frame(card, bg=self._card_bg)
        remember_frame.pack(fill='x')
        self.remember_me_cb = ttk.Checkbutton(
            remember_frame,
            text="Zapamiętaj mnie",
            variable=self.remember_me_var,
            style='Login.TCheckbutton'
        )
        self.remember_me_cb.pack(side='left')

        self.login_status = tk.Label(card, text="", fg='#DBDBDB', bg=self._card_bg, wraplength=420, justify='left')
        self.login_status.pack(fill='x', pady=(18, 0))

        self.manual_toggle = ttk.Button(
            container,
            text="Mam cookie steamLoginSecure",
            style='Link.TButton',
            command=self._toggle_manual_section
        )
        self.manual_toggle.grid(row=2, column=0, pady=(24, 6))

        self.manual_section = tk.Frame(container, bg=self._bg_color)
        self.manual_section.grid(row=3, column=0, pady=(0, 40))
        self.manual_section.grid_remove()

        manual_card = tk.Frame(
            self.manual_section,
            bg=self._card_bg,
            padx=32,
            pady=24,
            highlightbackground='#1E2130',
            highlightthickness=1
        )
        manual_card.pack()
        tk.Label(manual_card, text="Wklej wartość 'steamLoginSecure':", bg=self._card_bg, fg='#DBDBDB').grid(row=0, column=0, sticky='w')
        self.cookie_entry = ttk.Entry(manual_card, width=64)
        self.cookie_entry.grid(row=1, column=0, sticky='ew', pady=(6, 12))
        manual_card.grid_columnconfigure(0, weight=1)
        self.connect_button = ttk.Button(manual_card, text="Zapisz cookie i kontynuuj", command=self.connect_with_cookie)
        self.connect_button.grid(row=2, column=0, sticky='ew')

    def connect_with_cookie(self):
        """Sprawdza cookie, zapisuje je w kontrolerze i przełącza do widoku wyszukiwania."""
        cookie_value = self.cookie_entry.get().strip()

        if not cookie_value:
            # Tryb ograniczony bez cookie
            self.controller.login_cookie = None
            self.controller.steam_name = "Gość"  # zmiana nazwy wyświetlanej
            self.controller.switch_view("search")
            return

        if len(cookie_value) < 10:
            self.login_status.config(text="Cookie zbyt krótkie – pozostajesz w trybie ograniczonym.", foreground='orange')
            self.controller.login_cookie = None
            self.controller.steam_name = "Gość"
            self.controller.switch_view("search")
            return

        # Pełny tryb z cookie
        self.controller.login_cookie = cookie_value
        self.controller.steam_name = "Użytkowniku Steam"
        # Persistuj sesję jeśli zaznaczono "Zapamiętaj mnie"
        try:
            if self.remember_me_var.get() and hasattr(self.controller, 'persist_auth_state'):
                self.controller.persist_auth_state()
        except Exception:
            pass
        self.controller.switch_view("search")

    def connect_guest(self):
        """Przechodzi do trybu gościa z komunikatem ostrzegawczym."""
        self.controller.login_cookie = None
        self.controller.steam_name = "Gość"
        try:
            self.login_status.config(text="Tryb gościa: historia cen wymaga pełnego logowania.", foreground='#9CA3C4')
        except Exception:
            pass
        self.controller.switch_view("search")

    # ----------------------
    # Automatyczne pobranie cookie przez widoczne logowanie w przeglądarce (Selenium)
    # ----------------------
    def _set_status(self, text, color='gray'):
        try:
            self.login_status.config(text=text, foreground=color)
        except Exception:
            pass

    def start_steam_login_flow(self):
        # Uruchom w wątku, by nie blokować UI
        t = threading.Thread(target=self._steam_login_worker, daemon=True)
        t.start()

    def _steam_login_worker(self):
        self._async_ui(lambda: self._set_status("Uruchamiam przeglądarkę do logowania Steam...", 'gray'))
        # Lazy import selenium i webdriver-manager
        try:
            from selenium import webdriver
            import subprocess, os
            # Edge preferowany na Windows; fallback na Chrome
            driver = None
            last_error = None

            # Pomocniczo: wykryj ścieżki do przeglądarek (Windows)
            def _find_browser_path(candidates, reg_names):
                try:
                    import os
                    possible = []
                    for p in candidates:
                        if os.path.exists(p):
                            possible.append(p)
                    try:
                        import winreg
                        for reg_name in reg_names:
                            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                                try:
                                    with winreg.OpenKey(root, fr"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{reg_name}") as k:
                                        try:
                                            v, _ = winreg.QueryValueEx(k, None)
                                            if v:
                                                possible.append(v)
                                        except Exception:
                                            pass
                                        try:
                                            v, _ = winreg.QueryValueEx(k, 'Path')
                                            import os
                                            if v:
                                                exe = os.path.join(v, reg_names[0])
                                                if os.path.exists(exe):
                                                    possible.append(exe)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    return next((p for p in possible if p and os.path.exists(p)), None)
                except Exception:
                    return None

            edge_candidates = [
                r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
                r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            ]
            chrome_candidates = [
                r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            ]
            edge_path = _find_browser_path(edge_candidates, ["msedge.exe"])
            chrome_path = _find_browser_path(chrome_candidates, ["chrome.exe"])

            # 1) Spróbuj Edge przez Selenium Manager (bez webdriver-manager)
            try:
                from selenium.webdriver.edge.options import Options as EdgeOptions
                from selenium.webdriver.edge.service import Service as EdgeService
                edge_options = EdgeOptions()
                edge_options.add_argument("--start-maximized")
                # Ogranicz hałaśliwe logi z Chromium (USB/devtools)
                try:
                    edge_options.add_argument("--log-level=3")
                    edge_options.add_argument("--disable-logging")
                    edge_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])  # ukryj baner automat.
                    edge_options.add_experimental_option("useAutomationExtension", False)
                except Exception:
                    pass
                if edge_path:
                    try:
                        edge_options.binary_location = edge_path
                    except Exception:
                        pass
                # Przekieruj logi drivera do /dev/null
                try:
                    service = EdgeService(log_output=subprocess.DEVNULL)
                    driver = webdriver.Edge(service=service, options=edge_options)
                except Exception:
                    driver = webdriver.Edge(options=edge_options)
            except Exception as e:
                last_error = e
                driver = None

            # 2) Jeśli Edge nie ruszył, spróbuj Edge z webdriver-manager
            if driver is None:
                try:
                    from selenium.webdriver.edge.options import Options as EdgeOptions
                    from selenium.webdriver.edge.service import Service as EdgeService
                    from webdriver_manager.microsoft import EdgeChromiumDriverManager
                    edge_options = EdgeOptions()
                    edge_options.add_argument("--start-maximized")
                    try:
                        edge_options.add_argument("--log-level=3")
                        edge_options.add_argument("--disable-logging")
                        edge_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
                        edge_options.add_experimental_option("useAutomationExtension", False)
                    except Exception:
                        pass
                    if edge_path:
                        try:
                            edge_options.binary_location = edge_path
                        except Exception:
                            pass
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    driver = webdriver.Edge(service=service, options=edge_options)
                except Exception as e2:
                    last_error = e2
                    driver = None

            # 3) Fallback: Chrome tylko jeśli faktycznie znaleziono chrome.exe
            if driver is None and chrome_path:
                try:
                    from selenium.webdriver.chrome.options import Options as ChromeOptions
                    from selenium.webdriver.chrome.service import Service as ChromeService
                    chrome_options = ChromeOptions()
                    chrome_options.add_argument("--start-maximized")
                    try:
                        chrome_options.add_argument("--log-level=3")
                        chrome_options.add_argument("--disable-logging")
                        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
                        chrome_options.add_experimental_option("useAutomationExtension", False)
                    except Exception:
                        pass
                    try:
                        chrome_options.binary_location = chrome_path
                    except Exception:
                        pass
                    service = ChromeService(log_output=subprocess.DEVNULL)
                    driver = webdriver.Chrome(options=chrome_options)
                except Exception as e3:
                    last_error = e3
                    driver = None
            if driver is None:
                hint = "Zainstaluj Microsoft Edge (zalecane) lub Google Chrome, albo wklej cookie ręcznie."
                if chrome_path is None and edge_path is None:
                    hint = hint + " Nie wykryto zainstalowanego Edge/Chrome."
                self._async_ui(lambda: self._set_status(f"Nie udało się uruchomić przeglądarki: {last_error}\n{hint}", 'red'))
                return

            try:
                # Przejdź bezpośrednio do właściwej strony logowania
                login_url = "https://steamcommunity.com/login/home/?goto=login"
                driver.get(login_url)
                self._async_ui(lambda: self._set_status("Zaloguj się w otwartej przeglądarce. Czekam na cookie...", 'gray'))
                # Poczekaj aż pojawi się ciasteczko steamLoginSecure (użytkownik może potrzebować 2FA)
                cookie_value = None
                deadline = time.time() + 420  # 7 minut na cały proces
                # Czasami cookie pojawia się po przekierowaniu do 'steamcommunity.com' – upewnij się, że jesteśmy na domenie
                while time.time() < deadline:
                    try:
                        cookies = driver.get_cookies() or []
                        for c in cookies:
                            if c.get('name') == 'steamLoginSecure' and c.get('value'):
                                cookie_value = c.get('value')
                                break
                        if cookie_value:
                            break
                    except Exception:
                        pass
                    time.sleep(1)
                if not cookie_value:
                    self._async_ui(lambda: self._set_status("Nie wykryto cookie steamLoginSecure w limicie czasu.", 'orange'))
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    return

                # Sukces — zapisz cookie
                self._async_ui(lambda: self._set_status("Zalogowano. Cookie pobrane.", 'green'))
                self.controller.login_cookie = cookie_value

                # Spróbuj pobrać nazwę użytkownika po zalogowaniu
                user_name = None
                try:
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    # 1) Profil na community
                    try:
                        driver.get("https://steamcommunity.com/my/")
                        el = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".actual_persona_name"))
                        )
                        user_name = (el.text or "").strip()
                    except Exception:
                        user_name = None
                    # 2) Fallback: strona sklepu (górny pulldown)
                    if not user_name:
                        try:
                            driver.get("https://store.steampowered.com/")
                            el = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "#account_pulldown"))
                            )
                            user_name = (el.text or "").strip()
                        except Exception:
                            user_name = None
                except Exception:
                    user_name = None

                if user_name:
                    self.controller.steam_name = user_name
                else:
                    self.controller.steam_name = "Użytkowniku Steam"
                # Zamknij przeglądarkę
                try:
                    driver.quit()
                except Exception:
                    pass
                # Persistuj sesję jeśli zaznaczono "Zapamiętaj mnie"
                try:
                    if self.remember_me_var.get() and hasattr(self.controller, 'persist_auth_state'):
                        self.controller.persist_auth_state()
                except Exception:
                    pass
                # Przejdź do widoku wyszukiwania
                self._async_ui(lambda: self.controller.switch_view("search"))
            except Exception as e:
                self._async_ui(lambda: self._set_status(f"Błąd logowania: {e}", 'red'))
                try:
                    driver.quit()
                except Exception:
                    pass
        except ImportError:
            self._async_ui(lambda: self._set_status("Brak zależności: zainstaluj pakiety 'selenium' oraz 'webdriver-manager'.", 'red'))
        except Exception as e:
            self._async_ui(lambda: self._set_status(f"Błąd nieoczekiwany: {e}", 'red'))

    def _async_ui(self, fn):
        try:
            # Harmonogramuj na wątku UI
            self.controller.root.after(0, fn)
        except Exception:
            try:
                fn()
            except Exception:
                pass

    def _toggle_manual_section(self):
        if self.manual_section.winfo_ismapped():
            self.manual_section.grid_remove()
            self.manual_toggle.config(text="Mam cookie steamLoginSecure")
        else:
            self.manual_section.grid()
            self.manual_toggle.config(text="Ukryj ręczne logowanie")

    def _build_styles(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('Login.TCheckbutton', background=self._card_bg, foreground='#DBDBDB')
        style.map(
            'Login.TCheckbutton',
            foreground=[('disabled', '#7f7f7f')],
            background=[
                ('active', self._card_bg),
                ('selected', self._card_bg),
                ('!active', self._card_bg)
            ]
        )

        style.configure('Link.TButton', font=("Arial", 11, 'underline'), padding=4, background=self._bg_color, foreground='#DBDBDB', relief='flat')
        style.map('Link.TButton', foreground=[('active', '#ffffff')], background=[('active', self._bg_color)])

import tkinter as tk
from tkinter import ttk
import threading
import time
import sys

class LoginView:
    def __init__(self, master, app_controller):
        self.controller = app_controller
        
        self.frame = ttk.Frame(master, padding="20")
        self.frame.grid(row=0, column=0, sticky="nsew") 
        
        self.frame.grid_rowconfigure(0, weight=1) 
        self.frame.grid_rowconfigure(2, weight=1) 
        self.frame.grid_rowconfigure(1, weight=0) 
        self.frame.grid_columnconfigure(0, weight=1) 

        self._create_widgets()

    def _create_widgets(self):
        
        content_frame = ttk.Frame(self.frame)
        content_frame.grid(row=1, column=0, sticky="nsew") 

        # Nagłówek z dużym logo i tytułem obok (wyśrodkowany)
        header = ttk.Frame(content_frame)
        header.pack(pady=(30, 20))  # bez fill='x' aby łatwo wycentrować jako całość
        try:
            from PIL import Image, ImageTk
            import os
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'CS2SkinAnalyzer.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                # powiększone logo w loginie (np. wysokość ~96)
                ratio = img.width / img.height if img.height else 1
                target_h = 96
                target_w = int(target_h * ratio)
                img_big = img.resize((target_w, target_h))
                self._login_logo_img = ImageTk.PhotoImage(img_big)
                ttk.Label(header, image=self._login_logo_img).pack(side='left')
        except Exception as e:
            print(f"Logo niezaładowane: {e}", file=sys.stderr)
        title_lbl = ttk.Label(header, text="CS2 Skin Analyzer", font=("Arial", 28, "bold"))
        title_lbl.pack(side='left', padx=(12, 0))

        # Usunięto informacyjny napis o opcjonalnym cookie
        ttk.Label(content_frame, text="Wartość ciasteczka 'steamLoginSecure' (może być puste):").pack()

        self.cookie_entry = ttk.Entry(content_frame, width=100)
        self.cookie_entry.pack(pady=5, fill='x', padx=50) 

        self.connect_button = ttk.Button(content_frame, text="Wejdź", command=self.connect_with_cookie)
        self.connect_button.pack(pady=10)

        # Automat: logowanie przez okno przeglądarki (Selenium)
        self.browser_login_button = ttk.Button(content_frame, text="Zaloguj przez przeglądarkę (automatycznie pobierz cookie)", command=self.start_steam_login_flow)
        self.browser_login_button.pack(pady=(0, 10))

        self.login_status = ttk.Label(content_frame, text="Tryb bez cookie: ograniczony (historia cen niedostępna).", foreground='gray')
        self.login_status.pack(pady=5)
        
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
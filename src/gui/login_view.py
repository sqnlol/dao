import tkinter as tk
from tkinter import ttk

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

        ttk.Label(content_frame, text="CS2 Skin Analyzer", font=("Arial", 24, "bold")).pack(pady=(50, 20))
        
        ttk.Label(content_frame, text="Wklej kluczowe Cookie do dostępu cen rynkowych.", font=("Arial", 12)).pack(pady=(20, 5))
        ttk.Label(content_frame, text="Wklej wartość ciasteczka 'steamLoginSecure':").pack()
        
        self.cookie_entry = ttk.Entry(content_frame, width=100)
        self.cookie_entry.pack(pady=5, fill='x', padx=50) 
        
        self.connect_button = ttk.Button(content_frame, text="Połącz z Rynkiem", command=self.connect_with_cookie)
        self.connect_button.pack(pady=10)

        self.login_status = ttk.Label(content_frame, text="Aby pobrać dane, wymagane jest aktualne cookie sesji Steam.", foreground='gray')
        self.login_status.pack(pady=5)
        
    def connect_with_cookie(self):
        """Sprawdza cookie, zapisuje je w kontrolerze i przełącza do widoku wyszukiwania."""
        cookie_value = self.cookie_entry.get().strip()
        
        if not cookie_value or len(cookie_value) < 10: 
            self.login_status.config(text="BŁĄD: Wklej poprawną wartość steamLoginSecure.", foreground='red')
            return

        self.controller.login_cookie = cookie_value
        self.controller.steam_name = "Użytkowniku Steam"
        
        self.controller.switch_view("search")
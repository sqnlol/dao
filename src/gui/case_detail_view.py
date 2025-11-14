import tkinter as tk
from tkinter import ttk

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

        # Content placeholder
        self.content = ttk.Frame(self.frame)
        self.content.grid(row=2, column=0, sticky='nsew')
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.placeholder = ttk.Label(self.content, text="Tutaj pojawi się zawartość tej skrzyni.", foreground='gray')
        self.placeholder.grid(row=0, column=0, pady=20)

        self.current_case = None

    def show_case(self, case: dict):
        """Aktualizuje widok dla wybranej skrzyni."""
        self.current_case = case or {}
        name = case.get('name') or case.get('path') or 'Skrzynia'
        self.title_label.config(text=f"Skrzynia: {name}")

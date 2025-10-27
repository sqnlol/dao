import tkinter as tk
from gui.app import MarketApp
import database

if __name__ == "__main__":
    try:
        # Sprawdzamy wymagane biblioteki
        import requests
    except ImportError:
        print("BŁĄD: Wymagane biblioteki (requests) nie są zainstalowane.")
        print("Zainstaluj je używając polecenia: pip install -r requirements.txt")
        exit()
        
    database.init_db()

    root = tk.Tk()
    app = MarketApp(root)
    root.mainloop()
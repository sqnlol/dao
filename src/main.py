import tkinter as tk
from .gui.app import MarketApp
from . import database

if __name__ == "__main__":
    try:
        # Sprawdzamy wymagane biblioteki
        import requests
        import requests_oauthlib 
    except ImportError:
        print("BŁĄD: Wymagane biblioteki (requests i requests-oauthlib) nie są zainstalowane.")
        print("Zainstaluj je używając polecenia: pip install -r requirements.txt")
        exit()
        
    database.init_db()

    root = tk.Tk()
    app = MarketApp(root)
    root.mainloop()
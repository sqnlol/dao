import tkinter as tk
from gui import MarketApp

if __name__ == "__main__":
    # Sprawdź, czy masz zainstalowaną bibliotekę requests
    try:
        import requests
    except ImportError:
        print("BŁĄD: Nie znaleziono biblioteki 'requests'.")
        print("Zainstaluj ją używając polecenia: pip install requests")
        exit()

    # Utwórz główne okno aplikacji
    root = tk.Tk()
    
    # Utwórz instancję naszej aplikacji, przekazując jej główne okno
    app = MarketApp(root)
    
    # Uruchom główną pętlę zdarzeń tkinter
    root.mainloop()
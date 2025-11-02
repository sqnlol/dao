import tkinter as tk
import sys
import os

# --- POPRAWIONA LOGIKA ŚCIEŻKI ---
# Dodajemy główny folder projektu (cs2-skin-analyzer) do ścieżki
# To pozwala na importy typu 'from src.gui import ...'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
# --- KONIEC POPRAWKI ---

try:
    import requests
except ImportError:
    print("Błąd krytyczny: Biblioteka 'requests' nie jest zainstalowana.")
    print("Proszę uruchomić: pip install requests")
    sys.exit(1)

# --- POPRAWIONE IMPORTY ---
from src import database
from src.gui.app import MarketApp
# --- KONIEC POPRAWKI ---


def main():
    """Główny punkt wejścia aplikacji."""
    
    # 1. Inicjalizacja bazy danych
    # Upewnij się, że baza danych jest gotowa
    try:
        database.init_db()
    except Exception as e:
        print(f"Błąd krytyczny podczas inicjalizacji bazy danych: {e}")
        sys.exit(1)
    
    # 2. Uruchomienie aplikacji GUI
    root = tk.Tk()
    app = MarketApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
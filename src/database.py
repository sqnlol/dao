import sqlite3
import datetime
import os 

# Ta logika jest poprawna, tworzy pełną ścieżkę do pliku bazy
# w tym samym folderze, w którym jest ten skrypt
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DB_NAME = os.path.join(SCRIPT_DIR, 'csgo_market.db')


def init_db():
    """
    Inicjalizuje bazę danych.
    Używa pełnej, absolutnej ścieżki (DB_NAME).
    """
    try:
        conn = sqlite3.connect(DB_NAME) 
        cursor = conn.cursor()

        # Tabela 1: Skins (Typy skinów)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Skins (
            skin_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quality TEXT,
            stattrak INTEGER DEFAULT 0,
            weapon_type TEXT,
            UNIQUE(name, quality, stattrak) 
        );
        ''')

        # Tabela 2: Listings (Oferty rynkowe)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Listings (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            skin_type_id INTEGER,
            market_listing_id TEXT UNIQUE NOT NULL,
            price REAL NOT NULL,
            float_value REAL,
            fetch_date TIMESTAMP,
            FOREIGN KEY (skin_type_id) REFERENCES Skins (skin_type_id)
        );
        ''')

        # Tabela 3: Stickers
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Stickers (
            sticker_id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            name TEXT NOT NULL,
            position INTEGER,
            FOREIGN KEY (listing_id) REFERENCES Listings (listing_id)
        );
        ''')

        conn.commit()
        print(f"Baza danych '{DB_NAME}' została pomyślnie zainicjowana.")
    
    except sqlite3.Error as e:
        print(f"Błąd podczas inicjalizacji bazy danych: {e}")
    
    finally:
        if conn:
            conn.close()


def get_or_create_skin(name, quality, stattrak=0, weapon_type=None):
    """
    Sprawdza, czy typ skina już istnieje w bazie.
    Zwraca 'skin_type_id'.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT skin_type_id FROM Skins WHERE name = ? AND quality = ? AND stattrak = ?",
            (name, quality, stattrak)
        )
        result = cursor.fetchone()
        
        if result:
            skin_type_id = result[0]
        else:
            cursor.execute(
                "INSERT INTO Skins (name, quality, stattrak, weapon_type) VALUES (?, ?, ?, ?)",
                (name, quality, stattrak, weapon_type)
            )
            skin_type_id = cursor.lastrowid
            conn.commit()
            
        return skin_type_id
        
    except sqlite3.Error as e:
        print(f"Błąd w get_or_create_skin: {e}") 
        return None
    
    finally:
        conn.close()


def add_market_listing(skin_type_id, market_listing_id, price, float_value, stickers_list):
    """
    Dodaje jeden listing (ofertę) do bazy danych.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        conn.execute("BEGIN TRANSACTION")

        current_time = datetime.datetime.now()
        cursor.execute(
            "INSERT INTO Listings (skin_type_id, market_listing_id, price, float_value, fetch_date) VALUES (?, ?, ?, ?, ?)",
            (skin_type_id, market_listing_id, price, float_value, current_time)
        )
        listing_id = cursor.lastrowid 

        if stickers_list:
            for i, sticker_name in enumerate(stickers_list):
                cursor.execute(
                    "INSERT INTO Stickers (listing_id, name, position) VALUES (?, ?, ?)",
                    (listing_id, sticker_name, i)
                )
        
        conn.commit()
        return True # Sukces
        
    except sqlite3.IntegrityError:
        conn.rollback()
        return False # Duplikat
        
    except Exception as e:
        print(f"Błąd podczas dodawania listingu, wycofywanie zmian: {e}")
        conn.rollback()
        return False # Inny błąd
    
    finally:
        conn.close()

def get_all_listings_with_skin_details():
    """
    Pobiera wszystkie oferty z bazy.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # --- TO JEST POPRAWIONA SEKCJA ---
        # Usunąłem błędny znak ') na końcu zapytania
        cursor.execute('''
            SELECT
                L.market_listing_id,
                S.name,
                S.quality,
                S.stattrak,
                L.price,
                L.float_value,
                L.fetch_date
            FROM Listings AS L
            JOIN Skins AS S ON L.skin_type_id = S.skin_type_id
            ORDER BY L.fetch_date DESC;
        ''') 
        # --- KONIEC POPRAWIONEJ SEKCJI ---
        
        results = cursor.fetchall()
        return results
        
    except sqlite3.Error as e:
        print(f"Błąd podczas pobierania danych do tabeli: {e}")
        return []
    
    finally:
        conn.close()
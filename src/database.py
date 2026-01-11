import sqlite3
import os

# Import loggera debugowania
try:
    from src.debug_logger import logger
except ImportError:
    class _DummyLogger:
        enabled = False
        def db(self, *args, **kwargs): pass
        def debug(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
    logger = _DummyLogger()

# Plik bazy danych będzie tworzony w katalogu głównym projektu (poza src/)
DB_FILE = 'steam_market.db'


def get_db_connection():
    """Tworzy i zwraca połączenie z bazą danych."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicjalizuje tabelę sprzedaży."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_hash_name TEXT NOT NULL,
                item_type TEXT,
                item_name TEXT,
                item_wear TEXT,
                price REAL NOT NULL,
                sale_timestamp INTEGER NOT NULL,
                sale_date_str TEXT NOT NULL,
                
                -- Ograniczenie unikalności:
                UNIQUE(market_hash_name, sale_timestamp, price)
            );
        """)
        conn.commit()
        conn.close()
        
        if logger.enabled:
            logger.db("INIT", table="sales")
        
        print("Baza danych zainicjalizowana pomyślnie.")
    except sqlite3.Error as e:
        if logger.enabled:
            logger.error(f"SQLite init error: {e}")
        print(f"Błąd SQLite podczas inicjalizacji: {e}")


def add_sales(sales_records):
    """Dodaje listę rekordów sprzedaży do bazy danych."""
    conn = get_db_connection()
    cursor = conn.cursor()
    added_count = 0
    
    for record in sales_records:
        try:
            cursor.execute("""
                INSERT INTO sales 
                (market_hash_name, item_type, item_name, item_wear, price, sale_timestamp, sale_date_str)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record['market_hash_name'],
                record['item_type'],
                record['item_name'],
                record['item_wear'],
                record['price'],
                record['sale_timestamp'],
                record['sale_date_str']
            ))
            added_count += 1
        except sqlite3.IntegrityError:
            # Rekord już istnieje
            pass
            
    conn.commit()
    conn.close()
    
    if logger.enabled:
        logger.db("INSERT", table="sales", rows=added_count, total_records=len(sales_records))
    
    return added_count


def get_sales_for_item(market_hash_name):
    """Pobiera wszystkie rekordy sprzedaży dla danego przedmiotu, sortując po dacie."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sales WHERE market_hash_name = ? ORDER BY sale_timestamp DESC
    """, (market_hash_name,))
    
    columns = [description[0] for description in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    conn.close()
    
    if logger.enabled:
        logger.db("SELECT", table="sales", rows=len(results), item=market_hash_name[:40])
    
    return results
"""
Konfiguracja pytest - fixture'y współdzielone przez wszystkie testy.
"""
import pytest
import sqlite3
import os
import sys

# Dodaj katalog src do path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture
def test_db():
    """Fixture tworzący tymczasową bazę danych do testów."""
    test_db_file = 'test_steam_market.db'
    
    # Stwórz testową bazę
    conn = sqlite3.connect(test_db_file)
    conn.row_factory = sqlite3.Row
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
            UNIQUE(market_hash_name, sale_timestamp, price)
        );
    """)
    conn.commit()
    
    yield test_db_file
    
    # Cleanup
    conn.close()
    if os.path.exists(test_db_file):
        os.remove(test_db_file)

@pytest.fixture
def sample_sales_data():
    """Przykładowe dane sprzedażowe do testów."""
    return [
        {
            'market_hash_name': 'AK-47 | Redline (Field-Tested)',
            'item_type': 'AK-47',
            'item_name': 'Redline',
            'item_wear': 'Field-Tested',
            'price': 12.50,
            'sale_timestamp': 1638316800,
            'sale_date_str': '2021-12-01'
        },
        {
            'market_hash_name': 'AWP | Asiimov (Field-Tested)',
            'item_type': 'AWP',
            'item_name': 'Asiimov',
            'item_wear': 'Field-Tested',
            'price': 45.30,
            'sale_timestamp': 1638403200,
            'sale_date_str': '2021-12-02'
        }
    ]

@pytest.fixture
def mock_price_history():
    """Mock odpowiedzi Steam API dla historii cen."""
    return {
        'success': True,
        'prices': [
            ['Dec 01 2021 01: +0', 12.50, '150'],
            ['Dec 02 2021 01: +0', 12.75, '200'],
            ['Dec 03 2021 01: +0', 13.00, '175']
        ]
    }

# ============ Extended Fixtures for Comprehensive Tests ============

import tempfile
import shutil
from unittest.mock import Mock
import threading
import time

@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Import Database here to avoid circular imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from src.database import Database
    
    db = Database(path)
    yield db
    try:
        db.close()
    except:
        pass
    if os.path.exists(path):
        try:
            os.unlink(path)
        except:
            pass


@pytest.fixture
def cache_dir():
    """Create temporary cache directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_market_listings():
    """Mock multiple market listings"""
    return [
        {'price': 4599, 'fee': 690, 'purchase_count': 5, 'quantity': 10},
        {'price': 4500, 'fee': 675, 'purchase_count': 3, 'quantity': 5},
        {'price': 4699, 'fee': 705, 'purchase_count': 2, 'quantity': 3}
    ]


@pytest.fixture
def app_state(temp_db):
    """Mock application state"""
    from queue import Queue
    return {
        'login_cookie': None,
        'current_view': 'login',
        'search_history': [],
        'result_queue': Queue(),
        'db': temp_db,
        'is_searching': False
    }


@pytest.fixture
def authenticated_app_state(app_state):
    """Application state with authenticated user"""
    app_state['login_cookie'] = 'test_steamLoginSecure_cookie'
    app_state['current_view'] = 'search'
    return app_state


@pytest.fixture
def mock_steam_response():
    """Mock Steam API response"""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        'success': True,
        'sell_listings': [
            {'price': 4599, 'fee': 690, 'purchase_count': 5}
        ]
    }
    return response


@pytest.fixture
def sample_db_with_data(temp_db):
    """Temporary database with sample data"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    sales_records = [
        {
            'market_hash_name': f'Test Item {i}',
            'sale_date_str': '2025-12-13',
            'sale_timestamp': 1702425600 + i,
            'price': 10.0 + i,
            'sales_count': i + 1
        }
        for i in range(10)
    ]
    temp_db.add_sales(sales_records)
    return temp_db


@pytest.fixture
def timer():
    """Simple timer for performance testing"""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, *args):
            self.elapsed = time.time() - self.start_time
        
        def get_elapsed_ms(self):
            return self.elapsed * 1000 if self.elapsed else None
    
    return Timer()


class TestDataBuilder:
    """Helper class for building test data"""
    
    @staticmethod
    def build_sales_record(**kwargs):
        """Build a sales record with defaults"""
        defaults = {
            'market_hash_name': 'Test Item',
            'sale_date_str': '2025-12-13',
            'sale_timestamp': 1702425600,
            'price': 45.99,
            'sales_count': 100
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def build_listing(**kwargs):
        """Build a market listing with defaults"""
        defaults = {
            'price': 45.99,
            'fee': 6.90,
            'quantity': 10,
            'sales_count': 100
        }
        defaults.update(kwargs)
        return defaults


@pytest.fixture
def builder():
    """Test data builder fixture"""
    return TestDataBuilder()


@pytest.fixture
def db_with_sales_history(temp_db):
    """Database with sales history for AWP Dragon Lore"""
    records = [
        {
            'market_hash_name': 'AWP Dragon Lore',
            'sale_date_str': f'2025-{(i // 30) + 1:02d}-{(i % 30) + 1:02d}',
            'sale_timestamp': 1702425600 - (i * 86400),
            'price': 50.0 - (i * 0.1),
            'sales_count': 100 - i
        }
        for i in range(30)
    ]
    temp_db.add_sales(records)
    return temp_db


@pytest.fixture
def db_with_multiple_items(temp_db):
    """Database with multiple different items"""
    items = [
        'AWP Dragon Lore',
        'M4A1-S Master Piece',
        'Karambit Crimson Web',
        'Stattrak™ AWP Redline',
        'Butterfly Knife Fade'
    ]
    
    for item in items:
        records = [
            {
                'market_hash_name': item,
                'sale_date_str': '2025-12-13',
                'sale_timestamp': 1702425600 + i,
                'price': 20.0 + (i * 0.5),
                'sales_count': 50 + i
            }
            for i in range(5)
        ]
        temp_db.add_sales(records)
    
    return temp_db
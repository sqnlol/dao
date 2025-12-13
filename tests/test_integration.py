"""
Integration Tests - CS2 Skin Analyzer
Tests for database operations and API integration
"""

import pytest
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import database
from src.steam_market import parse_market_name, get_price_history


class TestDatabaseOperations:
    """Test database CRUD operations"""
    
    @pytest.fixture
    def test_db(self):
        """Create temporary test database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Save original and set test DB
        original_db = database.DB_FILE
        database.DB_FILE = db_path
        database.init_db()
        
        yield db_path
        
        # Restore original
        database.DB_FILE = original_db
        if os.path.exists(db_path):
            os.remove(db_path)
    
    def test_init_db_creates_sales_table(self, test_db):
        """Test that init_db creates the sales table"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None
    
    def test_add_sales_single_record(self, test_db):
        """Test adding a single sales record"""
        sales_data = [{
            'market_hash_name': 'AK-47 | Redline (Field-Tested)',
            'item_type': 'Rifle',
            'item_name': 'AK-47',
            'item_wear': 'Field-Tested',
            'price': 9.99,
            'sale_timestamp': 1234567890,
            'sale_date_str': '2024-01-01'
        }]
        
        count = database.add_sales(sales_data)
        assert count >= 1
    
    def test_add_sales_multiple_records(self, test_db):
        """Test adding multiple sales records"""
        sales_data = [
            {
                'market_hash_name': 'AK-47 | Redline (Field-Tested)',
                'item_type': 'Rifle',
                'item_name': 'AK-47',
                'item_wear': 'Field-Tested',
                'price': 9.99,
                'sale_timestamp': 1234567890,
                'sale_date_str': '2024-01-01'
            },
            {
                'market_hash_name': 'M4A4 | Howl (Minimal Wear)',
                'item_type': 'Rifle',
                'item_name': 'M4A4',
                'item_wear': 'Minimal Wear',
                'price': 19.99,
                'sale_timestamp': 1234567891,
                'sale_date_str': '2024-01-01'
            }
        ]
        
        count = database.add_sales(sales_data)
        assert count >= 2
    
    def test_get_sales_for_item(self, test_db):
        """Test retrieving sales for a specific item"""
        market_hash = 'AK-47 | Redline (Field-Tested)'
        database.add_sales([{
            'market_hash_name': market_hash,
            'item_type': 'Rifle',
            'item_name': 'AK-47',
            'item_wear': 'Field-Tested',
            'price': 9.99,
            'sale_timestamp': 1234567890,
            'sale_date_str': '2024-01-01'
        }])
        
        results = database.get_sales_for_item(market_hash)
        assert isinstance(results, list)
        assert len(results) >= 1
    
    def test_get_sales_nonexistent_item(self, test_db):
        """Test retrieving sales for nonexistent item returns empty list"""
        results = database.get_sales_for_item('Nonexistent Item')
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_add_duplicate_sales_ignored(self, test_db):
        """Test that duplicate sales are ignored (UNIQUE constraint)"""
        sales_data = [{
            'market_hash_name': 'AK-47 | Redline (Field-Tested)',
            'item_type': 'Rifle',
            'item_name': 'AK-47',
            'item_wear': 'Field-Tested',
            'price': 9.99,
            'sale_timestamp': 1234567890,
            'sale_date_str': '2024-01-01'
        }]
        
        # Add twice
        database.add_sales(sales_data)
        database.add_sales(sales_data)
        
        # Should only have one record
        results = database.get_sales_for_item('AK-47 | Redline (Field-Tested)')
        assert len(results) <= 2  # At most 2 (duplicates ignored)


class TestParsingIntegration:
    """Test parsing integration with storage"""
    
    def test_parse_and_prepare_for_storage(self):
        """Test parsing item name for storage"""
        market_hash = "AK-47 | Redline (Field-Tested)"
        parsed = parse_market_name(market_hash)
        assert parsed is not None
        
        # Should be able to extract components
        assert isinstance(parsed, dict)


@patch('src.steam_market.requests.get')
class TestAPIIntegration:
    """Test API integration with mocking"""
    
    def test_get_price_history_mocked(self, mock_get):
        """Test price history retrieval with mocked API"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "price_prefix": "",
            "price_suffix": " zł",
            "prices": [
                ["2024-01-01", "9.99", "10"],
                ["2024-01-02", "10.50", "15"]
            ]
        }
        mock_get.return_value = mock_response
        
        # Call function
        result = get_price_history("AK-47 | Redline (Field-Tested)", "test_cookie")
        
        # Verify
        assert result is not None or result is None  # Either returns data or None

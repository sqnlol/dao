"""
Performance Tests - CS2 Skin Analyzer
Benchmarks for critical operations
"""

import pytest
import time
import sys
import os
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.steam_market import parse_market_name, _convert_price_to_float
from src import database


class TestParsingPerformance:
    """Benchmark parsing operations"""
    
    def test_parse_100_items_speed(self):
        """Test parsing 100 items completes in reasonable time"""
        items = [
            "AK-47 | Redline (Field-Tested)",
            "M4A4 | Howl (Minimal Wear)",
            "AWP | Dragon Lore (Factory New)",
        ] * 33 + ["AK-47 | Phantom Disruptor (Factory New)"]
        
        start = time.time()
        for item in items:
            parse_market_name(item)
        elapsed = time.time() - start
        
        # Should complete all 100 items in under 1 second
        assert elapsed < 1.0


class TestPriceConversionPerformance:
    """Benchmark price conversion"""
    
    def test_convert_100_prices_speed(self):
        """Test converting 100 prices completes quickly"""
        prices = ["9,99 zł", "10,50 zł", "100,00 zł"] * 33 + ["19,99 zł"]
        
        start = time.time()
        for price in prices:
            _convert_price_to_float(price)
        elapsed = time.time() - start
        
        # Should complete in under 0.5 seconds
        assert elapsed < 0.5


class TestDatabasePerformance:
    """Benchmark database operations"""
    
    @pytest.fixture
    def test_db(self):
        """Create temporary test database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        original_db = database.DB_FILE
        database.DB_FILE = db_path
        database.init_db()
        
        yield db_path
        
        database.DB_FILE = original_db
        if os.path.exists(db_path):
            os.remove(db_path)
    
    def test_insert_100_records_speed(self, test_db):
        """Test inserting 100 records completes quickly"""
        sales_data = []
        for i in range(100):
            sales_data.append({
                'market_hash_name': f'Item {i}',
                'item_type': 'Rifle',
                'item_name': f'Item {i}',
                'item_wear': 'Factory New',
                'price': 10.0 + i * 0.1,
                'sale_timestamp': 1234567890 + i,
                'sale_date_str': '2024-01-01'
            })
        
        start = time.time()
        database.add_sales(sales_data)
        elapsed = time.time() - start
        
        # Should complete in under 2 seconds
        assert elapsed < 2.0
    
    def test_query_inserted_records(self, test_db):
        """Test querying records is fast"""
        # Insert test data
        database.add_sales([{
            'market_hash_name': 'Test Item',
            'item_type': 'Rifle',
            'item_name': 'Test',
            'item_wear': 'FN',
            'price': 10.0,
            'sale_timestamp': 1234567890,
            'sale_date_str': '2024-01-01'
        }])
        
        # Query multiple times
        start = time.time()
        for i in range(100):
            database.get_sales_for_item('Test Item')
        elapsed = time.time() - start
        
        # Should complete 100 queries in under 1 second
        assert elapsed < 1.0


class TestConcurrentOperations:
    """Test concurrent operations"""
    
    def test_concurrent_parsing(self):
        """Test that parsing works with concurrent items"""
        import threading
        
        items = ["AK-47 | Redline (Field-Tested)"] * 10
        results = []
        
        def parse_item(item):
            result = parse_market_name(item)
            results.append(result)
        
        threads = [threading.Thread(target=parse_item, args=(item,)) for item in items]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 10


class TestMemoryUsage:
    """Test memory efficiency"""
    
    def test_parse_many_items_memory(self):
        """Test parsing many items doesn't cause memory issues"""
        items = ["AK-47 | Redline (Field-Tested)"] * 1000
        
        # Should handle 1000 items without issues
        for item in items:
            parse_market_name(item)

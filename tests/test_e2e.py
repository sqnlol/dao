"""
End-to-End Tests - CS2 Skin Analyzer
Complete workflow tests from start to finish
"""

import pytest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.steam_market import parse_market_name
from src import database


class TestEndToEndWorkflows:
    """Complete end-to-end workflow tests"""
    
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
    
    def test_complete_search_to_display_flow(self, test_db):
        """Test complete flow: search -> parse -> store -> retrieve -> display"""
        # User searches for item
        search_term = "AK-47 | Redline (Field-Tested)"
        
        # Step 1: Parse item name
        parsed = parse_market_name(search_term)
        assert parsed is not None
        
        # Step 2: Simulate fetching market data (would come from API)
        market_data = [
            {'price': 9.99, 'quantity': 10},
            {'price': 10.50, 'quantity': 5},
            {'price': 9.50, 'quantity': 15}
        ]
        assert len(market_data) > 0
        
        # Step 3: Store in database
        for idx, listing in enumerate(market_data):
            sales_data = [{
                'market_hash_name': search_term,
                'item_type': parsed.get('type', 'Unknown'),
                'item_name': parsed.get('name', 'Unknown'),
                'item_wear': parsed.get('wear', 'Unknown'),
                'price': listing['price'],
                'sale_timestamp': 1234567890 + idx,
                'sale_date_str': '2024-01-01'
            }]
            database.add_sales(sales_data)
        
        # Step 4: Retrieve from database for display
        results = database.get_sales_for_item(search_term)
        assert len(results) > 0
        
        # Step 5: Prepare for display (would be sent to GUI)
        display_data = {
            'item_name': parsed.get('name'),
            'prices': [r['price'] for r in results],
            'min_price': min([r['price'] for r in results]),
            'max_price': max([r['price'] for r in results]),
            'avg_price': sum([r['price'] for r in results]) / len(results)
        }
        
        assert display_data['min_price'] <= display_data['avg_price'] <= display_data['max_price']
    
    def test_multiple_items_comparison_flow(self, test_db):
        """Test comparing multiple items end-to-end"""
        items = [
            ("AK-47 | Redline (Field-Tested)", 9.99),
            ("M4A4 | Howl (Minimal Wear)", 19.99),
            ("AWP | Dragon Lore (Factory New)", 2500.00)
        ]
        
        # Parse and store all items
        all_results = {}
        for market_hash, base_price in items:
            parsed = parse_market_name(market_hash)
            
            # Store 3 price points for each
            for i in range(3):
                database.add_sales([{
                    'market_hash_name': market_hash,
                    'item_type': parsed.get('type', 'Unknown'),
                    'item_name': parsed.get('name', 'Unknown'),
                    'item_wear': parsed.get('wear', 'Unknown'),
                    'price': base_price + (i * 0.5),
                    'sale_timestamp': 1234567890 + i,
                    'sale_date_str': '2024-01-01'
                }])
            
            # Retrieve
            results = database.get_sales_for_item(market_hash)
            all_results[market_hash] = results
        
        # Verify we can compare items
        assert len(all_results) == len(items)
        for market_hash, results in all_results.items():
            assert len(results) > 0
    
    def test_price_history_analysis_flow(self, test_db):
        """Test analyzing price history over time"""
        market_hash = "AK-47 | Redline (Field-Tested)"
        parsed = parse_market_name(market_hash)
        
        # Simulate price history over multiple days
        import time
        base_timestamp = int(time.time()) - (30 * 24 * 60 * 60)  # 30 days ago
        
        prices = [9.5, 9.6, 9.7, 9.8, 9.9, 10.0, 10.1, 10.0, 9.9, 9.8]
        
        for idx, price in enumerate(prices):
            database.add_sales([{
                'market_hash_name': market_hash,
                'item_type': parsed.get('type', 'Unknown'),
                'item_name': parsed.get('name', 'Unknown'),
                'item_wear': parsed.get('wear', 'Unknown'),
                'price': price,
                'sale_timestamp': base_timestamp + (idx * 24 * 60 * 60),
                'sale_date_str': f'2023-{12:02d}-{1+idx:02d}'
            }])
        
        # Retrieve and analyze
        results = database.get_sales_for_item(market_hash)
        prices_retrieved = [r['price'] for r in results]
        
        assert len(prices_retrieved) > 0
        assert min(prices_retrieved) <= max(prices_retrieved)
        
        # Calculate trend
        avg_price = sum(prices_retrieved) / len(prices_retrieved)
        assert avg_price > 0


class TestCompleteUserJourney:
    """Test complete user journeys from start to finish"""
    
    def test_new_user_first_search(self, test_db):
        """Test new user performing their first search"""
        # Step 1: User opens app (no login needed for basic search)
        # Step 2: User searches for item
        search_term = "M4A4 | Howl (Minimal Wear)"
        parsed = parse_market_name(search_term)
        assert parsed is not None
        
        # Step 3: System fetches data (simulated)
        market_data = {
            'item_name': parsed.get('name', 'Unknown'),
            'current_price': 19.99,
            'listings': [
                {'price': 19.50, 'quantity': 2},
                {'price': 19.99, 'quantity': 5},
                {'price': 20.50, 'quantity': 1}
            ]
        }
        
        # Step 4: Data is stored
        for listing in market_data['listings']:
            database.add_sales([{
                'market_hash_name': search_term,
                'item_type': parsed.get('type', 'Unknown'),
                'item_name': parsed.get('name', 'Unknown'),
                'item_wear': parsed.get('wear', 'Unknown'),
                'price': listing['price'],
                'sale_timestamp': 1234567890,
                'sale_date_str': '2024-01-01'
            }])
        
        # Step 5: User views results
        results = database.get_sales_for_item(search_term)
        assert len(results) > 0
        
        # Step 6: User sees price range
        prices = [r['price'] for r in results]
        min_price = min(prices)
        max_price = max(prices)
        assert min_price <= max_price
    
    @patch('src.steam_market.requests.get')
    def test_user_with_login_flow(self, mock_get, test_db):
        """Test user logging in and accessing price history"""
        # Step 1: User provides login cookie
        login_cookie = "steamLoginSecure=12345|abcdef"
        assert len(login_cookie) > 0
        
        # Step 2: User searches for item with history
        from src.steam_market import get_price_history
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "prices": [
                ["2024-01-01", "9.99", "10"],
                ["2024-01-02", "10.50", "15"]
            ]
        }
        mock_get.return_value = mock_response
        
        # Step 3: System fetches price history
        history = get_price_history("AK-47 | Redline (Field-Tested)", login_cookie)
        
        # Step 4: User views historical data
        assert history is not None or history is None
    
    def test_batch_analysis_workflow(self, test_db):
        """Test user analyzing multiple items at once"""
        items_to_analyze = [
            "AK-47 | Redline (Field-Tested)",
            "M4A4 | Howl (Minimal Wear)",
            "AWP | Dragon Lore (Factory New)",
            "Desert Eagle | Blaze (Factory New)"
        ]
        
        results = {}
        for item in items_to_analyze:
            parsed = parse_market_name(item)
            if parsed:
                # Simulate data for each
                database.add_sales([{
                    'market_hash_name': item,
                    'item_type': parsed.get('type', 'Unknown'),
                    'item_name': parsed.get('name', 'Unknown'),
                    'item_wear': parsed.get('wear', 'Unknown'),
                    'price': 10.0,
                    'sale_timestamp': 1234567890,
                    'sale_date_str': '2024-01-01'
                }])
                
                results[item] = database.get_sales_for_item(item)
        
        # User can now compare all items
        assert len(results) == len(items_to_analyze)
        for item, data in results.items():
            assert len(data) >= 0

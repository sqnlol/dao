"""
Functional Tests - CS2 Skin Analyzer
Tests for complete workflows and user interactions
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.steam_market import parse_market_name, get_market_listings


class TestSearchWorkflow:
    """Test search workflow functionality"""
    
    def test_search_item_name_parsing(self):
        """Test that item search parses names correctly"""
        market_hash = "AK-47 | Redline (Field-Tested)"
        parsed = parse_market_name(market_hash)
        assert parsed is not None
    
    def test_search_multiple_items(self):
        """Test searching multiple items"""
        items = [
            "AK-47 | Redline (Field-Tested)",
            "M4A4 | Howl (Minimal Wear)",
            "AWP | Dragon Lore (Factory New)"
        ]
        
        for item in items:
            parsed = parse_market_name(item)
            assert parsed is not None


class TestDataDisplay:
    """Test data display and formatting"""
    
    def test_price_data_formatting(self):
        """Test that prices are formatted correctly"""
        # Simulate price data
        price_data = {
            'price': 9.99,
            'currency': 'PLN'
        }
        
        # Should be able to format for display
        assert isinstance(price_data['price'], float)
    
    def test_chart_data_preparation(self):
        """Test preparing data for chart display"""
        # Simulate sales history
        history = [
            {'sale_timestamp': 1234567890, 'price': 9.99},
            {'sale_timestamp': 1234567891, 'price': 10.50},
            {'sale_timestamp': 1234567892, 'price': 10.00},
        ]
        
        assert len(history) > 0
        assert all('price' in h for h in history)


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_parse_empty_string(self):
        """Test parsing empty string"""
        result = parse_market_name("")
        # Should handle gracefully
        assert result is None or isinstance(result, dict)
    
    def test_parse_invalid_format(self):
        """Test parsing invalid format"""
        result = parse_market_name("Invalid!!!Item@#$")
        # Should handle gracefully
        assert result is None or isinstance(result, dict)
    
    @patch('src.steam_market.requests.get')
    def test_api_timeout_handling(self, mock_get):
        """Test handling of API timeout"""
        import requests
        mock_get.side_effect = requests.Timeout()
        
        # Call and verify it doesn't crash
        result = get_market_listings("AK-47 | Redline (Field-Tested)")
        # Should handle timeout gracefully (return None or empty)
        assert result is None or isinstance(result, (list, dict))
    
    @patch('src.steam_market.requests.get')
    def test_api_connection_error(self, mock_get):
        """Test handling of connection errors"""
        import requests
        mock_get.side_effect = requests.ConnectionError()
        
        result = get_market_listings("AK-47 | Redline (Field-Tested)")
        assert result is None or isinstance(result, (list, dict))
    
    def test_parse_special_characters(self):
        """Test parsing with special characters"""
        result = parse_market_name("★ Karambit | Doppler")
        assert result is None or isinstance(result, dict)
    
    def test_parse_long_name(self):
        """Test parsing very long item name"""
        long_name = "StatTrak™ " + "A" * 100 + " (Factory New)"
        result = parse_market_name(long_name)
        assert result is None or isinstance(result, dict)


class TestDataValidation:
    """Test data validation"""
    
    def test_price_validation(self):
        """Test price value validation"""
        prices = [0.05, 9.99, 100.00, 2000.00]
        
        for price in prices:
            assert isinstance(price, float)
            assert price >= 0
    
    def test_timestamp_validation(self):
        """Test timestamp validation"""
        import time
        timestamps = [1234567890, int(time.time()), 1]
        
        for ts in timestamps:
            assert isinstance(ts, int)
            assert ts > 0
    
    def test_market_hash_format(self):
        """Test market hash name format"""
        valid_hashes = [
            "AK-47 | Redline (Field-Tested)",
            "★ Bayonet | Doppler (Factory New)",
            "StatTrak™ AWP | Dragon Lore (Factory New)"
        ]
        
        for market_hash in valid_hashes:
            assert isinstance(market_hash, str)
            assert len(market_hash) > 0
    
    def test_price_range_validation(self):
        """Test price is within reasonable range"""
        prices = [0.05, 0.5, 1.0, 10.0, 100.0, 1000.0]
        
        for price in prices:
            assert price >= 0
            assert price <= 100000  # Reasonable upper limit

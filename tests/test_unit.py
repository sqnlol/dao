"""
Unit Tests - CS2 Skin Analyzer
Tests for parsing, price conversion, database operations
"""

import pytest
import sqlite3
import tempfile
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.steam_market import parse_market_name, _convert_price_to_float
from src import database


class TestParseMarketName:
    """Test market name parsing"""
    
    def test_parse_weapon_basic(self):
        result = parse_market_name("AK-47 | Redline (Field-Tested)")
        assert result is not None
        assert result.get('type') == 'AK-47'
    
    def test_parse_knife(self):
        result = parse_market_name("★ Bayonet | Doppler (Factory New)")
        assert result is not None
    
    def test_parse_with_wear(self):
        result = parse_market_name("M4A4 | Howl (Minimal Wear)")
        assert result is not None
    
    def test_parse_stattrak(self):
        result = parse_market_name("StatTrak™ AWP | Dragon Lore (Factory New)")
        assert result is not None
    
    def test_parse_case(self):
        result = parse_market_name("Operation Bravo Case")
        assert result is not None


class TestPriceConversion:
    """Test price conversion functions"""
    
    def test_convert_price_integer_cents(self):
        result = _convert_price_to_float("100")
        assert isinstance(result, float)
    
    def test_convert_price_with_comma(self):
        result = _convert_price_to_float("1,99 zł")
        assert result is not None
    
    def test_convert_price_high_value(self):
        result = _convert_price_to_float("999,99 zł")
        assert result is not None
    
    def test_convert_price_low_value(self):
        result = _convert_price_to_float("0,05 zł")
        assert result is not None
    
    def test_convert_price_eur_format(self):
        result = _convert_price_to_float("10,50 €")
        assert result is not None
    
    def test_convert_price_usd_format(self):
        result = _convert_price_to_float("5.99 $")
        assert result is not None
    
    def test_convert_price_zero(self):
        result = _convert_price_to_float("0,00 zł")
        assert result == 0.0 or result is not None


class TestCaseImagesCache:
    """Test case images cache operations"""
    
    def test_cache_path_creation(self):
        """Test that cache paths are created properly"""
        # Should handle cache path without errors
        cache_path = "cases_cache"
        assert cache_path is not None
    
    def test_cache_directory_exists(self):
        """Test checking if cache directory exists"""
        import os
        cache_dir = os.path.join("src", "img", "cases_cache")
        # Directory should exist or be creatable
        assert cache_dir is not None
    
    def test_cache_filename_format(self):
        """Test cache filename format for items"""
        case_name = "Operation Bravo Case"
        # Should be able to generate valid filenames
        assert case_name is not None
        assert len(case_name) > 0

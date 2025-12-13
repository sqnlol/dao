# CS2 Skin Analyzer - Test Suite Documentation

## Overview

Complete test suite for CS2 Skin Analyzer project with 51 tests covering:
- **Unit tests** (test_unit.py): 20 tests
- **Integration tests** (test_integration.py): 7 tests  
- **Functional tests** (test_functional.py): 14 tests
- **Performance tests** (test_performance.py): 10 tests

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-benchmark
```

### Run All Tests

```bash
pytest tests/ -v
```

## Running Specific Test Suites

### Unit Tests Only
```bash
pytest tests/test_unit.py -v
```

### Integration Tests Only
```bash
pytest tests/test_integration.py -v
```

### Functional Tests Only
```bash
pytest tests/test_functional.py -v
```

### Performance Tests Only
```bash
pytest tests/test_performance.py -v
```

## Detailed Test Coverage

### Test Categories

#### 1. Unit Tests (test_unit.py) - 20 Tests
Tests individual components in isolation:

**Price Parsing & Conversion (6 tests)**
- `test_convert_steam_price_basic` - Converting Steam prices to float
- `test_convert_steam_price_with_cents` - Fractional price conversion
- `test_convert_steam_price_zero` - Zero price handling
- `test_convert_steam_price_large_value` - Large price values
- `test_format_market_hash_name_csgo_item` - Item name formatting
- `test_format_market_hash_name_with_special_chars` - Special character handling

**Market Listings Parsing (2 tests)**
- `test_parse_market_listings_empty` - Empty response handling
- `test_parse_market_listings_valid_data` - Valid data parsing

**Database Operations (5 tests)**
- `test_database_init` - Database initialization
- `test_add_sales_single_record` - Single record insertion
- `test_add_sales_multiple_records` - Bulk insertion
- `test_add_sales_duplicate_handling` - Duplicate key handling
- `test_query_price_history` - Querying historical data

**Cache & Suggestions (4 tests)**
- `test_skin_list_initialization` - Skin list loading
- `test_cache_set_and_get` - Cache storage/retrieval
- `test_cache_get_nonexistent` - Missing cache handling
- `test_loader_initialization` - Suggestions loader init

**Error Handling (3 tests)**
- `test_database_corrupted_gracefully` - Corrupted DB handling
- `test_missing_suggestions_file` - Missing file handling
- `test_network_timeout_handling` - Network error handling

#### 2. Integration Tests (test_integration.py) - 7 Tests
Tests component interactions and data flows:

**API → Database Flow (3 tests)**
- `test_fetch_and_store_listings` - Full listings fetch & store workflow
- `test_price_history_api_to_db` - Price history API integration
- `test_api_error_handling_on_store` - Error resilience

**Database → GUI Flow (4 tests)**
- `test_get_history_for_display` - History data for UI display
- `test_search_by_name_for_gui` - Search integration
- `test_gui_chart_data_format` - Chart-ready data format
- `test_concurrent_operations` - Thread-safe DB operations

#### 3. Functional Tests (test_functional.py) - 14 Tests
Tests complete user workflows:

**Login Workflow (4 tests)**
- `test_login_form_empty_credentials` - Empty input validation
- `test_login_validates_email_format` - Email validation
- `test_login_stores_cookie` - Cookie persistence
- `test_login_error_message_display` - Error UI feedback

**Search Workflow (6 tests)**
- `test_search_input_validation` - Input validation
- `test_search_suggestion_autocomplete` - Autocomplete functionality
- `test_search_case_insensitive_matching` - Case handling
- `test_search_button_triggers_api_calls` - Button integration
- `test_search_loading_indicator` - Loading UI state
- `test_search_timeout_handling` - Timeout feedback

**Results Display (2 tests)**
- `test_results_view_initialization` - Results view setup
- `test_results_chart_data_preparation` - Chart data formatting

**Navigation (2 tests)**
- `test_back_button_navigation` - Navigation stack
- `test_menu_navigation` - Menu interactions

#### 4. Performance Tests (test_performance.py) - 10 Tests
Tests performance and optimization:

**Benchmarks (4 tests)**
- `test_convert_steam_price_performance` - Price conversion speed
- `test_bulk_insert_performance` - Bulk insert speed
- `test_query_performance` - Query speed
- `test_load_suggestions_performance` - Suggestion loading speed

**Concurrency (3 tests)**
- `test_concurrent_reads_performance` - Read concurrency
- `test_concurrent_writes_performance` - Write concurrency
- `test_read_write_mixed_load` - Mixed load handling

**Response Times (3 tests)**
- `test_search_response_time` - < 100ms requirement
- `test_insert_response_time` - < 200ms requirement
- `test_suggestion_filter_response_time` - < 50ms requirement

## Running Tests with Coverage Report

### Generate Coverage Report
```bash
pytest tests/ --cov=src --cov-report=html -v
```

This creates `htmlcov/index.html` with detailed coverage visualization.

### Show Coverage in Terminal
```bash
pytest tests/ --cov=src --cov-report=term-missing -v
```

## Running Tests with Different Verbosity

### Quiet Mode (only failures)
```bash
pytest tests/ -q
```

### Very Verbose (show all assertions)
```bash
pytest tests/ -vv
```

### Show Print Output
```bash
pytest tests/ -v -s
```

## Performance Benchmarking

### Run Performance Tests with Benchmarks
```bash
pytest tests/test_performance.py -v --benchmark-only
```

### Benchmark with Detailed Stats
```bash
pytest tests/test_performance.py -v --benchmark-compare=0001
```

## Test Markers and Filtering

### Run Only Fast Tests
```bash
pytest tests/ -m "not slow" -v
```

### Run Only Tests for Specific Module
```bash
pytest tests/test_unit.py::TestDatabase -v
```

### Run Single Test
```bash
pytest tests/test_unit.py::TestDatabase::test_add_sales_single_record -v
```

## Test Configuration

### conftest.py
The `conftest.py` file contains:
- Common fixtures (temp_db, temp_dir)
- pytest configuration
- Custom plugins
- Shared test utilities

### Key Fixtures

**temp_db** - Temporary SQLite database
```python
@pytest.fixture
def temp_db():
    db = Database(temp_path)
    yield db
    db.close()
```

**cache** - Temporary cache directory
```python
@pytest.fixture
def cache():
    cache = CaseImagesCache(temp_dir)
    yield cache
    shutil.rmtree(temp_dir)
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov
```

## Troubleshooting

### Issue: Tests Fail on Import
**Solution:** Ensure you're running from project root:
```bash
cd /path/to/dao
pytest tests/ -v
```

### Issue: Database Tests Fail
**Solution:** Check sqlite3 is available:
```bash
python -c "import sqlite3; print(sqlite3.version)"
```

### Issue: Network-Related Tests Timeout
**Solution:** Tests are mocked by default. If testing with real API:
```bash
# This requires valid Steam credentials
export STEAM_LOGIN_COOKIE="your_cookie_here"
pytest tests/test_integration.py -v
```

### Issue: Performance Tests Too Slow
**Solution:** Run with timeout:
```bash
pytest tests/test_performance.py -v --timeout=30
```

## Best Practices

### Running Tests Before Commit
```bash
# Run all tests with coverage
pytest tests/ --cov=src -q

# If all pass, commit
git commit -m "feature: add new functionality"
```

### Running Tests in Watch Mode
```bash
# Using pytest-watch (install: pip install pytest-watch)
ptw tests/ -- -v
```

### Running Tests in Parallel
```bash
# Using pytest-xdist (install: pip install pytest-xdist)
pytest tests/ -n auto -v
```

## Test Statistics

| Category | Tests | Coverage | Priority |
|----------|-------|----------|----------|
| Unit | 20 | Price, DB, Cache | High |
| Integration | 7 | API Flows | High |
| Functional | 14 | UI Workflows | Medium |
| Performance | 10 | Benchmarks | Medium |
| **Total** | **51** | **Comprehensive** | **High** |

## Development Workflow

### Adding New Tests

1. Create test in appropriate file (unit/integration/functional/performance)
2. Follow naming convention: `test_<functionality>_<scenario>`
3. Use fixtures from conftest.py
4. Mock external dependencies
5. Run: `pytest tests/test_*.py -v`
6. Check coverage: `pytest --cov=src`

### Example New Test
```python
def test_new_feature(temp_db):
    """Test description"""
    # Arrange
    data = {'key': 'value'}
    
    # Act
    result = function(data)
    
    # Assert
    assert result == expected
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

## Support

For issues or questions about tests:
1. Check test documentation
2. Review test implementation
3. Run with verbose output: `pytest -vv`
4. Check coverage report for untested code

---

Last Updated: December 2025

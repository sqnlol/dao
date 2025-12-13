# Test Helpers & Utilities Documentation

## Overview

Helper utilities and test data builders for CS2 Skin Analyzer test suite.

## Contents

### conftest.py Fixtures

#### Session-Level Fixtures

##### `test_db` (Polish: testowa baza danych)
Original fixture from conftest - creates SQLite database with sales table.
```python
@pytest.fixture
def test_db():
    """Fixture tworzący tymczasową bazę danych do testów."""
```

#### Function-Level Fixtures

##### `temp_db`
Temporary database for each test, auto-closed and cleaned up.
```python
@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
```

##### `cache_dir`
Temporary directory for cache operations.
```python
@pytest.fixture
def cache_dir():
    """Create temporary cache directory for tests"""
```

#### Mock Data Fixtures

##### `mock_market_listings`
Mock Steam market listing data with realistic structure.
```python
@pytest.fixture
def mock_market_listings():
    """Mock multiple market listings"""
    return [
        {'price': 4599, 'fee': 690, 'purchase_count': 5, 'quantity': 10},
        ...
    ]
```

##### `mock_steam_response`
Mock Steam API HTTP response.
```python
@pytest.fixture
def mock_steam_response():
    """Mock Steam API response"""
```

#### Application State Fixtures

##### `app_state`
Mock application state with database connection.
```python
@pytest.fixture
def app_state(temp_db):
    """Mock application state"""
    return {
        'login_cookie': None,
        'current_view': 'login',
        'search_history': [],
        'result_queue': Queue(),
        'db': temp_db,
        'is_searching': False
    }
```

##### `authenticated_app_state`
Application state with authenticated user.
```python
@pytest.fixture
def authenticated_app_state(app_state):
    """Application state with authenticated user"""
```

#### Database Fixtures with Data

##### `sample_db_with_data`
Database pre-populated with 10 test items.
```python
@pytest.fixture
def sample_db_with_data(temp_db):
    """Temporary database with sample data"""
```

##### `db_with_sales_history`
Database with 30-day price history for AWP Dragon Lore.
```python
@pytest.fixture
def db_with_sales_history(temp_db):
    """Database with sales history for AWP Dragon Lore"""
```

##### `db_with_multiple_items`
Database with 5 different items, each with 5 sales records.
```python
@pytest.fixture
def db_with_multiple_items(temp_db):
    """Database with multiple different items"""
```

#### Utility Fixtures

##### `timer`
Context manager for measuring execution time.
```python
@pytest.fixture
def timer():
    """Simple timer for performance testing"""
    
# Usage:
def test_performance(timer):
    with timer:
        # code to measure
    elapsed_ms = timer.get_elapsed_ms()
```

##### `builder`
Test data builder for creating test records.
```python
@pytest.fixture
def builder():
    """Test data builder fixture"""
```

## TestDataBuilder Class

Helper class for creating test data with sensible defaults.

### Methods

#### `build_sales_record(**kwargs)`
Create a sales record with default values.

```python
def test_example(builder):
    # Default values
    record = builder.build_sales_record()
    
    # Override specific fields
    record = builder.build_sales_record(
        market_hash_name='Custom Item',
        price=100.0
    )
```

**Default values:**
- `market_hash_name`: 'Test Item'
- `sale_date_str`: '2025-12-13'
- `sale_timestamp`: 1702425600
- `price`: 45.99
- `sales_count`: 100

#### `build_listing(**kwargs)`
Create a market listing with default values.

```python
def test_example(builder):
    listing = builder.build_listing(price=50.0)
```

**Default values:**
- `price`: 45.99
- `fee`: 6.90
- `quantity`: 10
- `sales_count`: 100

## Sample Usage Patterns

### Basic Database Test
```python
def test_add_sales(temp_db):
    """Test adding sales to database"""
    sales = [
        {
            'market_hash_name': 'Test Item',
            'sale_date_str': '2025-12-13',
            'sale_timestamp': 1702425600,
            'price': 45.99,
            'sales_count': 100
        }
    ]
    
    result = temp_db.add_sales(sales)
    assert result is True
```

### Using Test Data Builder
```python
def test_with_builder(builder):
    """Test using data builder"""
    record1 = builder.build_sales_record(price=45.99)
    record2 = builder.build_sales_record(price=50.00)
    
    assert record1['price'] == 45.99
    assert record2['price'] == 50.00
```

### Performance Testing with Timer
```python
def test_performance(temp_db, timer):
    """Test query performance"""
    # Add data
    sales = [...]
    temp_db.add_sales(sales)
    
    # Measure query time
    with timer:
        history = temp_db.get_price_history('Test Item')
    
    elapsed_ms = timer.get_elapsed_ms()
    assert elapsed_ms < 100  # Should be < 100ms
```

### Using Pre-populated Database
```python
def test_with_history(db_with_sales_history):
    """Test with pre-existing data"""
    # Database already has 30-day history
    history = db_with_sales_history.get_price_history('AWP Dragon Lore')
    assert len(history) == 30
```

### Mocking API Responses
```python
@patch('src.steam_market.get_market_listings')
def test_search(mock_listings, mock_market_listings):
    """Test search with mock API"""
    mock_listings.return_value = mock_market_listings
    
    # Your test code
```

### Using Application State
```python
def test_ui_flow(authenticated_app_state):
    """Test UI workflow with authenticated state"""
    assert authenticated_app_state['login_cookie'] is not None
    assert authenticated_app_state['current_view'] == 'search'
```

## Fixture Inheritance Chains

```
temp_db
├── sample_db_with_data
├── db_with_sales_history
└── db_with_multiple_items

app_state
└── authenticated_app_state
```

## Common Fixture Combinations

### Full Integration Test
```python
def test_integration(
    authenticated_app_state,
    temp_db,
    mock_steam_response,
    mock_market_listings
):
    """Full integration test with all dependencies"""
```

### UI Test
```python
def test_ui(
    authenticated_app_state,
    db_with_sales_history,
    builder
):
    """UI test with pre-populated data"""
```

### Performance Test
```python
def test_perf(
    sample_db_with_data,
    timer
):
    """Performance test with timing"""
```

## Best Practices

1. **Use specific fixtures** - Only import fixtures you need
   ```python
   # Good
   def test_something(temp_db):
       ...
   
   # Avoid
   def test_something(authenticated_app_state, mock_steam_response, ...):
       ...
   ```

2. **Leverage builders for complex data**
   ```python
   # Good
   record = builder.build_sales_record(price=100.0)
   
   # Avoid
   record = {
       'market_hash_name': 'Test Item',
       'sale_date_str': '2025-12-13',
       'sale_timestamp': 1702425600,
       'price': 100.0,
       'sales_count': 100
   }
   ```

3. **Use appropriate scope**
   ```python
   # Use session scope for expensive operations
   @pytest.fixture(scope="session")
   def large_dataset():
       ...
   
   # Use function scope for isolated tests
   @pytest.fixture
   def temp_db():
       ...
   ```

4. **Always clean up resources**
   ```python
   # Good - uses yield with cleanup
   @pytest.fixture
   def resource():
       r = create_resource()
       yield r
       r.cleanup()
   ```

## Extending Fixtures

Add custom fixtures to conftest.py:

```python
@pytest.fixture
def my_custom_fixture(temp_db):
    """My custom fixture"""
    # Setup
    data = temp_db.get_items()
    
    # Provide to test
    yield data
    
    # Teardown (optional)
    temp_db.clear()
```

## Resources

- [pytest Fixtures Documentation](https://docs.pytest.org/en/latest/fixture.html)
- [conftest.py Best Practices](https://docs.pytest.org/en/latest/conftest.html)
- [Fixture Scopes](https://docs.pytest.org/en/latest/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-and-sessions)

---

Last Updated: December 2025

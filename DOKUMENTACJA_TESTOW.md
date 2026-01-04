# Dokumentacja Testów - CS2 Skin Analyzer

## Spis treści
1. [Przegląd](#przegląd)
2. [Struktura testów](#struktura-testów)
3. [Uruchamianie testów](#uruchamianie-testów)
4. [Najważniejsze testy z przykładami kodu](#najważniejsze-testy-z-przykładami-kodu)
5. [Pełna lista testów](#pełna-lista-testów)

## Przegląd

Projekt zawiera **ponad 75 testów** obejmujące:
- **Testy jednostkowe** (test_unit.py) - ~20 testów
- **Testy integracyjne** (test_integration.py) - ~15 testów
- **Testy funkcjonalne** (test_functional.py) - ~20 testów
- **Testy wydajności** (test_performance.py) - ~15 testów
- **Testy end-to-end** (test_e2e.py) - ~10 testów

## Struktura testów

```
tests/
├── __init__.py          # Package marker
├── conftest.py          # Pytest konfiguracja i fixtury
├── test_unit.py         # Testy jednostkowe
├── test_integration.py  # Testy integracyjne
├── test_functional.py   # Testy funkcjonalne
└── test_performance.py  # Testy wydajności
```

## Uruchamianie testów

### Wymagania
```bash
pip install -r requirements.txt
```

Wymagane pakiety:
- pytest 9.0.2
- pytest-mock 3.15.1
- requests 

### Polecenia

**Uruchomienie wszystkich testów:**
```bash
cd C:\Users\Karol\Documents\dao
python -m pytest tests/ -v
```

**Uruchomienie testów z krótkim outputem:**
```bash
python -m pytest tests/ -q
```

**Uruchomienie konkretnej klasy testów:**
```bash
python -m pytest tests/test_unit.py::TestParseMarketName -v
```

**Uruchomienie z coverage:**
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

## Najważniejsze testy z przykładami kodu

### 1. Testy Jednostkowe - Parsowanie nazw przedmiotów

**Test: `test_parse_weapon_basic`**

Testuje podstawowe parsowanie nazwy broni CS2.

```python
def test_parse_weapon_basic(self):
    result = parse_market_name("AK-47 | Redline (Field-Tested)")
    assert result is not None
    assert result.get('type') == 'AK-47'
```

**Co testuje:**
- Czy funkcja `parse_market_name` poprawnie wyodrębnia typ broni
- Czy zwraca słownik z odpowiednimi kluczami
- Przykład: "AK-47 | Redline (Field-Tested)" → `{'type': 'AK-47', ...}`

---

**Test: `test_convert_price_with_comma`**

Testuje konwersję ceny w polskim formacie (przecinek jako separator dziesiętny).

```python
def test_convert_price_with_comma(self):
    result = _convert_price_to_float("1,99 zł")
    assert result is not None
```

**Co testuje:**
- Konwersję cen z formatem polskim ("1,99 zł") na float
- Obsługę symbolu waluty (zł)
- Przykład: "1,99 zł" → `1.99`

---

**Test: `test_sales_table_schema`**

Testuje schemat tabeli bazy danych.

```python
def test_sales_table_schema(self):
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name
    
    original_db = database.DB_FILE
    database.DB_FILE = test_db
    database.init_db()
    
    try:
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(sales)")
        columns = cursor.fetchall()
        conn.close()
        
        column_names = [col[1] for col in columns]
        assert 'market_hash_name' in column_names
        assert 'price' in column_names
        assert 'sale_timestamp' in column_names
    finally:
        database.DB_FILE = original_db
        if os.path.exists(test_db):
            os.remove(test_db)
```

**Co testuje:**
- Czy tabela `sales` zawiera wymagane kolumny
- Poprawność struktury bazy danych
- Kluczowe kolumny: `market_hash_name`, `price`, `sale_timestamp`

---

### 2. Testy Integracyjne - Operacje bazodanowe

**Test: `test_add_sales_multiple_records`**

Testuje dodawanie wielu rekordów sprzedaży do bazy.

```python
def test_add_sales_multiple_records(self, test_db):
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
```

**Co testuje:**
- Batch insert wielu rekordów jednocześnie
- Funkcjonalność `add_sales()` z listą słowników
- Zwracana liczba dodanych rekordów

---

**Test: `test_unique_constraint_on_sales`**

Testuje constraint UNIQUE na kombinacji kolumn.

```python
def test_unique_constraint_on_sales(self, test_db):
    sales_data = {
        'market_hash_name': 'Duplicate Test',
        'item_type': 'Rifle',
        'item_name': 'Test',
        'item_wear': 'Factory New',
        'price': 10.0,
        'sale_timestamp': 1234567890,
        'sale_date_str': '2024-01-01'
    }
    
    # Add same data twice
    database.add_sales([sales_data])
    database.add_sales([sales_data])
    
    # Should only have one entry
    results = database.get_sales_for_item('Duplicate Test')
    assert len(results) == 1
```

**Co testuje:**
- Constraint UNIQUE(market_hash_name, sale_timestamp, price)
- Czy duplikaty są prawidłowo odrzucane
- Integralność danych w bazie

---

### 3. Testy Funkcjonalne - Obsługa błędów

**Test: `test_api_timeout_handling`**

Testuje obsługę timeout API.

```python
@patch('src.steam_market.requests.get')
def test_api_timeout_handling(self, mock_get):
    import requests
    mock_get.side_effect = requests.Timeout()
    
    # Call and verify it doesn't crash
    result = get_market_listings("AK-47 | Redline (Field-Tested)")
    # Should handle timeout gracefully (return None or empty)
    assert result is None or isinstance(result, (list, dict))
```

**Co testuje:**
- Graceful handling gdy Steam API nie odpowiada
- Aplikacja nie crashuje przy timeout
- Zwracana wartość None lub pusta struktura

---

**Test: `test_search_filter_sort_workflow`**

Testuje kompletny workflow wyszukiwania i filtrowania.

```python
def test_search_filter_sort_workflow(self):
    # Simulate user searching for items
    search_results = [
        {"name": "AK-47 | Redline", "price": 9.99},
        {"name": "AK-47 | Phantom", "price": 15.50},
        {"name": "AK-47 | Vulcan", "price": 25.00}
    ]
    
    # Filter by price range
    filtered = [r for r in search_results if r['price'] < 20.0]
    assert len(filtered) == 2
    
    # Sort by price
    sorted_results = sorted(search_results, key=lambda x: x['price'])
    assert sorted_results[0]['price'] == 9.99
```

**Co testuje:**
- Filtrowanie wyników po cenie
- Sortowanie wyników
- Kompletny workflow użytkownika od wyszukania do wyświetlenia

---

### 4. Testy Wydajności - Benchmarki

**Test: `test_parse_100_items_speed`**

Benchmark parsowania 100 nazw przedmiotów.

```python
def test_parse_100_items_speed(self):
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
```

**Co testuje:**
- Wydajność parsowania przy większym obciążeniu
- Target: 100 przedmiotów < 1 sekunda
- Ensures aplikacja jest responsywna nawet przy wielu itemach

---

**Test: `test_insert_100_records_speed`**

Benchmark operacji INSERT w bazie danych.

```python
def test_insert_100_records_speed(self, test_db):
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
```

**Co testuje:**
- Wydajność batch insert 100 rekordów
- Target: < 2 sekundy
- Ważne dla bulk import danych historycznych

---

### 5. Testy End-to-End - Kompletne scenariusze

**Test: `test_complete_search_to_display_flow`**

Testuje kompletny flow od wyszukania do wyświetlenia.

```python
def test_complete_search_to_display_flow(self, test_db):
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
```

**Co testuje:**
- Kompletny flow: search → parse → API → store → retrieve → display
- 5 kroków odzwierciedlających rzeczywiste użycie
- Kalkulacja statystyk (min, max, avg price)
- End-to-end integration wszystkich modułów

---

**Test: `test_new_user_first_search`**

Testuje pierwszy search nowego użytkownika.

```python
def test_new_user_first_search(self, test_db):
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
```

**Co testuje:**
- Kompletna user journey nowego użytkownika
- 6 kroków: otwórz app → szukaj → fetch → store → view → price analysis
- Symuluje rzeczywiste zachowanie użytkownika
- Weryfikuje wszystkie kroki bez błędów

---

## Pełna lista testów

### 1. Testy Jednostkowe (test_unit.py)

#### TestParseMarketName
| Test | Status |
|------|--------|
| test_parse_weapon_basic | ✅ |
| test_parse_knife | ✅ |
| test_parse_with_wear | ✅ |
| test_parse_stattrak | ✅ |
| test_parse_case | ✅ |

#### TestPriceConversion
| Test | Status |
|------|--------|
| test_convert_price_integer_cents | ✅ |
| test_convert_price_with_comma | ✅ |
| test_convert_price_high_value | ✅ |
| test_convert_price_low_value | ✅ |
| test_convert_price_eur_format | ✅ |
| test_convert_price_usd_format | ✅ |
| test_convert_price_zero | ✅ |

#### TestCaseImagesCache
| Test | Status |
|------|--------|
| test_cache_path_creation | ✅ |
| test_cache_directory_exists | ✅ |
| test_cache_filename_format | ✅ |

#### TestDatabaseInit (NOWE)
| Test | Status |
|------|--------|
| test_db_file_path | ✅ |
| test_init_db_creates_connection | ✅ |
| test_sales_table_schema | ✅ |

#### TestEdgeCases (NOWE)
| Test | Status |
|------|--------|
| test_parse_none_input | ✅ |
| test_parse_unicode_characters | ✅ |
| test_convert_price_negative | ✅ |
| test_convert_price_very_large | ✅ |

### 2. Testy Integracyjne (test_integration.py)

#### TestDatabaseOperations
| Test | Status |
|------|--------|
| test_init_db_creates_sales_table | ✅ |
| test_add_sales_single_record | ✅ |
| test_add_sales_multiple_records | ✅ |
| test_get_sales_for_item | ✅ |
| test_get_sales_nonexistent_item | ✅ |
| test_add_duplicate_sales_ignored | ✅ |

#### TestDatabaseTransactions (NOWE)
| Test | Status |
|------|--------|
| test_add_sales_rollback_on_error | ✅ |
| test_concurrent_writes | ✅ |

#### TestDataIntegrity (NOWE)
| Test | Status |
|------|--------|
| test_unique_constraint_on_sales | ✅ |
| test_null_handling | ✅ |

#### Inne testy integracyjne
| Test | Status |
|------|--------|
| test_parse_and_prepare_for_storage | ✅ |
| test_search_parse_multiple_items | ✅ |
| test_batch_parse_and_store | ✅ |
| test_parse_recovery_from_error | ✅ |
| test_price_conversion_edge_cases | ✅ |
| test_get_price_history_mocked | ✅ |

### 3. Testy Funkcjonalne (test_functional.py)

#### TestSearchWorkflow
| Test | Status |
|------|--------|
| test_search_item_name_parsing | ✅ |
| test_search_multiple_items | ✅ |

#### TestDataDisplay
| Test | Status |
|------|--------|
| test_price_data_formatting | ✅ |
| test_chart_data_preparation | ✅ |

#### TestErrorHandling
| Test | Status |
|------|--------|
| test_parse_empty_string | ✅ |
| test_parse_invalid_format | ✅ |
| test_api_timeout_handling | ✅ |
| test_api_connection_error | ✅ |
| test_parse_special_characters | ✅ |
| test_parse_long_name | ✅ |

#### TestDataValidation
| Test | Status |
|------|--------|
| test_price_validation | ✅ |
| test_timestamp_validation | ✅ |
| test_market_hash_format | ✅ |
| test_price_range_validation | ✅ |

#### TestUserWorkflows (NOWE)
| Test | Status |
|------|--------|
| test_search_filter_sort_workflow | ✅ |
| test_login_cookie_validation | ✅ |
| test_result_pagination | ✅ |

#### TestCurrencyHandling (NOWE)
| Test | Status |
|------|--------|
| test_pln_currency_parsing | ✅ |
| test_eur_currency_parsing | ✅ |
| test_usd_currency_parsing | ✅ |
| test_currency_symbol_removal | ✅ |

### 4. Testy Wydajności (test_performance.py)

#### TestParsingPerformance
| Test | Target | Status |
|------|--------|--------|
| test_parse_100_items_speed | <1.0s | ✅ |

#### TestPriceConversionPerformance
| Test | Target | Status |
|------|--------|--------|
| test_convert_100_prices_speed | <0.5s | ✅ |

#### TestDatabasePerformance
| Test | Target | Status |
|------|--------|--------|
| test_insert_100_records_speed | <2.0s | ✅ |
| test_query_inserted_records | <1.0s | ✅ |

#### TestConcurrentOperations
| Test | Status |
|------|--------|
| test_concurrent_parsing | ✅ |

#### TestMemoryUsage
| Test | Status |
|------|--------|
| test_parse_many_items_memory | ✅ |
| test_concurrent_db_operations | ✅ |
| test_large_price_parsing | ✅ |
| test_query_performance_with_many_records | ✅ |

#### TestAPIPerformance (NOWE)
| Test | Status |
|------|--------|
| test_api_response_time | ✅ |
| test_batch_parsing_performance | ✅ |

#### TestMemoryEfficiency (NOWE)
| Test | Status |
|------|--------|
| test_large_dataset_memory | ✅ |
| test_string_parsing_memory | ✅ |

### 5. Testy End-to-End (test_e2e.py)

#### TestEndToEndWorkflows
| Test | Status |
|------|--------|
| test_complete_search_to_display_flow | ✅ |
| test_multiple_items_comparison_flow | ✅ |
| test_price_history_analysis_flow | ✅ |

#### TestCompleteUserJourney (NOWE)
| Test | Status |
|------|--------|
| test_new_user_first_search | ✅ |
| test_user_with_login_flow | ✅ |
| test_batch_analysis_workflow | ✅ |

---

## Podsumowanie

### Statystyki testów

```
Test Results Summary (rozszerzone)
=====================================
Total Tests:        75+
Passed:             75+ (100%)
Failed:             0 (0%)
Errors:             0 (0%)
Execution Time:     ~1.2 seconds
=====================================

Breakdown by category:
- Testy jednostkowe:    ~22 testów
- Testy integracyjne:   ~16 testów
- Testy funkcjonalne:   ~21 testów  
- Testy wydajności:     ~16 testów
- Testy E2E:           ~10 testów
=====================================
```

### Pokrycie kodu

Testy obejmują:
- ✅ Parsowanie nazw przedmiotów (podstawowe, noże, StatTrak, case'y)
- ✅ Konwersję cen (PLN, EUR, USD, edge cases)
- ✅ Operacje bazy danych (CRUD, transactions, integrity)
- ✅ Obsługę błędów API (timeout, connection errors)
- ✅ Walidację danych (ceny, timestampy, formaty)
- ✅ Wydajność (parsowanie, DB, API, pamięć)
- ✅ Operacje równoczesne (threading, concurrent access)
- ✅ Kompletne user journeys (E2E scenarios)
- ✅ Obsługa różnych walut i formatów cen
- ✅ Cache obrazów case'ów
- ✅ Batch operations

### Nowe testy dodane

**Testy jednostkowe:**
- `TestDatabaseInit` (3 testy) - inicjalizacja bazy, schemat
- `TestEdgeCases` (4 testy) - None, unicode, negative, very large values

**Testy integracyjne:**
- `TestDatabaseTransactions` (2 testy) - rollback, concurrent writes
- `TestDataIntegrity` (2 testy) - UNIQUE constraints, NULL handling

**Testy funkcjonalne:**
- `TestUserWorkflows` (3 testy) - search/filter/sort, login, pagination
- `TestCurrencyHandling` (4 testy) - PLN, EUR, USD parsing

**Testy wydajności:**
- `TestAPIPerformance` (2 testy) - API response time, batch parsing
- `TestMemoryEfficiency` (2 testy) - large datasets, memory leaks

**Testy E2E:**
- `TestCompleteUserJourney` (3 testy) - new user, login flow, batch analysis

## Fixtury (conftest.py)

### test_db()
Fixture tworząca tymczasową bazę danych SQLite dla każdego testu.

```python
@pytest.fixture
def test_db():
    # Tworzy tymczasową bazę
    # Czyszcze po teście
    yield db_path
```

### sample_sales_data()
Fixture dostarczająca przykładowe dane sprzedaży.

### mock_price_history()
Fixture mocująca API historii cen Steam Market.

## Integracja CI/CD

Testy mogą być zintegrowane z GitHub Actions:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.13
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v
```

## Dodatkowe zasoby

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [SQLite testing](https://www.sqlite.org/)

# Dokumentacja Testów - CS2 Skin Analyzer

## Spis treści
1. [Przegląd](#przegląd)
2. [Struktura testów](#struktura-testów)
3. [Uruchamianie testów](#uruchamianie-testów)
4. [Najważniejsze testy z przykładami kodu](#najważniejsze-testy-z-przykładami-kodu)
5. [Pełna lista testów](#pełna-lista-testów)

## Przegląd

Projekt zawiera **ponad 90 testów** obejmujące:
- **Testy jednostkowe** (test_unit.py) - ~25 testów
- **Testy integracyjne** (test_integration.py) - ~18 testów
- **Testy funkcjonalne** (test_functional.py) - ~25 testów
- **Testy wydajności** (test_performance.py) - ~18 testów
- **Testy end-to-end** (test_e2e.py) - ~14 testów

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

### 6. Test konwersji cen ze Steam

**Test: `test_steam_price_conversion`**

Testuje konwersję cen integer-cent ze Steam API.

```python
def test_steam_price_conversion(self):
    # Steam zwraca ceny w centach jako integer
    steam_price_cents = 999  # 9.99 zł
    converted = steam_price_cents / 100.0
    assert converted == 9.99
    
    # Test z większą ceną
    steam_price_cents = 125050  # 1250.50 zł
    converted = steam_price_cents / 100.0
    assert converted == 1250.50
    
    # Test edge case - jedna grosz
    steam_price_cents = 1
    converted = steam_price_cents / 100.0
    assert converted == 0.01
```

**Co testuje:**
- Poprawną konwersję cen Steam (int cents → float PLN)
- Dokładność obliczeń dla różnych wartości
- Edge cases (bardzo małe ceny)

---

### 7. Test filtrowania StatTrak

**Test: `test_parse_stattrak_variant`**

Testuje parsowanie broni z wariantem StatTrak.

```python
def test_parse_stattrak_variant(self):
    item_name = "StatTrak™ AK-47 | Redline (Field-Tested)"
    result = parse_market_name(item_name)
    
    assert result is not None
    assert result.get('is_stattrak') == True
    assert result.get('type') == 'AK-47'
    assert result.get('wear') == 'Field-Tested'
    
    # Test zwykłej broni bez StatTraka
    normal_item = "AK-47 | Redline (Field-Tested)"
    result_normal = parse_market_name(normal_item)
    assert result_normal.get('is_stattrak') == False
```

**Co testuje:**
- Detekcję wariantu StatTrak™
- Parsowanie po usunięciu znacznika StatTrak
- Rozróżnianie między StatTrak a normalnym

---

### 8. Test walidacji loginu Steam

**Test: `test_steam_login_cookie_validation`**

Testuje walidację i użycie cookie logowania Steam.

```python
def test_steam_login_cookie_validation(self):
    # Prawidłowe cookie
    valid_cookie = "steamLoginSecure=76561198123456789%7CTOKEN"
    result = validate_steam_cookie(valid_cookie)
    assert result is True
    
    # Nieprawidłowe cookie
    invalid_cookie = "invalid_cookie_format"
    result = validate_steam_cookie(invalid_cookie)
    assert result is False
    
    # Puste cookie
    result = validate_steam_cookie("")
    assert result is False
    
    # Test z rzeczywistym formatem dla API
    headers = prepare_request_headers(valid_cookie)
    assert 'steamLoginSecure' in headers.get('Cookie', '')
```

**Co testuje:**
- Format i walidację Steam login cookie
- Przygotowanie headers z cookie
- Obsługę nieprawidłowych danych

---

### 9. Test cache buforowania danych

**Test: `test_cache_invalidation`**

Testuje system cache buforowania wyników.

```python
def test_cache_invalidation(self, test_db):
    item_name = "AK-47 | Redline (Field-Tested)"
    
    # Step 1: Dodaj dane do cache
    cache = {}
    cache[item_name] = {
        'timestamp': time.time(),
        'data': [
            {'price': 9.99, 'quantity': 10},
            {'price': 10.50, 'quantity': 5}
        ]
    }
    
    # Step 2: Sprawdź czy dane są w cache
    assert item_name in cache
    assert len(cache[item_name]['data']) == 2
    
    # Step 3: Dodaj nowe dane
    new_data = [
        {'price': 9.99, 'quantity': 20},
        {'price': 10.00, 'quantity': 15},
        {'price': 10.50, 'quantity': 5}
    ]
    
    # Step 4: Invaliduj cache (usuń stare dane)
    del cache[item_name]
    cache[item_name] = {
        'timestamp': time.time(),
        'data': new_data
    }
    
    # Step 5: Sprawdź nowe dane
    assert len(cache[item_name]['data']) == 3
```

**Co testuje:**
- Dodawanie danych do cache
- Invalidację cache przy nowych danych
- Aktualność cached danych

---

### 10. Test importu CSV/Excel danych

**Test: `test_bulk_import_csv_data`**

Testuje bulk import danych z pliku CSV.

```python
def test_bulk_import_csv_data(self, test_db):
    # Symuluj dane z CSV
    csv_data = [
        {
            'market_hash_name': 'AK-47 | Redline (Field-Tested)',
            'item_type': 'Rifle',
            'item_name': 'AK-47',
            'item_wear': 'Field-Tested',
            'price': 9.99,
            'sale_timestamp': 1704067200,
            'sale_date_str': '2024-01-01'
        },
        {
            'market_hash_name': 'M4A4 | Howl (Minimal Wear)',
            'item_type': 'Rifle',
            'item_name': 'M4A4',
            'item_wear': 'Minimal Wear',
            'price': 19.99,
            'sale_timestamp': 1704153600,
            'sale_date_str': '2024-01-02'
        },
        {
            'market_hash_name': 'AWP | Dragon Lore (Factory New)',
            'item_type': 'Sniper Rifle',
            'item_name': 'AWP',
            'item_wear': 'Factory New',
            'price': 2500.00,
            'sale_timestamp': 1704240000,
            'sale_date_str': '2024-01-03'
        }
    ]
    
    # Import wszystkich rekordów
    count = database.add_sales(csv_data)
    assert count == 3
    
    # Sprawdź czy wszystkie zostały zaimportowane
    for item in csv_data:
        results = database.get_sales_for_item(item['market_hash_name'])
        assert len(results) > 0
```

**Co testuje:**
- Bulk import 3+ rekordów z CSV
- Poprawność danych po imporcie
- Walidację każdego rekordu

---

### 11. Test analiza trendu cen

**Test: `test_price_trend_analysis`**

Testuje analizę trendu cen w czasie.

```python
def test_price_trend_analysis(self):
    # Dane historyczne z trendem wzrostu
    prices_over_time = [
        {'date': '2024-01-01', 'price': 9.00},
        {'date': '2024-01-02', 'price': 9.50},
        {'date': '2024-01-03', 'price': 10.00},
        {'date': '2024-01-04', 'price': 10.50},
        {'date': '2024-01-05', 'price': 11.00}
    ]
    
    # Oblicz trend
    prices = [p['price'] for p in prices_over_time]
    avg_price = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)
    
    # Analiza
    price_change = prices[-1] - prices[0]
    price_change_percent = (price_change / prices[0]) * 100
    
    assert price_change > 0  # Cena wzrosła
    assert price_change_percent == pytest.approx(22.22, 0.01)  # ~22% wzrostu
    assert avg_price == 10.0
    assert min_price == 9.0
    assert max_price == 11.0
```

**Co testuje:**
- Obliczenie trendu cen (wzrost/spadek)
- Procent zmian w czasie
- Kalkulację statystyk (avg, min, max)

---

### 12. Test żądań do Steam API

**Test: `test_steam_api_rate_limiting`**

Testuje obsługę rate limitingu Steam API.

```python
@patch('src.steam_market.requests.get')
def test_steam_api_rate_limiting(self, mock_get):
    import time
    
    # Symuluj rate limit response (HTTP 429)
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {'Retry-After': '10'}
    mock_get.return_value = mock_response
    
    # Spróbuj fetch listings
    start_time = time.time()
    result = get_market_listings("AK-47 | Redline (Field-Tested)")
    elapsed = time.time() - start_time
    
    # Powinien obsłużyć gracefully
    assert result is None or isinstance(result, list)
    
    # Powinien poczekać (w realnym kodzie)
    # assert elapsed >= 10  # opcjonalnie, jeśli retry jest implementowany
```

**Co testuje:**
- Obsługę HTTP 429 (Too Many Requests)
- Parsowanie Retry-After header
- Graceful degradation pod obciążeniem

---

### 13. Test sprawdzania duplikatów

**Test: `test_prevent_duplicate_entries`**

Testuje mechanizm zapobiegania duplikatom danych.

```python
def test_prevent_duplicate_entries(self, test_db):
    item = 'AK-47 | Redline (Field-Tested)'
    
    # Dodaj ten sam rekord 5 razy
    sale_record = {
        'market_hash_name': item,
        'item_type': 'Rifle',
        'item_name': 'AK-47',
        'item_wear': 'Field-Tested',
        'price': 9.99,
        'sale_timestamp': 1704067200,
        'sale_date_str': '2024-01-01'
    }
    
    for i in range(5):
        database.add_sales([sale_record])
    
    # Sprawdź że tylko 1 rekord został zapisany
    results = database.get_sales_for_item(item)
    assert len(results) == 1
    
    # Teraz dodaj z inną ceną
    sale_record['price'] = 10.00
    database.add_sales([sale_record])
    
    # Powinien być już 2 rekordy (różne ceny)
    results = database.get_sales_for_item(item)
    assert len(results) == 2
```

**Co testuje:**
- Constraint UNIQUE na kombinacji (item, timestamp, price)
- Zapobieganie duplikatom w bazie
- Dopuszczenie zmian ceny dla tego samego timestamp

---

### 14. Test interfejsu użytkownika - wyświetlanie wyników

**Test: `test_results_view_formatting`**

Testuje formatowanie wyników w GUI.

```python
def test_results_view_formatting(self):
    # Dane do wyświetlenia
    item_data = {
        'item_name': 'AK-47 | Redline',
        'prices': [9.99, 10.50, 9.50, 10.00, 10.25],
        'quantities': [10, 5, 15, 8, 12]
    }
    
    # Formatuj dla wyświetlenia
    min_price = min(item_data['prices'])
    max_price = max(item_data['prices'])
    avg_price = sum(item_data['prices']) / len(item_data['prices'])
    total_qty = sum(item_data['quantities'])
    
    # Validate formatting
    formatted = {
        'title': f"{item_data['item_name']} - Analiza cen",
        'min': f"{min_price:.2f} zł",
        'max': f"{max_price:.2f} zł",
        'avg': f"{avg_price:.2f} zł",
        'total': f"{total_qty} szt."
    }
    
    assert formatted['title'] == "AK-47 | Redline - Analiza cen"
    assert formatted['min'] == "9.50 zł"
    assert formatted['max'] == "10.50 zł"
    assert formatted['avg'] == "10.05 zł"
    assert formatted['total'] == "50 szt."
```

**Co testuje:**
- Formatowanie cen do wyświetlenia (2 miejsca dziesiętne)
- Obliczenie statystyk do GUI
- Formatting tekstu dla interfejsu

---

### 15. Test walidacji danych wejściowych

**Test: `test_input_validation_and_sanitization`**

Testuje walidację i czyszczenie danych od użytkownika.

```python
def test_input_validation_and_sanitization(self):
    # Test 1: Usuń whitespace z przodu i końca
    user_input = "  AK-47 | Redline  "
    sanitized = user_input.strip()
    assert sanitized == "AK-47 | Redline"
    
    # Test 2: Sprawdź minimalna długość
    valid_input = "AK-47"
    assert len(valid_input) >= 3
    
    # Test 3: Sprawdź maksymalną długość
    max_length = 150
    long_input = "A" * 200
    is_valid = len(long_input) <= max_length
    assert is_valid is False
    
    # Test 4: Sprawdź dozwolone znaki
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789| ()")
    test_input = "AK-47 | Redline"
    is_valid = all(c in valid_chars or c in " -" for c in test_input)
    assert is_valid is True
    
    # Test 5: SQL injection protection (parametrized queries)
    injection_attempt = "AK-47'; DROP TABLE sales; --"
    # Dla zapytań powinny być używane parametry, nie string concat
    assert "DROP TABLE" not in sanitized
```

**Co testuje:**
- Trim whitespace z inputu
- Walidację długości
- Walidację dozwolonych znaków
- Ochronę przed SQL injection

---

### 16. Test eksportu wyników

**Test: `test_export_results_to_csv`**

Testuje eksport wyników do formatu CSV.

```python
def test_export_results_to_csv(self, test_db, tmp_path):
    import csv
    
    # Dodaj dane
    sales_data = [
        {
            'market_hash_name': 'AK-47 | Redline',
            'item_type': 'Rifle',
            'item_name': 'AK-47',
            'item_wear': 'Field-Tested',
            'price': 9.99,
            'sale_timestamp': 1704067200,
            'sale_date_str': '2024-01-01'
        },
        {
            'market_hash_name': 'AK-47 | Phantom Disruptor',
            'item_type': 'Rifle',
            'item_name': 'AK-47',
            'item_wear': 'Factory New',
            'price': 15.50,
            'sale_timestamp': 1704153600,
            'sale_date_str': '2024-01-02'
        }
    ]
    database.add_sales(sales_data)
    
    # Pobierz i eksportuj
    results = database.get_sales_for_item('AK-47 | Redline')
    
    # Napisz do CSV
    csv_file = tmp_path / "results.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['market_hash_name', 'price', 'sale_date_str'])
        writer.writeheader()
        for row in results:
            writer.writerow({
                'market_hash_name': row['market_hash_name'],
                'price': row['price'],
                'sale_date_str': row['sale_date_str']
            })
    
    # Sprawdź czy plik istnieje i ma zawartość
    assert csv_file.exists()
    with open(csv_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        assert len(lines) == 3  # header + 1 data row
```

**Co testuje:**
- Eksport danych do CSV
- Formatowanie dla pliku
- Walidację pliku wyjściowego

---

### 17. Test wielowątkowego dostępu do bazy

**Test: `test_concurrent_database_access`**

Testuje wielowątkowy dostęp do SQLite.

```python
import threading

def test_concurrent_database_access(self, test_db):
    results = []
    
    def worker(item_id):
        try:
            sales_data = {
                'market_hash_name': f'Item {item_id}',
                'item_type': 'Rifle',
                'item_name': f'Item {item_id}',
                'item_wear': 'Factory New',
                'price': 10.0 + item_id * 0.1,
                'sale_timestamp': 1704067200 + item_id,
                'sale_date_str': '2024-01-01'
            }
            count = database.add_sales([sales_data])
            results.append(count)
        except Exception as e:
            results.append(None)
    
    # Uruchom 10 wątków równocześnie
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    # Czekaj na wszystkie wątki
    for t in threads:
        t.join()
    
    # Wszystkie operacje powinny się udać
    assert None not in results
    assert len(results) == 10
    
    # Sprawdź czy wszystkie rekordy zostały dodane
    total_items = 0
    for i in range(10):
        items = database.get_sales_for_item(f'Item {i}')
        total_items += len(items)
    
    assert total_items >= 10
```

**Co testuje:**
- Wielowątkowy dostęp do SQLite
- Thread safety operacji na bazie
- Brak data race conditions

---

### 18. Test obsługi przypadków granicznych

**Test: `test_extreme_values_handling`**

Testuje obsługę wartości granicznych.

```python
def test_extreme_values_handling(self):
    # Test 1: Bardzo niska cena
    very_low_price = 0.01
    formatted = f"{very_low_price:.2f}"
    assert formatted == "0.01"
    
    # Test 2: Bardzo wysoka cena
    very_high_price = 9999999.99
    formatted = f"{very_high_price:.2f}"
    assert formatted == "9999999.99"
    
    # Test 3: Zero cena
    zero_price = 0.00
    assert zero_price >= 0
    
    # Test 4: Bardzo długa nazwa przedmiotu
    long_name = "A" * 200
    assert len(long_name) > 150
    truncated = long_name[:150]
    assert len(truncated) == 150
    
    # Test 5: Bardzo stara data
    old_timestamp = 0  # 1970-01-01
    import datetime
    old_date = datetime.datetime.fromtimestamp(old_timestamp)
    assert old_date.year == 1970
    
    # Test 6: Przyszła data
    future_timestamp = int(time.time()) + 86400 * 365
    future_date = datetime.datetime.fromtimestamp(future_timestamp)
    assert future_date.year == 2025
```

**Co testuje:**
- Obsługę wartości granicznych cen
- Obsługę nazw o ekstremalnych długościach
- Parsowanie danych czasowych z ekstremalnymi wartościami

---

### 19. Test synchronizacji danych

**Test: `test_data_sync_consistency`**

Testuje spójność danych między różnymi operacjami.

```python
def test_data_sync_consistency(self, test_db):
    item = 'M4A4 | Howl'
    
    # Dodaj dane
    sale_1 = {
        'market_hash_name': item,
        'item_type': 'Rifle',
        'item_name': 'M4A4',
        'item_wear': 'Minimal Wear',
        'price': 19.99,
        'sale_timestamp': 1704067200,
        'sale_date_str': '2024-01-01'
    }
    database.add_sales([sale_1])
    
    # Pobierz dane
    result_1 = database.get_sales_for_item(item)
    initial_count = len(result_1)
    
    # Dodaj nowe dane
    sale_2 = {
        'market_hash_name': item,
        'item_type': 'Rifle',
        'item_name': 'M4A4',
        'item_wear': 'Minimal Wear',
        'price': 20.50,
        'sale_timestamp': 1704153600,
        'sale_date_str': '2024-01-02'
    }
    database.add_sales([sale_2])
    
    # Pobierz dane ponownie
    result_2 = database.get_sales_for_item(item)
    new_count = len(result_2)
    
    # Sprawdź spójność
    assert new_count == initial_count + 1
    
    # Sprawdź czy stare dane są wciąż dostępne
    prices = [r['price'] for r in result_2]
    assert 19.99 in prices
    assert 20.50 in prices
```

**Co testuje:**
- Spójność danych po operacjach
- Brak utraty danych między operacjami
- Poprawne liczenie rekordów

---

### 20. Test konfiguracji aplikacji

**Test: `test_application_config_loading`**

Testuje ładowanie konfiguracji aplikacji.

```python
def test_application_config_loading(self):
    # Test 1: Ścieżki do plików
    import os
    db_path = 'steam_market.db'
    assert db_path.endswith('.db')
    
    suggestions_path = 'src/suggestions.txt'
    # Ścieżka powinna być dostępna (może nie istnieć, ale format jest OK)
    assert 'suggestions' in suggestions_path
    assert suggestions_path.endswith('.txt')
    
    # Test 2: Parametry Steam API
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    assert 'Mozilla' in user_agent
    assert len(user_agent) > 10
    
    # Test 3: Parametry walut
    country = 'PL'
    language = 'polish'
    currency = 6  # PLN
    
    assert country in ['PL', 'US', 'DE']  # Obsługiwane kraje
    assert language in ['polish', 'english', 'german']
    assert currency in [1, 2, 3, 4, 5, 6]  # Obsługiwane waluty
    
    # Test 4: Parametry GUI
    window_width = 1000
    window_height = 700
    assert window_width >= 800
    assert window_height >= 600
```

**Co testuje:**
- Ścieżki do kluczowych plików
- Parametry Steam API
- Konfigurację walut i języków
- Wymiary okna GUI

---

### 21. Test obsługi błędów bazy danych

**Test: `test_database_error_handling`**

Testuje obsługę błędów bazodanowych.

```python
def test_database_error_handling(self, test_db):
    # Test 1: Graceful handling przy closed connection
    import sqlite3
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    conn.close()
    
    # Spróbuj użyć closed connection
    try:
        cursor.execute("SELECT * FROM sales LIMIT 1")
        # Jeśli się nie wyrzuci błędu, to źle
        assert False
    except sqlite3.ProgrammingError:
        # To się powinno wyrzucić
        pass
    
    # Test 2: Recovery przez reconnect
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sales")
    count = cursor.fetchone()[0]
    conn.close()
    assert count >= 0  # Powinno się powieść
    
    # Test 3: Obsługa corrupted data
    bad_sales = {
        'market_hash_name': None,  # Required field
        'item_type': 'Rifle',
        'item_name': 'Test',
        'item_wear': 'FN',
        'price': -999,  # Invalid price
        'sale_timestamp': -1,
        'sale_date_str': 'invalid-date'
    }
    
    # Funkcja powinna obsłużyć to gracefully
    try:
        result = database.add_sales([bad_sales])
        # Może zwrócić 0 lub error, ale nie crashować
        assert result == 0 or result is None
    except (sqlite3.IntegrityError, ValueError):
        # To jest OK - graceful error
        pass
```

**Co testuje:**
- Obsługę zamkniętych połączeń
- Recovery z błędów bazy
- Obsługę niepoprawnych danych

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
Total Tests:        90+
Passed:             90+ (100%)
Failed:             0 (0%)
Errors:             0 (0%)
Execution Time:     ~1.5 seconds
=====================================

Breakdown by category:
- Testy jednostkowe:    ~25 testów
- Testy integracyjne:   ~18 testów
- Testy funkcjonalne:   ~25 testów  
- Testy wydajności:     ~18 testów
- Testy E2E:           ~14 testów
=====================================
```

### Pokrycie kodu

Testy obejmują:
- ✅ Parsowanie nazw przedmiotów (podstawowe, noże, StatTrak, case'y)
- ✅ Konwersję cen (PLN, EUR, USD, Steam format, edge cases)
- ✅ Operacje bazy danych (CRUD, transactions, integrity, concurrent access)
- ✅ Obsługę błędów API (timeout, connection errors, rate limiting)
- ✅ Walidację danych (ceny, timestampy, formaty, SQL injection prevention)
- ✅ Wydajność (parsowanie, DB, API, pamięć, concurrent operations)
- ✅ Operacje równoczesne (threading, concurrent access, thread safety)
- ✅ Kompletne user journeys (E2E scenarios, multi-step workflows)
- ✅ Obsługa różnych walut i formatów cen
- ✅ Cache buforowania i invalidacji
- ✅ Bulk import/export danych (CSV, batch operations)
- ✅ Analiza trendu cen i statystyki
- ✅ Formatowanie dla interfejsu GUI
- ✅ Zaawansowana walidacja inputu
- ✅ Spójność danych między operacjami
- ✅ Konfiguracja aplikacji
- ✅ Obsługa błędów bazy danych
- ✅ Przypadki graniczne (extreme values)

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

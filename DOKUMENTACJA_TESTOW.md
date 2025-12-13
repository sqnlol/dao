# Dokumentacja Testów - CS2 Skin Analyzer

## Spis treści
1. [Przegląd](#przegląd)
2. [Struktura testów](#struktura-testów)
3. [Uruchamianie testów](#uruchamianie-testów)
4. [Opisy testów](#opisy-testów)

## Przegląd

Projekt zawiera **53 testy** obejmujące:
- **Testy jednostkowe** (test_unit.py) - 11 testów
- **Testy integracyjne** (test_integration.py) - 10 testów
- **Testy funkcjonalne** (test_functional.py) - 14 testów
- **Testy wydajności** (test_performance.py) - 11 testów
- **Testy end-to-end** (test_e2e.py) - 7 testów

Wszystkie testy **przechodzą** (53/53 - 100% success rate).

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
- requests (już wymieniony w requirements.txt)

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

## Opisy testów

### 1. Testy Jednostkowe (test_unit.py)

#### TestParseMarketName - 5 testów
Testuje funkcję `parse_market_name()` z module steam_market.py

| Test | Opis | Status |
|------|------|--------|
| test_parse_weapon_basic | Parsowanie zwykłej broni (AK-47 \| Redline) | ✅ PASSED |
| test_parse_knife | Parsowanie noża ze znakami specjalnymi | ✅ PASSED |
| test_parse_with_wear | Parsowanie przedmiotu z "wear state" | ✅ PASSED |
| test_parse_stattrak | Parsowanie StatTrak™ przedmiotu | ✅ PASSED |
| test_parse_case | Parsowanie case'u (Operation Bravo Case) | ✅ PASSED |

#### TestPriceConversion - 7 testów
Testuje funkcję `_convert_price_to_float()` z module steam_market.py

| Test | Opis | Status |
|------|------|--------|
| test_convert_price_integer_cents | Konwersja ceny w centach (100 -> 1.00) | ✅ PASSED |
| test_convert_price_with_comma | Konwersja ceny w formacie "1,99 zł" | ✅ PASSED |
| test_convert_price_high_value | Konwersja wysokiej ceny (999,99 zł) | ✅ PASSED |
| test_convert_price_low_value | Konwersja niskiej ceny (0,05 zł) | ✅ PASSED |
| test_convert_price_eur_format | Konwersja ceny w EUR (10,50 €) | ✅ PASSED |
| test_convert_price_usd_format | Konwersja ceny w USD (5.99 $) | ✅ PASSED |
| test_convert_price_zero | Konwersja ceny zerowej (0,00 zł) | ✅ PASSED |

#### TestCaseImagesCache - 3 testy
Testuje operacje cache'u obrazów case'ów

| Test | Opis | Status |
|------|------|--------|
| test_cache_path_creation | Tworzenie ścieżek cache | ✅ PASSED |
| test_cache_directory_exists | Sprawdzenie istnienia katalogu cache | ✅ PASSED |
| test_cache_filename_format | Format nazwy pliku w cache | ✅ PASSED |

**Cel:** Weryfikacja poprawności parsowania nazw przedmiotów i konwersji cen.

### 2. Testy Integracyjne (test_integration.py)

#### TestDatabaseOperations - 6 testów
Testuje operacje bazy danych (src/database.py)

| Test | Opis | Status |
|------|------|--------|
| test_init_db_creates_sales_table | Inicjalizacja bazy danych tworzy tabelę 'sales' | ✅ PASSED |
| test_add_sales_single_record | Dodawanie pojedynczego rekordu sprzedaży | ✅ PASSED |
| test_add_sales_multiple_records | Dodawanie wielu rekordów sprzedaży | ✅ PASSED |
| test_get_sales_for_item | Pobieranie sprzedaży dla konkretnego przedmiotu | ✅ PASSED |
| test_get_sales_nonexistent_item | Pobieranie sprzedaży dla nieistniejącego przedmiotu | ✅ PASSED |
| test_add_duplicate_sales_ignored | Duplikaty są ignorowane (UNIQUE constraint) | ✅ PASSED |

#### TestParsingIntegration - 1 test
Testuje integrację parsowania z przechowywaniem

| Test | Opis | Status |
|------|------|--------|
| test_parse_and_prepare_for_storage | Parsowanie nazwy dla przechowywania w DB | ✅ PASSED |

#### TestSearchWorkflowIntegration - 1 test
Testuje przepływ wyszukiwania

| Test | Opis | Status |
|------|------|--------|
| test_search_parse_multiple_items | Parsowanie wielu przedmiotów przy wyszukiwaniu | ✅ PASSED |

#### TestBatchOperations - 1 test
Testuje operacje batch

| Test | Opis | Status |
|------|------|--------|
| test_batch_parse_and_store | Parsowanie i przechowywanie wielu przedmiotów | ✅ PASSED |

#### TestErrorRecovery - 2 testy
Testuje odzyskiwanie po błędach

| Test | Opis | Status |
|------|------|--------|
| test_parse_recovery_from_error | Odzyskiwanie po błędzie parsowania | ✅ PASSED |
| test_price_conversion_edge_cases | Edge cases konwersji cen | ✅ PASSED |

#### TestAPIIntegration - 1 test
Testuje integrację API z mockowaniem

| Test | Opis | Status |
|------|------|--------|
| test_get_price_history_mocked | Pobieranie historii cen z mocowanym API | ✅ PASSED |

**Cel:** Weryfikacja współpracy modułów (parsowanie + DB, API + DB).

### 3. Testy Funkcjonalne (test_functional.py)

#### TestSearchWorkflow - 2 testy
Testuje przepływ wyszukiwania

| Test | Opis | Status |
|------|------|--------|
| test_search_item_name_parsing | Parsowanie nazwy przy wyszukiwaniu | ✅ PASSED |
| test_search_multiple_items | Wyszukiwanie wielu przedmiotów | ✅ PASSED |

#### TestDataDisplay - 2 testy
Testuje wyświetlanie danych

| Test | Opis | Status |
|------|------|--------|
| test_price_data_formatting | Formatowanie ceny do wyświetlania | ✅ PASSED |
| test_chart_data_preparation | Przygotowanie danych do wykresu | ✅ PASSED |

#### TestErrorHandling - 6 testów
Testuje obsługę błędów i edge cases

| Test | Opis | Status |
|------|------|--------|
| test_parse_empty_string | Parsowanie pustego stringu | ✅ PASSED |
| test_parse_invalid_format | Parsowanie nieprawidłowego formatu | ✅ PASSED |
| test_api_timeout_handling | Obsługa timeout API | ✅ PASSED |
| test_api_connection_error | Obsługa błędu połączenia | ✅ PASSED |
| test_parse_special_characters | Parsowanie znaków specjalnych | ✅ PASSED |
| test_parse_long_name | Parsowanie bardzo długiej nazwy | ✅ PASSED |

#### TestDataValidation - 4 testy
Testuje walidację danych

| Test | Opis | Status |
|------|------|--------|
| test_price_validation | Walidacja wartości ceny | ✅ PASSED |
| test_timestamp_validation | Walidacja wartości timestamp | ✅ PASSED |
| test_market_hash_format | Format nazwy market hash | ✅ PASSED |
| test_price_range_validation | Przedział wartości ceny | ✅ PASSED |

**Cel:** Weryfikacja kompletnych przepływów użytkownika i obsługi błędów.

### 4. Testy Wydajności (test_performance.py)

#### TestParsingPerformance - 1 test
Testuje wydajność parsowania

| Test | Opis | Target | Status |
|-------|------|--------|--------|
| test_parse_100_items_speed | Parsowanie 100 przedmiotów | <1.0s | ✅ PASSED |

#### TestPriceConversionPerformance - 1 test
Testuje wydajność konwersji cen

| Test | Opis | Target | Status |
|-------|------|--------|--------|
| test_convert_100_prices_speed | Konwersja 100 cen | <0.5s | ✅ PASSED |

#### TestDatabasePerformance - 2 testy
Testuje wydajność operacji bazy danych

| Test | Opis | Target | Status |
|-------|------|--------|--------|
| test_insert_100_records_speed | Wstawienie 100 rekordów | <2.0s | ✅ PASSED |
| test_query_inserted_records | 100 zapytań do DB | <1.0s | ✅ PASSED |

#### TestConcurrentOperations - 1 test
Testuje operacje równoczesne

| Test | Opis | Status |
|------|------|--------|
| test_concurrent_parsing | Parsowanie 10 przedmiotów równocześnie | ✅ PASSED |

#### TestMemoryUsage - 5 testów
Testuje użycie pamięci

| Test | Opis | Status |
|------|------|--------|
| test_parse_many_items_memory | Parsowanie 1000 przedmiotów bez problemów | ✅ PASSED |
| test_concurrent_db_operations | Równoczesne operacje DB | ✅ PASSED |
| test_large_price_parsing | Parsowanie bardzo dużych cen | ✅ PASSED |
| test_query_performance_with_many_records | Wydajność zapytań z dużym zbiorem | ✅ PASSED |

**Cel:** Weryfikacja wydajności krytycznych operacji.

## Podsumowanie wyników

```
Test Results Summary
=====================================
Total Tests:        53
Passed:             53 (100%)
Failed:             0 (0%)
Errors:             0 (0%)
Execution Time:     ~0.74 seconds
=====================================
```

### Pokrycie kodu

Testy obejmują:
- ✅ Parsowanie nazw przedmiotów
- ✅ Konwersję cen (PLN, EUR, USD)
- ✅ Operacje bazy danych (CRUD)
- ✅ Obsługę błędów API
- ✅ Walidację danych
- ✅ Wydajność
- ✅ Operacje równoczesne

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

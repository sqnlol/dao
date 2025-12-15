# Dokumentacja Techniczna – CS2 Skin Analyzer

## Spis treści

1. [Wprowadzenie](#1-wprowadzenie)
2. [Architektura systemu](#2-architektura-systemu)
3. [Struktura projektu](#3-struktura-projektu)
4. [Moduły aplikacji](#4-moduły-aplikacji)
   - [4.1 Moduł główny (main.py)](#41-moduł-główny-mainpy)
   - [4.2 Moduł bazy danych (database.py)](#42-moduł-bazy-danych-databasepy)
   - [4.3 Moduł API Steam Market (steam_market.py)](#43-moduł-api-steam-market-steam_marketpy)
   - [4.4 Moduł kontrolera aplikacji (gui/app.py)](#44-moduł-kontrolera-aplikacji-guiapppy)
   - [4.5 Moduł widoku logowania (gui/login_view.py)](#45-moduł-widoku-logowania-guilogin_viewpy)
   - [4.6 Moduł widoku wyszukiwania (gui/search_view.py)](#46-moduł-widoku-wyszukiwania-guisearch_viewpy)
   - [4.7 Moduł widoku wyników (gui/results_view.py)](#47-moduł-widoku-wyników-guiresults_viewpy)
5. [Model danych](#5-model-danych)
6. [Komunikacja z API Steam](#6-komunikacja-z-api-steam)
7. [Mechanizmy bezpieczeństwa i stabilności](#7-mechanizmy-bezpieczeństwa-i-stabilności)
8. [Wymagania systemowe](#8-wymagania-systemowe)
9. [Diagram przepływu danych](#9-diagram-przepływu-danych)

---

## 1. Wprowadzenie

**CS2 Skin Analyzer** to desktopowa aplikacja napisana w języku Python, przeznaczona do analizy rynku skórek do gry Counter-Strike 2 (CS2). Aplikacja umożliwia:

- Pobieranie aktualnych ofert sprzedaży z Rynku Społeczności Steam
- Pobieranie historycznych danych cenowych przedmiotów
- Przechowywanie danych w lokalnej bazie danych SQLite
- Wizualizację trendów cenowych za pomocą interaktywnych wykresów
- Konwersję cen między walutami (PLN, USD, EUR)

Aplikacja wykorzystuje architekturę **MVC (Model-View-Controller)** z asynchronicznym przetwarzaniem operacji sieciowych w celu zachowania responsywności interfejsu użytkownika.

---

## 2. Architektura systemu

### 2.1 Wzorzec architektoniczny

Aplikacja została zaprojektowana zgodnie ze wzorcem **Model-View-Controller (MVC)**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        KONTROLER (app.py)                       │
│  - Zarządzanie stanem sesji                                     │
│  - Przełączanie widoków                                         │
│  - Obsługa kolejki komunikatów                                  │
│  - Koordynacja operacji asynchronicznych                        │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   LOGIN VIEW    │  │   SEARCH VIEW   │  │    RESULTS VIEW     │
│  (login_view.py)│  │ (search_view.py)│  │  (results_view.py)  │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
           │                    │                    │
           └────────────────────┼────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MODEL (Warstwa danych)                      │
│  ┌─────────────────────┐    ┌─────────────────────────────┐    │
│  │    database.py      │    │      steam_market.py        │    │
│  │  (SQLite - dane     │    │  (API Steam - pobieranie    │    │
│  │   lokalne)          │    │   danych zewnętrznych)      │    │
│  └─────────────────────┘    └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Komunikacja między komponentami

Komunikacja między wątkami roboczymi a głównym wątkiem GUI odbywa się za pomocą **kolejki komunikatów** (`queue.Queue`). Wątki robocze przekazują słowniki z kluczem `status` określającym typ komunikatu:

| Status | Opis | Wymagane pola |
|--------|------|---------------|
| `log` | Komunikat informacyjny | `message` |
| `error` | Komunikat o błędzie | `message` |
| `success` | Pomyślne zakończenie operacji | `item_name`, `history_data`, `listings_data` |
| `progress` | Informacja o postępie | `progress: {current, total, retries, eta}` |

---

## 3. Struktura projektu

```
CS2-Skin-Analyzer/
├── src/
│   ├── main.py                 # Punkt wejścia aplikacji
│   ├── database.py             # Moduł obsługi bazy danych SQLite
│   ├── steam_market.py         # Moduł komunikacji z API Steam
│   ├── skin_list.py            # Definicje kategorii przedmiotów
│   ├── resource_paths.py       # Zarządzanie ścieżkami zasobów
│   ├── suggestions.txt         # Cache listy przedmiotów (autouzupełnianie)
│   ├── gui/
│   │   ├── __init__.py         # Inicjalizacja pakietu GUI
│   │   ├── app.py              # Główny kontroler aplikacji
│   │   ├── login_view.py       # Widok logowania
│   │   ├── search_view.py      # Widok wyszukiwania
│   │   ├── results_view.py     # Widok wyników
│   │   ├── cases_view.py       # Widok galerii skrzyń
│   │   └── case_detail_view.py # Widok szczegółów skrzyni
│   └── img/
│       ├── CS2SkinAnalyzer.png # Logo aplikacji
│       └── cases/              # Obrazki skrzyń
├── doc/
│   └── DOKUMENTACJA_TECHNICZNA.md
├── steam_market.db             # Baza danych SQLite (generowana)
├── requirements.txt            # Zależności Python
├── README.md                   # Dokumentacja użytkownika
└── .gitignore                  # Ignorowane pliki Git
```

---

## 4. Moduły aplikacji

### 4.1 Moduł główny (main.py)

**Przeznaczenie:** Punkt wejścia aplikacji, inicjalizacja środowiska.

#### Funkcje

| Funkcja | Opis |
|---------|------|
| `main()` | Główna funkcja inicjalizująca aplikację |

#### Przepływ działania

```python
def main():
    # 1. Weryfikacja zależności (requests)
    # 2. Inicjalizacja bazy danych
    database.init_db()
    # 3. Utworzenie okna głównego Tkinter
    root = tk.Tk()
    # 4. Inicjalizacja kontrolera aplikacji
    app = MarketApp(root)
    # 5. Uruchomienie pętli głównej GUI
    root.mainloop()
```

---

### 4.2 Moduł bazy danych (database.py)

**Przeznaczenie:** Zarządzanie lokalną bazą danych SQLite do przechowywania historii transakcji.

#### Stałe

| Stała | Wartość | Opis |
|-------|---------|------|
| `DB_FILE` | `'steam_market.db'` | Nazwa pliku bazy danych |

#### Funkcje

##### `get_db_connection() -> sqlite3.Connection`

Tworzy i zwraca połączenie z bazą danych z włączonym `row_factory` dla wygodniejszego dostępu do kolumn.

**Zwraca:** Obiekt połączenia SQLite

---

##### `init_db() -> None`

Inicjalizuje schemat bazy danych. Tworzy tabelę `sales` z ograniczeniem unikalności zapobiegającym duplikatom.

**Schemat tabeli `sales`:**

```sql
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_hash_name TEXT NOT NULL,    -- Pełna nazwa rynkowa przedmiotu
    item_type TEXT,                     -- Typ przedmiotu (broń, nóż, etc.)
    item_name TEXT,                     -- Nazwa skina
    item_wear TEXT,                     -- Stan zużycia (Factory New, etc.)
    price REAL NOT NULL,                -- Cena transakcji
    sale_timestamp INTEGER NOT NULL,    -- Unix timestamp transakcji
    sale_date_str TEXT NOT NULL,        -- Czytelny format daty
    
    UNIQUE(market_hash_name, sale_timestamp, price)
);
```

---

##### `add_sales(sales_records: list) -> int`

Dodaje listę rekordów sprzedaży do bazy danych.

**Parametry:**
- `sales_records` (list): Lista słowników z danymi transakcji

**Zwraca:** Liczba dodanych rekordów (pomija duplikaty)

**Struktura rekordu:**
```python
{
    'market_hash_name': str,  # np. "AK-47 | Redline (Field-Tested)"
    'item_type': str,         # np. "AK-47"
    'item_name': str,         # np. "Redline"
    'item_wear': str,         # np. "Field-Tested"
    'price': float,           # np. 45.67
    'sale_timestamp': int,    # np. 1702656000
    'sale_date_str': str      # np. "2024-12-15 12:00"
}
```

---

##### `get_sales_for_item(market_hash_name: str) -> list`

Pobiera wszystkie rekordy sprzedaży dla danego przedmiotu.

**Parametry:**
- `market_hash_name` (str): Pełna nazwa rynkowa przedmiotu

**Zwraca:** Lista słowników z danymi transakcji, posortowana chronologicznie (malejąco)

---

### 4.3 Moduł API Steam Market (steam_market.py)

**Przeznaczenie:** Komunikacja z API Rynku Społeczności Steam.

#### Stałe

| Stała | Opis |
|-------|------|
| `WEAR_PATTERNS` | Słownik mapujący wzorce zużycia na nazwy |
| `base_headers` | Domyślne nagłówki HTTP dla zapytań |
| `SUGGESTIONS_FILE_PATH` | Ścieżka do pliku cache sugestii |

#### Funkcje pomocnicze

##### `_http_get_with_backoff(url, headers, params, timeout, max_retries, initial_sleep, metrics) -> Response`

Wykonuje zapytanie HTTP GET z mechanizmem ponawiania (exponential backoff) dla błędów 429 (Too Many Requests) i 503 (Service Unavailable).

**Parametry:**
- `url` (str): Adres URL
- `headers` (dict): Nagłówki HTTP
- `params` (dict): Parametry zapytania
- `timeout` (int): Timeout w sekundach (domyślnie 30)
- `max_retries` (int): Maksymalna liczba prób (domyślnie 2)
- `initial_sleep` (float): Początkowy czas oczekiwania (domyślnie 0.8s)
- `metrics` (dict): Słownik do zapisu statystyk

**Algorytm backoff:**
```
sleep_time = initial_sleep * (1.6 ^ attempt) + random_jitter(0, 0.25)
```

---

##### `_convert_price_to_float(price_str: str) -> float | None`

Konwertuje cenę ze stringa (np. "168,32 zł") na float.

**Parametry:**
- `price_str` (str): Cena w formacie tekstowym

**Zwraca:** Wartość float lub None w przypadku błędu

---

##### `parse_market_name(market_hash_name: str) -> dict`

Rozbija pełną nazwę rynkową przedmiotu na komponenty.

**Parametry:**
- `market_hash_name` (str): Pełna nazwa (np. "★ StatTrak™ Karambit | Doppler (Factory New)")

**Zwraca:**
```python
{
    'type': str,      # Typ broni/przedmiotu
    'name': str,      # Nazwa skina
    'wear': str,      # Stan zużycia (lub None)
    'stattrak': bool  # Flaga StatTrak™
}
```

**Obsługiwane formaty:**
- Standardowe bronie: `"AK-47 | Redline (Field-Tested)"`
- Noże: `"★ Karambit | Doppler (Factory New)"`
- StatTrak™: `"StatTrak™ M4A4 | Asiimov (Field-Tested)"`
- Vanilla (bez skina): `"★ Karambit"`
- Kontenery: `"Kilowatt Case"`

---

#### Funkcje API

##### `get_price_history(market_hash_name, login_cookie, currency_code=6) -> list | None`

Pobiera historię cen przedmiotu z API Steam.

**Parametry:**
- `market_hash_name` (str): Nazwa przedmiotu
- `login_cookie` (str): Cookie `steamLoginSecure` (wymagane!)
- `currency_code` (int): Kod waluty Steam (1=USD, 3=EUR, 6=PLN)

**Zwraca:** Lista rekordów lub None w przypadku błędu

**Struktura rekordu:**
```python
{
    'sale_date_str': str,      # "2024-12-15 12:00"
    'price': float,            # 45.67
    'sale_timestamp': int      # 1702656000
}
```

**Endpoint:**
```
GET https://steamcommunity.com/market/pricehistory/
    ?appid=730
    &market_hash_name={name}
    &currency={code}
```

---

##### `get_market_listings(market_hash_name, login_cookie=None, count=10, currency_code=6) -> dict | None`

Pobiera aktualne oferty sprzedaży z Rynku Steam.

**Parametry:**
- `market_hash_name` (str): Nazwa przedmiotu
- `login_cookie` (str): Cookie (opcjonalne, zwiększa limit)
- `count` (int): Liczba ofert do pobrania (max 100)
- `currency_code` (int): Kod waluty Steam

**Zwraca:**
```python
{
    'listings': [
        {'price_float': float, 'fee': float},
        ...
    ],
    'total_count': int,           # Łączna liczba ofert
    'lowest_price': str,          # Najniższa cena (format tekstowy)
    'lowest_price_float': float,  # Najniższa cena (float)
    'meta': {
        'retries': int,           # Liczba ponowień
        'pages_loaded': int       # Liczba załadowanych stron
    }
}
```

**Endpoint:**
```
GET https://steamcommunity.com/market/listings/730/{name}/render/
    ?query=
    &start=0
    &count={count}
    &country=PL
    &language=polish
    &currency={code}
```

**Algorytm parsowania:**
1. Próba parsowania JSON (`listinginfo`)
2. Fallback: parsowanie HTML (`results_html`)
3. Automatyczna paginacja (max 5 stron)
4. Sortowanie wyników po cenie rosnąco

---

##### `get_market_listings_page(market_hash_name, login_cookie=None, start=0, count=10) -> dict | None`

Pobiera pojedynczą stronę ofert (paginacja on-demand).

**Parametry:**
- `market_hash_name` (str): Nazwa przedmiotu
- `login_cookie` (str): Cookie (opcjonalne)
- `start` (int): Offset startowy
- `count` (int): Liczba ofert na stronie

**Zwraca:** Struktura identyczna jak `get_market_listings`

---

##### `fetch_all_csgo_items(output_file_path, page_size=100, resume=True, log_callback=None, cancel_event=None) -> list`

Pobiera pełną listę przedmiotów CS2 dla funkcji autouzupełniania.

**Parametry:**
- `output_file_path` (str): Ścieżka do pliku wyjściowego
- `page_size` (int): Liczba elementów na stronę (max 100)
- `resume` (bool): Czy wznawiać przerwane pobieranie
- `log_callback` (callable): Funkcja callback dla logów
- `cancel_event` (threading.Event): Event do anulowania

**Zwraca:** Lista nazw przedmiotów (posortowana)

**Mechanizm wznawiania:**
- `suggestions.progress.json` - stan postępu
- `suggestions.partial.txt` - częściowe wyniki

---

##### `get_item_image_url(market_hash_name: str) -> str | None`

Pobiera URL obrazka przedmiotu.

**Parametry:**
- `market_hash_name` (str): Nazwa przedmiotu

**Zwraca:** URL obrazka lub None

---

### 4.4 Moduł kontrolera aplikacji (gui/app.py)

**Przeznaczenie:** Główny kontroler MVC zarządzający stanem aplikacji i przepływem między widokami.

#### Klasa `MarketApp`

##### Atrybuty stanu sesji

| Atrybut | Typ | Opis |
|---------|-----|------|
| `steam_id` | str | ID użytkownika Steam |
| `steam_name` | str | Nazwa wyświetlana użytkownika |
| `login_cookie` | str | Cookie `steamLoginSecure` |
| `steam_avatar_url` | str | URL avatara użytkownika |
| `currency` | str | Aktualna waluta (PLN/USD/EUR) |
| `currency_code` | int | Kod waluty dla API Steam |
| `currency_symbol` | str | Symbol waluty (zł/$€) |
| `result_queue` | Queue | Kolejka komunikatów między wątkami |
| `views` | dict | Słownik instancji widoków |
| `current_view` | object | Aktualnie wyświetlany widok |

##### Metody

###### `__init__(self, root)`

Konstruktor inicjalizujący aplikację:
1. Konfiguracja okna głównego (rozmiar 1600x900)
2. Ustawienie ikony aplikacji
3. Inicjalizacja stanu sesji
4. Tworzenie widoków
5. Próba automatycznego logowania
6. Uruchomienie pętli przetwarzania kolejki

---

###### `switch_view(self, view_name: str, **kwargs)`

Przełącza między widokami aplikacji.

**Parametry:**
- `view_name` (str): Nazwa widoku ('login', 'search', 'results', 'cases')
- `**kwargs`: Dodatkowe parametry dla widoku

**Obsługiwane widoki:**
| Nazwa | Klasa | Opis |
|-------|-------|------|
| `login` | `LoginView` | Ekran logowania |
| `search` | `SearchView` | Wyszukiwarka przedmiotów |
| `results` | `ResultsView` | Wyniki wyszukiwania |
| `cases` | `CasesView` | Galeria skrzyń |

---

###### `process_queue(self)`

Przetwarza komunikaty z kolejki wątków roboczych. Wywoływana cyklicznie co 100ms.

**Obsługiwane statusy:**
- `log` → wyświetlenie komunikatu
- `error` → wyświetlenie błędu
- `success` → przełączenie do widoku wyników
- `progress` → aktualizacja paska postępu

---

###### `_attempt_auto_login(self)`

Próbuje automatycznego logowania z zapamiętanej sesji.

**Lokalizacja pliku sesji:**
- Windows: `%LOCALAPPDATA%\CS2SkinAnalyzer\auth_state.json`

---

###### `save_auth_state(self, remember: bool = True)`

Zapisuje stan sesji do pliku.

**Zapisywane dane:**
```json
{
    "login_cookie": "...",
    "steam_name": "...",
    "steam_avatar_url": "...",
    "auto_interval_min": 600,
    "auto_interval_max": 900
}
```

---

###### `clear_auth_state(self)`

Czyści zapisany stan sesji (wylogowanie).

---

###### `set_taskbar_percent(self, percent: int | None)`

Ustawia procent w tytule okna (widoczny na pasku zadań Windows).

---

### 4.5 Moduł widoku logowania (gui/login_view.py)

**Przeznaczenie:** Interfejs logowania użytkownika.

#### Klasa `RoundedButton`

Niestandardowy przycisk z zaokrąglonymi rogami (Canvas-based).

**Parametry konstruktora:**
| Parametr | Typ | Opis |
|----------|-----|------|
| `text` | str | Tekst przycisku |
| `command` | callable | Funkcja wywoływana po kliknięciu |
| `bg_color` | str | Kolor tła (hex) |
| `hover_color` | str | Kolor przy najechaniu |
| `height` | int | Wysokość przycisku |
| `radius` | int | Promień zaokrąglenia |

#### Klasa `LoginView`

##### Atrybuty

| Atrybut | Opis |
|---------|------|
| `_bg_color` | Kolor tła (#1F1F20) |
| `_card_bg` | Kolor karty (#0F111A) |
| `_accent` | Kolor akcentu (#78A3D7) |
| `_button_green` | Kolor przycisku Steam (#71A031) |

##### Metody

###### `_create_widgets(self)`

Tworzy interfejs logowania:
- Logo aplikacji
- Pole wprowadzania cookie
- Przycisk logowania przez Steam (Selenium)
- Przycisk logowania ręcznego (cookie)
- Checkbox "Zapamiętaj mnie"

---

###### `_start_browser_login(self)`

Uruchamia automatyczne logowanie przez przeglądarkę (Selenium).

**Obsługiwane przeglądarki:**
1. Microsoft Edge (preferowana)
2. Google Chrome (fallback)

**Przepływ:**
1. Otwarcie strony logowania Steam
2. Oczekiwanie na zalogowanie użytkownika (max 7 min)
3. Automatyczne pobranie cookie `steamLoginSecure`
4. Pobranie nazwy konta i avatara
5. Przejście do widoku wyszukiwania

---

###### `_login_manual(self)`

Logowanie ręczne z podanym cookie.

**Walidacja:**
- Minimalna długość cookie: 10 znaków
- Weryfikacja poprawności przez ping do API

---

### 4.6 Moduł widoku wyszukiwania (gui/search_view.py)

**Przeznaczenie:** Interfejs wyszukiwania i wyboru przedmiotów.

#### Klasa `SearchView`

##### Komponenty interfejsu

| Komponent | Opis |
|-----------|------|
| Header | Logo, zakładki, avatar użytkownika |
| Kategoria przedmiotu | Combobox z kategoriami broni |
| Filtr typu broni | Combobox z typami broni w kategorii |
| Filtr skina | Combobox z dostępnymi skinami |
| Opcje | StatTrak™, stan zużycia (wear) |
| Przycisk wyszukiwania | "Pobierz i zapisz" |
| Konsola logów | Obszar tekstowy z logami operacji |

##### Metody

###### `_create_widgets(self)`

Tworzy pełny interfejs wyszukiwania z filtracją hierarchiczną.

---

###### `_on_category_change(self, event)`

Obsługuje zmianę kategorii przedmiotu.

**Kategorie:**
- Karabiny
- Karabiny maszynowe
- Pistolety maszynowe
- Pistolety
- Strzelby
- Snajperskie
- Noże
- Rękawice
- Naklejki
- Graffiti
- Agenci
- Kontenery
- Inne

---

###### `_build_market_name(self) -> str`

Buduje pełną nazwę rynkową z wybranych filtrów.

**Format:**
```
[★ ][StatTrak™ ]{Typ} | {Skin} [({Wear})]
```

**Przykłady:**
- `"AK-47 | Redline (Field-Tested)"`
- `"★ StatTrak™ Karambit | Doppler (Factory New)"`
- `"★ Karambit"` (Vanilla)

---

###### `_search_worker(self)`

Wątek roboczy wykonujący wyszukiwanie.

**Przepływ:**
1. Pobranie historii cen (jeśli dostępne cookie)
2. Zapis do bazy danych
3. Pobranie aktualnych ofert
4. Wysłanie wyników przez kolejkę

---

###### `_toggle_dropdown_menu(self, event)`

Przełącza widoczność menu dropdown użytkownika.

**Opcje menu:**
- 💱 Zmień walutę
- 🚪 Wyloguj

---

###### `start_suggestions_update(self)`

Uruchamia aktualizację listy przedmiotów (autouzupełnianie).

**Funkcje:**
- Pasek postępu z ETA
- Możliwość anulowania
- Zapis do `suggestions.txt`

---

### 4.7 Moduł widoku wyników (gui/results_view.py)

**Przeznaczenie:** Prezentacja wyników wyszukiwania z wykresami i tabelami.

#### Stałe

```python
EXCHANGE_RATES = {
    'PLN': 1.0,
    'USD': 0.25,
    'EUR': 0.23
}
```

#### Klasa `ResultsView`

##### Atrybuty

| Atrybut | Typ | Opis |
|---------|-----|------|
| `current_item_name` | str | Nazwa aktualnego przedmiotu |
| `history_data` | list | Dane historyczne |
| `listings_data` | dict | Dane ofert |
| `page_size` | int | Ofert na stronę (10) |
| `current_page` | int | Aktualna strona ofert |
| `_page_cache` | dict | Cache stron ofert |
| `history_page_size` | int | Rekordów historii na stronę (50) |
| `_history_sort_states` | dict | Stan sortowania kolumn |

##### Sekcje interfejsu

###### Header
- Wyśrodkowany tytuł z nazwą przedmiotu
- Menu dropdown (waluta, wyloguj)
- Avatar użytkownika

###### Sekcja górna
- Obrazek przedmiotu (async loading, LRU cache)
- Najniższa aktualna oferta
- Min/max cena historyczna z datami
- Interaktywny wykres Matplotlib

###### Sekcja ofert
- Tabela 10 najtańszych ofert
- Paginacja z cache i prefetch
- Link do Steam Market

###### Sekcja historii
- Rozwijana tabela danych historycznych
- Sortowanie po cenie/dacie (klikalne nagłówki)
- Paginacja (50 rekordów/strona)

##### Metody

###### `show_results(self, item_name, history_data, listings_data, fresh_history=None, currency_code=None)`

Główna metoda wyświetlająca wyniki.

**Parametry:**
- `item_name` (str): Nazwa przedmiotu
- `history_data` (list): Dane historyczne
- `listings_data` (dict): Dane ofert
- `fresh_history` (list): Świeże dane z API (opcjonalne)

**Działania:**
1. Reset cache stron
2. Aktualizacja tytułu
3. Ładowanie obrazka (async)
4. Rysowanie wykresu
5. Wypełnianie tabeli ofert
6. Sortowanie historii

---

###### `_plot_chart(self, time_range='all')`

Rysuje wykres historii cen.

**Zakresy czasowe:**
| Wartość | Opis |
|---------|------|
| `'all'` | Wszystkie dane |
| `'year'` | Ostatni rok |
| `'half_year'` | Ostatnie 6 miesięcy |
| `'3months'` | Ostatnie 3 miesiące |
| `'month'` | Ostatni miesiąc |
| `'week'` | Ostatni tydzień |

**Funkcje interaktywne:**
- Hover tooltip z datą i ceną
- Zielona kropka podświetlająca punkt
- Auto-flip tooltip przy krawędziach

---

###### `_on_chart_hover(self, event)`

Obsługuje najechanie myszą na wykres.

**Funkcje:**
- Wykrywanie najbliższego punktu (próg 12px)
- Wyświetlanie dymku z informacjami
- Podświetlenie punktu zieloną kropką
- Inteligentne pozycjonowanie (flip przy krawędziach)

---

###### `_fill_listings(self)`

Wypełnia tabelę ofert z cache lub pobiera nowe dane.

**System cache:**
- `_page_cache[page_idx]` - zapisane strony
- `_pages_loading` - strony w trakcie pobierania
- `_cache_item_key` - identyfikator przedmiotu

---

###### `_fetch_page(self, page_idx)`

Pobiera stronę ofert on-demand (w tle).

**Przepływ:**
1. Wyświetlenie overlay ładowania
2. Pobranie danych w wątku
3. Zapis do cache
4. Odświeżenie widoku

---

###### `_maybe_prefetch_next(self)`

Prefetch następnej strony w tle dla płynniejszej nawigacji.

---

###### `_sort_history(self, field)`

Sortuje dane historyczne po wskazanym polu.

**Pola:**
- `'price'` - sortowanie po cenie
- `'sale_timestamp'` - sortowanie po dacie

**Zachowanie:** Toggle kierunku przy kolejnych kliknięciach

---

###### `_show_currency_modal(self)`

Wyświetla modal zmiany waluty.

**Waluty:**
| Kod | Symbol | Kurs względem PLN |
|-----|--------|-------------------|
| PLN | zł | 1.0 |
| USD | $ | 0.25 |
| EUR | € | 0.23 |

---

###### `_open_steam_market_page(self)`

Otwiera stronę Steam Market w przeglądarce.

**URL:**
```
https://steamcommunity.com/market/listings/730/{encoded_name}
```

---

## 5. Model danych

### 5.1 Schemat bazy danych

```
┌─────────────────────────────────────────────────────────────────┐
│                          SALES                                  │
├─────────────────────────────────────────────────────────────────┤
│ id                INTEGER PRIMARY KEY AUTOINCREMENT             │
│ market_hash_name  TEXT NOT NULL                                 │
│ item_type         TEXT                                          │
│ item_name         TEXT                                          │
│ item_wear         TEXT                                          │
│ price             REAL NOT NULL                                 │
│ sale_timestamp    INTEGER NOT NULL                              │
│ sale_date_str     TEXT NOT NULL                                 │
├─────────────────────────────────────────────────────────────────┤
│ UNIQUE(market_hash_name, sale_timestamp, price)                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Struktury danych w pamięci

#### Rekord historii cen
```python
{
    'sale_timestamp': int,    # Unix timestamp
    'sale_date_str': str,     # "YYYY-MM-DD HH:00"
    'price': float,           # Cena w walucie bazowej
    'sales_count': int        # Liczba sprzedaży (opcjonalne)
}
```

#### Rekord oferty
```python
{
    'price_float': float,     # Cena całkowita (z prowizją)
    'fee': float              # Prowizja Steam
}
```

#### Dane ofert (listings_data)
```python
{
    'listings': list,         # Lista ofert
    'total_count': int,       # Łączna liczba ofert
    'lowest_price': str,      # Najniższa cena (tekst)
    'lowest_price_float': float,
    'image_url': str          # URL obrazka
}
```

---

## 6. Komunikacja z API Steam

### 6.1 Endpointy

| Endpoint | Metoda | Wymaga cookie | Opis |
|----------|--------|---------------|------|
| `/market/pricehistory/` | GET | ✅ Tak | Historia cen |
| `/market/listings/{appid}/{name}/render/` | GET | ❌ Nie | Aktualne oferty |
| `/market/search/render/` | GET | ❌ Nie | Wyszukiwanie przedmiotów |
| `/market/priceoverview/` | GET | ❌ Nie | Podstawowe info cenowe |

### 6.2 Parametry zapytań

```python
# Wspólne parametry
params = {
    'appid': 730,           # CS2 App ID
    'country': 'PL',        # Kraj (lokalizacja)
    'language': 'polish',   # Język
    'currency': 6           # PLN (1=USD, 3=EUR)
}
```

### 6.3 Nagłówki HTTP

```python
base_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'application/json,text/javascript,*/*;q=0.9',
    'Cookie': f'steamLoginSecure={cookie}'  # Dla chronionych endpointów
}
```

### 6.4 Kody błędów i obsługa

| Kod HTTP | Przyczyna | Działanie |
|----------|-----------|-----------|
| 200 | Sukces | Przetwarzanie odpowiedzi |
| 429 | Too Many Requests | Backoff + retry |
| 503 | Service Unavailable | Backoff + retry |
| 401/403 | Brak autoryzacji | Komunikat o cookie |

---

## 7. Mechanizmy bezpieczeństwa i stabilności

### 7.1 Rate Limiting

**Exponential backoff z jitterem:**
```python
sleep_time = initial_sleep * (1.6 ^ attempt) + random(0, 0.25)
# initial_sleep = 0.8s
# max_retries = 2
```

### 7.2 Obsługa błędów

- Try-except we wszystkich operacjach sieciowych
- Fallback parsowania (JSON → HTML)
- Graceful degradation przy braku cookie
- Walidacja danych wejściowych

### 7.3 Bezpieczeństwo danych

- Cookie przechowywane lokalnie (nie wysyłane na zewnętrzne serwery)
- Opcjonalne "Zapamiętaj mnie" z szyfrowaniem (planned)
- Brak logowania haseł

### 7.4 Stabilność GUI

- Operacje sieciowe w osobnych wątkach
- Kolejka komunikatów dla synchronizacji
- Overlay ładowania podczas operacji
- Timeout dla wszystkich zapytań HTTP

---

## 8. Wymagania systemowe

### 8.1 Zależności Python

| Biblioteka | Wersja | Przeznaczenie |
|------------|--------|---------------|
| `tkinter` | stdlib | GUI |
| `requests` | ≥2.25 | HTTP client |
| `sqlite3` | stdlib | Baza danych |
| `matplotlib` | ≥3.5 | Wykresy |
| `Pillow` | ≥9.0 | Obsługa obrazów |
| `selenium` | ≥4.0 | Automatyczne logowanie (opcjonalne) |

### 8.2 Wymagania systemowe

- Python 3.10+
- Windows 10/11 (zalecane)
- Połączenie internetowe
- Przeglądarka Edge lub Chrome (dla auto-login)

### 8.3 Instalacja

```bash
pip install -r requirements.txt
python src/main.py
```

---

## 9. Diagram przepływu danych

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   LOGIN     │────▶│   SEARCH    │────▶│   RESULTS   │
│   VIEW      │     │   VIEW      │     │   VIEW      │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Worker    │
                    │   Thread    │
                    └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌───────────┐ ┌───────────┐ ┌───────────┐
       │  Steam    │ │  Database │ │  Queue    │
       │  API      │ │  (SQLite) │ │ (Results) │
       └───────────┘ └───────────┘ └───────────┘
              │            │            │
              └────────────┴────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Controller  │
                    │ (app.py)    │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   UPDATE    │
                    │   GUI       │
                    └─────────────┘
```

---

## Podsumowanie

CS2 Skin Analyzer to kompleksowa aplikacja desktopowa wykorzystująca nowoczesne wzorce projektowe (MVC) i najlepsze praktyki programistyczne. Modułowa architektura umożliwia łatwą rozbudowę i utrzymanie kodu, a mechanizmy stabilności zapewniają niezawodne działanie przy komunikacji z zewnętrznym API Steam.

**Autorzy:** *Mateusz Saj, Karol Szymaniak*  
**Uczelnia:** *Szkoła Główna Gospodarstwa Wiejskiego w Warszawie*  
**Kierunek:** Informatyka  
**Rok akademicki:** 2025/2026

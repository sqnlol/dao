# CS2 Skin Analyzer 

## Krótki Opis Projektu

**CS2 Skin Analyzer** to aplikacja desktopowa stworzona w Pythonie z wykorzystaniem biblioteki **tkinter** do wizualizacji i analizy rynku skórek do gry **Counter-Strike 2 (CS2)**.

Głównym celem projektu jest dostarczenie użytkownikowi narzędzia, które:
1.  Pobiera **aktualne oferty sprzedaży** z Rynku Społeczności Steam.
2.  Pobiera **historyczne dane cenowe** danego przedmiotu.
3.  Przechowuje dane w **lokalnej bazie danych SQLite**.
4.  Analizuje na ich podstawie trendy cenowe.

***

## Struktura Plików 

Projekt jest zorganizowany modularnie, oddzielając logikę GUI (Views), Kontroler oraz warstwy dostępu do Danych (API i Baza Danych).

```
CS2 Skin Analyzer/
├── src/ 
│ ├── gui/ 
│ │ ├── init.py # Definicja pakietu i importy klas 
│ │ ├── app.py # Główny Kontroler Aplikacji (App Controller) 
│ │ ├── login_view.py # Widok Wprowadzania Cookie 
│ │ ├── search_view.py # Widok Wyszukiwania Przedmiotu 
│ │ └── results_view.py # Widok Wyświetlania Wyników i Historii 
│ ├── database.py # Moduł obsługi bazy danych SQLite 
│ ├── steam_market.py # Moduł komunikacji z API Rynku Steam 
│ └── main.py # Punkt wejścia aplikacji 
├── .gitignore # Plik ignorowanych plików dla Git (m.in. steam_market.db) 
├── requirements.txt # Wymagane zależności Pythona (np. requests) 
└── README.md # Dokumentacja projektu
```

***

## Dokumentacja Techniczna 

### Główne Pliki i Role

#### `main.py`
Pełni rolę **inicjatora** systemu.
* Sprawdza, czy zainstalowano krytyczną zależność (`requests`).
* Wywołuje funkcję `database.init_db()` w celu przygotowania lokalnej bazy danych.
* Tworzy główne okno `tkinter` (`root`) i uruchamia główny kontroler aplikacji - `MarketApp`.

#### `src/gui/app.py`
Jest to **główny kontroler** (`MarketApp`) i menadżer stanu.
* **Zarządzanie Widokami**: Odpowiada za przełączanie się między widokami (`login`, `search`, `results`) za pomocą metody `switch_view`.
* **Dane Sesyjne**: Przechowuje globalne dane aplikacji, w tym kluczowe `self.login_cookie`.
* **Wątkowość (Threading)**: Wykorzystuje **kolejkę (`queue.Queue`)** o nazwie `self.result_queue` do bezpiecznej komunikacji między wątkami roboczymi (pobieranie API) a głównym wątkiem GUI. Metoda `process_queue` cyklicznie sprawdza kolejkę i aktualizuje GUI na podstawie otrzymanych komunikatów (logi, błędy, sukces).
* **Autouzupełnianie**: Zarządza listą `self.all_suggestions` wczytaną z pliku lub pobraną z API.

#### `src/gui/login_view.py`
**Widok logowania**.
* Zbiera wartość klucza sesyjnego **`steamLoginSecure`** od użytkownika.
* Po zatwierdzeniu, przekazuje tę wartość do kontrolera (`self.controller.set_cookie`) i przełącza widok na wyszukiwarkę.

#### `src/gui/search_view.py`
**Widok wyszukiwania i Inicjator Działania**.
* Zawiera interaktywne elementy (pole tekstowe z autouzupełnianiem, `ttk.Checkbutton` dla StatTrak, `ttk.Combobox` dla jakości zużycia).
* Metoda **`start_search_thread`** uruchamia funkcję **`_search_worker`** w osobnym wątku (`threading.Thread`), aby operacje sieciowe nie blokowały interfejsu.
* **`_search_worker`**:
    1.  Wywołuje `steam_market.fetch_price_history` (historyczne transakcje).
    2.  Wywołuje `steam_market.fetch_market_listings` (aktualne oferty).
    3.  Wywołuje `database.add_sales`, zapisując historyczne dane do SQLite.
    4.  Pobiera zagregowaną historię z bazy (`database.get_sales_for_item`).
    5.  Przesyła pomyślne wyniki (`status: success`, `history_data`, `listings_data`) do kolejki kontrolera.
* Posiada tymczasowe okno **logu konsolowego** (`scrolledtext.ScrolledText`) do informowania użytkownika o statusie operacji.

#### `src/gui/results_view.py`
**Widok prezentacji wyników**.
* Wyświetla nazwę przedmiotu i dane podsumowujące (najniższa aktualna oferta, najwyższe zlecenie kupna).
* Prezentuje tabelę (`ttk.Treeview`) z **10 najtańszymi aktualnymi ofertami**.
* Umożliwia **rozwinięcie/zwinięcie** szczegółowej tabeli zawierającej wszystkie historyczne dane sprzedaży pobrane z bazy SQLite (`history_data`).

### Warstwa Danych i API

#### `steam_market.py`
Moduł realizujący komunikację z API Rynku Steam (`requests`).

* **`parse_market_name(market_hash_name)`**: Kluczowa funkcja do standaryzacji nazw. Wykorzystuje moduł **`re` (regex)** do ekstrakcji kluczowych informacji:
    * Typ przedmiotu, nazwa bazowa.
    * Jakość zużycia (`wear`: Factory New, Minimal Wear, itd.) - wykorzystuje **`WEAR_PATTERNS`**.
    * Status **StatTrak™**.
* **`fetch_price_history(market_hash_name, cookie)`**: Pobiera historyczne transakcje. Wymaga przekazania **`steamLoginSecure` cookie** w nagłówku zapytania, aby omijać geolokalizację i limity dostępu narzucane przez Steam dla niezalogowanych zapytań.
* **`fetch_market_listings(market_hash_name)`**: Pobiera aktualne oferty rynkowe. Zawiera logikę do przeliczania cen z formatu wewnętrznego Steam (integer, z opłatami) na cenę brutto float w lokalnej walucie (PLN).

#### `database.py`
Moduł zarządzający persystencją danych przy użyciu **SQLite3**.

* **`init_db()`**: Tworzy tabelę **`sales`**. Tabela posiada kolumny m.in. na nazwę, cenę, czas sprzedaży (`sale_timestamp`). Najważniejsza jest definicja **unikalnego klucza złożonego**: `UNIQUE(market_hash_name, sale_timestamp, price)`, który zapobiega wielokrotnemu zapisaniu tej samej transakcji, gdy dane historyczne są pobierane w różnych sesjach.
* **`add_sales(sales_records)`**: Wstawia listę rekordów. Używa konstrukcji `try...except sqlite3.IntegrityError` do **ignorowania duplikatów**, co gwarantuje czystość danych.
* **`get_sales_for_item(market_hash_name)`**: Pobiera całą, zagregowaną historię danego przedmiotu z bazy, posortowaną chronologicznie.

### Wymagane Biblioteki

| Biblioteka | Cel |
| :--- | :--- |
| `tkinter` / `tkinter.ttk` | Budowa interfejsu graficznego (GUI) dla platformy desktopowej. `ttk` zapewnia nowoczesne widżety. |
| `requests` | Wykonywanie zapytań HTTP do zewnętrznych zasobów (API Rynku Steam). |
| `sqlite3` | Obsługa wbudowanej, lokalnej bazy danych do przechowywania historii cen. |
| `threading` | Uruchamianie długotrwałych operacji sieciowych w osobnym wątku, aby aplikacja GUI pozostawała responsywna. |
| `queue` | Bezpieczna komunikacja między wątkiem roboczym a głównym wątkiem GUI (FIFO). |
| `re` (regex) | Parsowanie tekstowe, głównie do ekstrakcji atrybutów przedmiotu z nazwy rynkowej. |

***

## Historia Zmian (Changelog) 

### CS2 Skin Analyzer v0.3 (Tydzień 3):

| Data | Opis Zmiany / Działania | Status |
| :--- | :--- | :--- |
| **Widok Wyszukiwania** | Zamiast ręcznego wpisywania nazwy całej skórki użytkownik wybiera bazową nazwę i wariant z predefiniowanej listy. | Ukończono |
| **Wykres Sprzedaży** | Dodano wykres historycznych transakcji w `ResultsView` (Matplotlib) z wyborem zakresu: tydzień / miesiąc / ogółem. | Ukończono |
| **Wyświetlanie Aktualnych Ofert** | Po dodaniu nowych funkcji pojawił się błąd w pełnym wyświetlaniu ofert – trwa naprawa parsowania/odświeżania. | W trakcie naprawy |

### CS2 Skin Analyzer v0.4 (Tydzień 4):

| Data | Opis Zmiany / Działania | Status |
| :--- | :--- | :--- |
| **Poprawa Parsowania Ofert** | Najpierw JSON `listinginfo`, potem fallback HTML; eliminacja błędów `NoneType`. | Ukończono |
| **Paginacja Backend** | Wielostronicowe pobieranie ofert z limitacją `MAX_PAGES` + metryki (strony, retry). | Ukończono |
| **On-Demand Paginacja GUI** | Dynamiczne pobieranie stron (`get_market_listings_page`) zamiast ładowania całego zestawu. | Ukończono |
| **Cache Stron** | Cache + prefetch kolejnej strony dla płynniejszej nawigacji. | Ukończono |
| **Izolacja Cache per Przedmiot** | Reset cache przy zmianie itemu, brak mieszania ofert. | Ukończono |
| **Overlay Ładowania** | Półprzezroczysty overlay nad tabelą ofert w czasie pobierania. | Ukończono |
| **Najniższa Oferta Spójna** | Najniższa cena wyliczana z parsowanych ofert (nie tylko z API). | Ukończono |
| **Usunięcie Highest Buy Order** | Pole najwyższego zlecenia kupna usunięte (mała wartość analityczna). | Ukończono |
| **Backoff + Jitter** | Mechanizm ponawiania (exponential backoff) dla 429/503 z losowym jitter. | Ukończono |
| **Metryki** | Logowanie: liczba stron i retry w SearchView. | Ukończono |
| **Format Dat Historycznych** | Parsowanie dat do `YYYY-MM-DD HH:00`. | Ukończono |
| **Sortowanie Cen Ofert** | Rosnąco po cenie (None na końcu). | Ukończono |
| **Spójność Licznika Ofert** | "Łącznie ofert" używa bieżącego `total_count`. | Ukończono |
| **Prefetch Logi** | Logi informujące cache vs sieć + status prefetchu. | Ukończono |

### CS2 Skin Analyzer v0.2 (Tydzień 2):

#### Ekran Logowania

![gui_login_v0.2](https://github.com/sqnlol/dao/blob/main/src/img/gui_login_v0.2.png?raw=true)

#### Ekran Wyszukiwania

![gui_search_v0.2](https://github.com/sqnlol/dao/blob/main/src/img/gui_search_v0.2.png?raw=true)

#### Ekran Wyników (schowane dane historyczne)

![gui_result1_v0.2](https://github.com/sqnlol/dao/blob/main/src/img/gui_result1_v0.2.png?raw=true)

#### Ekran Wyników (widoczne dane historyczne)

![gui_result2_v0.2](https://github.com/sqnlol/dao/blob/main/src/img/gui_result2_v0.2.png?raw=true)

| Data | Opis Zmiany / Działania | Status |
| :--- | :--- | :--- |
| **Zależności** | Dodano plik `requirements.txt` do zarządzania zależnościami. | Ukończono |
| **Kontrola Wersji** | Dodano plik `.gitignore` (ignorowanie plików binarnych i bazy danych `steam_market.db`). | Ukończono |
| **Architektura Danych** | **Kluczowa zmiana**: Wprowadzenie konieczności podawania cookie `steamLoginSecure` w celu ominięcia blokad API i dostępu do pełnej historii cen. | Ukończono |
| **Widok 1: Logowanie** | Stworzenie ekranu `LoginView.py` do wprowadzania wymaganego klucza cookie. | Ukończono |
| **Logowanie** | Dodanie logowania poprzez Steam, aby każdy użytkownik korzystał ze swojego własnego cookie | W planach |
| **Widok 2: Wyszukiwanie** | Stworzenie ekranu `SearchView.py` z pełnym zestawem filtrów: wybór jakości przedmiotu oraz checkbox na StatTrak™. | Ukończono |
| **Autouzupełnianie** | Dodanie autouzupełniania nazw skórek po wpisaniu pasujących nazw. | W toku |
| **Logowanie** | Dodano tymczasowe okno konsolowe/logi do `SearchView` informujące o statusie operacji (pobieranie, zapis, błędy). | Ukończono |
| **Widok 3: Wyniki** | Stworzenie ekranu `ResultsView.py` wyświetlającego: 10 najtańszych aktualnych ofert, historyczne min/max ceny, oraz rozwijaną tabelę historycznych danych ze steamcommunity.com/market/pricehistory/. | Ukończono |
| **Sortowanie tabel** | Dodanie możliwości sortowania rekordów w zależności od Daty lub Ceny sprzedaży | W planach |
| **Nawigacja** | Dodano przycisk powrotu z ekranu wyników do wyszukiwarki. | Ukończono |
| **Baza Danych** | Wdrożenie `database.py` i SQLite do **agregowania i przechowywania** pobranych rekordów sprzedaży, z unikalnym kluczem złożonym, zapobiegającym duplikatom. | Ukończono |

### CS Skin Analyzer v0.1 (Tydzień 1)

![gui_v0.1](https://github.com/sqnlol/dao/blob/main/src/img/gui_v0.1.png?raw=true)

| Data | Opis Zmiany / Działania | Status |
| :--- | :--- | :--- |
| **Początek Projektu** | Uruchomienie aplikacji poprzez konsolę (`python main.py`). | Ukończono |
| **Architektura** | Stworzenie pierwszej, szkieletowej struktury kodu i wstępnych modułów. | Ukończono |
| **Interfejs Graficzny** | Pierwsza wersja interfejsu graficznego (GUI) za pomocą `tkinter`. | Ukończono |
| **Wizualizacja** | Wyświetlanie statycznej, przykładowej tabeli w GUI. | Ukończono |
| **Deployment** | Próba kompilacji projektu do formatu wykonywalnego `.exe`. | W toku |
| **Współpraca** | Integracja kodu z systemem kontroli wersji GitHub. | Ukończono |
| **Wyzwania API** | Stwierdzenie problemów z pobieraniem danych z API Steam (blokowanie zapytań bez nagłówków przeglądarki/cookie). | Napotkano |
| **Alternatywy** | Początkowe próby pracy z zewnętrznymi API (porzucone na rzecz bezpośredniego dostępu Steam). | W toku |

***

## Aktualna Architektura (v0.4)

### Warstwa GUI
| Plik | Rola | Kluczowe Elementy |
| :--- | :--- | :--- |
| `login_view.py` | Pobranie i zapis cookie `steamLoginSecure`. | Pole wejściowe cookie, walidacja, przekazanie do kontrolera. |
| `search_view.py` | Wybór przedmiotu z listy i uruchomienie pobierania. | Wątek `_search_worker`, logi, parsowanie nazwy, zapis do DB. |
| `results_view.py` | Prezentacja wyników: wykres, oferty, historia, paginacja. | Cache stron, prefetch, overlay, dynamiczne etykiety. |
| `app.py` | Główny kontroler i pętla odczytu kolejki. | `switch_view`, `process_queue`, dystrybucja komunikatów. |

### Warstwa Backend / API
| Moduł | Funkcja | Szczegóły |
| :--- | :--- | :--- |
| `steam_market.get_price_history` | Pobieranie historii cen. | Wymaga cookie, parsowanie dat (UTC). |
| `steam_market.get_market_listings` | Pobieranie pakietu ofert + metryki. | JSON→HTML fallback, sortowanie, min-cena z listingu. |
| `steam_market.get_market_listings_page` | Stronicowanie on-demand. | Parametry start/count; integracja z ResultsView. |
| `steam_market.parse_market_name` | Standaryzacja nazwy. | Typ, wear, StatTrak. |

### Warstwa Danych
| Moduł | Funkcja | Szczegóły |
| :--- | :--- | :--- |
| `database.init_db` | Inicjalizacja schematu. | Tabela `sales` + unikaty. |
| `database.add_sales` | Dodanie rekordów. | Ignorowanie duplikatów `IntegrityError`. |
| `database.get_sales_for_item` | Odczyt danych historycznych. | Sortowanie chronologiczne. |

### Mechanizmy Wydajności / Stabilności
* Exponential backoff + jitter dla kodów 429/503.
* Prefetch następnej strony ofert (thread + log).
* Cache stron per przedmiot (reset przy zmianie itemu).
* Overlay przy wczytywaniu ofert (Canvas + stipple).

### Format Danych (Listings)
```
{
  'listings': [ {'price_float': float|None, 'fee': float|None}, ... ],
  'total_count': int,
  'lowest_price': str,
  'lowest_price_float': float,
  'meta': { 'retries': int, 'pages_loaded': int }
}
```

### Uruchomienie (Quick Start)
1. Instalacja zależności:
    ```bash
    pip install -r requirements.txt
    ```
2. Start aplikacji:
    ```bash
    python src\main.py
    ```
3. Wprowadź cookie `steamLoginSecure`.
4. Wybierz przedmiot → poczekaj na pobranie → analizuj oferty i wykres.

### Najczęstsze Problemy
| Problem | Przyczyna | Rozwiązanie |
| :--- | :--- | :--- |
| Brak historii cen | Cookie wygasło lub brak | Podaj aktualne `steamLoginSecure`. |
| Mało ofert | Limit API / brak dalszych stron | Spróbuj ponownie; możliwy rate limit. |
| Zła najniższa cena | Stare źródło z API | Obecnie liczona z listingu. |
| 429/503 | Rate limit Steam | Odczekaj; backoff działa automatycznie. |

### Backlog (Plany)
* Sortowanie ofert po wielu kolumnach + filtr minimalnej ceny.
* Trwały cache między sesjami (plik/SQLite dodatkowa tabela).
* Eksport historii do CSV.
* Alerty cenowe (progi + powiadomienia w UI).

***

## Licencja
Projekt edukacyjno-analityczny. Używaj zgodnie z regulaminem Steam. Brak gwarancji.

## Autor
Rozwój: architektura, backend, GUI, dokumentacja.

Zgłaszaj błędy i pomysły poprzez Issues.

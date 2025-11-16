# CS2 Skin Analyzer 

## Krótki Opis Projektu

**CS2 Skin Analyzer** to aplikacja desktopowa stworzona w Pythonie z wykorzystaniem biblioteki **tkinter** do wizualizacji i analizy rynku skórek do gry **Counter-Strike 2 (CS2)**.

Głównym celem projektu jest dostarczenie użytkownikowi narzędzia, które:
1.  Pobiera **aktualne oferty sprzedaży** z Rynku Społeczności Steam.
2.  Pobiera **historyczne dane cenowe** danego przedmiotu.
3.  Przechowuje dane w **lokalnej bazie danych SQLite**.
4.  Analizuje na ich podstawie trendy cenowe.

***

## Spis treści

- [Krótki opis](#krótki-opis-projektu)
- [Uruchomienie (Quick Start)](#uruchomienie-quick-start)
- [Struktura plików](#struktura-plików)
- [Architektura i dokumentacja techniczna](#architektura-i-dokumentacja-techniczna)
- [Format danych (Listings)](#format-danych-listings)
- [Najczęstsze problemy](#najczęstsze-problemy)
- [Historia zmian (Changelog)](#historia-zmian-changelog)

## Uruchomienie (Quick Start)
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

## Architektura i dokumentacja techniczna

### Warstwa GUI
| Plik | Rola | Kluczowe Elementy |
| :--- | :--- | :--- |
| `login_view.py` | Logowanie (ręczne i automatyczne) i zapis cookie `steamLoginSecure`. | Pole cookie; Selenium (Edge/Chrome) do logowania i automatycznego pobrania cookie; pobieranie nazwy konta; statusy. |
| `search_view.py` | Wybór przedmiotu i uruchomienie pobierania. | Filtry (StatTrak™, wear), taksonomia (w tym noże i „Vanilla”); nagłówek z powitaniem i trybem cookie; autouzupełnianie on‑demand z postępem/anulowaniem; logi. |
| `results_view.py` | Prezentacja wyników: wykres, oferty, historia, obrazek. | Interaktywny hover (dymek + zielona kropka); zakresy czasu; paginacja z cache/prefetch; overlay podczas ładowania; sortowalna historia; sekcja obrazka z LRU cache. |
| `app.py` | Kontroler, stan sesji, ikony i pętla kolejki. | Ustawienie ikon PNG/ICO; `switch_view`; `process_queue` (obsługa log/progress/error/success); integracja z pobieraniem sugestii. |

#### Szczegółowe funkcje GUI

- `login_view.py`
    - Ręczne podanie cookie `steamLoginSecure` lub start automatycznego logowania przez przeglądarkę (Selenium: Edge → Chrome fallback, wyciszone logi).
    - Po zalogowaniu automatyczne wykrycie cookie i zapis do kontrolera; pobranie nazwy konta (community/store) i przejście do wyszukiwania.
    - Wyśrodkowany nagłówek z dużym logo i tytułem; komunikaty statusu (kolory: gray/orange/green/red).

- `search_view.py`
    - Nagłówek: „Witaj, <nazwa>”, przycisk Wyloguj, etykieta „Brak Cookie – funkcjonalność ograniczona” (dynamicznie ukrywana/pokazywana).
    - Taksonomia: kategorie broni (w tym „Snajperskie”), obsługa noży ze znakiem „★” i wariantem „Vanilla” (bez separatora i wear), MP7.
    - Filtry: StatTrak™, wear (włączane/wyłączane zależnie od typu/skin).
    - Autouzupełnianie on‑demand: przycisk aktualizacji, pasek postępu z ETA, etykieta inline, możliwość anulowania; zapis do `src/suggestions.txt`.
    - Logi operacyjne w dolnym panelu; wątki do pobierania danych; przekazanie wyników przez kolejkę do kontrolera.

- `results_view.py`
    - Wykres: zakresy „Tydzień/Miesiąc/Ogółem”; interaktywny hover z dymkiem (data+price), auto‑flip przy krawędziach i zielona kropka podświetlająca punkt.
    - Oferty: paginacja 10/strona, cache stron, prefetch kolejnej, stały kontener z półprzezroczystym overlayem podczas ładowania.
    - Podsumowanie: najniższa i najwyższa historyczna cena (z datą).
    - Historia: rozwijana tabela, sortowanie po Cenie i Dacie (klik w nagłówek) z ikonami kierunku i domyślnie najnowszymi na górze.
    - Obrazek przedmiotu: async pobieranie, skalowanie, LRU cache w pamięci (fallback: placeholder).

- `app.py`
    - Stan sesji: `login_cookie`, `steam_name`.
    - Ikony aplikacji: `iconphoto` (PNG) i generowanie wielorozmiarowego `.ico` + `iconbitmap` (Windows).
    - Pętla `process_queue`: odbiór komunikatów z wątków (log/progress/error/success) i delegacja do widoków; wstrzyknięcie `image_url` do `listings_data`.
    - Obsługa pobierania autouzupełniania (start/aktualizacja/anulowanie) i przekazanie listy do `search_view.set_suggestions`.

### Warstwa Backend / API
| Moduł | Funkcja | Szczegóły |
| :--- | :--- | :--- |
| `steam_market.get_price_history` | Pobieranie historii cen. | Wymaga `steamLoginSecure`; zwraca listę rekordów: `sale_timestamp`, `sale_date_str`, `price`, `sales_count`. |
| `steam_market.get_market_listings` | Pobieranie pakietu ofert + metryki. | Parsowanie JSON (fallback HTML); `lowest_price_float`, `total_count`, `listings` z polską lokalizacją (country=PL, language=polish, currency=6). |
| `steam_market.get_market_listings_page` | Stronicowanie on‑demand. | Paginacja start/count; spójna z GUI cache/prefetch; aktualizuje `total_count` i ceny min. |
| `steam_market.parse_market_name` | Standaryzacja nazwy rynku. | Typ, nazwa bazowa, wear; obsługa StatTrak™ i formatu noży (gwiazdka, Vanilla bez wear). |
| `steam_market.fetch_all_csgo_items` | Pełna lista pozycji dla autouzupełniania. | Zapis do `src/suggestions.txt`; tryb wznawiania, pliki postępu, callback z komunikatami `PROGRESS`, obsługa anulowania. |
| `steam_market.get_item_image_url` | URL obrazka dla pozycji. | Używany do asynchronicznego pobrania miniatury w `ResultsView`. |

#### Zasady i stabilność API
- Nagłówki przeglądarkowe i stały `User-Agent` wymagane dla spójności odpowiedzi Steam.
- Lokalizacja wymuszona: `country='PL'`, `language='polish'`, `currency=6` (PLN).
- Ponawianie przy 429/503: exponential backoff + jitter; logowanie metryk (strony, retry).
- Historia cen zwraca `None` przy braku/wygaśnięciu cookie – GUI prezentuje komunikat zamiast wykrzaczać wykres.

### Warstwa Danych
| Moduł | Funkcja | Szczegóły |
| :--- | :--- | :--- |
| `database.init_db` | Inicjalizacja schematu. | Tabela `sales` + unikaty. |
| `database.add_sales` | Dodanie rekordów. | Ignorowanie duplikatów `IntegrityError`. |
| `database.get_sales_for_item` | Odczyt danych historycznych. | Sortowanie chronologiczne. |

### Kontrakty komunikatów i kolejki
- Wątki robocze przekazują do kontrolera słowniki o kluczu `status` ∈ {`log`, `error`, `success`, `progress`}.
- `success` musi zawierać: `item_name`, `history_data`, `listings_data` (opcjonalnie `image_url`).
- `progress`: pole `progress` ze strukturą `{ current, total, retries, eta }` (sekundy); GUI aktualizuje pasek i etykietę postępu.
- Kontroler (`app.py`) dystrybuuje komunikaty do widoków, w tym wstrzykuje `image_url` do `listings_data` przed przełączeniem na Results.

### Ikony i branding
- Ikona PNG ustawiana przez `iconphoto`; generowanie wielorozmiarowego `.ico` i ustawienie `iconbitmap` (Windows taskbar).
- LoginView: duże logo + tytuł, wyśrodkowane; SearchView: nagłówek z powitaniem i statusem cookie.

### Mechanizmy Wydajności / Stabilności
* Exponential backoff + jitter dla kodów 429/503.
* Prefetch następnej strony ofert (thread + log).
* Cache stron per przedmiot (reset przy zmianie itemu).
* Overlay przy wczytywaniu ofert (Canvas + stipple).

### Kluczowe pliki i role (szczegóły)
* `main.py` — inicjalizacja aplikacji: sprawdzenie zależności (`requests`), `database.init_db()`, start `tkinter` i kontrolera `MarketApp`.
* `src/gui/app.py` — kontroler i stan sesji (`login_cookie`), przełączanie widoków, pętla `process_queue` na komunikaty z wątków.
* `src/gui/login_view.py` — input i zapis `steamLoginSecure`.
* `src/gui/search_view.py` — UI wyszukiwania + worker `_search_worker` (pobrania, zapis do DB, publikacja wyników do kolejki).
* `src/gui/results_view.py` — prezentacja wyników (tabela ofert z paginacją, wykres, historia), cache i prefetch stron.

### Wymagane biblioteki

| Biblioteka | Cel |
| :--- | :--- |
| `tkinter` / `tkinter.ttk` | Budowa interfejsu graficznego (GUI) dla platformy desktopowej. `ttk` zapewnia nowoczesne widżety. |
| `requests` | Wykonywanie zapytań HTTP do zewnętrznych zasobów (API Rynku Steam). |
| `sqlite3` | Obsługa wbudowanej, lokalnej bazy danych do przechowywania historii cen. |
| `threading` | Uruchamianie długotrwałych operacji sieciowych w osobnym wątku, aby aplikacja GUI pozostawała responsywna. |
| `queue` | Bezpieczna komunikacja między wątkiem roboczym a głównym wątkiem GUI (FIFO). |
| `re` (regex) | Parsowanie tekstowe, głównie do ekstrakcji atrybutów przedmiotu z nazwy rynkowej. |
| `matplotlib` | Renderowanie wykresu historii cen (Figure, Axes, event hover). |
| `numpy` | Efektywne obliczenia dystansu punktu (hover), operacje na tablicach. |
| `Pillow` (`PIL`) | Skalowanie i konwersja obrazków skórek oraz generacja ikony `.ico`. |
| `selenium` | Automatyczne uruchamianie przeglądarki (Edge/Chrome) i przechwytywanie cookie `steamLoginSecure`. |
| `webdriver-manager` | Automatyczne zarządzanie sterownikami Selenium (fallback przy braku wbudowanego). |
| `pyinstaller` | Budowanie dystrybucji wykonywalnej (.exe) aplikacji. |

## Format Danych (Listings)
```
{
    'listings': [ {'price_float': float|None, 'fee': float|None}, ... ],
    'total_count': int,
    'lowest_price': str,
    'lowest_price_float': float,
    'meta': { 'retries': int, 'pages_loaded': int }
}
```

## Najczęstsze Problemy
| Problem | Przyczyna | Rozwiązanie |
| :--- | :--- | :--- |
| Brak historii cen | Cookie wygasło lub brak | Podaj aktualne `steamLoginSecure`. |
| Mało ofert | Limit API / brak dalszych stron | Spróbuj ponownie; możliwy rate limit. |
| Zła najniższa cena | Stare źródło z API | Obecnie liczona z listingu. |
| 429/503 | Rate limit Steam | Odczekaj; backoff działa automatycznie. |

## Historia Zmian (Changelog)

### CS2 Skin Analyzer v0.5 (Tydzień 5):

#### Ekran Główny z Interaktywnym GUI

![gui_main_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/main_screen.png?raw=true)
*Zrzut: Główny ekran z ciemnym nagłówkiem, wyśrodkowanym tytułem i sidebarową nawigacją.*

#### Zmiana Waluty i Wykresy Cenowe

![gui_currency_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/currency_selector.png?raw=true)
*Zrzut: Dropdown zmiany waluty (PLN/USD/EUR) w sidebarze.*

#### Zakładka Skrzynie CS2

![gui_cases_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/cases_view.png?raw=true)
*Zrzut: Widok galerii skrzyń z miniaturkami i przyciskami akcji.*

![gui_case_detail_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/case_detail.png?raw=true)
*Zrzut: Szczegóły wybranej skrzyni z obrazkiem, nazwą i przyciskami „Szukaj na Steam".*

#### Auto-odświeżanie Sugestii

![gui_auto_refresh_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/auto_refresh.png?raw=true)
*Zrzut: Ustawienia auto-odświeżania listy przedmiotów z regulacją interwałów.*

| Data | Opis Zmiany / Działania | Status |
| :--- | :--- | :--- |
| **Interaktywne GUI** | Dodano ciemny nagłówek z wyśrodkowanym białym tytułem „CS2 Skin Analyzer"; sidebar z nawigacją i hover-efektem (pogrubienie przy najechaniu na „Główna"/„Skrzynie"); wszystkie przyciski akcji (`Action.TButton`) z pogrubionymi ramkami. | Ukończono |
| **Skrót Klawiszowy** | Dodano skrót `Ctrl+Enter` do szybkiego uruchomienia „Pobierz i zapisz"; hint wyświetlany w pasku informacyjnym. | Ukończono |
| **Czarne Elementy Estetyczne** | Konsola statusu (logi) z czarnym tłem i jasnym tekstem; czarny pasek nagłówka; sidebar z ciemnym tłem `#1a1a1a`. | Ukończono |
| **Zmiana Walut** | Dropdown w sidebarze umożliwiający wybór PLN / USD / EUR; automatyczna konwersja cen w wykresach, ofertach i historii; `currency_code` przekazywany do API Steam. | Ukończono |
| **Wykresy Cenowe z Konwersją** | Wykres automatycznie dostosowuje oś Y do wybranej waluty; hover dymek wyświetla cenę w aktualnej walucie; konwersja tylko dla danych z bazy (dane z API już w docelowej walucie). | Ukończono |
| **Zakładka „Skrzynie"** | Nowy widok `CasesView` z siatką miniaturek wszystkich skrzyń CS2 ładowanych z folderu `src/img/cases`; kafelki z białym tłem, nazwą i klikalnym podglądem. | Ukończono |
| **Szczegóły Skrzyni** | `CaseDetailView` wyświetla powiększony obrazek, nazwę i ścieżkę do pliku; przyciski: „Otwórz plik", „Pokaż w folderze", „Szukaj na Steam" (otwiera przeglądarkę z wyszukiwaniem na Steam Market). | Ukończono |
| **Bezpieczne Ładowanie Obrazków** | Wszystkie obrazy (skrzynie, ikony) ładowane asynchronicznie w wątku pomocniczym; `ImageTk.PhotoImage` tworzony **tylko** w głównym wątku Tkinter (naprawa błędu `main thread is not in main loop`). | Ukończono |
| **Auto-odświeżanie Sugestii** | Checkbox „Auto-odświeżanie sugestii" z regulacją interwałów (min–max w sekundach); cykliczne pobieranie listy przedmiotów w tle z zapisem do `src/suggestions.txt`; etykieta ETA kolejnego cyklu; przycisk „Cykl teraz" wymuszający natychmiastową aktualizację. | Ukończono |
| **Interwały Auto-odświeżania** | Użytkownik ustawia zakres czasu (domyślnie 600–900 s); aplikacja losuje delay z tego przedziału po każdym cyklu; możliwość włączenia/wyłączenia i natychmiastowego wymuszenia cyklu. | Ukończono |
| **Rate Limiting Fixes** | Zwiększono opóźnienia i backoff w `_http_get_with_backoff` (initial: 2.0s, mnożnik: 2.0x, jitter: 0.5–1.5s) oraz opóźnienie między pobieraniem historii a listingów (3.0s zamiast 1.5s), aby uniknąć błędów HTTP 429 od Steam. | Ukończono |
| **Powiększone Logo** | Logo w sidebarze zwiększone z 64×64 do 80×80 px dla lepszej widoczności. | Ukończono |

### CS2 Skin Analyzer v0.4 (Tydzień 4):

#### Ekran Logowania

![gui_login_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_login_v0.4.png?raw=true)

#### Ekran Wyszukiwania (Guest)

![gui_search_guest_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_search_guest_v0.4.png?raw=true)

#### Ekran Wyszukiwania (User)

![gui_search_log_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_search_log_v0.4.png?raw=true)

#### Ekran Wyników (Guest)

![gui_result_guest_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_result_guest_v0.4.png?raw=true)

#### Ekran Wyników (User)

![gui_result_log_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_result_log_v0.4.png?raw=true)

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
| **Backoff + Jitter** | Mechanizm ponawiania (exponential backoff) dla błędów 429/503 z losowym jitter. | Ukończono |
| **Metryki** | Logowanie: liczba stron i retry w SearchView. | Ukończono |
| **Format Dat Historycznych** | Parsowanie dat do `YYYY-MM-DD HH:00`. | Ukończono |
| **Sortowanie Cen Ofert** | Rosnąco po cenie (None na końcu). | Ukończono |
| **Spójność Licznika Ofert** | "Łącznie ofert" używa bieżącego `total_count`. | Ukończono |
| **Prefetch Logi** | Logi informujące cache vs sieć + status prefetchu. | Ukończono |
| **Interaktywny hover na wykresie** | Dymek z datą i ceną, dynamiczne pozycjonowanie (flip przy krawędziach), zielone podświetlenie punktu. | Ukończono |
| **Automatyczne logowanie przez przeglądarkę** | Selenium otwiera Edge/Chrome; po zalogowaniu automatycznie pobiera cookie `steamLoginSecure` (limit ~7 min), wyciszone logi. | Ukończono |
| **Pobranie nazwy konta** | Po zalogowaniu pobierana jest nazwa konta ze Steam (`steamcommunity`/`store`) i wyświetlana jako „Witaj, <nazwa>”. | Ukończono |
| **Branding i ikony** | Logo aplikacji w oknie; generowanie wielorozmiarowego `.ico`; ustawienie `iconphoto`/`iconbitmap`; duży nagłówek i wyśrodkowanie w LoginView. | Ukończono |
| **UI: powitanie i tryb cookie** | Nagłówek w SearchView: „Witaj, …”, przycisk Wyloguj, dynamiczna etykieta „Brak Cookie – funkcjonalność ograniczona”. | Ukończono |
| **Taxonomia i nazewnictwo** | Refaktor kategorii (oddzielne „Snajperskie”), dodano MP7, pełen zestaw noży z gwiazdką „★”, obsługa wariantu „Vanilla” (bez wear i separatora). | Ukończono |
| **Obrazek przedmiotu** | Sekcja obrazu w ResultsView: asynchroniczne pobieranie i skalowanie, LRU cache obrazków, placeholder gdy brak. | Ukończono |
| **Sortowanie tabeli historii** | Klikalne nagłówki Cena/Data z przełączaniem kierunku i strzałkami; domyślnie najnowsze na górze. | Ukończono |
| **Autouzupełnianie on‑demand** | Przycisk „Zaktualizuj listę przedmiotów”, pasek postępu + ETA i anulowanie; zapis do `src/suggestions.txt`. | Ukończono |
| **Komunikat o braku historii** | Na wykresie pojawia się informacja „Brak historii cen (wymagane cookie)” gdy brak danych/cookie. | Ukończono |

### CS2 Skin Analyzer v0.3 (Tydzień 3):

#### Ekran Wyszukiwania

![gui_search_v0.3](https://github.com/sqnlol/dao/blob/main/src/img/gui_search_v0.3.png?raw=true)

#### Ekran Wyników

![gui_result_v0.3](https://github.com/sqnlol/dao/blob/main/src/img/gui_result_v0.3.png?raw=true)

| Data | Opis Zmiany / Działania | Status |
| :--- | :--- | :--- |
| **Widok Wyszukiwania** | Zamiast ręcznego wpisywania nazwy całej skórki użytkownik wybiera bazową nazwę i wariant z predefiniowanej listy. | Ukończono |
| **Wykres Sprzedaży** | Dodano wykres historycznych transakcji w `ResultsView` (Matplotlib) z wyborem zakresu: tydzień / miesiąc / ogółem. | Ukończono |
| **Wyświetlanie Aktualnych Ofert** | Po dodaniu nowych funkcji pojawił się błąd w pełnym wyświetlaniu ofert – trwa naprawa parsowania/odświeżania. | W trakcie naprawy |

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
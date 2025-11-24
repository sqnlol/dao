# CS2 Skin Analyzer 

## KrĂłtki Opis Projektu

**CS2 Skin Analyzer** to aplikacja desktopowa stworzona w Pythonie z wykorzystaniem biblioteki **tkinter** do wizualizacji i analizy rynku skĂłrek do gry **Counter-Strike 2 (CS2)**.

GĹ‚Ăłwnym celem projektu jest dostarczenie uĹĽytkownikowi narzÄ™dzia, ktĂłre:
1.  Pobiera **aktualne oferty sprzedaĹĽy** z Rynku SpoĹ‚ecznoĹ›ci Steam.
2.  Pobiera **historyczne dane cenowe** danego przedmiotu.
3.  Przechowuje dane w **lokalnej bazie danych SQLite**.
4.  Analizuje na ich podstawie trendy cenowe.

***

## Spis treĹ›ci

- [KrĂłtki opis](#krĂłtki-opis-projektu)
- [Uruchomienie (Quick Start)](#uruchomienie-quick-start)
- [Struktura plikĂłw](#struktura-plikĂłw)
- [Architektura i dokumentacja techniczna](#architektura-i-dokumentacja-techniczna)
- [Format danych (Listings)](#format-danych-listings)
- [NajczÄ™stsze problemy](#najczÄ™stsze-problemy)
- [Historia zmian (Changelog)](#historia-zmian-changelog)

## Uruchomienie (Quick Start)
1. Instalacja zaleĹĽnoĹ›ci:
    ```bash
    pip install -r requirements.txt
    ```
2. Start aplikacji:
    ```bash
    python src\main.py
    ```
3. WprowadĹş cookie `steamLoginSecure`.
4. Wybierz przedmiot â†’ poczekaj na pobranie â†’ analizuj oferty i wykres.

## Struktura PlikĂłw 

Projekt jest zorganizowany modularnie, oddzielajÄ…c logikÄ™ GUI (Views), Kontroler oraz warstwy dostÄ™pu do Danych (API i Baza Danych).

```
CS2 Skin Analyzer/
â”śâ”€â”€ src/ 
â”‚ â”śâ”€â”€ gui/ 
â”‚ â”‚ â”śâ”€â”€ init.py # Definicja pakietu i importy klas 
â”‚ â”‚ â”śâ”€â”€ app.py # GĹ‚Ăłwny Kontroler Aplikacji (App Controller) 
â”‚ â”‚ â”śâ”€â”€ login_view.py # Widok Wprowadzania Cookie 
â”‚ â”‚ â”śâ”€â”€ search_view.py # Widok Wyszukiwania Przedmiotu 
â”‚ â”‚ â””â”€â”€ results_view.py # Widok WyĹ›wietlania WynikĂłw i Historii 
â”‚ â”śâ”€â”€ database.py # ModuĹ‚ obsĹ‚ugi bazy danych SQLite 
â”‚ â”śâ”€â”€ steam_market.py # ModuĹ‚ komunikacji z API Rynku Steam 
â”‚ â””â”€â”€ main.py # Punkt wejĹ›cia aplikacji 
â”śâ”€â”€ .gitignore # Plik ignorowanych plikĂłw dla Git (m.in. steam_market.db) 
â”śâ”€â”€ requirements.txt # Wymagane zaleĹĽnoĹ›ci Pythona (np. requests) 
â””â”€â”€ README.md # Dokumentacja projektu
```

***

## Architektura i dokumentacja techniczna

### Warstwa GUI
| Plik | Rola | Kluczowe Elementy |
| :--- | :--- | :--- |
| `login_view.py` | Logowanie (rÄ™czne i automatyczne) i zapis cookie `steamLoginSecure`. | Pole cookie; Selenium (Edge/Chrome) do logowania i automatycznego pobrania cookie; pobieranie nazwy konta; statusy. |
| `search_view.py` | WybĂłr przedmiotu i uruchomienie pobierania. | Filtry (StatTrakâ„˘, wear), taksonomia (w tym noĹĽe i â€žVanillaâ€ť); nagĹ‚Ăłwek z powitaniem i trybem cookie; autouzupeĹ‚nianie onâ€‘demand z postÄ™pem/anulowaniem; logi. |
| `results_view.py` | Prezentacja wynikĂłw: wykres, oferty, historia, obrazek. | Interaktywny hover (dymek + zielona kropka); zakresy czasu; paginacja z cache/prefetch; overlay podczas Ĺ‚adowania; sortowalna historia; sekcja obrazka z LRU cache. |
| `app.py` | Kontroler, stan sesji, ikony i pÄ™tla kolejki. | Ustawienie ikon PNG/ICO; `switch_view`; `process_queue` (obsĹ‚uga log/progress/error/success); integracja z pobieraniem sugestii. |

#### SzczegĂłĹ‚owe funkcje GUI

- `login_view.py`
    - RÄ™czne podanie cookie `steamLoginSecure` lub start automatycznego logowania przez przeglÄ…darkÄ™ (Selenium: Edge â†’ Chrome fallback, wyciszone logi).
    - Po zalogowaniu automatyczne wykrycie cookie i zapis do kontrolera; pobranie nazwy konta (community/store) i przejĹ›cie do wyszukiwania.
    - WyĹ›rodkowany nagĹ‚Ăłwek z duĹĽym logo i tytuĹ‚em; komunikaty statusu (kolory: gray/orange/green/red).

- `search_view.py`
    - NagĹ‚Ăłwek: â€žWitaj, <nazwa>â€ť, przycisk Wyloguj, etykieta â€žBrak Cookie â€“ funkcjonalnoĹ›Ä‡ ograniczonaâ€ť (dynamicznie ukrywana/pokazywana).
    - Taksonomia: kategorie broni (w tym â€žSnajperskieâ€ť), obsĹ‚uga noĹĽy ze znakiem â€žâ…â€ť i wariantem â€žVanillaâ€ť (bez separatora i wear), MP7.
    - Filtry: StatTrakâ„˘, wear (wĹ‚Ä…czane/wyĹ‚Ä…czane zaleĹĽnie od typu/skin).
    - AutouzupeĹ‚nianie onâ€‘demand: przycisk aktualizacji, pasek postÄ™pu z ETA, etykieta inline, moĹĽliwoĹ›Ä‡ anulowania; zapis do `src/suggestions.txt`.
    - Logi operacyjne w dolnym panelu; wÄ…tki do pobierania danych; przekazanie wynikĂłw przez kolejkÄ™ do kontrolera.

- `results_view.py`
    - Wykres: zakresy â€žTydzieĹ„/MiesiÄ…c/OgĂłĹ‚emâ€ť; interaktywny hover z dymkiem (data+price), autoâ€‘flip przy krawÄ™dziach i zielona kropka podĹ›wietlajÄ…ca punkt.
    - Oferty: paginacja 10/strona, cache stron, prefetch kolejnej, staĹ‚y kontener z pĂłĹ‚przezroczystym overlayem podczas Ĺ‚adowania.
    - Podsumowanie: najniĹĽsza i najwyĹĽsza historyczna cena (z datÄ…).
    - Historia: rozwijana tabela, sortowanie po Cenie i Dacie (klik w nagĹ‚Ăłwek) z ikonami kierunku i domyĹ›lnie najnowszymi na gĂłrze.
    - Obrazek przedmiotu: async pobieranie, skalowanie, LRU cache w pamiÄ™ci (fallback: placeholder).

- `app.py`
    - Stan sesji: `login_cookie`, `steam_name`.
    - Ikony aplikacji: `iconphoto` (PNG) i generowanie wielorozmiarowego `.ico` + `iconbitmap` (Windows).
    - PÄ™tla `process_queue`: odbiĂłr komunikatĂłw z wÄ…tkĂłw (log/progress/error/success) i delegacja do widokĂłw; wstrzykniÄ™cie `image_url` do `listings_data`.
    - ObsĹ‚uga pobierania autouzupeĹ‚niania (start/aktualizacja/anulowanie) i przekazanie listy do `search_view.set_suggestions`.

### Warstwa Backend / API
| ModuĹ‚ | Funkcja | SzczegĂłĹ‚y |
| :--- | :--- | :--- |
| `steam_market.get_price_history` | Pobieranie historii cen. | Wymaga `steamLoginSecure`; zwraca listÄ™ rekordĂłw: `sale_timestamp`, `sale_date_str`, `price`, `sales_count`. |
| `steam_market.get_market_listings` | Pobieranie pakietu ofert + metryki. | Parsowanie JSON (fallback HTML); `lowest_price_float`, `total_count`, `listings` z polskÄ… lokalizacjÄ… (country=PL, language=polish, currency=6). |
| `steam_market.get_market_listings_page` | Stronicowanie onâ€‘demand. | Paginacja start/count; spĂłjna z GUI cache/prefetch; aktualizuje `total_count` i ceny min. |
| `steam_market.parse_market_name` | Standaryzacja nazwy rynku. | Typ, nazwa bazowa, wear; obsĹ‚uga StatTrakâ„˘ i formatu noĹĽy (gwiazdka, Vanilla bez wear). |
| `steam_market.fetch_all_csgo_items` | PeĹ‚na lista pozycji dla autouzupeĹ‚niania. | Zapis do `src/suggestions.txt`; tryb wznawiania, pliki postÄ™pu, callback z komunikatami `PROGRESS`, obsĹ‚uga anulowania. |
| `steam_market.get_item_image_url` | URL obrazka dla pozycji. | UĹĽywany do asynchronicznego pobrania miniatury w `ResultsView`. |

#### Zasady i stabilnoĹ›Ä‡ API
- NagĹ‚Ăłwki przeglÄ…darkowe i staĹ‚y `User-Agent` wymagane dla spĂłjnoĹ›ci odpowiedzi Steam.
- Lokalizacja wymuszona: `country='PL'`, `language='polish'`, `currency=6` (PLN).
- Ponawianie przy 429/503: exponential backoff + jitter; logowanie metryk (strony, retry).
- Historia cen zwraca `None` przy braku/wygaĹ›niÄ™ciu cookie â€“ GUI prezentuje komunikat zamiast wykrzaczaÄ‡ wykres.

### Warstwa Danych
| ModuĹ‚ | Funkcja | SzczegĂłĹ‚y |
| :--- | :--- | :--- |
| `database.init_db` | Inicjalizacja schematu. | Tabela `sales` + unikaty. |
| `database.add_sales` | Dodanie rekordĂłw. | Ignorowanie duplikatĂłw `IntegrityError`. |
| `database.get_sales_for_item` | Odczyt danych historycznych. | Sortowanie chronologiczne. |

### Kontrakty komunikatĂłw i kolejki
- WÄ…tki robocze przekazujÄ… do kontrolera sĹ‚owniki o kluczu `status` â {`log`, `error`, `success`, `progress`}.
- `success` musi zawieraÄ‡: `item_name`, `history_data`, `listings_data` (opcjonalnie `image_url`).
- `progress`: pole `progress` ze strukturÄ… `{ current, total, retries, eta }` (sekundy); GUI aktualizuje pasek i etykietÄ™ postÄ™pu.
- Kontroler (`app.py`) dystrybuuje komunikaty do widokĂłw, w tym wstrzykuje `image_url` do `listings_data` przed przeĹ‚Ä…czeniem na Results.

### Ikony i branding
- Ikona PNG ustawiana przez `iconphoto`; generowanie wielorozmiarowego `.ico` i ustawienie `iconbitmap` (Windows taskbar).
- LoginView: duĹĽe logo + tytuĹ‚, wyĹ›rodkowane; SearchView: nagĹ‚Ăłwek z powitaniem i statusem cookie.

### Mechanizmy WydajnoĹ›ci / StabilnoĹ›ci
* Exponential backoff + jitter dla kodĂłw 429/503.
* Prefetch nastÄ™pnej strony ofert (thread + log).
* Cache stron per przedmiot (reset przy zmianie itemu).
* Overlay przy wczytywaniu ofert (Canvas + stipple).

### Kluczowe pliki i role (szczegĂłĹ‚y)
* `main.py` â€” inicjalizacja aplikacji: sprawdzenie zaleĹĽnoĹ›ci (`requests`), `database.init_db()`, start `tkinter` i kontrolera `MarketApp`.
* `src/gui/app.py` â€” kontroler i stan sesji (`login_cookie`), przeĹ‚Ä…czanie widokĂłw, pÄ™tla `process_queue` na komunikaty z wÄ…tkĂłw.
* `src/gui/login_view.py` â€” input i zapis `steamLoginSecure`.
* `src/gui/search_view.py` â€” UI wyszukiwania + worker `_search_worker` (pobrania, zapis do DB, publikacja wynikĂłw do kolejki).
* `src/gui/results_view.py` â€” prezentacja wynikĂłw (tabela ofert z paginacjÄ…, wykres, historia), cache i prefetch stron.

### Wymagane biblioteki

| Biblioteka | Cel |
| :--- | :--- |
| `tkinter` / `tkinter.ttk` | Budowa interfejsu graficznego (GUI) dla platformy desktopowej. `ttk` zapewnia nowoczesne widĹĽety. |
| `requests` | Wykonywanie zapytaĹ„ HTTP do zewnÄ™trznych zasobĂłw (API Rynku Steam). |
| `sqlite3` | ObsĹ‚uga wbudowanej, lokalnej bazy danych do przechowywania historii cen. |
| `threading` | Uruchamianie dĹ‚ugotrwaĹ‚ych operacji sieciowych w osobnym wÄ…tku, aby aplikacja GUI pozostawaĹ‚a responsywna. |
| `queue` | Bezpieczna komunikacja miÄ™dzy wÄ…tkiem roboczym a gĹ‚Ăłwnym wÄ…tkiem GUI (FIFO). |
| `re` (regex) | Parsowanie tekstowe, gĹ‚Ăłwnie do ekstrakcji atrybutĂłw przedmiotu z nazwy rynkowej. |
| `matplotlib` | Renderowanie wykresu historii cen (Figure, Axes, event hover). |
| `numpy` | Efektywne obliczenia dystansu punktu (hover), operacje na tablicach. |
| `Pillow` (`PIL`) | Skalowanie i konwersja obrazkĂłw skĂłrek oraz generacja ikony `.ico`. |
| `selenium` | Automatyczne uruchamianie przeglÄ…darki (Edge/Chrome) i przechwytywanie cookie `steamLoginSecure`. |
| `webdriver-manager` | Automatyczne zarzÄ…dzanie sterownikami Selenium (fallback przy braku wbudowanego). |
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

## NajczÄ™stsze Problemy
| Problem | Przyczyna | RozwiÄ…zanie |
| :--- | :--- | :--- |
| Brak historii cen | Cookie wygasĹ‚o lub brak | Podaj aktualne `steamLoginSecure`. |
| MaĹ‚o ofert | Limit API / brak dalszych stron | SprĂłbuj ponownie; moĹĽliwy rate limit. |
| ZĹ‚a najniĹĽsza cena | Stare ĹşrĂłdĹ‚o z API | Obecnie liczona z listingu. |
| 429/503 | Rate limit Steam | Odczekaj; backoff dziaĹ‚a automatycznie. |

## Historia Zmian (Changelog)

### CS2 Skin Analyzer v0.6 (TydzieĹ„ 6):

#### Ekran Logowania (Reworked)

![gui_login_v0.6](https://github.com/sqnlol/dao/blob/main/src/img/gui_login_v0.6.png?raw=true)

#### Cache obrazkĂłw skrzyĹ„ i akcje w widoku szczegĂłĹ‚Ăłw

- `CasesView` wczytuje listÄ™ skrzyĹ„ z moduĹ‚u `case_images_cache`, sprawdza brakujÄ…ce zasoby i w tle pobiera ich miniatury prosto ze Steam Market (z adaptacyjnym opĂłĹşnieniem i logami postÄ™pu). Po zakoĹ„czeniu siatka kafelkĂłw automatycznie siÄ™ odĹ›wieĹĽa, dziÄ™ki czemu widok zawsze pokazuje realne obrazki, a nie placeholdery.
- `CaseDetailView` korzysta juĹĽ wyĹ‚Ä…cznie z lokalnego cacheâ€™u i daje szybkie akcje: â€žOtwĂłrz plikâ€ť, â€žPokaĹĽ w folderzeâ€ť oraz â€žSzukaj na Steamâ€ť. Pozwala to szybko przejĹ›Ä‡ od galerii do plikĂłw lub strony spoĹ‚ecznoĹ›ci bez rÄ™cznego szukania Ĺ›cieĹĽek.

#### Sugestie przeniesione do katalogu uĹĽytkownika i szybkie odĹ›wieĹĽanie

- Nowy moduĹ‚ `resource_paths` kieruje `suggestions.txt` do `%LOCALAPPDATA%\CS2SkinAnalyzer` (z kopiowaniem zasobĂłw przy pierwszym starcie) i prawidĹ‚owo rozwiÄ…zuje Ĺ›cieĹĽki w buildach PyInstaller (`_MEIPASS`). DziÄ™ki temu wersja `.exe` faktycznie zapisuje/odczytuje autouzupeĹ‚nianie, zamiast tkwiÄ‡ na wbudowanych placeholderach.
- Przycisk â€žOdĹ›wieĹĽ autouzupeĹ‚nianieâ€ť w `SearchView` korzysta z lekkiego wÄ…tku `_fetch_suggestions_async`, ktĂłry Ĺ‚aduje lokalny plik i po zakoĹ„czeniu wywoĹ‚uje `set_suggestions`. Widok od razu przeĹ‚adowuje taksonomiÄ™ (`skin_list` jest importowany ponownie), wiÄ™c wszystkie comboboxy (Agenci, rÄ™kawice, graffiti itd.) natychmiast widzÄ… nowe kategorie bez peĹ‚nego pobierania z sieci.

| Data | Opis Zmiany / DziaĹ‚ania | Status |
| :--- | :--- | :--- |
| **Cache skrzyĹ„** | Dodano `case_images_cache.py` + integracjÄ™ w `CasesView`: sprawdzanie brakujÄ…cych obrazĂłw, asynchroniczne pobieranie z logami postÄ™pu i automatyczne odĹ›wieĹĽenie kafelkĂłw po zakoĹ„czeniu. | UkoĹ„czono |
| **Akcje w szczegĂłĹ‚ach skrzyni** | `CaseDetailView` pokazuje Ĺ›cieĹĽkÄ™ cache, pozwala otworzyÄ‡ plik/ folder oraz przenosi do wyszukiwarki Steam jednym klikniÄ™ciem. | UkoĹ„czono |
| **Sugestie w LocalAppData** | Wszystkie moduĹ‚y (`app.py`, `suggestions_loader.py`, `skin_list_builder.py`) korzystajÄ… z `resource_paths.get_writable_suggestions_path()`, wiÄ™c dane autouzupeĹ‚niania zapisujÄ… siÄ™ w katalogu uĹĽytkownika zarĂłwno w dev, jak i w buildzie `.exe`. | UkoĹ„czono |
| **Szybkie odĹ›wieĹĽanie autouzupeĹ‚niania** | Przycisk w SearchView wywoĹ‚uje `_fetch_suggestions_async`, ktĂłry Ĺ‚aduje lokalne `suggestions.txt` i po wysĹ‚aniu komunikatu do GUI przeĹ‚adowuje taksonomiÄ™ (gloves, agents, graffiti, kontenery) bez dodatkowego ruchu sieciowego. | UkoĹ„czono |
| **Rework graficzny** | Ulepszenie szaty graficznej na przestrzeni caĹ‚ej aplikacji | W trakcie |

#### Napotkane BĹ‚Ä™dy (TydzieĹ„ 6)

| Problem | Objaw | Status | RozwiÄ…zanie / Plan |
| :--- | :--- | :--- | :--- |
| Brak zapisu sugestii w buildzie `.exe` | AutouzupeĹ‚nianie nie aktualizowaĹ‚o siÄ™ (plik w katalogu tymczasowym, brak zapisu). | RozwiÄ…zano | Przeniesienie `suggestions.txt` do `%LOCALAPPDATA%` przez `resource_paths`. |
| Miniatury skrzyĹ„ nie odĹ›wieĹĽaĹ‚y siÄ™ | Po pobraniu obrazkĂłw dalej placeholdery w kafelkach. | RozwiÄ…zano | Callback koĹ„cowy wÄ…tku pobierania wywoĹ‚uje przebudowÄ™ gridu `CasesView`. |
| HTTP 429 przy masowym pobieraniu obrazkĂłw | Zbyt szybka sekwencja GET powodowaĹ‚a blokady. | RozwiÄ…zano | Adaptacyjne opĂłĹşnienie + exponential backoff + jitter + rozrzedzenie ĹĽÄ…daĹ„. |
| Powolne odĹ›wieĹĽanie taksonomii po aktualizacji sugestii | Comboboxy dĹ‚ugo nie widziaĹ‚y nowych kategorii. | RozwiÄ…zano | WÄ…tek `_fetch_suggestions_async` + ponowny import `skin_list` tuĹĽ po wczytaniu. |
| Niejednolity styl komponentĂłw | RĂłĹĽne marginesy, wysokoĹ›ci przyciskĂłw. | W trakcie | Ujednolicenie styli (`Action.TButton`, spacing); dalsze korekty. |
| Potencjalne przepeĹ‚nienie LRU cache obrazkĂłw | DĹ‚ugie sesje mogÄ… zwiÄ™kszaÄ‡ uĹĽycie RAM. | W toku | Plan ograniczenia rozmiaru cache i usuwania najstarszych wpisĂłw. |
| Brak komunikatu przy pustym pliku sugestii | Pusty `suggestions.txt` skutkowaĹ‚ brakiem nowych pozycji bez wyjaĹ›nienia. | W toku | Dodanie logu ostrzegawczego + fallback do poprzedniej listy. |
| Duplikaty prĂłb dodania rekordĂłw sprzedaĹĽy | Wstawianie tych samych timestampĂłw powodowaĹ‚o IntegrityError (ukryte). | Oczekiwane / Zneutralizowane | Unikalny klucz (nazwa+timestamp+price) w SQLite odrzuca duplikaty; brak dodatkowego dziaĹ‚ania. |
| Brak timeoutĂłw dla czÄ™Ĺ›ci ĹĽÄ…daĹ„ | Przy sĹ‚abym Ĺ‚Ä…czu wiszÄ…ce requesty wydĹ‚uĹĽaĹ‚y operacje. | Planowane | Ustawienie jawnych timeoutĂłw w warstwie HTTP (requests) + retry. |
| Skalowanie obrazkĂłw skrzyĹ„ z utratÄ… proporcji | NiektĂłre miniatury lekko znieksztaĹ‚cone przy fitowaniu. | Planowane | Zachowanie aspect ratio przez `thumbnail()` + letterboxing (tĹ‚o). |
| Brak walidacji formatu cookie w UI | Bdne wklejenie skróconego lub uszkodzonego cookie nie dawao ostrzeenia. | Planowane | Regex walidacja dugoci/formatu znaków przed akceptacj w LoginView. |

### CS2 Skin Analyzer v0.5 (TydzieĹ„ 5):

#### Ekran GĹ‚Ăłwny z Interaktywnym GUI

![gui_main_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/ekran%20g%C5%82owny.png?raw=true)
*Zrzut: GĹ‚Ăłwny ekran z ciemnym nagĹ‚Ăłwkiem, wyĹ›rodkowanym tytuĹ‚em i sidebarowÄ… nawigacjÄ….*

#### Napotkane BĹ‚Ä™dy (TydzieĹ„ 5)

| Problem | Objaw | Status | RozwiÄ…zanie / Plan |
| :--- | :--- | :--- | :--- |
| HTTP 429 przy sekwencyjnym pobraniu historii i ofert | Natychmiastowe pobranie ofert po historii dawaĹ‚o 429. | RozwiÄ…zano | WydĹ‚uĹĽenie przerwy (3.0s) + silniejszy backoff (2.0x). |
| BĹ‚Ä…d "main thread is not in main loop" przy obrazkach | Tworzenie `PhotoImage` w wÄ…tku koĹ„czyĹ‚o siÄ™ wyjÄ…tkiem. | RozwiÄ…zano | Tworzenie obrazĂłw przeniesione do gĹ‚Ăłwnego wÄ…tku przez `after()`. |
| Brak autoâ€‘odĹ›wieĹĽenia galerii po pobraniu obrazkĂłw | Miniatury wymagaĹ‚y rÄ™cznego przejĹ›cia widoku. | RozwiÄ…zano | Dodano koĹ„cowy callback przebudowujÄ…cy siatkÄ™. |
| NiespĂłjne importy (relatywne vs absolutne) | Trudniejsze uruchamianie w buildzie `.exe`. | RozwiÄ…zano | Standaryzacja do absolutnych `from src...`. |
| Spadek pĹ‚ynnoĹ›ci wykresu przy peĹ‚nym zakresie | Przy â€žOgĂłĹ‚emâ€ť render trwaĹ‚ odczuwalnie dĹ‚uĹĽej. | W toku | Plan downsamplingu i leniwej aktualizacji hover meta. |
| Sporadyczne `NoneType` przy parsowaniu ofert | BrakujÄ…ce pola w odpowiedzi powodowaĹ‚y wyjÄ…tki. | RozwiÄ…zano | Najpierw parse JSON, fallback HTML; dodatkowe `None`-guardy. |
| Zawieszanie przy braku odpowiedzi Steam | Brak szybkiej Ĺ›cieĹĽki przerwania przy dĹ‚ugim oczekiwaniu. | Planowane | Dodanie globalnych timeoutĂłw i licznikĂłw prĂłb. |
| Powielone logi prefetchu | Wielokrotne wpisy "prefetch" zaciemniaĹ‚y konsolÄ™. | Planowane | Agregacja metryk i pojedynczy log podsumowujÄ…cy. |
| Brak walidacji formatu cookie w UI | BĹ‚Ä™dne wklejenie skrĂłconego cookie nie dawaĹ‚o ostrzeĹĽenia. | Planowane | Prosta regex walidacja dĹ‚ugoĹ›ci/znakĂłw przed akceptacjÄ…. |
| Hover wykresu czÄ™Ĺ›ciowo nachodziĹ‚ na krawÄ™dĹş okna | Dymek czasem opuszczaĹ‚ obszar osi. | RozwiÄ…zano | Dodano logikÄ™ flipowania pozycji przy krawÄ™dziach. |

#### Zmiana Waluty i Wykresy Cenowe

![gui_currency_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/waluta.png?raw=true)
*Zrzut: Dropdown zmiany waluty (PLN/USD/EUR) w sidebarze.*

#### ZakĹ‚adka Skrzynie CS2

![gui_cases_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/skrzynie.png?raw=true)
*Zrzut: Widok galerii skrzyĹ„ z miniaturkami i przyciskami akcji.*

![gui_case_detail_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/skrzynie%20dokladne.png?raw=true)
*Zrzut: SzczegĂłĹ‚y wybranej skrzyni z obrazkiem, nazwÄ… i przyciskami â€žSzukaj na Steam".*

#### Auto-odĹ›wieĹĽanie Sugestii

![gui_auto_refresh_v0.5](https://github.com/sqnlol/dao/blob/main/src/img/week5/autoodswiezanie.png?raw=true)
*Zrzut: Ustawienia auto-odĹ›wieĹĽania listy przedmiotĂłw z regulacjÄ… interwaĹ‚Ăłw.*

| Data | Opis Zmiany / DziaĹ‚ania | Status |
| :--- | :--- | :--- |
| **Interaktywne GUI** | Dodano ciemny nagĹ‚Ăłwek z wyĹ›rodkowanym biaĹ‚ym tytuĹ‚em â€žCS2 Skin Analyzer"; sidebar z nawigacjÄ… i hover-efektem (pogrubienie przy najechaniu na â€žGĹ‚Ăłwna"/â€žSkrzynie"); wszystkie przyciski akcji (`Action.TButton`) z pogrubionymi ramkami. | UkoĹ„czono |
| **SkrĂłt Klawiszowy** | Dodano skrĂłt `Ctrl+Enter` do szybkiego uruchomienia â€žPobierz i zapisz"; hint wyĹ›wietlany w pasku informacyjnym. | UkoĹ„czono |
| **Czarne Elementy Estetyczne** | Konsola statusu (logi) z czarnym tĹ‚em i jasnym tekstem; czarny pasek nagĹ‚Ăłwka; sidebar z ciemnym tĹ‚em `#1a1a1a`. | UkoĹ„czono |
| **Zmiana Walut** | Dropdown w sidebarze umoĹĽliwiajÄ…cy wybĂłr PLN / USD / EUR; automatyczna konwersja cen w wykresach, ofertach i historii; `currency_code` przekazywany do API Steam. | UkoĹ„czono |
| **Wykresy Cenowe z KonwersjÄ…** | Wykres automatycznie dostosowuje oĹ› Y do wybranej waluty; hover dymek wyĹ›wietla cenÄ™ w aktualnej walucie; konwersja tylko dla danych z bazy (dane z API juĹĽ w docelowej walucie). | UkoĹ„czono |
| **ZakĹ‚adka â€žSkrzynie"** | Nowy widok `CasesView` z siatkÄ… miniaturek wszystkich skrzyĹ„ CS2 Ĺ‚adowanych z folderu `src/img/cases`; kafelki z biaĹ‚ym tĹ‚em, nazwÄ… i klikalnym podglÄ…dem. | UkoĹ„czono |
| **SzczegĂłĹ‚y Skrzyni** | `CaseDetailView` wyĹ›wietla powiÄ™kszony obrazek, nazwÄ™ i Ĺ›cieĹĽkÄ™ do pliku; przyciski: â€žOtwĂłrz plik", â€žPokaĹĽ w folderze", â€žSzukaj na Steam" (otwiera przeglÄ…darkÄ™ z wyszukiwaniem na Steam Market). | UkoĹ„czono |
| **Bezpieczne Ĺadowanie ObrazkĂłw** | Wszystkie obrazy (skrzynie, ikony) Ĺ‚adowane asynchronicznie w wÄ…tku pomocniczym; `ImageTk.PhotoImage` tworzony **tylko** w gĹ‚Ăłwnym wÄ…tku Tkinter (naprawa bĹ‚Ä™du `main thread is not in main loop`). | UkoĹ„czono |
| **Auto-odĹ›wieĹĽanie Sugestii** | Checkbox â€žAuto-odĹ›wieĹĽanie sugestii" z regulacjÄ… interwaĹ‚Ăłw (minâ€“max w sekundach); cykliczne pobieranie listy przedmiotĂłw w tle z zapisem do `src/suggestions.txt`; etykieta ETA kolejnego cyklu; przycisk â€žCykl teraz" wymuszajÄ…cy natychmiastowÄ… aktualizacjÄ™. | UkoĹ„czono |
| **InterwaĹ‚y Auto-odĹ›wieĹĽania** | UĹĽytkownik ustawia zakres czasu (domyĹ›lnie 600â€“900 s); aplikacja losuje delay z tego przedziaĹ‚u po kaĹĽdym cyklu; moĹĽliwoĹ›Ä‡ wĹ‚Ä…czenia/wyĹ‚Ä…czenia i natychmiastowego wymuszenia cyklu. | UkoĹ„czono |
| **Rate Limiting Fixes** | ZwiÄ™kszono opĂłĹşnienia i backoff w `_http_get_with_backoff` (initial: 2.0s, mnoĹĽnik: 2.0x, jitter: 0.5â€“1.5s) oraz opĂłĹşnienie miÄ™dzy pobieraniem historii a listingĂłw (3.0s zamiast 1.5s), aby uniknÄ…Ä‡ bĹ‚Ä™dĂłw HTTP 429 od Steam. | UkoĹ„czono |
| **PowiÄ™kszone Logo** | Logo w sidebarze zwiÄ™kszone z 64Ă—64 do 80Ă—80 px dla lepszej widocznoĹ›ci. | UkoĹ„czono |

### CS2 Skin Analyzer v0.4 (TydzieĹ„ 4):

#### Ekran Logowania

![gui_login_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_login_v0.4.png?raw=true)

#### Ekran Wyszukiwania (Guest)

![gui_search_guest_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_search_guest_v0.4.png?raw=true)

#### Ekran Wyszukiwania (User)

![gui_search_log_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_search_log_v0.4.png?raw=true)

#### Ekran WynikĂłw (Guest)

![gui_result_guest_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_result_guest_v0.4.png?raw=true)

#### Ekran WynikĂłw (User)

![gui_result_log_v0.4](https://github.com/sqnlol/dao/blob/main/src/img/gui_result_log_v0.4.png?raw=true)

| Data | Opis Zmiany / DziaĹ‚ania | Status |
| :--- | :--- | :--- |
| **Poprawa Parsowania Ofert** | Najpierw JSON `listinginfo`, potem fallback HTML; eliminacja bĹ‚Ä™dĂłw `NoneType`. | UkoĹ„czono |
| **Paginacja Backend** | Wielostronicowe pobieranie ofert z limitacjÄ… `MAX_PAGES` + metryki (strony, retry). | UkoĹ„czono |
| **On-Demand Paginacja GUI** | Dynamiczne pobieranie stron (`get_market_listings_page`) zamiast Ĺ‚adowania caĹ‚ego zestawu. | UkoĹ„czono |
| **Cache Stron** | Cache + prefetch kolejnej strony dla pĹ‚ynniejszej nawigacji. | UkoĹ„czono |
| **Izolacja Cache per Przedmiot** | Reset cache przy zmianie itemu, brak mieszania ofert. | UkoĹ„czono |
| **Overlay Ĺadowania** | PĂłĹ‚przezroczysty overlay nad tabelÄ… ofert w czasie pobierania. | UkoĹ„czono |
| **NajniĹĽsza Oferta SpĂłjna** | NajniĹĽsza cena wyliczana z parsowanych ofert (nie tylko z API). | UkoĹ„czono |
| **UsuniÄ™cie Highest Buy Order** | Pole najwyĹĽszego zlecenia kupna usuniÄ™te (maĹ‚a wartoĹ›Ä‡ analityczna). | UkoĹ„czono |
| **Backoff + Jitter** | Mechanizm ponawiania (exponential backoff) dla bĹ‚Ä™dĂłw 429/503 z losowym jitter. | UkoĹ„czono |
| **Metryki** | Logowanie: liczba stron i retry w SearchView. | UkoĹ„czono |
| **Format Dat Historycznych** | Parsowanie dat do `YYYY-MM-DD HH:00`. | UkoĹ„czono |
| **Sortowanie Cen Ofert** | RosnÄ…co po cenie (None na koĹ„cu). | UkoĹ„czono |
| **SpĂłjnoĹ›Ä‡ Licznika Ofert** | "ĹÄ…cznie ofert" uĹĽywa bieĹĽÄ…cego `total_count`. | UkoĹ„czono |
| **Prefetch Logi** | Logi informujÄ…ce cache vs sieÄ‡ + status prefetchu. | UkoĹ„czono |
| **Interaktywny hover na wykresie** | Dymek z datÄ… i cenÄ…, dynamiczne pozycjonowanie (flip przy krawÄ™dziach), zielone podĹ›wietlenie punktu. | UkoĹ„czono |
| **Automatyczne logowanie przez przeglÄ…darkÄ™** | Selenium otwiera Edge/Chrome; po zalogowaniu automatycznie pobiera cookie `steamLoginSecure` (limit ~7 min), wyciszone logi. | UkoĹ„czono |
| **Pobranie nazwy konta** | Po zalogowaniu pobierana jest nazwa konta ze Steam (`steamcommunity`/`store`) i wyĹ›wietlana jako â€žWitaj, <nazwa>â€ť. | UkoĹ„czono |
| **Branding i ikony** | Logo aplikacji w oknie; generowanie wielorozmiarowego `.ico`; ustawienie `iconphoto`/`iconbitmap`; duĹĽy nagĹ‚Ăłwek i wyĹ›rodkowanie w LoginView. | UkoĹ„czono |
| **UI: powitanie i tryb cookie** | NagĹ‚Ăłwek w SearchView: â€žWitaj, â€¦â€ť, przycisk Wyloguj, dynamiczna etykieta â€žBrak Cookie â€“ funkcjonalnoĹ›Ä‡ ograniczonaâ€ť. | UkoĹ„czono |
| **Taxonomia i nazewnictwo** | Refaktor kategorii (oddzielne â€žSnajperskieâ€ť), dodano MP7, peĹ‚en zestaw noĹĽy z gwiazdkÄ… â€žâ…â€ť, obsĹ‚uga wariantu â€žVanillaâ€ť (bez wear i separatora). | UkoĹ„czono |
| **Obrazek przedmiotu** | Sekcja obrazu w ResultsView: asynchroniczne pobieranie i skalowanie, LRU cache obrazkĂłw, placeholder gdy brak. | UkoĹ„czono |
| **Sortowanie tabeli historii** | Klikalne nagĹ‚Ăłwki Cena/Data z przeĹ‚Ä…czaniem kierunku i strzaĹ‚kami; domyĹ›lnie najnowsze na gĂłrze. | UkoĹ„czono |
| **AutouzupeĹ‚nianie onâ€‘demand** | Przycisk â€žZaktualizuj listÄ™ przedmiotĂłwâ€ť, pasek postÄ™pu + ETA i anulowanie; zapis do `src/suggestions.txt`. | UkoĹ„czono |
| **Komunikat o braku historii** | Na wykresie pojawia siÄ™ informacja â€žBrak historii cen (wymagane cookie)â€ť gdy brak danych/cookie. | UkoĹ„czono |

### CS2 Skin Analyzer v0.3 (TydzieĹ„ 3):

#### Ekran Wyszukiwania

![gui_search_v0.3](https://github.com/sqnlol/dao/blob/main/src/img/gui_search_v0.3.png?raw=true)

#### Ekran WynikĂłw

![gui_result_v0.3](https://github.com/sqnlol/dao/blob/main/src/img/gui_result_v0.3.png?raw=true)

| Data | Opis Zmiany / DziaĹ‚ania | Status |
| :--- | :--- | :--- |
| **Widok Wyszukiwania** | Zamiast rÄ™cznego wpisywania nazwy caĹ‚ej skĂłrki uĹĽytkownik wybiera bazowÄ… nazwÄ™ i wariant z predefiniowanej listy. | UkoĹ„czono |
| **Wykres SprzedaĹĽy** | Dodano wykres historycznych transakcji w `ResultsView` (Matplotlib) z wyborem zakresu: tydzieĹ„ / miesiÄ…c / ogĂłĹ‚em. | UkoĹ„czono |
| **WyĹ›wietlanie Aktualnych Ofert** | Po dodaniu nowych funkcji pojawiĹ‚ siÄ™ bĹ‚Ä…d w peĹ‚nym wyĹ›wietlaniu ofert â€“ trwa naprawa parsowania/odĹ›wieĹĽania. | W trakcie naprawy |

### CS2 Skin Analyzer v0.2 (TydzieĹ„ 2):

#### Ekran Logowania

![gui_login_v0.2](https://github.com/sqnlol/dao/blob/main/src/img/gui_login_v0.2.png?raw=true)

#### Ekran Wyszukiwania

![gui_search_v0.2](https://github.com/sqnlol/dao/blob/main/src/img/gui_search_v0.2.png?raw=true)

#### Ekran WynikĂłw (schowane dane historyczne)

![gui_result1_v0.2](https://github.com/sqnlol/dao/blob/main/src/img/gui_result1_v0.2.png?raw=true)

#### Ekran WynikĂłw (widoczne dane historyczne)

![gui_result2_v0.2](https://github.com/sqnlol/dao/blob/main/src/img/gui_result2_v0.2.png?raw=true)

| Data | Opis Zmiany / DziaĹ‚ania | Status |
| :--- | :--- | :--- |
| **ZaleĹĽnoĹ›ci** | Dodano plik `requirements.txt` do zarzÄ…dzania zaleĹĽnoĹ›ciami. | UkoĹ„czono |
| **Kontrola Wersji** | Dodano plik `.gitignore` (ignorowanie plikĂłw binarnych i bazy danych `steam_market.db`). | UkoĹ„czono |
| **Architektura Danych** | **Kluczowa zmiana**: Wprowadzenie koniecznoĹ›ci podawania cookie `steamLoginSecure` w celu ominiÄ™cia blokad API i dostÄ™pu do peĹ‚nej historii cen. | UkoĹ„czono |
| **Widok 1: Logowanie** | Stworzenie ekranu `LoginView.py` do wprowadzania wymaganego klucza cookie. | UkoĹ„czono |
| **Logowanie** | Dodanie logowania poprzez Steam, aby kaĹĽdy uĹĽytkownik korzystaĹ‚ ze swojego wĹ‚asnego cookie | W planach |
| **Widok 2: Wyszukiwanie** | Stworzenie ekranu `SearchView.py` z peĹ‚nym zestawem filtrĂłw: wybĂłr jakoĹ›ci przedmiotu oraz checkbox na StatTrakâ„˘. | UkoĹ„czono |
| **AutouzupeĹ‚nianie** | Dodanie autouzupeĹ‚niania nazw skĂłrek po wpisaniu pasujÄ…cych nazw. | W toku |
| **Logowanie** | Dodano tymczasowe okno konsolowe/logi do `SearchView` informujÄ…ce o statusie operacji (pobieranie, zapis, bĹ‚Ä™dy). | UkoĹ„czono |
| **Widok 3: Wyniki** | Stworzenie ekranu `ResultsView.py` wyĹ›wietlajÄ…cego: 10 najtaĹ„szych aktualnych ofert, historyczne min/max ceny, oraz rozwijanÄ… tabelÄ™ historycznych danych ze steamcommunity.com/market/pricehistory/. | UkoĹ„czono |
| **Sortowanie tabel** | Dodanie moĹĽliwoĹ›ci sortowania rekordĂłw w zaleĹĽnoĹ›ci od Daty lub Ceny sprzedaĹĽy | W planach |
| **Nawigacja** | Dodano przycisk powrotu z ekranu wynikĂłw do wyszukiwarki. | UkoĹ„czono |
| **Baza Danych** | WdroĹĽenie `database.py` i SQLite do **agregowania i przechowywania** pobranych rekordĂłw sprzedaĹĽy, z unikalnym kluczem zĹ‚oĹĽonym, zapobiegajÄ…cym duplikatom. | UkoĹ„czono |

### CS Skin Analyzer v0.1 (TydzieĹ„ 1)

![gui_v0.1](https://github.com/sqnlol/dao/blob/main/src/img/gui_v0.1.png?raw=true)

| Data | Opis Zmiany / DziaĹ‚ania | Status |
| :--- | :--- | :--- |
| **PoczÄ…tek Projektu** | Uruchomienie aplikacji poprzez konsolÄ™ (`python main.py`). | UkoĹ„czono |
| **Architektura** | Stworzenie pierwszej, szkieletowej struktury kodu i wstÄ™pnych moduĹ‚Ăłw. | UkoĹ„czono |
| **Interfejs Graficzny** | Pierwsza wersja interfejsu graficznego (GUI) za pomocÄ… `tkinter`. | UkoĹ„czono |
| **Wizualizacja** | WyĹ›wietlanie statycznej, przykĹ‚adowej tabeli w GUI. | UkoĹ„czono |
| **Deployment** | PrĂłba kompilacji projektu do formatu wykonywalnego `.exe`. | W toku |
| **WspĂłĹ‚praca** | Integracja kodu z systemem kontroli wersji GitHub. | UkoĹ„czono |
| **Wyzwania API** | Stwierdzenie problemĂłw z pobieraniem danych z API Steam (blokowanie zapytaĹ„ bez nagĹ‚ĂłwkĂłw przeglÄ…darki/cookie). | Napotkano |
| **Alternatywy** | PoczÄ…tkowe prĂłby pracy z zewnÄ™trznymi API (porzucone na rzecz bezpoĹ›redniego dostÄ™pu Steam). | W toku |

***

import requests
import re
import time
import json
import sys
import random
from urllib.parse import quote

from src import resource_paths

SUGGESTIONS_FILE_PATH = resource_paths.get_writable_suggestions_path()
SUGGESTIONS_PROGRESS_PATH = resource_paths.get_data_path('suggestions.progress.json')
SUGGESTIONS_PARTIAL_PATH = resource_paths.get_data_path('suggestions.partial.txt')

# ------------------------------------------------------------------
# STAŁE
# ------------------------------------------------------------------
WEAR_PATTERNS = {
    "(Factory New)": "Factory New",
    "(Minimal Wear)": "Minimal Wear",
    "(Field-Tested)": "Field-Tested",
    "(Well-Worn)": "Well-Worn",
    "(Battle-Scarred)": "Battle-Scarred"
}

base_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
    'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    # Lżejszy Accept żeby zwiększyć szansę na JSON, nie pełny HTML
    'Accept': 'application/json,text/javascript,*/*;q=0.9'
}

# ------------------------------------------------------------------
# POMOCNICZE: BEZPIECZNE GET Z BACKOFFEM (429/503)
# ------------------------------------------------------------------
def _http_get_with_backoff(url, headers=None, params=None, timeout=30, max_retries=2, initial_sleep=0.8, metrics=None):
    """GET z backoffem dla 429/503 + losowy jitter; aktualizuje metrics['retries']."""
    sleep_time = initial_sleep
    attempt = 0
    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        if resp.status_code not in (429, 503):
            return resp
        jitter = random.uniform(0.0, 0.25)
        wait = sleep_time + jitter
        print(f"Ostrzeżenie: HTTP {resp.status_code} dla {url}. Odczekuję {wait:.2f}s i ponawiam...", file=sys.stderr)
        attempt += 1
        if metrics is not None:
            metrics['retries'] = metrics.get('retries', 0) + 1
        if attempt > max_retries:
            return resp
        time.sleep(wait)
        sleep_time *= 1.6

# ------------------------------------------------------------------
# FUNKCJA POMOCNICZA DO KONWERSJI CEN
# ------------------------------------------------------------------
def _convert_price_to_float(price_str):
    """Konwertuje string ceny (np. "168,32 zł") na float (np. 168.32)."""
    if not price_str:
        return None
    try:
        # Usuń walutę, białe znaki i zamień przecinek na kropkę
        cleaned_str = re.sub(r"[^\d,\.]", "", price_str).replace(",", ".")
        return float(cleaned_str)
    except (ValueError, TypeError):
        return None

# ------------------------------------------------------------------
# PARSOWANIE NAZW
# ------------------------------------------------------------------
def parse_market_name(market_hash_name):
    """Rozbija pełną nazwę rynku Steam na części: typ, skin (name), wear i flagę StatTrak™.

    Obsługa kolejności dla noży: "★ StatTrak™ <Typ Noża> | <Skin> (<Wear>)" lub bez StatTrak™.
    Jeśli brak skina (lista pusta), nazwa może być: "★ StatTrak™ <Typ Noża> (<Wear>)" albo bez wear jeśli nie występuje.
    """
    original = market_hash_name
    name_parts = {'type': 'Unknown', 'name': original, 'wear': None, 'stattrak': False}

    # 1. Gwiazdka (noże) – musi być przed StatTrak™ w naszej konwencji
    is_knife = False
    if market_hash_name.startswith("★ "):
        is_knife = True
        market_hash_name = market_hash_name[2:]  # usuń "★ "

    # 2. StatTrak™ (po gwiazdce jeśli nóż)
    if market_hash_name.startswith("StatTrak™ "):
        name_parts['stattrak'] = True
        market_hash_name = market_hash_name.replace("StatTrak™ ", "", 1)

    # 3. Wear wzorzec
    for pattern, wear_name in WEAR_PATTERNS.items():
        # Wear zwykle występuje na końcu w nawiasach, ale zachowujemy prostą heurystykę obecności patternu
        if pattern in market_hash_name:
            name_parts['wear'] = wear_name
            market_hash_name = market_hash_name.replace(f" {pattern}", "")
            break

    # 4. Rozbicie typu i skina po separatorze " | "
    if " | " in market_hash_name:
        parts = market_hash_name.split(" | ")
        if len(parts) == 2:
            name_parts['type'] = parts[0]
            name_parts['name'] = parts[1]
        else:
            name_parts['name'] = market_hash_name
            if is_knife:
                name_parts['type'] = parts[0]
    else:
        # Brak separatora – dla noży bez skina traktuj całość jako typ
        if is_knife:
            name_parts['type'] = market_hash_name
            name_parts['name'] = ""
        else:
            # Kontenery itd.
            if " Case" in market_hash_name or " Capsule" in market_hash_name:
                name_parts['type'] = "Container"
                name_parts['name'] = market_hash_name
            else:
                name_parts['name'] = market_hash_name

    # 5. Jeśli to nóż, a typ nie rozpoznany, ustaw ogólny typ
    if is_knife and not name_parts['type']:
        name_parts['type'] = 'Knife'
    return name_parts

# ------------------------------------------------------------------
# API: HISTORIA CEN
# ------------------------------------------------------------------
def get_price_history(market_hash_name, login_cookie, currency_code=6):
    """Pobiera historię cen z Steam API.
    
    Args:
        currency_code: Kod waluty Steam API (1=USD, 3=EUR, 6=PLN)
    """
    if not login_cookie:
        print("Błąd: Próba pobrania historii cen bez ciasteczka.", file=sys.stderr)
        return None
    try:
        url = "https://steamcommunity.com/market/pricehistory/"
        headers = base_headers.copy()
        headers['Cookie'] = f"steamLoginSecure={login_cookie}"
        params = {
            'appid': 730,
            'market_hash_name': market_hash_name,
            'currency': currency_code,
        }
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('prices'):
                history = []
                for entry in data['prices']:
                    dt_str = entry[0]  # np. "Nov 11 2013 01: +0"
                    # Usuń sufiks ": +0" i wczytaj do datetime jako UTC
                    try:
                        base = dt_str.split(':')[0]  # "Nov 11 2013 01"
                        from datetime import datetime
                        import calendar
                        dt = datetime.strptime(base, "%b %d %Y %H")
                        ts = calendar.timegm(dt.timetuple())  # traktuj jako UTC
                        display = dt.strftime("%Y-%m-%d %H:00")
                    except Exception:
                        # Fallback do wartości oryginalnych, jeśli parsowanie się nie uda
                        ts = int(time.time())
                        display = dt_str
                    history.append({
                        'sale_date_str': display,
                        'price': entry[1],
                        'sale_timestamp': ts,
                    })
                return history
            else:
                return []
        else:
            snippet = ''
            try:
                snippet = response.text[:120]
            except Exception:
                snippet = ''
            print(f"Błąd połączenia z API Steam (historia cen): {response.status_code} {response.reason} for url: {response.url} | body: {snippet}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Błąd sieci (historia cen): {e}", file=sys.stderr)
        return None

# ------------------------------------------------------------------
# API: AKTUALNE OFERTY (LISTINGS) - POPRAWIONE PARSOWANIE
# ------------------------------------------------------------------
def get_market_listings(market_hash_name, login_cookie=None, count=10, currency_code=6):
    """Pobiera aktualne oferty z endpointu /render/. Nie wymaga cookie.

    Args:
        currency_code: Kod waluty Steam API (1=USD, 3=EUR, 6=PLN)

    Zwraca słownik dostosowany do ResultsView:
    {
        'listings': [ {'price_float': float|None, 'fee': float|None} ],
        'total_count': int,
        'lowest_price': str|None,
        'highest_buy_order': str|None
    }
    """
    headers = base_headers.copy()
    if login_cookie:
        headers['Cookie'] = f"steamLoginSecure={login_cookie}"

    url = f"https://steamcommunity.com/market/listings/730/{quote(market_hash_name)}/render/"

    params = {
        'query': '',
        'start': 0,
        'count': min(max(count, 1), 100),  # bezpieczne widełki
        'country': 'PL',
        'language': 'polish',
        'currency': currency_code
    }

    try:
        metrics = {'retries': 0, 'pages_loaded': 1}
        response = _http_get_with_backoff(url, headers=headers, params=params, timeout=30, max_retries=2, initial_sleep=0.8, metrics=metrics)
        
        if response.status_code != 200:
            print(f"Błąd połączenia z API Steam (oferty): {response.status_code} {response.reason} for url: {url}", file=sys.stderr)
            return None

        # Uwaga: czasem API zwraca literalne `null` -> Python None
        try:
            data = response.json()
        except json.JSONDecodeError:
            print("Błąd dekodowania JSON z API Steam (oferty).", file=sys.stderr)
            return None

        if not isinstance(data, dict) or data is None:
            print("Błąd API: pusta odpowiedź lub nieprawidłowy JSON dla ofert (None).", file=sys.stderr)
            return None

        if data.get('success') is False:
            # Zwracamy pustą strukturę zamiast None żeby GUI zachowało spójność
            print("Błąd API: Sukces=False w odpowiedzi ofert.", file=sys.stderr)
            return {
                'listings': [],
                'total_count': 0,
                'lowest_price': None
            }

        total_count = data.get('total_count', 0)
        listings_html = data.get('results_html') or ''
        
        # --- POPRAWIONA LOGIKA PARSOWANIA: listinginfo najpierw, HTML uzupełniająco ---
        listings = []
        listinginfo = data.get('listinginfo') if isinstance(data, dict) else None
        if isinstance(listinginfo, dict):
            for _, info in list(listinginfo.items()):
                try:
                    price_int = info.get('converted_price')
                    fee_int = info.get('converted_fee')
                    if price_int is None or fee_int is None:
                        continue
                    total = (price_int + fee_int) / 100.0
                    listings.append({'price_float': float(total), 'fee': float(fee_int) / 100.0})
                    if len(listings) >= count:
                        break
                except Exception as e:
                    print(f"Ostrzeżenie: listinginfo rekord pominięty: {e}", file=sys.stderr)
                    continue

        if len(listings) < count and listings_html:
            try:
                # Uogólniony wzorzec: bierzemy też wiersze bez "recent"
                listing_rows = re.findall(r'<div class="market_listing_row[^\"]*"(.*?)</div></div>', listings_html, re.DOTALL)
                for row_html in listing_rows:
                    price_match = re.search(r'market_listing_price_with_fee">([\s\S]*?)</span>', row_html)
                    fee_match = re.search(r'market_listing_fee">([\s\S]*?)</span>', row_html)
                    price_str = price_match.group(1).strip() if price_match else None
                    fee_str = fee_match.group(1).strip() if fee_match else None
                    price_float = _convert_price_to_float(price_str)
                    fee_float = _convert_price_to_float(fee_str)
                    listings.append({'price_float': price_float, 'fee': fee_float})
                    if len(listings) >= count:
                        break
            except Exception as e:
                print(f"Ostrzeżenie: błąd parsowania HTML: {e}", file=sys.stderr)
                
        # --- KONIEC POPRAWKI ---

        # Paginacja: jeśli total_count > już zebrane i nadal za mało, dołóż następne strony
        MAX_PAGES = 5
        start_offset = params['start']
        while len(listings) < count and total_count > len(listings) and metrics['pages_loaded'] < MAX_PAGES:
            start_offset += params['count']
            page_params = params.copy()
            page_params['start'] = start_offset
            try:
                time.sleep(random.uniform(0.4, 0.7))
                page_resp = _http_get_with_backoff(url, headers=headers, params=page_params, timeout=30, max_retries=1, initial_sleep=0.7, metrics=metrics)
                if page_resp.status_code != 200:
                    break
                page_data = page_resp.json()
                page_html = page_data.get('results_html') or ''
                page_listinginfo = page_data.get('listinginfo') if isinstance(page_data, dict) else None
                # Najpierw JSON
                if isinstance(page_listinginfo, dict):
                    for _, info in list(page_listinginfo.items()):
                        price_int = info.get('converted_price')
                        fee_int = info.get('converted_fee')
                        if price_int is None or fee_int is None:
                            continue
                        total = (price_int + fee_int) / 100.0
                        listings.append({'price_float': float(total), 'fee': float(fee_int) / 100.0})
                        if len(listings) >= count:
                            break
                # Potem HTML
                if len(listings) < count and page_html:
                    page_rows = re.findall(r'<div class=\"market_listing_row[^\"]*\"(.*?)</div></div>', page_html, re.DOTALL)
                    for row_html in page_rows:
                        price_match = re.search(r'market_listing_price_with_fee\">([\s\S]*?)</span>', row_html)
                        fee_match = re.search(r'market_listing_fee\">([\s\S]*?)</span>', row_html)
                        price_str = price_match.group(1).strip() if price_match else None
                        fee_str = fee_match.group(1).strip() if fee_match else None
                        price_float = _convert_price_to_float(price_str)
                        fee_float = _convert_price_to_float(fee_str)
                        listings.append({'price_float': price_float, 'fee': fee_float})
                        if len(listings) >= count:
                            break
                metrics['pages_loaded'] += 1
            except Exception as e:
                print(f"Ostrzeżenie: błąd paginacji ofert: {e}", file=sys.stderr)
                break

        # Sortowanie po cenie (None na końcu)
        listings.sort(key=lambda x: (x['price_float'] is None, x.get('price_float', 0.0)))

        # Wyznacz najniższą cenę bezpośrednio z sparsowanych ofert, aby była spójna z tabelą
        lowest_price = data.get('lowest_price')
        lowest_price_float = _convert_price_to_float(lowest_price)
        try:
            computed_min = next((it.get('price_float') for it in listings if it.get('price_float') is not None), None)
        except Exception:
            computed_min = None
        if computed_min is not None:
            lowest_price_float = computed_min
            lowest_price = f"{computed_min:.2f} PLN"

        # Fallback jeśli brak najniższej oferty
        if lowest_price is None:
            overview = _fetch_price_overview(market_hash_name, headers=headers)
            if overview:
                lowest_price = overview.get('lowest_price') or lowest_price
                lowest_price_float = overview.get('lowest_price_float') or lowest_price_float

        return {
            'listings': listings,
            'total_count': total_count,
            'lowest_price': lowest_price,
            'lowest_price_float': lowest_price_float,
            'meta': metrics
        }
    except Exception as e:
        print(f"Nieoczekiwany błąd podczas parsowania ofert: {e}", file=sys.stderr)
        return None

def get_market_listings_page(market_hash_name, login_cookie=None, start=0, count=10):
    """Pobiera pojedynczą stronę ofert (on-demand paginacja)."""
    headers = base_headers.copy()
    if login_cookie:
        headers['Cookie'] = f"steamLoginSecure={login_cookie}"
    url = f"https://steamcommunity.com/market/listings/730/{quote(market_hash_name)}/render/"
    params = {
        'query': '',
        'start': start,
        'count': min(max(count, 1), 100),
        'country': 'PL',
        'language': 'polish',
        'currency': 6
    }
    try:
        resp = _http_get_with_backoff(url, headers=headers, params=params, timeout=30, max_retries=2, initial_sleep=0.8, metrics={})
        if resp.status_code != 200:
            return None
        try:
            data = resp.json()
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict) or data.get('success') is False:
            return None
        total_count = data.get('total_count', 0)
        listings = []
        listinginfo = data.get('listinginfo') if isinstance(data, dict) else None
        if isinstance(listinginfo, dict):
            for _, info in list(listinginfo.items()):
                price_int = info.get('converted_price')
                fee_int = info.get('converted_fee')
                if price_int is None or fee_int is None:
                    continue
                total = (price_int + fee_int) / 100.0
                listings.append({'price_float': float(total), 'fee': float(fee_int) / 100.0})
                if len(listings) >= count:
                    break
        if len(listings) < count:
            html = data.get('results_html') or ''
            if html:
                try:
                    rows = re.findall(r'<div class="market_listing_row[^"]*"(.*?)</div></div>', html, re.DOTALL)
                    for row_html in rows:
                        price_match = re.search(r'market_listing_price_with_fee">([\s\S]*?)</span>', row_html)
                        fee_match = re.search(r'market_listing_fee">([\s\S]*?)</span>', row_html)
                        price_str = price_match.group(1).strip() if price_match else None
                        fee_str = fee_match.group(1).strip() if fee_match else None
                        listings.append({'price_float': _convert_price_to_float(price_str), 'fee': _convert_price_to_float(fee_str)})
                        if len(listings) >= count:
                            break
                except Exception:
                    pass
        lowest_price = data.get('lowest_price')
        return {
            'listings': listings,
            'total_count': total_count,
            'lowest_price': lowest_price,
            'lowest_price_float': _convert_price_to_float(lowest_price)
        }
    except Exception:
        return None

    
# Alias dla kompatybilności ze starszym kodem / dokumentacją
def fetch_market_listings(market_hash_name, login_cookie=None, count=10):
    return get_market_listings(market_hash_name, login_cookie=login_cookie, count=count)
# ------------------------------------------------------------------
# API: LISTA WSZYSTKICH PRZEDMIOTÓW (DLA SUGESTII)
# ------------------------------------------------------------------
def fetch_all_csgo_items(
    output_file_path: str = SUGGESTIONS_FILE_PATH,
    page_size: int = 100,
    resume: bool = True,
    progress_path: str = SUGGESTIONS_PROGRESS_PATH,
    partial_path: str = SUGGESTIONS_PARTIAL_PATH,
    log_callback=None,
    cancel_event=None,
):
    """
    Pobiera listę wszystkich przedmiotów CS2 (appid=730) z endpointu search/render
    i zapisuje ją do pliku suggestions.txt. Zwraca listę nazw (posortowaną).

    - Używa parametrów: appid=730, sortowanie po nazwie, kraj PL, język polish, waluta PLN.
    - Paginacja po "start" i "count".
    """
    all_items = set()
    start = 0
    total_count = None
    count = max(10, min(int(page_size), 100))
    metrics = { 'retries': 0 }
    # Przy wznowieniu: wczytaj postęp i dotychczas zebrane wpisy
    partial_file = None
    try:
        if resume:
            # start i zebrane elementy
            import os
            if os.path.exists(progress_path):
                try:
                    prog = json.load(open(progress_path, 'r', encoding='utf-8'))
                    start = int(prog.get('next_start', 0))
                    total_count = prog.get('total_count')
                except Exception:
                    start = 0
            # wczytaj dotychczas zapisane wpisy do zbioru (unikalność)
            if os.path.exists(partial_path):
                try:
                    with open(partial_path, 'r', encoding='utf-8') as pf:
                        for ln in pf:
                            nm = ln.strip()
                            if nm:
                                all_items.add(nm)
                except Exception:
                    pass
        # otwórz plik partial do dopisywania
        import os
        os.makedirs(os.path.dirname(partial_path) or '.', exist_ok=True)
        os.makedirs(os.path.dirname(output_file_path) or '.', exist_ok=True)
        os.makedirs(os.path.dirname(progress_path) or '.', exist_ok=True)
        partial_file = open(partial_path, 'a', encoding='utf-8')
    except Exception as e:
        print(f"Ostrzeżenie: problem z inicjalizacją plików wznowienia: {e}", file=sys.stderr)

    # Pomiar czasu dla ETA
    start_time = time.time()
    last_time = start_time
    processed_items_for_eta = 0
    try:
        while True:
            # Sprawdzenie anulowania przed pobraniem strony
            if cancel_event is not None and getattr(cancel_event, 'is_set', lambda: False)():
                if callable(log_callback):
                    try:
                        log_callback("Anulowano pobieranie (przed kolejnym żądaniem).")
                    except Exception:
                        pass
                break
            params = {
                'query': '',
                'start': start,
                'count': count,
                'norender': 1,
                'appid': 730,
                'search_descriptions': 0,
                'sort_column': 'name',
                'sort_dir': 'asc',
                'country': 'PL',
                'language': 'polish',
                'currency': 6
            }
            url = "https://steamcommunity.com/market/search/render/"
            resp = _http_get_with_backoff(url, headers=base_headers, params=params, timeout=40, max_retries=2, initial_sleep=0.9, metrics=metrics)
            if resp.status_code != 200:
                print(f"Błąd API sugestii: {resp.status_code} {resp.reason}", file=sys.stderr)
                # Zapisz stan do wznowienia
                try:
                    if resume:
                        json.dump({'next_start': start, 'total_count': total_count}, open(progress_path, 'w', encoding='utf-8'))
                except Exception:
                    pass
                break
            try:
                data = resp.json()
            except json.JSONDecodeError:
                print("Błąd dekodowania JSON dla sugestii.", file=sys.stderr)
                try:
                    if resume:
                        json.dump({'next_start': start, 'total_count': total_count}, open(progress_path, 'w', encoding='utf-8'))
                except Exception:
                    pass
                break
            if not isinstance(data, dict) or data.get('success') is False:
                print("API sugestii zwróciło błąd/niepowodzenie.", file=sys.stderr)
                try:
                    if resume:
                        json.dump({'next_start': start, 'total_count': total_count}, open(progress_path, 'w', encoding='utf-8'))
                except Exception:
                    pass
                break

            total_count = data.get('total_count', 0) if total_count is None else total_count
            results = data.get('results') or []
            if not results:
                # Brak wyników na tej stronie – zakończ jeżeli doszliśmy do końca
                if total_count is not None and start >= total_count:
                    break
                else:
                    # ostrożny fallback – przerwij, by uniknąć pętli
                    print("Brak wyników na stronie, przerywam.", file=sys.stderr)
                    break

            newly_added = 0
            for item in results:
                # Sprawdzenie anulowania wewnątrz pętli przetwarzania wyników
                if cancel_event is not None and getattr(cancel_event, 'is_set', lambda: False)():
                    if callable(log_callback):
                        try:
                            log_callback("Anulowano pobieranie (przetwarzanie wyników strony).")
                        except Exception:
                            pass
                    break
                name = item.get('hash_name') or item.get('market_hash_name') or item.get('name')
                if isinstance(name, str):
                    nm = name.strip()
                    if nm and nm not in all_items:
                        all_items.add(nm)
                        if partial_file:
                            try:
                                partial_file.write(nm + '\n')
                            except Exception:
                                pass
                        newly_added += 1

            # flush i zapis progresu
            try:
                if partial_file:
                    partial_file.flush()
                if resume:
                    json.dump({'next_start': start + len(results), 'total_count': total_count}, open(progress_path, 'w', encoding='utf-8'))
            except Exception:
                pass

            start += len(results)
            # Jeśli wiemy już total_count, przerwij po osiągnięciu końca
            if total_count is not None and start >= total_count:
                break
            # logowanie postępu
            try:
                if callable(log_callback):
                    # Oblicz ETA (tylko jeśli znamy total_count i mamy prędkość > 0)
                    now = time.time()
                    elapsed = now - start_time
                    current_count = len(all_items)
                    eta_seconds = -1
                    if total_count and total_count > 0 and current_count > 0:
                        speed = current_count / elapsed  # items per second
                        remaining = max(0, total_count - current_count)
                        if speed > 0:
                            eta_seconds = int(remaining / speed)
                    # Przyjazny format ETA
                    if eta_seconds >= 0:
                        mins = eta_seconds // 60
                        secs = eta_seconds % 60
                        eta_str = f"ETA {mins:02d}:{secs:02d}"
                    else:
                        eta_str = "ETA ?"
                    # Log tekstowy z ETA
                    log_callback(f"Sugestie: {current_count} / {total_count or '?'} (offset {start - len(results)}), +{newly_added} | retries={metrics.get('retries',0)} | {eta_str}")
                    # Log strukturalny dla progresu (prefiks PROGRESS) rozszerzony o ETA
                    total_for_progress = total_count if total_count is not None else 0
                    log_callback(f"PROGRESS {current_count} {total_for_progress} {metrics.get('retries',0)} {eta_seconds}")
            except Exception:
                pass
            # krótka pauza dla uprzejmości względem API i ograniczeń
            # Sprawdzenie anulowania przed uśpieniem
            if cancel_event is not None and getattr(cancel_event, 'is_set', lambda: False)():
                if callable(log_callback):
                    try:
                        log_callback("Anulowano pobieranie (po stronie).")
                    except Exception:
                        pass
                break
            time.sleep(random.uniform(0.45, 0.9))

        items_sorted = sorted(all_items)
        # Finalizacja: jeśli ukończono, przenieś partial -> output i usuń progress
        if output_file_path and (total_count is None or start >= (total_count or 0)):
            try:
                import os
                os.makedirs(os.path.dirname(output_file_path) or '.', exist_ok=True)
                # Nadpisz ostateczny plik uporządkowaną listą (deterministyczny wynik)
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    for n in items_sorted:
                        f.write(n + '\n')
                # usuń partial i progress
                try:
                    if resume:
                        if os.path.exists(progress_path):
                            os.remove(progress_path)
                        if os.path.exists(partial_path):
                            os.remove(partial_path)
                except Exception:
                    pass
                print(f"Zapisano sugestie do pliku: {output_file_path} (pozycji: {len(items_sorted)})")
            except Exception as e:
                print(f"Błąd zapisu pliku sugestii: {e}", file=sys.stderr)
        if cancel_event is not None and getattr(cancel_event, 'is_set', lambda: False)():
            # Anulowano – zwróć None aby kontroler mógł zasygnalizować przerwanie
            return None
        return items_sorted
    except Exception as e:
        print(f"Błąd sieci (sugestie): {e}", file=sys.stderr)
        return None
    finally:
        try:
            if partial_file:
                partial_file.close()
        except Exception:
            pass

# ------------------------------------------------------------------
# DODATKOWE API: priceoverview i itemordershistogram
# ------------------------------------------------------------------
def _fetch_price_overview(market_hash_name, headers, timeout=20):
    """Pobiera priceoverview dla uzyskania lowest_price i median_price."""
    try:
        url = "https://steamcommunity.com/market/priceoverview/"
        params = {
            'appid': 730,
            'market_hash_name': market_hash_name,
            'country': 'PL',
            'currency': 6
        }
        resp = _http_get_with_backoff(url, headers=headers, params=params, timeout=timeout, max_retries=2, initial_sleep=0.8, metrics={})
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data or data.get('success') is False:
            return None
        lowest_price = data.get('lowest_price')
        median_price = data.get('median_price')
        return {
            'lowest_price': lowest_price,
            'lowest_price_float': _convert_price_to_float(lowest_price),
            'median_price': median_price,
            'median_price_float': _convert_price_to_float(median_price)
        }
    except Exception as e:
        print(f"Ostrzeżenie: błąd priceoverview: {e}", file=sys.stderr)
        return None

def _fetch_item_nameid(market_hash_name, headers, timeout=20):
    """Pobiera stronę przedmiotu i wyciąga item_nameid potrzebne do histogramu zleceń."""
    try:
        url = f"https://steamcommunity.com/market/listings/730/{quote(market_hash_name)}"
        resp = _http_get_with_backoff(url, headers=headers, timeout=timeout, max_retries=2, initial_sleep=0.8, metrics={})
        if resp.status_code != 200:
            return None
        html = resp.text
        m = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", html)
        if m:
            return m.group(1)
        # alternatywny fallback (rzadziej potrzebny)
        m2 = re.search(r"item_nameid\"\s*:\s*\"?(\d+)\"?", html)
        if m2:
            return m2.group(1)
        return None
    except Exception as e:
        print(f"Ostrzeżenie: błąd pobierania item_nameid: {e}", file=sys.stderr)
        return None


def get_item_image_url(market_hash_name, login_cookie=None, currency_code=6, timeout=12):
    """Pobiera URL obrazka przedmiotu (og:image) z strony listingowej.

    Args:
        currency_code: Kod waluty Steam API (1=USD, 3=EUR, 6=PLN)

    Zwraca URL (string) lub None przy błędzie.
    """
    try:
        headers = base_headers.copy()
        if login_cookie:
            headers['Cookie'] = f"steamLoginSecure={login_cookie}"
        # Dodaj parametr currency do URL
        url = f"https://steamcommunity.com/market/listings/730/{quote(market_hash_name)}?currency={currency_code}"
        resp = _http_get_with_backoff(url, headers=headers, timeout=timeout, max_retries=1, initial_sleep=0.6, metrics={})
        if resp is None or resp.status_code != 200:
            return None
        html = resp.text
        # Najpierw spróbuj metatagu og:image
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
        if m:
            return m.group(1)
        # Fallback: element <img ... class="market_listing_largeimage" src="...">
        m2 = re.search(r'<img[^>]*class="[^"]*largeimage[^"]*"[^>]*src="([^"]+)"', html)
        if m2:
            return m2.group(1)
        # Fallback alternatywny: small preview image
        m3 = re.search(r'<img[^>]*class="[^"]*market_listing_item_img[^"]*"[^>]*src="([^"]+)"', html)
        if m3:
            return m3.group(1)
        # Ostateczny fallback: market search -> icon_url(_large)
        try:
            url2 = "https://steamcommunity.com/market/search/render/"
            params = {
                'query': market_hash_name,
                'appid': 730,
                'start': 0,
                'count': 10,
                'norender': 1,
                'search_descriptions': 0,
                'sort_column': 'name',
                'sort_dir': 'asc',
                'country': 'PL',
                'language': 'polish',
                'currency': currency_code,
            }
            resp2 = _http_get_with_backoff(url2, headers=headers, params=params, timeout=timeout, max_retries=1, initial_sleep=0.5, metrics={})
            if resp2 is None or resp2.status_code != 200:
                return None
            data = resp2.json()
            results = data.get('results') or []
            # Prefer exact match po hash_name
            match = None
            for it in results:
                nm = it.get('hash_name') or it.get('market_hash_name') or it.get('name')
                if isinstance(nm, str) and nm.strip() == market_hash_name:
                    match = it
                    break
            if match is None and results:
                match = results[0]
            if not match:
                return None
            ad = match.get('asset_description') or {}
            icon = ad.get('icon_url_large') or ad.get('icon_url')
            if not icon:
                asset = match.get('asset') or {}
                icon = asset.get('icon_url') or asset.get('icon_url_large')
            if not icon:
                return None
            # Normalizuj ścieżki economy/image
            if icon.startswith('http'):
                return icon.replace('http://', 'https://')
            if icon.startswith('/'):
                return 'https://community.cloudflare.steamstatic.com' + icon
            if icon.startswith('economy/image/'):
                return 'https://community.cloudflare.steamstatic.com/' + icon
            return None
        except Exception as e:
            print(f"Ostrzeżenie: fallback search image_url nieudany: {e}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Ostrzeżenie: błąd pobierania image_url: {e}", file=sys.stderr)
        return None

def _fetch_highest_buy_order_from_histogram(item_nameid, headers, timeout=20):
    """Pobiera histogram zleceń i zwraca highest_buy_order (float i str)."""
    try:
        url = "https://steamcommunity.com/market/itemordershistogram"
        params = {
            'country': 'PL',
            'language': 'polish',
            'currency': 6,
            'item_nameid': item_nameid,
            'two_factor': 0
        }
        resp = _http_get_with_backoff(url, headers=headers, params=params, timeout=timeout, max_retries=2, initial_sleep=0.8, metrics={})
        if resp.status_code != 200:
            return None
        data = resp.json()
        hbo = data.get('highest_buy_order')
        if hbo is None:
            return None
        # najwyższe zlecenie bywa liczbą w stringu, czasem z formatowaniem
        hbo_float = _convert_price_to_float(str(hbo))
        # jeśli API zwraca grosze jako int (np. '12345'), skoryguj
        if hbo_float is None and isinstance(hbo, str) and hbo.isdigit():
            hbo_float = int(hbo) / 100.0
        return {
            'highest_buy_order': str(hbo) if not isinstance(hbo, str) else hbo,
            'highest_buy_order_float': hbo_float
        }
    except Exception as e:
        print(f"Ostrzeżenie: błąd histogramu zleceń: {e}", file=sys.stderr)
        return None
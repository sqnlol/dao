import requests
import re
import time
import json
import sys
import random
from urllib.parse import quote

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
    name_parts = {'type': 'Unknown', 'name': market_hash_name, 'wear': None, 'stattrak': False}
    if market_hash_name.startswith("StatTrak™"):
        name_parts['stattrak'] = True
        market_hash_name = market_hash_name.replace("StatTrak™ ", "")
    for pattern, wear_name in WEAR_PATTERNS.items():
        if pattern in market_hash_name:
            name_parts['wear'] = wear_name
            market_hash_name = market_hash_name.replace(f" {pattern}", "")
            break
    if "★" in market_hash_name:
        name_parts['type'] = "Knife"
        name_parts['name'] = market_hash_name.replace("★ ", "")
    elif "|" in market_hash_name:
        parts = market_hash_name.split(" | ")
        if len(parts) == 2:
            name_parts['type'] = parts[0]
            name_parts['name'] = parts[1]
        else:
            name_parts['name'] = market_hash_name
    elif " Case" in market_hash_name or " Capsule" in market_hash_name:
         name_parts['type'] = "Container"
         name_parts['name'] = market_hash_name
    return name_parts

# ------------------------------------------------------------------
# API: HISTORIA CEN
# ------------------------------------------------------------------
def get_price_history(market_hash_name, login_cookie):
    if not login_cookie:
        print("Błąd: Próba pobrania historii cen bez ciasteczka.", file=sys.stderr)
        return None
    try:
        url = f"https://steamcommunity.com/market/pricehistory/?appid=730&market_hash_name={quote(market_hash_name)}"
        headers = base_headers.copy()
        headers['Cookie'] = f"steamLoginSecure={login_cookie}"
        response = requests.get(url, headers=headers, timeout=10)
        
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
            print(f"Błąd połączenia z API Steam (historia cen): {response.status_code} {response.reason} for url: {url}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Błąd sieci (historia cen): {e}", file=sys.stderr)
        return None

# ------------------------------------------------------------------
# API: AKTUALNE OFERTY (LISTINGS) - POPRAWIONE PARSOWANIE
# ------------------------------------------------------------------
def get_market_listings(market_hash_name, login_cookie=None, count=10):
    """Pobiera aktualne oferty z endpointu /render/. Nie wymaga cookie.

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
        'currency': 6  # PLN (ważne dla spójności formatów cen)
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
def fetch_all_csgo_items():
    print("Rozpoczynanie pobierania pełnej listy przedmiotów z rynku Steam z filtrami...")
    all_items = set()
    start = 0
    total_count = 1
    query = 'appid:730 (tag_weapon OR tag_itemset OR tag_type_hands OR tag_type_knife OR tag_type_container)'
    try:
        while start < total_count:
            url = f"https://steamcommunity.com/market/search/render/?query={quote(query)}&start={start}&count=10&norender=1"
            response = requests.get(url, headers=base_headers, timeout=30)
            if response.status_code != 200:
                print(f"Błąd API sugestii: {response.status_code}. Przerywanie.", file=sys.stderr)
                break
            data = response.json()
            if not data.get('success'):
                print("API sugestii zwróciło błąd. Przerywanie.", file=sys.stderr)
                break
            total_count = data.get('total_count', 0)
            results = data.get('results', [])
            if not results:
                break
            for item in results:
                all_items.add(item['market_hash_name'])
            start += 10
            print(f"Pobrano: {len(all_items)} z {total_count}")
            time.sleep(1) 
        print(f"Pobieranie zakończone. Łącznie {len(all_items)} unikalnych przedmiotów.")
        return sorted(list(all_items))
    except Exception as e:
        print(f"Błąd sieci (sugestie): {e}", file=sys.stderr)
        return None

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
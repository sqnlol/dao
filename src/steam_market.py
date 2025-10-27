import requests
import re
import json
import time
from datetime import datetime
import sys
import urllib.parse

# Stałe
APPID = 730 # CS2/CS:GO

# Wzorce regex do parsowania
WEAR_PATTERNS = [
    r'\((Factory New)\)',
    r'\((Minimal Wear)\)',
    r'\((Field-Tested)\)',
    r'\((Well-Worn)\)',
    r'\((Battle-Scarred)\)'
]
STATTRACK_PATTERN = r'StatTrak™'

# ------------------------------------------------------------------
# PARSOWANIE NAZWY PRZEDMIOTU
# ------------------------------------------------------------------
def parse_market_name(market_hash_name):
    """Parsuje pełną nazwę rynkową na podstawowe elementy."""

    parts = {
        'type': 'Unknown',
        'name': market_hash_name,
        'wear': None,
        'stattrack': False
    }

    # 1. Wykrycie jakości zużycia (Wear)
    for pattern in WEAR_PATTERNS:
        match = re.search(pattern, market_hash_name)
        if match:
            parts['wear'] = match.group(1)
            # Usuń jakość zużycia z nazwy
            market_hash_name = market_hash_name.replace(match.group(0), '').strip()
            break

    # 2. Wykrycie StatTrak
    if re.search(STATTRACK_PATTERN, market_hash_name):
        parts['stattrack'] = True
        # Usuń StatTrak z nazwy
        market_hash_name = market_hash_name.replace('StatTrak™', '').strip()

    # 3. Parsowanie typu i nazwy
    if '|' in market_hash_name:
        # Broń/Nóż: GLOCK-18 | Water Elemental
        type_name, item_name = market_hash_name.split('|', 1)
        parts['type'] = type_name.strip()
        parts['name'] = item_name.strip()
    else:
        # Rękawiczki lub inne przedmioty
        parts['name'] = market_hash_name.strip()
        if 'Gloves' in parts['name'] or 'Hand Wraps' in parts['name']:
            parts['type'] = 'Rękawice'
        elif 'Case' in parts['name']:
            parts['type'] = 'Skrzynka'
        else:
            parts['type'] = 'Inne'

    return parts


# ------------------------------------------------------------------
# POBIERANIE HISTORII CEN
# ------------------------------------------------------------------
def get_price_history(market_hash_name, login_cookie):
    """
    Pobiera historię cen z rynku Steam.

    Wymaga aktywnego cookie 'steamLoginSecure'.
    """

    if not login_cookie:
        print("Błąd: Wymagane cookie 'steamLoginSecure'!", file=sys.stderr)
        return None

    url = 'https://steamcommunity.com/market/pricehistory/'

    params = {
        'appid': APPID,
        'market_hash_name': market_hash_name
    }

    # Cookie do uwierzytelnienia na rynku
    headers = {
        'Cookie': f'steamLoginSecure={login_cookie}'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status() # Wyrzuci wyjątek dla statusów 4xx/5xx

        data = response.json()

        if data.get('success', False) is False:
            print(f"Błąd API: Sukces = False. Sprawdź, czy cookie jest aktualne i czy przedmiot istnieje: {market_hash_name}", file=sys.stderr)
            return None

        # Parsowanie danych
        prices = data.get('prices', [])
        history = []
        for entry in prices:
            # Format: [ "Data", cena (float), liczba_sprzedanych ]
            date_str = entry[0]
            price = entry[1]
            sales = entry[2]

            # Konwersja daty: format "Jan 01 2023 00:00 +0"
            try:
                dt_obj = datetime.strptime(date_str[:-4].strip(), '%b %d %Y %H:%M')
                timestamp = int(dt_obj.timestamp())
                sale_date_str = dt_obj.strftime('%Y-%m-%d %H:%M')
            except ValueError:
                # Awaryjna konwersja (np. jeśli format się zmieni)
                timestamp = 0
                sale_date_str = date_str

            history.append({
                'sale_date_str': sale_date_str,
                'sale_timestamp': timestamp,
                'price': float(price),
                'sales_count': sales
            })

        return history

    except requests.exceptions.RequestException as e:
        print(f"Błąd połączenia z API Steam (historia cen): {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Błąd dekodowania JSON z API Steam.", file=sys.stderr)
        return None


# ------------------------------------------------------------------
# POBIERANIE WSZYSTKICH PRZEDMIOTÓW (DLA AUTOUZUPEŁNIANIA)
# ------------------------------------------------------------------
def fetch_all_csgo_items(appid=APPID):
    """
    Pobiera pełną listę nazw wszystkich przedmiotów z rynku CS2/CS:GO w sposób iteracyjny,
    stosując filtry.
    """
    url = "https://steamcommunity.com/market/search/render/"
    all_item_names = set()
    start = 0
    count = 100
    total_items = 1

    print("Rozpoczynanie pobierania pełnej listy przedmiotów z rynku Steam z filtrami...")

    try:
        while start < total_items:
            params = {
                'query': '',
                'start': start,
                'count': count,
                'appid': appid,
                'norender': 1,
                # NOWE FILTRY w zapytaniu, celujące w skiny i skrzynie
                'category_730_Type[]': [
                    'tag_Weapon',
                    'tag_Knife',
                    'tag_Container'
                ],
                'category_730_Exterior[]': ['tag_Exterior_Factory_New', 'tag_Exterior_Minimal_Wear', 'tag_Exterior_Field-Tested', 'tag_Exterior_Well-Worn', 'tag_Exterior_Battle-Scarred'],
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                print(f"Błąd API: 'success': false przy pobieraniu wszystkich przedmiotów.", file=sys.stderr)
                return None

            total_items = data.get('total_count', 0)

            for item in data.get('results', []):
                # POPRAWKA: Sprawdzenie istnienia klucza
                if 'market_hash_name' in item:
                    all_item_names.add(item['market_hash_name'])
                else:
                    item_id = item.get('asset_description', {}).get('classid')
                    print(f"Ostrzeżenie: Pominięto przedmiot bez 'market_hash_name'. ID klasy: {item_id}", file=sys.stderr)

            print(f"Pobrano: {len(all_item_names)} z {total_items}")

            start += count
            time.sleep(2.0) # Zwiększone opóźnienie dla bezpieczeństwa

        print(f"Pobieranie zakończone. Łącznie {len(all_item_names)} unikalnych przedmiotów.")
        return sorted(list(all_item_names))

    except requests.exceptions.RequestException as e:
        print(f"Błąd połączenia z API Steam przy pobieraniu wszystkich przedmiotów: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Błąd dekodowania JSON z API Steam (wszystkie przedmioty).", file=sys.stderr)
        return None


# ------------------------------------------------------------------
# POBIERANIE AKTUALNYCH OFERT (LISTINGS) - ZMODYFIKOWANE
# ------------------------------------------------------------------
def get_market_listings(market_hash_name, login_cookie, count):
    """
    Pobiera aktualne, najtańsze oferty sprzedaży dla przedmiotu.

    Args:
        market_hash_name (str): Pełna nazwa przedmiotu (market_hash_name).
        login_cookie (str): Cookie uwierzytelniające 'steamLoginSecure'.
        count (int): Liczba ofert do pobrania.

    Returns:
        dict: Słownik zawierający 'listings' (lista ofert), 'total_count',
              'lowest_price' (najniższa oferta widoczna) i 'highest_buy_order'
              (najwyższe zlecenie kupna), lub None w przypadku błędu.
    """

    # 🛑 Zmiana: Ręczne kodowanie nazwy przedmiotu dla całego URL
    encoded_market_hash_name = urllib.parse.quote(market_hash_name)

    # Parametry są teraz puste, bo są już w URL
    params = {
        'query': '',
        'start': 0,
        'count': {count},
        'country': 'PL',
        'language': 'polish',
        'currency': 6
    }

    # Dodanie nagłówka z cookie
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
        'Cookie': f'steamLoginSecure={login_cookie}'
    }

    full_url = f"https://steamcommunity.com/market/listings/{APPID}/{encoded_market_hash_name}/render/"
    try:
        response = requests.get(full_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"DEBUG: Pełny URL zapytania o oferty: {response.request.url}", file=sys.stderr)

        if response.status_code == 429:
            print("BŁĄD: Zostałeś tymczasowo zablokowany przez Steam (Rate Limit - 429).")
            print("Odczekaj kilka minut przed kolejną próbą.")
            return None

        if data.get('success') != True:
            print(f"Błąd API: Sukces = False przy pobieraniu ofert dla: {market_hash_name}", file=sys.stderr)
            return None

        listings = []
        if data.get('listings'):
            for listing_id, listing_data in data['listings'].items():
                converted_price = listing_data.get('converted_price')
                final_price = listing_data.get('converted_price_with_fee')
                final_price_float = final_price / 100.0 if final_price is not None else None
                fee_float = (final_price - converted_price) / 100.0 if final_price and converted_price is not None else None

                listings.append({
                    'listing_id': listing_id,
                    'price_float': final_price_float,
                    'price_str': listing_data.get('converted_price_per_unit', 'N/A'),
                    'fee': fee_float,
                    'steam_id_lister': listing_data.get('steamid_lister')
                })

        lowest_price_str = data.get('lowest_price')
        highest_buy_order_str = data.get('highest_buy_order')

        return {
            'listings': listings,
            'total_count': data.get('total_count', 0),
            'lowest_price': lowest_price_str,
            'highest_buy_order': highest_buy_order_str
        }

    except requests.exceptions.RequestException as e:
        print(f"Błąd połączenia z API Steam (oferty): {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Błąd dekodowania JSON z API Steam (oferty).", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Nieoczekiwany błąd w get_market_listings: {e}", file=sys.stderr)
        return None
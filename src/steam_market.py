import requests
import re
import time
import json
import sys
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
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
}

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
                    history.append({
                        'sale_date_str': entry[0],
                        'price': entry[1],
                        'sale_timestamp': time.mktime(time.strptime(entry[0], "%b %d %Y %H: +0")),
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
def get_market_listings(market_hash_name, login_cookie, count=10):
    if not login_cookie:
        print("Błąd: Próba pobrania ofert bez ciasteczka.", file=sys.stderr)
        return None
        
    headers = base_headers.copy()
    headers['Cookie'] = f"steamLoginSecure={login_cookie}"
    
    url = f"https://steamcommunity.com/market/listings/730/{quote(market_hash_name)}/render/"
    
    params = {
        'query': '',
        'start': 0,
        'count': count, 
        'country': 'PL',
        'language': 'polish',
        # Usunięto 'currency' aby pobierało w walucie z ciasteczka (PLN)
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"Błąd połączenia z API Steam (oferty): {response.status_code} {response.reason} for url: {url}", file=sys.stderr)
            return None

        data = response.json()
        
        total_count = data.get('total_count', 0)
        listings_html = data.get('results_html', '')
        
        # --- POPRAWIONA LOGIKA PARSOWANIA (ABY PASOWAŁA DO results_view.py) ---
        listings = []
        if listings_html:
            # Używamy Twojego oryginalnego, działającego regexa
            listing_rows = re.findall(r'<div class="market_listing_row market_recent_listing_row"(.*?)</div></div>', listings_html, re.DOTALL)
            
            for row_html in listing_rows[:count]:
                
                # Szukaj ceny końcowej (z prowizją)
                price_match = re.search(r'market_listing_price_with_fee">([\s\S]*?)</span>', row_html)
                # Szukaj samej prowizji
                fee_match = re.search(r'market_listing_fee">([\s\S]*?)</span>', row_html)
                
                price_str = price_match.group(1).strip() if price_match else None
                fee_str = fee_match.group(1).strip() if fee_match else None

                # Konwertuj na float, tak jak oczekuje results_view.py
                price_float = _convert_price_to_float(price_str)
                fee_float = _convert_price_to_float(fee_str)
                
                # Zwróć dane w formacie, którego oczekuje results_view.py
                listings.append({
                    'price_float': price_float, 
                    'fee': fee_float
                })
        # --- KONIEC POPRAWKI ---

        lowest_price = data.get('lowest_price', "N/A")
        highest_buy_order = data.get('highest_buy_order', "N/A")

        return {
            'listings': listings, 
            'total_count': total_count,
            'lowest_price': lowest_price,
            'highest_buy_order': highest_buy_order
        }

    except Exception as e:
        print(f"Nieoczekiwany błąd podczas parsowania ofert: {e}", file=sys.stderr)
        return None

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
            url = f"https://steamcommunity.com/market/search/render/?query={quote(query)}&start={start}&count=100&norender=1"
            response = requests.get(url, headers=base_headers, timeout=10)
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
            start += 100
            print(f"Pobrano: {len(all_items)} z {total_count}")
            time.sleep(1) 
        print(f"Pobieranie zakończone. Łącznie {len(all_items)} unikalnych przedmiotów.")
        return sorted(list(all_items))
    except Exception as e:
        print(f"Błąd sieci (sugestie): {e}", file=sys.stderr)
        return None
import requests
import urllib.parse
import sys # Użyjemy do logowania błędów na konsolę

def get_cheapest_listings(market_hash_name, count=10):
    """
    Pobiera najtańsze oferty dla danego przedmiotu z rynku Steam.

    :param market_hash_name: Dokładna nazwa rynkowa przedmiotu
    :param count: Liczba ofert do pobrania
    :return: Lista słowników z ofertami LUB 
             pusta lista [] jeśli nie ma ofert LUB 
             None jeśli wystąpił błąd (np. timeout, zła nazwa).
    """
    
    encoded_name = urllib.parse.quote(market_hash_name)
    url = f"https://steamcommunity.com/market/listings/730/{encoded_name}/render/"
    
    params = {
        'query': '',
        'start': 0,
        'count': count,
        'country': 'PL',
        'language': 'polish',
        'currency': 6 # 3 = PLN
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36'
    }

    try:
        # Używamy timeout=30, tak jak ustaliłeś
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 429:
            # Używamy sys.stderr, aby błędy drukowały się na konsoli, nawet gdy GUI działa
            print("BŁĄD: Zostałeś tymczasowo zablokowany przez Steam (Rate Limit - 429).", file=sys.stderr)
            return None
        
        response.raise_for_status()  

        data = response.json()

        if not data or not data.get('success'):
            print(f"Błąd: Steam API zwróciło 'success: false' dla '{market_hash_name}'. Sprawdź nazwę.", file=sys.stderr)
            return None

        listings_data = data.get('listinginfo', {})
        
        if not listings_data:
            print("Nie znaleziono żadnych aktywnych ofert dla tego przedmiotu.", file=sys.stderr)
            return [] # Zwracamy pustą listę, to nie jest błąd

        parsed_listings = []
        
        for listing_id, details in listings_data.items():
            price_without_fee = details.get('converted_price', 0)
            fee = details.get('converted_fee', 0)
            total_price_integer = price_without_fee + fee
            total_price_float = total_price_integer / 100.0
            asset_id = details.get('asset', {}).get('id')
            
            parsed_listings.append({
                'listing_id': listing_id,
                'asset_id': asset_id,
                'price_pln': total_price_float
            })

        parsed_listings.sort(key=lambda x: x['price_pln'])

        return parsed_listings

    except requests.exceptions.Timeout:
        print("BŁĄD: Przekroczono czas oczekiwania na odpowiedź od Steam.", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"BŁĄD: Wystąpił błąd połączenia: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"BŁĄD: Wystąpił nieoczekiwany błąd: {e}", file=sys.stderr)
        return None
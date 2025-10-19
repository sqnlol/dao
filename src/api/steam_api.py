import requests

def get_skin_price_history(skin_name: str):
    """Pobiera dane cenowe danego skina z rynku Steam."""
    url = "https://steamcommunity.com/market/pricehistory/"
    params = {
        "country": "PL",
        "currency": 6,  # PLN
        "appid": 730,   # CS2
        "market_hash_name": skin_name
    }

    # Dodajemy nagłówki przeglądarki
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pl-PL,pl;q=0.9",
        "Referer": "https://steamcommunity.com/market/"
    }

    response = requests.get(url, params=params, headers=headers)

    # Sprawdzamy czy odpowiedź jest poprawna
    try:
        data = response.json()
    except Exception:
        raise Exception("Nie udało się odczytać odpowiedzi JSON — prawdopodobnie blokada Steam.")

    if isinstance(data, list):
        raise Exception("Odpowiedź API jest listą — Steam mógł zablokować dane lub zapytanie jest błędne.")

    if "prices" not in data:
        raise Exception(f"Brak danych 'prices' w odpowiedzi: {data}")

    prices = data["prices"]
    parsed_data = []

    for entry in prices:
        try:
            date, price, volume = entry
            parsed_data.append({
                "date": date,
                "price": float(price.replace("$", "").replace(",", ".").strip()),
                "volume": volume
            })
        except Exception:
            continue

    if not parsed_data:
        raise Exception("Nie udało się sparsować żadnych danych cenowych.")

    return parsed_data

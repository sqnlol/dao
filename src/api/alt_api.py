# src/api/alt_api.py
import requests
import urllib.parse

def _call_steam(skin_name: str):
    url = "https://steamcommunity.com/market/pricehistory/"
    params = {
        "country": "PL",
        "currency": 6,
        "appid": 730,
        "market_hash_name": skin_name
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pl-PL,pl;q=0.9",
        "Referer": "https://steamcommunity.com/market/"
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    try:
        return ("steam", r.json())
    except Exception:
        return ("steam", None)

def _call_skinport(skin_name: str):
    # Skinport docs: /v1/sales/history endpoint (public docs). :contentReference[oaicite:2]{index=2}
    base = "https://api.skinport.com/v1/sales/history"
    # Skinport może wymagać dokładnego market_hash_name lub item id.
    # URL-encode the market name
    params = {"market_hash_name": skin_name}
    r = requests.get(base, params=params, timeout=15)
    try:
        return ("skinport", r.json())
    except Exception:
        return ("skinport", None)

def get_price_data(skin_name: str):
    """
    Próbuje pobrać dane: najpierw Steam, potem Skinport.
    Zwraca listę rekordów: [{"date":..., "price":..., "volume":...}, ...]
    Jeśli nie uda się pobrać żadnych danych, rzuca Exception z tekstem diagnostycznym.
    """
    # 1) Steam
    source, data = _call_steam(skin_name)
    if data and isinstance(data, dict) and data.get("success"):
        # standardowy Steam format: data["prices"] = [[date_str, "$x.xx", volume], ...]
        prices = data.get("prices", [])
        parsed = []
        for entry in prices:
            try:
                date, price, volume = entry
                price_num = float(price.replace("$", "").replace(",", ".").strip())
                parsed.append({"date": date, "price": price_num, "volume": volume, "source": "steam"})
            except Exception:
                continue
        if parsed:
            return parsed

    # 2) Skinport
    source2, data2 = _call_skinport(skin_name)
    if data2:
        # Skinport może zwracać kilka formatów: agregaty (24h/7d/30d) lub listę obiektów
        parsed = []
        if isinstance(data2, dict):
            # jeśli jest agregat (np. keys "24h","7d", "30d"), dodajemy je jako rekordy bez daty konkretnej
            # lub jeśli istnieje pole 'items' lub 'data', załóżmy że to lista sprzedaży
            # najpierw sprawdzamy czy mamy listę sprzedaży w data2.get('list') lub similar
            candidates = []
            for k in ("prices","sales","data","items","results"):
                if k in data2 and isinstance(data2[k], list):
                    candidates = data2[k]
                    break

            if candidates:
                for entry in candidates[:200]:
                    # próbujemy wyciągnąć pola daty/ceny/ilości w najbardziej prawdopodobny sposób
                    if isinstance(entry, dict):
                        date = entry.get("created_at") or entry.get("date") or entry.get("time")
                        price = entry.get("price") or entry.get("sale_price") or entry.get("unit_price")
                        volume = entry.get("quantity") or entry.get("volume") or 1
                        try:
                            price_num = float(str(price).replace(",", "."))
                        except Exception:
                            continue
                        parsed.append({"date": date, "price": price_num, "volume": volume, "source": "skinport"})
            else:
                # Spróbujmy zebrać agregaty, które mogą istnieć (min/max/avg/median dla 24h/7d/30d)
                # Znajdź liczby/struktury które wyglądają jak statystyki
                for period in ("24h", "7d", "30d", "90d", "all_time"):
                    if period in data2 and isinstance(data2[period], dict):
                        stats = data2[period]
                        avg = stats.get("avg") or stats.get("mean") or stats.get("average")
                        vol = stats.get("volume") or stats.get("count") or stats.get("sales")
                        try:
                            price_num = float(str(avg).replace(",", "."))
                            parsed.append({"date": period, "price": price_num, "volume": vol, "source": "skinport_agg"})
                        except Exception:
                            continue

        elif isinstance(data2, list):
            # Jeśli Skinport zwróci bezpośrednio listę sprzedaży
            for entry in data2[:200]:
                if isinstance(entry, dict):
                    date = entry.get("created_at") or entry.get("date")
                    price = entry.get("price") or entry.get("sale_price")
                    volume = entry.get("quantity") or 1
                    try:
                        price_num = float(str(price).replace(",", "."))
                    except Exception:
                        continue
                    parsed.append({"date": date, "price": price_num, "volume": volume, "source": "skinport"})
        if parsed:
            return parsed

    # Nic nie zwrócono
    raise Exception("Nie udało się pobrać danych z żadnego źródła (Steam/Skinport). Spróbuj innej nazwy skina lub poczekaj chwilę (rate-limit).")

# src/scraper/steam_selenium.py
import time
import json
import os
import urllib.parse
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException

def ensure_data_dir():
    if not os.path.exists("data"):
        os.makedirs("data")

def slugify(name: str) -> str:
    # prosty slug do nazw plików
    safe = "".join(c if c.isalnum() or c in " _-." else "_" for c in name)
    return safe.replace(" ", "_").replace("|", "_").replace("/", "_")

def fetch_pricehistory_via_browser(skin_name: str, country="PL", currency=6, appid=730, headless=True, wait_seconds=3, timeout=30):
    """
    Otwiera stronę listing'u i wykona fetch do endpointu pricehistory w kontekście przeglądarki.
    Zwraca sparsowany JSON (dict) lub rzuca wyjątek.
    """
    ensure_data_dir()
    encoded = urllib.parse.quote(skin_name, safe='')
    listing_url = f"https://steamcommunity.com/market/listings/{appid}/{encoded}"
    pricehistory_url = (
        "https://steamcommunity.com/market/pricehistory/"
        f"?country={country}&currency={currency}&appid={appid}&market_hash_name={urllib.parse.quote(skin_name)}"
    )

    # Konfiguracja Chromedriver (webdriver-manager pobierze pasujący sterownik)
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")  # jeśli starsza wersja, spróbuj "--headless"
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=pl-PL")
    chrome_options.add_argument("--window-size=1200,900")

    service = Service(ChromeDriverManager().install())
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except WebDriverException as e:
        raise RuntimeError(f"Nie udało się uruchomić ChromeDriver: {e}")

    try:
        driver.set_page_load_timeout(timeout)
        driver.get(listing_url)
        # daj czas na uruchomienie JS i ewentualne re-directy
        time.sleep(wait_seconds)

        # 1) Spróbuj odczytać zmienną globalną z wykresem, jeśli jest dostępna
        try:
            price_var = driver.execute_script("return window.g_rgPriceHistory || window.g_rgMarketPriceHistory || null;")
            if price_var:
                # g_rgPriceHistory zwykle ma strukturę z listą prices i success
                # upewnijmy się, że mamy dict-like obiekt - jeśli jest, zapiszemy go
                return price_var
        except Exception:
            # nie krytyczne, kontynuujemy do fetch
            pass

        # 2) Bezpośrednie wywołanie fetch (w kontekście przeglądarki) do endpointu pricehistory
        fetch_script = f"""
const callback = arguments[arguments.length - 1];

// ustaw cookie, które Steam oczekuje
document.cookie = "Steam_Language=english; path=/;";

// wykonaj zapytanie fetch z pełnym nagłówkiem przeglądarki
fetch("{pricehistory_url}", {{
    method: "GET",
    credentials: "same-origin",
    headers: {{
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }}
}})
.then(r => r.text())
.then(txt => {{
    try {{
        const j = JSON.parse(txt);
        callback({{ok: true, data: j}});
    }} catch(e) {{
        callback({{ok: false, error: "Invalid JSON", text: txt}});
    }}
}})
.catch(err => {{
    callback({{ok: false, error: String(err)}});
}});
"""


        # execute_async_script wykona fetch i zwróci wynik
        result = driver.execute_async_script(fetch_script)

        if not isinstance(result, dict):
            raise RuntimeError("Nieoczekiwany wynik fetch (nie-dict).")

        if not result.get("ok"):
            err_text = result.get("error") or result.get("text") or str(result)
            raise RuntimeError(f"Fetch do pricehistory nie powiódł się: {err_text}")

        data = result.get("data")
        if not data:
            print("DEBUG: odpowiedź pricehistory =", json.dumps(result, indent=2, ensure_ascii=False))
            raise RuntimeError("Brak danych w odpowiedzi pricehistory.")

        # Zapis pliku JSON do data/
        slug = slugify(skin_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/{slug}_pricehistory_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # zwróć dict i ścieżkę pliku
        return {"data": data, "file": filename}
    finally:
        try:
            driver.quit()
        except Exception:
            pass

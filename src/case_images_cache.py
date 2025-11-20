"""
Moduł do zarządzania cache'owaniem obrazków skrzyń CS2.
Pobiera obrazki ze Steam Market API i zapisuje je lokalnie.
"""

import os
import sys
import requests
from PIL import Image
from io import BytesIO
import threading
import time

# Ścieżka do folderu cache
CACHE_DIR = os.path.join(os.path.dirname(__file__), "img", "cases_cache")

# Lista wszystkich skrzyń CS2 z dokładnymi nazwami Steam Market (34 skrzynie)
CS2_CASES = [
    # Aktywne skrzynie
    {"name": "Skrzynia Kilowata", "market_name": "Kilowatt Case"},
    {"name": "Skrzynia Rewolucji", "market_name": "Revolution Case"},
    {"name": "Skrzynia Operacji Riptide", "market_name": "Operation Riptide Case"},
    {"name": "Skrzynia Sny i Koszmary", "market_name": "Dreams & Nightmares Case"},
    {"name": "Skrzynia Odrzutu", "market_name": "Recoil Case"},
    {"name": "Skrzynia Snakebite", "market_name": "Snakebite Case"},
    {"name": "Skrzynia Operacji Broken Fang", "market_name": "Operation Broken Fang Case"},
    {"name": "Skrzynia Fracture", "market_name": "Fracture Case"},
    {"name": "Skrzynia Prisma 2", "market_name": "Prisma 2 Case"},
    {"name": "Skrzynia Pazura", "market_name": "Clutch Case"},
    {"name": "Skrzynia Prisma", "market_name": "Prisma Case"},
    {"name": "Skrzynia CS20", "market_name": "CS20 Case"},
    {"name": "Skrzynia Operacji Shattered Web", "market_name": "Shattered Web Case"},
    {"name": "Skrzynia Danger Zone", "market_name": "Danger Zone Case"},
    {"name": "Skrzynia Horizon", "market_name": "Horizon Case"},
    {"name": "Skrzynia Spektrum 2", "market_name": "Spectrum 2 Case"},
    {"name": "Skrzynia Operacji Hydra", "market_name": "Operation Hydra Case"},
    {"name": "Skrzynia Spektrum", "market_name": "Spectrum Case"},
    {"name": "Skrzynia Rękawiczek", "market_name": "Glove Case"},
    {"name": "Skrzynia Gamma 2", "market_name": "Gamma 2 Case"},
    {"name": "Skrzynia Gamma", "market_name": "Gamma Case"},
    {"name": "Skrzynia Chroma 3", "market_name": "Chroma 3 Case"},
    {"name": "Skrzynia Operacji Wildfire", "market_name": "Operation Wildfire Case"},
    {"name": "Skrzynia Cienia", "market_name": "Shadow Case"},
    {"name": "Skrzynia Revolver", "market_name": "Revolver Case"},
    # Usunięto: Skrzynia Operacji Vanguard (rate limiting)
    # Usunięto: Skrzynia Falchion (rate limiting)
    # Usunięto: Skrzynia Chroma 2 (rate limiting)
    {"name": "Skrzynia Chroma", "market_name": "Chroma Case"},
    {"name": "Skrzynia Operacji Breakout", "market_name": "Operation Breakout Weapon Case"},
    {"name": "Skrzynia Łowcy", "market_name": "Huntsman Weapon Case"},
    {"name": "Skrzynia Operacji Phoenix", "market_name": "Operation Phoenix Weapon Case"},
    {"name": "Skrzynia Zimowej Ofensywy", "market_name": "Winter Offensive Weapon Case"},
    {"name": "Skrzynia CS:GO 3", "market_name": "CS:GO Weapon Case 3"},
    {"name": "Skrzynia Operacji Bravo", "market_name": "Operation Bravo Case"},
    {"name": "Skrzynia CS:GO 2", "market_name": "CS:GO Weapon Case 2"},
    {"name": "Skrzynia CS:GO", "market_name": "CS:GO Weapon Case"},
]


def ensure_cache_dir():
    """Tworzy folder cache jeśli nie istnieje."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        print(f"Utworzono folder cache: {CACHE_DIR}")


def get_cache_path(case_name):
    """Zwraca ścieżkę do pliku cache dla danej skrzyni."""
    # Normalizuj nazwę do bezpiecznej nazwy pliku
    safe_name = case_name.replace(" ", "_").replace(":", "").replace("/", "_")
    return os.path.join(CACHE_DIR, f"{safe_name}.png")


def is_cached(case_name):
    """Sprawdza czy obrazek jest już w cache."""
    cache_path = get_cache_path(case_name)
    return os.path.exists(cache_path)


def get_cached_image_path(case_name):
    """Zwraca ścieżkę do cache'owanego obrazka lub None jeśli nie istnieje."""
    cache_path = get_cache_path(case_name)
    if os.path.exists(cache_path):
        return cache_path
    return None


def download_and_cache_case_image(market_name, case_name, login_cookie=None):
    """
    Pobiera obrazek skrzyni ze Steam Market i zapisuje w cache.
    
    Args:
        market_name: Nazwa rynkowa skrzyni (np. "Kilowatt Case")
        case_name: Przyjazna nazwa do użycia w cache (np. "Skrzynia Kilowata")
        login_cookie: Steam login cookie (opcjonalne)
    
    Returns:
        str: Ścieżka do zapisanego pliku lub None przy błędzie
    """
    try:
        # Import tutaj żeby uniknąć circular imports
        from steam_market import get_item_image_url
        
        # Pobierz URL obrazka
        image_url = get_item_image_url(market_name, login_cookie, currency_code=6, timeout=15)
        if not image_url:
            print(f"Nie można pobrać URL obrazka dla: {market_name}", file=sys.stderr)
            return None
        
        # Pobierz obrazek
        resp = requests.get(image_url, timeout=15)
        if resp.status_code != 200 or not resp.content:
            print(f"Błąd pobierania obrazka {market_name}: HTTP {resp.status_code}", file=sys.stderr)
            return None
        
        # Otwórz i przetworz obrazek
        img = Image.open(BytesIO(resp.content))
        
        # Konwertuj do RGB jeśli potrzeba
        if img.mode == 'RGBA':
            # Dodaj białe tło dla przezroczystości
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 3 to alpha channel
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Zapisz w cache
        ensure_cache_dir()
        cache_path = get_cache_path(case_name)
        img.save(cache_path, 'PNG', optimize=True)
        
        print(f"Zapisano w cache: {case_name}")
        return cache_path
        
    except Exception as e:
        print(f"Błąd cachowania {market_name}: {e}", file=sys.stderr)
        return None


def download_all_cases(login_cookie=None, delay=2.0, progress_callback=None, adaptive_delay=True):
    """
    Pobiera i cachuje wszystkie skrzynie CS2.
    
    Args:
        login_cookie: Steam login cookie (opcjonalne, ale zalecane)
        delay: Bazowe opóźnienie między requestami w sekundach (żeby nie przekroczyć rate limit)
        progress_callback: Funkcja callback(current, total, case_name, success) wywoływana po każdej skrzyni
        adaptive_delay: Czy zwiększać opóźnienie po napotkaniu błędów 429
    
    Returns:
        dict: {"success": int, "failed": int, "total": int, "failed_cases": list}
    """
    total = len(CS2_CASES)
    success_count = 0
    failed_count = 0
    failed_cases = []
    current_delay = delay
    consecutive_429 = 0  # Licznik kolejnych błędów 429
    
    print(f"\nRozpoczynam pobieranie {total} skrzyń...\n")
    
    for idx, case in enumerate(CS2_CASES, 1):
        case_name = case["name"]
        market_name = case["market_name"]
        
        # Sprawdź czy już jest w cache
        if is_cached(case_name):
            print(f"[{idx}/{total}] {case_name} - już w cache, pomijam")
            success_count += 1
            if progress_callback:
                progress_callback(idx, total, case_name, True)
            continue
        
        print(f"[{idx}/{total}] Pobieram: {case_name}... (delay: {current_delay:.1f}s)")
        
        # Pobierz i zapisz
        result = download_and_cache_case_image(market_name, case_name, login_cookie)
        
        if result:
            success_count += 1
            consecutive_429 = 0  # Reset licznika przy sukcesie
            if progress_callback:
                progress_callback(idx, total, case_name, True)
        else:
            failed_count += 1
            failed_cases.append(case_name)
            consecutive_429 += 1  # Zwiększ licznik błędów
            if progress_callback:
                progress_callback(idx, total, case_name, False)
        
        # Adaptacyjne opóźnienie - zwiększaj delay jeśli napotykamy błędy 429
        if adaptive_delay and consecutive_429 > 0:
            # Po każdych 2 błędach 429 zwiększ delay o 50%
            if consecutive_429 % 2 == 0:
                current_delay = min(current_delay * 1.5, 15.0)  # Max 15s
                print(f"  → Zwiększam delay do {current_delay:.1f}s z powodu rate limitingu")
        
        # Opóźnienie między requestami (oprócz ostatniego)
        if idx < total:
            time.sleep(current_delay)
    
    print(f"\n{'='*60}")
    print(f"Zakończono pobieranie:")
    print(f"  Sukces: {success_count}/{total}")
    print(f"  Błędy: {failed_count}/{total}")
    if failed_cases:
        print(f"  Nieudane: {', '.join(failed_cases)}")
    print(f"{'='*60}\n")
    
    return {
        "success": success_count,
        "failed": failed_count,
        "total": total,
        "failed_cases": failed_cases
    }


def download_all_cases_async(login_cookie=None, delay=2.0, progress_callback=None, completion_callback=None):
    """
    Asynchroniczna wersja download_all_cases - uruchamia w osobnym wątku.
    
    Args:
        login_cookie: Steam login cookie
        delay: Opóźnienie między requestami
        progress_callback: Funkcja callback(current, total, case_name, success)
        completion_callback: Funkcja callback(results_dict) wywołana po zakończeniu
    """
    def worker():
        results = download_all_cases(login_cookie, delay, progress_callback)
        if completion_callback:
            completion_callback(results)
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def get_all_cases_list():
    """
    Zwraca listę wszystkich skrzyń z informacją o dostępności w cache.
    
    Returns:
        list: Lista dict z kluczami: name, market_name, cached, cache_path
    """
    result = []
    for case in CS2_CASES:
        cache_path = get_cached_image_path(case["name"])
        result.append({
            "name": case["name"],
            "market_name": case["market_name"],
            "cached": cache_path is not None,
            "cache_path": cache_path
        })
    return result


# Funkcja pomocnicza do jednorazowego użycia z linii komend
if __name__ == "__main__":
    print("=" * 60)
    print("Cache Manager dla obrazków skrzyń CS2")
    print("=" * 60)
    
    # Sprawdź czy użytkownik chce pobrać wszystkie obrazki
    response = input("\nCzy chcesz pobrać wszystkie obrazki skrzyń? (t/n): ").strip().lower()
    
    if response == 't':
        # Opcjonalnie można przekazać cookie
        cookie = input("Podaj steamLoginSecure cookie (Enter aby pominąć): ").strip()
        if not cookie:
            cookie = None
        
        # Pobierz wszystkie
        download_all_cases(login_cookie=cookie, delay=2.5)
    else:
        # Pokaż status cache
        cases = get_all_cases_list()
        cached = [c for c in cases if c["cached"]]
        print(f"\nStatus cache: {len(cached)}/{len(cases)} skrzyń w cache")
        
        if len(cached) < len(cases):
            print("\nBrakujące skrzynie:")
            for case in cases:
                if not case["cached"]:
                    print(f"  - {case['name']}")

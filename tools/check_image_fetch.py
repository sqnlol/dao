import sys
import os

# Ensure repo root is on sys.path so `src` package can be imported when running from tools/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.steam_market import get_item_image_url

samples = [
    "AK-47 | Redline (Field-Tested)",
    "★ Karambit | Doppler (Factory New)",
    "Glock-18 | Fade (Factory New)"
]

for name in samples:
    print(f"Checking: {name}")
    try:
        url = get_item_image_url(name, login_cookie=None)
        print(f" -> URL: {url}\n")
    except Exception as e:
        print(f" -> Exception: {e}\n")

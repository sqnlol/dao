# src/scraper/run_scraper.py
from steam_selenium import fetch_pricehistory_via_browser
import os
import sys

def main():
    if len(sys.argv) >= 2:
        skin = " ".join(sys.argv[1:])
    else:
        skin = "AK-47 | Redline (Field-Tested)"

    print(f"Pobieram pricehistory dla: {skin}")
    try:
        result = fetch_pricehistory_via_browser(skin, headless=False, wait_seconds=6)
        if isinstance(result, dict) and "file" in result:
            print("✅ Dane pobrane i zapisane do:", result["file"])
        else:
            print("✅ Dane:", result)
    except Exception as e:
        print("❌ Błąd:", e)

if __name__ == "__main__":
    main()

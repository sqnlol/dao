# Cache obrazków skrzyń CS2

Ten folder zawiera cache'owane obrazki skrzyń CS2 pobrane ze Steam Market API.

## Jak działa

1. **Pierwsza konfiguracja**: Uruchom `download_case_images.py` z głównego katalogu projektu:
   ```
   python download_case_images.py
   ```

2. **Automatyczne pobieranie**: Przy pierwszym otwarciu zakładki "Skrzynie" w aplikacji, brakujące obrazki będą pobrane automatycznie w tle.

3. **Cache lokalny**: Pobrane obrazki są zapisywane w tym folderze jako pliki PNG i używane przy kolejnych uruchomieniach.

## Struktura

- Każda skrzynia ma swój plik PNG nazwany według przyjaznej nazwy (np. `Skrzynia_Kilowata.png`)
- Format: PNG, zoptymalizowany
- Obrazki są pobierane ze Steam Market API w najwyższej dostępnej jakości

## Zarządzanie cache

Możesz:
- Usunąć konkretny plik aby wymusić ponowne pobranie tej skrzyni
- Usunąć cały folder aby wyczyścić cache (obrazki będą pobrane ponownie)
- Ręcznie dodać/podmienić obrazki (muszą być w formacie PNG)

## Lista skrzyń

Cache zawiera obrazki 34 skrzyń CS2, w tym:
- Aktywne skrzynie (Kilowatt, Revolution, etc.)
- Skrzynie operacji (Riptide, Broken Fang, etc.)
- Skrzynie specjalne (Dreams & Nightmares, CS20, etc.)
- Starsze skrzynie (Gamma, Chroma, Spectrum, etc.)

**Uwaga:** 3 skrzynie zostały usunięte z listy z powodu rate limitingu Steam API:
- Skrzynia Operacji Vanguard
- Skrzynia Falchion  
- Skrzynia Chroma 2

Pełna lista znajduje się w `src/case_images_cache.py`.

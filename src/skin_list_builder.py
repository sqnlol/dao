# src/skin_list_builder.py

import os
import json
import sys
from collections import defaultdict

try:
    from src import resource_paths
except ImportError:  # Allow running directly from src directory during development
    import resource_paths
from src import steam_market

SUGGESTIONS_FILE = resource_paths.get_writable_suggestions_path()
OUTPUT_JSON = os.path.join('src', 'skin_list_generated.json')


def normalize_type(item_type: str) -> str:
    # Zwraca nazwę typu broni dokładnie tak, jak w market hash name (bez wear)
    return item_type.strip() if item_type else ''


def build_skin_mapping_from_suggestions(suggestions_path: str = SUGGESTIONS_FILE):
    mapping = defaultdict(set)

    if not os.path.exists(suggestions_path):
        print(f"Brak pliku sugestii: {suggestions_path}", file=sys.stderr)
        return {}

    try:
        with open(suggestions_path, 'r', encoding='utf-8') as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    except Exception as e:
        print(f"Błąd odczytu {suggestions_path}: {e}", file=sys.stderr)
        return {}

    for name in lines:
        # Próbuj sparować nazwę z pomocą istniejącej funkcji
        try:
            parts = steam_market.parse_market_name(name)
        except Exception as e:
            # Jeśli parse się wysypie, pomiń wpis, ale zaloguj
            print(f"WARN: parse_market_name nie powiodło się dla: {name} -> {e}", file=sys.stderr)
            continue

        item_type = normalize_type(parts.get('type'))
        skin_name = parts.get('name')

        if not item_type or not skin_name:
            # Heurystyka: skrzynki itp. – jeśli kończy się na 'Case', dodaj jako pustą listę
            if name.endswith(' Case') or name.endswith(' Case (Holo/Foil)') or name.endswith('Case'):
                mapping[name]  # pusta lista skinów dla skrzynek
            continue

        # Dodaj wpis bez wear'u; StatTrak™ i wear usuwane przez parse_market_name
        mapping[item_type].add(skin_name)

    # Konwersja do list posortowanych
    out = {k: sorted(list(v)) for k, v in mapping.items()}
    return out


def save_mapping_to_json(mapping: dict, output_path: str = OUTPUT_JSON):
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2, sort_keys=True)
        return True
    except Exception as e:
        print(f"Błąd zapisu JSON {output_path}: {e}", file=sys.stderr)
        return False


def generate():
    mapping = build_skin_mapping_from_suggestions()
    if not mapping:
        print("Nie wygenerowano mapy skinów (brak lub błąd sugestii).", file=sys.stderr)
        return False
    ok = save_mapping_to_json(mapping)
    if ok:
        print(f"Zapisano: {OUTPUT_JSON} (pozycje: {sum(len(v) for v in mapping.values())}, typów: {len(mapping)})")
    return ok


if __name__ == '__main__':
    generate()

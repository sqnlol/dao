# src/suggestions_loader.py

import os
from typing import Dict, List, Set, Tuple
import re

SUGGESTIONS_FILE = os.path.join(os.path.dirname(__file__), 'suggestions.txt')

AGENT_COLLECTION_HINTS = {
    'The Professionals', 'Gendarmerie Nationale', 'Guerrilla Warfare', 'NZSAS', 'Phoenix',
    'Sabre', 'FBI Sniper', 'FBI SWAT', 'Elite Crew', 'FBI HRT', 'NSWC SEAL', 'USAF TACP',
    'SAS', 'KSK', 'TACAP Cavalry', 'Sabre Footsoldier', 'SWAT', 'Brazilian 1st Battalion',
    'SEAL Frogman'
}

WEAR_SUFFIXES = {
    'Factory New', 'Minimal Wear', 'Field-Tested', 'Well-Worn', 'Battle-Scarred'
}

def _is_knife_type(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    # Include known knife identifiers; exclude gloves/wraps
    hints = [
        'knife', 'bayonet', 'karambit', 'daggers', 'kukri', 'navaja',
        'stiletto', 'talon', 'ursus', 'classic', 'paracord', 'survival',
        'nomad', 'skeleton', 'butterfly', 'huntsman', 'falchion', 'bowie', 'gut', 'flip'
    ]
    if any(h in n for h in hints):
        return True
    # Explicitly exclude glove families
    if 'gloves' in n or 'wraps' in n:
        return False
    return False

# Canonical weapon names to ingest from suggestions.txt
WEAPON_NAMES: Set[str] = {
    # Rifles
    'AK-47', 'M4A4', 'M4A1-S', 'FAMAS', 'Galil AR', 'AUG', 'SG 553',
    # Sniper Rifles
    'AWP', 'G3SG1', 'SCAR-20', 'SSG 08',
    # Pistols
    'Desert Eagle', 'USP-S', 'Glock-18', 'Five-SeveN', 'Tec-9', 'CZ75-Auto', 'P2000', 'Dual Berettas', 'P250', 'R8 Revolver',
    # SMGs
    'MP9', 'MAC-10', 'MP5-SD', 'MP7', 'PP-Bizon', 'P90', 'UMP-45',
    # Shotguns
    'MAG-7', 'Nova', 'Sawed-Off', 'XM1014',
    # Heavy
    'M249', 'Negev'
}


def _split_paren(value: str) -> Tuple[str, str]:
    # Returns (base, paren) where paren includes parentheses when present
    value = value.strip()
    if value.endswith(')') and '(' in value:
        idx = value.rfind('(')
        base = value[:idx].strip()
        paren = value[idx:].strip()
        return base, paren
    return value, ''


def build_structured_suggestions() -> Dict[str, object]:
    if not os.path.exists(SUGGESTIONS_FILE):
        return {}

    gloves_types: Set[str] = set()
    gloves_skins: Dict[str, Set[str]] = {}
    gloves_wear: Set[str] = set()
    gloves_skin_to_wears: Dict[str, Dict[str, Set[str]]] = {}

    stickers_types: List[str] = ['Esportowa', 'Zwykła']
    stickers_events: Set[str] = set()
    stickers_event_to_names: Dict[str, Set[str]] = {}
    stickers_normal_names: Set[str] = set()
    stickers_qualities: Set[str] = set()

    zeus_skins: Set[str] = set()
    zeus_wear_map: Dict[str, Set[str]] = {}

    # Knives aggregation
    knives_types: Set[str] = set()
    knives_skins: Dict[str, Set[str]] = {}
    knives_wear_map: Dict[str, Dict[str, Set[str]]] = {}

    # General weapons (non-knife) aggregation
    weapon_to_skins: Dict[str, Set[str]] = {}
    weapon_skin_to_wears: Dict[str, Dict[str, Set[str]]] = {}
    weapon_souvenir_skins: Dict[str, Set[str]] = {}
    weapon_stattrak_skins: Dict[str, Set[str]] = {}

    graffiti_types: List[str] = ['Esportowe', 'Zwykłe']
    graffiti_events: Set[str] = set()
    graffiti_event_to_names: Dict[str, Set[str]] = {}
    graffiti_normal_names: Set[str] = set()
    graffiti_name_to_colors: Dict[str, Set[str]] = {}

    agent_names: Set[str] = set()
    agent_collections: Set[str] = set()
    agent_collection_map: Dict[str, Set[str]] = {}

    cont_cases: Set[str] = set()
    cont_common: Set[str] = set()
    cont_event: Set[str] = set()
    cont_sets_collection: Set[str] = set()
    cont_sets_souvenir: Set[str] = set()
    cont_sets_other: Set[str] = set()
    cont_terminals: Set[str] = set()

    try:
        with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as f:
            for raw in f:
                s = raw.strip()
                if not s or s.startswith('#'):
                    continue

                if ' | ' in s:
                    left, right = s.split(' | ', 1)
                    # Sticker
                    if left == 'Sticker':
                        right_parts = [p.strip() for p in right.split('|')]
                        name_part = right_parts[0] if right_parts else ''
                        event_part = right_parts[1] if len(right_parts) > 1 else ''
                        base, paren = _split_paren(name_part)
                        display_name = name_part.strip()
                        if paren:
                            q = paren.strip('()').strip()
                            if q:
                                stickers_qualities.add(q)
                        if event_part:
                            stickers_events.add(event_part)
                            if event_part not in stickers_event_to_names:
                                stickers_event_to_names[event_part] = set()
                            if display_name:
                                stickers_event_to_names[event_part].add(display_name)
                        else:
                            if display_name:
                                stickers_normal_names.add(display_name)
                        continue
                    # Graffiti
                    if left == 'Sealed Graffiti':
                        # Esportowe: "Name | Event" (drugi separator '|')
                        if ' | ' in right:
                            r_parts = [p.strip() for p in right.split(' | ')]
                            if len(r_parts) >= 2:
                                base2 = r_parts[0]
                                event2 = r_parts[-1]
                                if base2 and event2:
                                    graffiti_events.add(event2)
                                    if event2 not in graffiti_event_to_names:
                                        graffiti_event_to_names[event2] = set()
                                    graffiti_event_to_names[event2].add(base2)
                                    continue
                        # Zwykłe: "Name (Color)"
                        base, paren = _split_paren(right)
                        color = paren.strip('()').strip() if paren else ''
                        if base:
                            graffiti_normal_names.add(base)
                            if color:
                                if base not in graffiti_name_to_colors:
                                    graffiti_name_to_colors[base] = set()
                                graffiti_name_to_colors[base].add(color)
                        continue
                    # Zeus
                    if left == 'Zeus x27':
                        base, paren = _split_paren(right)
                        if base:
                            zeus_skins.add(base)
                            wear = paren.strip('()').strip() if paren else ''
                            if wear and any(w in wear for w in WEAR_SUFFIXES):
                                if base not in zeus_wear_map:
                                    zeus_wear_map[base] = set()
                                zeus_wear_map[base].add(wear)
                        continue
                    # Gloves (broad match: anything with Gloves or Wraps)
                    if 'Gloves' in left or left.endswith('Wraps'):
                        gloves_types.add(left)
                        base, paren = _split_paren(right)
                        if left not in gloves_skins:
                            gloves_skins[left] = set()
                        if base:
                            gloves_skins[left].add(base)
                            # Per-skin wears mapping
                            if left not in gloves_skin_to_wears:
                                gloves_skin_to_wears[left] = {}
                            if base not in gloves_skin_to_wears[left]:
                                gloves_skin_to_wears[left][base] = set()
                        if paren and any(w in paren for w in WEAR_SUFFIXES):
                            gloves_wear.add(paren)
                            # Normalize with parentheses for UI consistency
                            wear_norm = paren if paren.startswith('(') else f'({paren.strip()})'
                            if left in gloves_skin_to_wears and base:
                                gloves_skin_to_wears[left][base].add(wear_norm)
                        continue
                    # Agent: left is agent name, right a known collection, and no wear parens
                    if right in AGENT_COLLECTION_HINTS:
                        agent_names.add(left)
                        agent_collections.add(right)
                        if right not in agent_collection_map:
                            agent_collection_map[right] = set()
                        agent_collection_map[right].add(left)
                        continue
                    # Generic weapons (Weapon | Skin (Wear)) – strip prefixes and collect
                    norm_left = left
                    if norm_left.startswith('Souvenir '):
                        norm_left = norm_left[len('Souvenir '):]
                    if norm_left.startswith('StatTrak™ '):
                        norm_left = norm_left[len('StatTrak™ '):]
                    if norm_left in WEAPON_NAMES:
                        base, paren = _split_paren(right)
                        if norm_left not in weapon_to_skins:
                            weapon_to_skins[norm_left] = set()
                        if base:
                            weapon_to_skins[norm_left].add(base)
                            if norm_left not in weapon_skin_to_wears:
                                weapon_skin_to_wears[norm_left] = {}
                            if base not in weapon_skin_to_wears[norm_left]:
                                weapon_skin_to_wears[norm_left][base] = set()
                            wear = paren.strip('()').strip() if paren else ''
                            if wear and wear in WEAR_SUFFIXES:
                                weapon_skin_to_wears[norm_left][base].add(f'({wear})')
                            # Souvenir detection: original 'left' had 'Souvenir ' prefix
                            if left.startswith('Souvenir '):
                                if norm_left not in weapon_souvenir_skins:
                                    weapon_souvenir_skins[norm_left] = set()
                                weapon_souvenir_skins[norm_left].add(base)
                            # StatTrak detection: original 'left' had 'StatTrak™ ' prefix
                            if left.startswith('StatTrak™ '):
                                if norm_left not in weapon_stattrak_skins:
                                    weapon_stattrak_skins[norm_left] = set()
                                weapon_stattrak_skins[norm_left].add(base)
                        continue
                else:
                    # Containers and other single-token items
                    # Knives may also come without a skin ("★ KnifeType" or with wear). Handle star-prefix outside split.
                    if s.startswith('★ '):
                        rest = s[2:].strip()
                        if rest.startswith('StatTrak™ '):
                            rest = rest[len('StatTrak™ '):].strip()
                        # Pattern without pipe: treat as type-only (vanilla-like); we don't record wears for vanilla
                        base_type, _paren = _split_paren(rest)
                        if base_type and _is_knife_type(base_type):
                            knives_types.add(base_type)
                        # If there is a pipe, it would be handled in the earlier branch
                        continue
                    if s.endswith(' Case'):
                        cont_cases.add(s)
                        continue
                    if s.endswith(' Capsule'):
                        cont_common.add(s)
                        continue
                    if 'Souvenir' in s and 'Package' in s:
                        cont_sets_souvenir.add(s)
                        continue
                    if s.endswith(' Package'):
                        cont_sets_other.add(s)
                        continue
                    if 'Collection' in s:
                        cont_sets_collection.add(s)
                        continue
                    if 'Terminal' in s:
                        cont_terminals.add(s)
                        continue
                    # Heuristic event containers (RMR, Major, etc.)
                    if any(tok in s for tok in ['RMR', 'Challengers', 'Contenders', 'Legends']):
                        cont_event.add(s)
                        continue
    except Exception:
        # On any error, return empty -> caller should keep defaults
        return {}

    # Assemble structures
    gloves_skins_dict = {k: sorted(list(v)) for k, v in gloves_skins.items()}
    gloves_wear_map = {gt: {sn: sorted(list(ws)) for sn, ws in mp.items()} for gt, mp in gloves_skin_to_wears.items()} if gloves_skin_to_wears else {}
    gloves_struct = {
        'types': sorted(list(gloves_types)) if gloves_types else [],
        'skins': gloves_skins_dict,
        'wear': sorted(list(gloves_wear)) if gloves_wear else [],
        'wear_map': gloves_wear_map
    }

    stickers_struct = {
        'types': stickers_types,
        'events': sorted(list(stickers_events)) if stickers_events else [],
        'event_to_names': {e: sorted(list(n)) for e, n in stickers_event_to_names.items()} if stickers_event_to_names else {},
        'normal_names': sorted(list(stickers_normal_names)) if stickers_normal_names else [],
        'qualities': sorted(list(stickers_qualities)) if stickers_qualities else ['Paper', 'Holo', 'Foil', 'Glitter', 'Gold']
    }

    graffiti_struct = {
        'types': graffiti_types,  # ["Esportowe", "Zwykłe"]
        'events': sorted(list(graffiti_events)) if graffiti_events else [],
        'event_to_names': {e: sorted(list(n)) for e, n in graffiti_event_to_names.items()} if graffiti_event_to_names else {},
        'normal_names': sorted(list(graffiti_normal_names)) if graffiti_normal_names else [],
        'name_to_colors': {n: sorted(list(c)) for n, c in graffiti_name_to_colors.items()} if graffiti_name_to_colors else {},
    }

    agents_struct = {
        'collections': sorted(list(agent_collections)) if agent_collections else [],
        'names': sorted(list(agent_names)) if agent_names else [],
        'map': {c: sorted(list(v)) for c, v in agent_collection_map.items()} if agent_collection_map else {}
    }

    # Build knives when star-prefixed items were encountered in two-branch parsing above
    # We also need to catch star-prefixed lines with pipe in the main branch
    try:
        with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as f2:
            for raw2 in f2:
                s2 = raw2.strip()
                if not s2 or not s2.startswith('★ '):
                    continue
                rest2 = s2[2:].strip()
                if rest2.startswith('StatTrak™ '):
                    rest2 = rest2[len('StatTrak™ '):].strip()
                if ' | ' in rest2:
                    ktype, right2 = rest2.split(' | ', 1)
                    if ktype and _is_knife_type(ktype):
                        knives_types.add(ktype)
                        base, paren = _split_paren(right2)
                        if ktype not in knives_skins:
                            knives_skins[ktype] = set()
                        if base:
                            knives_skins[ktype].add(base)
                            if ktype not in knives_wear_map:
                                knives_wear_map[ktype] = {}
                            if base not in knives_wear_map[ktype]:
                                knives_wear_map[ktype][base] = set()
                            wear = paren.strip('()').strip() if paren else ''
                            if wear and wear in WEAR_SUFFIXES:
                                knives_wear_map[ktype][base].add(f'({wear})')
    except Exception:
        pass

    containers_struct = {
        'types': ["Skrzynia", "Pojemnik z naklejkami", "Zestaw (Package)", "Terminal"],
        'cases': sorted(list(cont_cases)) if cont_cases else [],
        'common': sorted(list(cont_common)) if cont_common else [],
        'event_containers': sorted(list(cont_event)) if cont_event else [],
        'sets_collection': sorted(list(cont_sets_collection)) if cont_sets_collection else [],
        'sets_souvenir': sorted(list(cont_sets_souvenir)) if cont_sets_souvenir else [],
        'sets_other': sorted(list(cont_sets_other)) if cont_sets_other else [],
        'terminals': sorted(list(cont_terminals)) if cont_terminals else [],
    }

    weapons_struct = {
        'skins': {w: sorted(list(s)) for w, s in weapon_to_skins.items()} if weapon_to_skins else {},
        'wears': {w: {sn: sorted(list(ws)) for sn, ws in mp.items()} for w, mp in weapon_skin_to_wears.items()} if weapon_skin_to_wears else {},
        'souvenir': {w: sorted(list(s)) for w, s in weapon_souvenir_skins.items()} if weapon_souvenir_skins else {},
        'stattrak': {w: sorted(list(s)) for w, s in weapon_stattrak_skins.items()} if weapon_stattrak_skins else {},
    }

    return {
        'GLOVES': gloves_struct,
        'STICKERS': stickers_struct,
        'ZEUS_SKINS': sorted(list(zeus_skins)) if zeus_skins else [],  # backward compatibility
        'ZEUS': {
            'skins': sorted(list(zeus_skins)) if zeus_skins else [],
            'name_to_wears': {k: sorted(list(v)) for k, v in zeus_wear_map.items()} if zeus_wear_map else {},
        },
        'GRAFFITI': graffiti_struct,
        'AGENTS': agents_struct,
        'CONTAINERS': containers_struct,
        'KNIVES': {
            'types': sorted(list(knives_types)) if knives_types else [],
            'skins': {k: sorted(list(v)) for k, v in knives_skins.items()} if knives_skins else {},
            'wear_map': {t: {sn: sorted(list(ws)) for sn, ws in mp.items()} for t, mp in knives_wear_map.items()} if knives_wear_map else {}
        },
        'WEAPONS': weapons_struct,
    }

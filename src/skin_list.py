# src/skin_list.py

"""
Zmieniliśmy strukturę na SŁOWNIK (dictionary).
Klucz to "Typ Broni" (np. "AK-47").
Wartość to LISTA skinów dla tej broni (np. ["Redline", "Asiimov"]).

Dla skrzynek, wartość to pusta lista [].
"""

SKIN_DATA = {
    # --- Karbany ---
    "AK-47": [
        "Redline", "Asiimov", "The Empress", "Bloodsport", "Case Hardened",
        "Vulcan", "Wild Lotus", "X-Ray", "Fire Serpent", "Gold Arabesque",
        "Neon Rider", "Point Disarray", "Slate", "Legion of Anubis", "Fuel Injector"
    ],
    "M4A4": [
        "Howl", "The Emperor", "Asiimov", "Poseidon", "Temukau", "Dragon King",
        "Neo-Noir", "Desolate Space", "龍王 (Dragon King)", "Buzz Kill", "In Living Color"
    ],
    "M4A1-S": [
        "Printstream", "Knight", "Welcome to the Jungle", "Blue Phosphor",
        "Golden Coil", "Mecha Industries", "Hyper Beast", "Cyrex", "Player Two", "Imminent Danger"
    ],
    "AWP": [
        "Asiimov", "Dragon Lore", "Gungnir", "Medusa", "The Prince", "Oni Taiji",
        "Fade", "Neo-Noir", "Hyper Beast", "Containment Breach", "Lightning Strike", "Redline"
    ],
    "FAMAS": [
        "Commemoration", "Eye of Athena", "Roll Cage", "Mecha Industries", "Djinn"
    ],
    "Galil AR": [
        "Cerberus", "Chatterbox", "Eco", "Chromatic Aberration", "Sugar Rush"
    ],

    # --- Pistolety ---
    "Desert Eagle": [
        "Blaze", "Printstream", "Fennec Fox", "Code Red", "Ocean Drive",
        "Sunset Storm 壱", "Sunset Storm 弐", "Conspiracy", "Mecha Industries"
    ],
    "USP-S": [
        "Kill Confirmed", "The Traitor", "Printstream", "Neo-Noir", "Orion",
        "Cortex", "Dark Water", "Target Acquired"
    ],
    "Glock-18": [
        "Fade", "Gamma Doppler", "Twilight Galaxy", "Water Elemental", "Neo-Noir",
        "Vogue", "Bullet Queen", "Snack Attack"
    ],
    "Five-SeveN": [
        "Case Hardened", "Hyper Beast", "Monkey Business", "Angry Mob", "Fowl Play", "Boost Protocol"
    ],
    "Tec-9": [
        "Fuel Injector", "Nuclear Threat", "Isaac", "Bamboozle", "Remote Control"
    ],

    # --- PM-y ---
    "MP9": [
        "Wild Lily", "Bulldozer", "Hot Rod", "Starlight Protector", "Food Chain"
    ],
    "MAC-10": [
        "Case Hardened", "Neon Rider", "Stalker", "Gold Brick", "Disco Tech"
    ],

    # --- Skrzynki (pusta lista oznacza brak drugiego wyboru) ---
    "CS:GO Weapon Case": [],
    "Operation Bravo Case": [],
    "Operation Phoenix Weapon Case": [],
    "Operation Vanguard Weapon Case": [],
    "Operation Breakout Weapon Case": [],
    "Operation Wildfire Case": [],
    "Operation Hydra Case": [],
    "Chroma Case": [],
    "Chroma 2 Case": [],
    "Chroma 3 Case": [],
    "Falchion Case": [],
    "Shadow Case": [],
    "Revolver Case": [],
    "Gamma Case": [],
    "Gamma 2 Case": [],
    "Glove Case": [],
    "Spectrum Case": [],
    "Spectrum 2 Case": [],
    "Clutch Case": [],
    "Horizon Case": [],
    "Danger Zone Case": [],
    "Prisma Case": [],
    "Prisma 2 Case": [],
    "CS20 Case": [],
    "Shattered Web Case": [],
    "Fracture Case": [],
    "Operation Riptide Case": [],
    "Operation Broken Fang Case": [],
    "Snakebite Case": [],
    "Dreams & Nightmares Case": [],
    "Recoil Case": [],
    "Revolution Case": [],
    "Kilowatt Case": [],
}
# ─────────────────────────────────────────────
# petgame_natures.py
# Modul independent — naturi si interactiuni dintre ele.
# Nu importa nimic din bot — poate fi folosit si de un flash game.
# ─────────────────────────────────────────────

import random


# ─────────────────────────────────────────────
# DEFINITII NATURI
# ─────────────────────────────────────────────

NATURES = {
    'fire': {
        'name': 'Foc',
        'icon': '🔥',
        'color': '#f97316',
        'flavor': 'Agresiv, energie înaltă, arde scurt și puternic.',
        'bonus_stat': 'attack',
    },
    'water': {
        'name': 'Apă',
        'icon': '💧',
        'color': '#3b82f6',
        'flavor': 'Adaptabil, rezistent, controlează fluxul luptei.',
        'bonus_stat': 'speed',
    },
    'nature': {
        'name': 'Natură',
        'icon': '🌿',
        'color': '#22c55e',
        'flavor': 'Răbdător, regenerativ, câștigă prin uzură.',
        'bonus_stat': 'hp',
    },
    'earth': {
        'name': 'Pământ',
        'icon': '⛰️',
        'color': '#a16207',
        'flavor': 'Stabil, apărare ridicată, lent dar implacabil.',
        'bonus_stat': 'defense',
    },
    'storm': {
        'name': 'Furtună',
        'icon': '⚡',
        'color': '#eab308',
        'flavor': 'Rapid, imprevizibil, combo-uri electrizante.',
        'bonus_stat': 'speed',
    },
    'ice': {
        'name': 'Gheață',
        'icon': '❄️',
        'color': '#67e8f9',
        'flavor': 'Control și lentire, răcește orice amenințare.',
        'bonus_stat': 'control',
    },
    'shadow': {
        'name': 'Umbră',
        'icon': '🌑',
        'color': '#6d28d9',
        'flavor': 'Imprevizibil, misterios, evită atacuri cu abilități psihice.',
        'bonus_stat': 'evasion',
    },
    'crystal': {
        'name': 'Cristal',
        'icon': '💎',
        'color': '#c084fc',
        'flavor': 'Echilibrat, versatil, reflectă o parte din daune.',
        'bonus_stat': 'reflection',
    },
    'steel': {
        'name': 'Metal',
        'icon': '⚙️',
        'color': '#94a3b8',
        'flavor': 'Tanc pur, rezistențe multiple, daune constante.',
        'bonus_stat': 'defense',
    },
    'light': {
        'name': 'Lumină',
        'icon': '✨',
        'color': '#fbbf24',
        'flavor': 'Suport și vindecare, contracarează Umbra.',
        'bonus_stat': 'healing',
    },
    'dragon': {
        'name': 'Dragon',
        'icon': '🐉',
        'color': '#dc2626',
        'flavor': 'Primordial, devastator, descendent din cei mai vechi stăpâni ai lumii.',
        'bonus_stat': 'attack',
    },
}


# ─────────────────────────────────────────────
# MATRICEA DE INTERACTIUNI
# Linii = atacator, Coloane = tinta
# Valori: 2.0 = eficace, 1.0 = normal, 0.5 = ineficace, 0.0 = imun
# ─────────────────────────────────────────────

_ORDER = ['fire', 'water', 'nature', 'earth', 'storm', 'ice', 'shadow', 'crystal', 'steel', 'light', 'dragon']

_MATRIX = [
    # foc   apa   nat   pam   fur   ghe   umb   cri   met   lum   dra
    [1.0,  0.0,  2.0,  2.0,  0.5,  2.0,  2.0,  0.0,  2.0,  1.0,  0.0],  # fire
    [2.0,  1.0,  0.0,  2.0,  1.0,  0.5,  0.0,  2.0,  2.0,  0.0,  2.0],  # water
    [0.0,  2.0,  1.0,  2.0,  0.5,  1.0,  1.0,  1.0,  0.0,  2.0,  2.0],  # nature
    [2.0,  2.0,  0.0,  1.0,  2.0,  0.0,  2.0,  0.5,  0.0,  1.0,  2.0],  # earth
    [2.0,  2.0,  2.0,  0.0,  1.0,  0.0,  1.0,  1.0,  2.0,  0.5,  1.0],  # storm
    [1.0,  0.0,  2.0,  0.0,  0.5,  1.0,  2.0,  2.0,  1.0,  2.0,  1.0],  # ice
    [2.0,  0.0,  0.5,  2.0,  2.0,  1.0,  1.0,  2.0,  0.0,  0.0,  2.0],  # shadow
    [0.0,  2.0,  0.0,  1.0,  2.0,  2.0,  1.0,  1.0,  0.5,  2.0,  1.0],  # crystal
    [2.0,  0.5,  2.0,  0.0,  2.0,  2.0,  0.5,  1.0,  1.0,  1.0,  0.5],  # steel
    [0.5,  1.0,  1.0,  0.5,  0.5,  2.0,  2.0,  2.0,  2.0,  1.0,  0.0],  # light
    [0.0,  2.0,  2.0,  2.0,  0.5,  1.0,  0.0,  0.0,  2.0,  2.0,  1.0],  # dragon
]

# Lookup dict precalculat pentru acces O(1)
INTERACTION_TABLE: dict[tuple[str, str], float] = {
    (attacker, target): _MATRIX[i][j]
    for i, attacker in enumerate(_ORDER)
    for j, target in enumerate(_ORDER)
}


# ─────────────────────────────────────────────
# FUNCTII PUBLICE
# ─────────────────────────────────────────────

def get_interaction(attacker_nature: str, target_nature: str) -> dict:
    """
    Returneaza informatia completa despre interactiunea dintre doua naturi.

    Returns:
        {
            'multiplier': float,   # 0.0 / 0.5 / 1.0 / 2.0
            'immune': bool,        # True daca multiplier == 0.0
            'label': str,          # 'Imun!' / 'Super eficace!' / 'Ineficace!' / ''
        }
    """
    multiplier = INTERACTION_TABLE.get((attacker_nature, target_nature), 1.0)
    immune = multiplier == 0.0
    if immune:
        label = 'Imun!'
    elif multiplier == 2.0:
        label = 'Super eficace!'
    elif multiplier == 0.5:
        label = 'Ineficace!'
    else:
        label = ''
    return {
        'multiplier': multiplier,
        'immune': immune,
        'label': label,
    }


def get_nature(nature_key: str) -> dict | None:
    """Returneaza definitia unei naturi dupa cheie. None daca nu exista."""
    return NATURES.get(nature_key)


def roll_nature(available_natures: list[str]) -> str | None:
    """
    Alege aleatoriu o natura din lista disponibila a speciei.
    Returneaza None daca lista e goala.
    """
    if not available_natures:
        return None
    return random.choice(available_natures)


def all_nature_keys() -> list[str]:
    """Returneaza toate cheile de naturi definite."""
    return list(NATURES.keys())

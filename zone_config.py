# ─────────────────────────────────────────────
# zone_config.py
# Pool-uri de specii si naturi per zona, cu sistem de raritate.
# Editeaza DOAR acest fisier.
# ─────────────────────────────────────────────
#
# RARITATE — sanse de aparitie:
#   common:    60%
#   uncommon:  25%
#   rare:      10%
#   epic:       4%
#   legendary:  1%
#
# Format entry: ('cheie', 'raritate')
# ─────────────────────────────────────────────

RARITY_WEIGHTS = {
    'common':    60,
    'uncommon':  25,
    'rare':      10,
    'epic':       4,
    'legendary':  1,
}

ZONE_POOLS = {

    'arena': {
        'species': [
            ('dog',      'common'),
            ('cat',      'common'),
            ('duck',     'common'),
            ('blackcat', 'uncommon'),
            ('fox',      'rare'),
            ('rhino',    'epic'),
        ],
        'natures': [
            ('nature',  'common'),
            ('water',   'common'),
            ('earth',   'common'),
            ('fire',    'uncommon'),
            ('storm',   'uncommon'),
            ('ice',     'rare'),
            ('steel',   'rare'),
            ('light',   'epic'),
            ('shadow',  'epic'),
            ('crystal', 'epic'),
            ('dragon',  'legendary'),
        ],
    },

    'vanatoare': {
        'species': [
            ('cat',  'common'),
            ('duck', 'common'),
            ('fox',  'uncommon'),
            ('rhino', 'uncommon'),
        ],
        'natures': [
            ('nature', 'common'),
            ('water',  'common'),
            ('earth',  'common'),
            ('storm',  'uncommon'),
            ('ice',    'rare'),
            ('steel',  'uncommon'),
        ],
    },

    'padure': {
        'species': [
            ('cat',  'common'),
            ('duck', 'common'),
        ],
        'natures': [
            ('nature', 'common'),
            ('water',  'common'),
            ('earth',  'uncommon'),
        ],
    },

    'paduremid': {
        'species': [
            ('cat',  'common'),
            ('dog',  'common'),
            ('duck', 'common'),
            ('fox',  'uncommon'),
            ('rhino', 'uncommon'),
        ],
        'natures': [
            ('nature', 'common'),
            ('water',  'common'),
            ('earth',  'common'),
            ('storm',  'uncommon'),
            ('steel',  'uncommon'),
        ],
    },

    'paduredeep': {
        'species': [
            ('cat',      'common'),
            ('duck',     'common'),
            ('rhino',    'uncommon'),
            ('fox',      'uncommon'),
            ('blackcat', 'rare'),
        ],
        'natures': [
            ('nature', 'common'),
            ('water',  'common'),
            ('earth',  'common'),
            ('steel',  'uncommon'),
            ('storm',  'uncommon'),
            ('ice',    'rare'),
            ('shadow', 'epic'),
        ],
    },

    'pescuit': {
        'species': [
            ('verdian',    'common'),
            ('toadisimo',  'common'),
            ('goldfish',   'legendary'),
        ],
        'natures': [
            ('water',  'common'),
            ('nature', 'common'),
            ('dragon', 'legendary'),
        ],
    },

}

# Fallback daca zona nu e definita
DEFAULT_POOL = {
    'species': [
        ('dog',      'common'),
        ('cat',      'common'),
        ('duck',     'common'),
        ('blackcat', 'uncommon'),
        ('fox',      'rare'),
        ('rhino',    'epic'),
    ],
    'natures': [
        ('nature',  'common'),
        ('water',   'common'),
        ('earth',   'common'),
        ('fire',    'uncommon'),
        ('storm',   'uncommon'),
        ('ice',     'rare'),
        ('steel',   'rare'),
        ('light',   'epic'),
        ('shadow',  'epic'),
        ('crystal', 'epic'),
        ('dragon',  'legendary'),
    ],
}


def get_zone_pool(zone: str) -> dict:
    return ZONE_POOLS.get(zone, DEFAULT_POOL)


def weighted_choice(entries: list) -> str:
    """
    Alege random dintr-o lista de (cheie, raritate) folosind RARITY_WEIGHTS.
    """
    import random
    keys    = [e[0] for e in entries]
    weights = [RARITY_WEIGHTS.get(e[1], 60) for e in entries]
    return random.choices(keys, weights=weights, k=1)[0]

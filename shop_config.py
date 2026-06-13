# ─────────────────────────────────────────────
# shop_config.py
# Config magazine pentru Petomania.
# Fiecare magazin are un ID unic, un NPC si o lista de iteme vandabile.
# Itemele TREBUIE sa existe in inventory_config.py
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# STRUCTURA UNUI MAGAZIN:
#
# 'shop_id': {
#     'name':     'Numele Magazinului',   # Afișat în header
#     'npc':      'Nume NPC',             # Afișat sub titlu
#     'npc_icon': '🧙',                   # Emoji NPC
#     'desc':     'Descriere scurtă',     # Tagline
#     'categories': ['mancare', 'medical'],  # Categorii active (tab-uri)
#     'items': {
#         'mancare': ['item_key_1', 'item_key_2'],  # Cheile din inventory_config
#         'medical': ['item_key_3'],
#     }
# }
# ─────────────────────────────────────────────

SHOPS = {

    # ── ASSETS — Lunara Silvermist ────────────────────────────────────
    'lunara': {
        'name':     'Prăvălia Lunara',
        'npc':      'Lunara Silvermist',
        'npc_icon': '👸',
        'desc':     'Articole rare din toate colțurile regatului.',
        'categories': ['nexus', 'potiuni', 'esente'],
        'items': {
            'nexus':   ['nexus_basic'],
            'potiuni': ['healing_potion_small','energy_potion_small','mp_potion_small'],
            'esente':  [],   # de populat
        }
    },

    # ── PIATA — Negustor General ──────────────────────────────────────
    'piata_general': {
        'name':     'Piața Mare',
        'npc':      'Negustorul Bogdan',
        'npc_icon': '🧑‍🌾',
        'desc':     'Tot ce ai nevoie pentru drum lung.',
        'categories': ['mancare', 'medical'],
        'items': {
            'mancare': [],   # de populat
            'medical': [],   # de populat
        }
    },

    # ── CASTEL — Armurier ─────────────────────────────────────────────
    'castel_armurier': {
        'name':     'Arsenalul Regal',
        'npc':      'Armurier Dragoș',
        'npc_icon': '⚔️',
        'desc':     'Echipamente pentru aventurieri cu rang.',
        'categories': ['esente', 'capcane'],
        'items': {
            'esente':  [],   # de populat
            'capcane': [],   # de populat
        }
    },

    # ── BISERICA — Preoteasă ──────────────────────────────────────────
    'biserica_preoteasa': {
        'name':     'Sanctuarul Sfânt',
        'npc':      'Preoteasa Mirela',
        'npc_icon': '⛪',
        'desc':     'Ofrande și remedii binecuvântate.',
        'categories': ['ofrande', 'medical'],
        'items': {
            'ofrande': [],   # de populat
            'medical': [],   # de populat
        }
    },

    # ── AVENTURA — Explorator ─────────────────────────────────────────
    'aventura_explorator': {
        'name':     'Tabăra Exploratorilor',
        'npc':      'Exploratorul Viorel',
        'npc_icon': '🗺️',
        'desc':     'Capcane și provizii pentru expediții.',
        'categories': ['capcane', 'mancare'],
        'items': {
            'capcane': [],   # de populat
            'mancare': [],   # de populat
        }
    },
}

# ─────────────────────────────────────────────
# HELPER — returnează config magazin după ID
# ─────────────────────────────────────────────

def get_shop(shop_id: str) -> dict | None:
    return SHOPS.get(shop_id)


def get_all_shops() -> dict:
    return SHOPS

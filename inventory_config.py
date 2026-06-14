# ─────────────────────────────────────────────
# inventory_config.py
# Catalogul de iteme pentru sistemul Rucsac.
# Adaugă iteme noi DOAR în acest fișier.
# Codul din petgame_app.py nu trebuie modificat.
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# STRUCTURA UNUI ITEM:
#
# {
#     'key':      'nexus_simplu',      # ID unic snake_case
#     'name':     'Nexus Simplu',      # Nume afișat
#     'desc':     'Descriere scurtă',  # Afișat în popup
#     'icon':     '🔵',               # Emoji fallback (folosit daca lipseste img)
#     'img':      '/static/items/inventory_items/Nexus_Basic.png',  # PNG custom
#     'price':    50,                  # Preț Dacoins (0 = nu se cumpără)
#
#     # EFECTE — folosite de logica use_item()
#     # Omite cheile care nu se aplică itemului.
#     'effects': {
#         'hunger':     20,    # Mâncare — crește foamea
#         'energy':     15,    # Mâncare — crește energia
#         'hp':         30,    # Mâncare/Medical — restaurează HP luptă
#     },
#
#     # COMPORTAMENT
#     'usable_outside_battle': True,   # False = stub "doar în luptă"
#     'usable_in_zone': False,         # True = necesită zonă specifică (ofrande/capcane)
#     'quest_item': False,             # True = nu se poate arunca, nu apare "Folosește"
# }
# ─────────────────────────────────────────────

INVENTORY_ITEMS = {

    # ── NEXUS GLOBURI ────────────────────────────
    'nexus': [
    {
        'key':   'nexus_basic',
        'name':  'Nexus Basic',
        'desc':  'Un glob de energie primară. Folosit pentru captura companionilor.',
        'icon':  '🔮',
        'img':   '/static/items/inventory_items/Nexus_Basic.png',
        'price': 50,
        'effects': {},
        'usable_outside_battle': False,
        'capture_item': True,
        'quest_item': False,
    },
],

    # ── MÂNCARE ──────────────────────────────────
    'mancare': [
        {
            'key':   'lapte',
            'name':  'Lapte Proaspăt',
            'desc':  'Lapte muls direct de la vacă. Restaurează 5 HP și 5 MP.',
            'icon':  '🥛',
            'img':   '/static/items/inventory_items/Lapte.png',
            'price': 0,
            'effects': { 'hp': 5, 'mp': 5 },
            'usable_outside_battle': True,
            'quest_item': False,
        },
    ],

    # ── MEDICAMENTE ──────────────────────────────
    'medical': [
        # Primul item va fi adăugat aici
    ],

    # ── ESENȚE ───────────────────────────────────
    'esente': [
        # Primul item va fi adăugat aici
    ],

    # ── POȚIUNI ──────────────────────────────────
    'potiuni': [
    {
        'key':   'healing_potion_small',
        'name':  'Poțiune de Vindecare Mică',
        'desc':  'Restaurează 30 HP unui companion.',
        'icon':  '🧪',
        'img':   '/static/items/inventory_items/HealingPotion_Small.png',
        'price': 30,
        'effects': { 'hp': 30 },
        'usable_outside_battle': True,
        'quest_item': False,
    },
    {
    'key':   'energy_potion_small',
    'name':  'Poțiune de Energie Mică',
    'desc':  'Restaurează 30 energie unui companion.',
    'icon':  '🧪',
    'img':   '/static/items/inventory_items/EnergyPotion_Small.png',
    'price': 25,
    'effects': { 'energy': 30 },
    'usable_outside_battle': True,
    'quest_item': False,
},
    {
    'key':   'mp_potion_small',
    'name':  'Poțiune de Move Power',
    'desc':  'Restaurează 5 MP la toate abilitățile unui companion.',
    'icon':  '🔵',
    'img':   '/static/items/inventory_items/MovePowerPotion_Small.png',
    'price': 40,
    'effects': { 'mp': 5 },
    'usable_outside_battle': True,
    'quest_item': False,
},
    ],

    # ── OFRANDE ──────────────────────────────────
    'ofrande': [
        # Primul item va fi adăugat aici
    ],

    # ── CAPCANE ──────────────────────────────────
    'capcane': [
        # Primul item va fi adăugat aici
    ],

    # ── QUEST ITEMS ──────────────────────────────
    'quest': [
        # Quest items sunt adăugate programatic, nu manual
    ],
}

# ─────────────────────────────────────────────
# CONSTANTE SISTEM
# ─────────────────────────────────────────────

CATEGORY_SLOTS = 10   # Sloturi unice per categorie
STACK_MAX      = 12   # Cantitate maximă per slot

CATEGORY_NAMES = {
    'nexus':   'Nexus Globuri',
    'mancare': 'Mâncare',
    'medical': 'Medicamente',
    'esente':  'Esențe',
    'potiuni': 'Poțiuni',
    'ofrande': 'Ofrande',
    'capcane': 'Capcane',
    'quest':   'Quest Items',
}

CATEGORY_ORDER = ['nexus', 'mancare', 'medical', 'esente', 'potiuni', 'ofrande', 'capcane', 'quest']

# Mesaje stub per categorie când efectul nu e implementat încă
USE_STUB_MESSAGES = {
    'nexus':   'Nexus Globurile se folosesc în captură.',
    'esente':  'Efectul acestei esențe va fi definit în curând.',
    'potiuni': 'Poțiunile se folosesc înainte sau în timpul luptei.',
    'ofrande': 'Această ofrandă poate fi prezentată doar în zone specifice.',
    'capcane': 'Capcanele pot fi plasate doar în zone specifice.',
}

# ─────────────────────────────────────────────
# HELPER — lookup rapid după cheie
# ─────────────────────────────────────────────

def get_item(category: str, item_key: str) -> dict | None:
    """Returnează un item după categorie și cheie."""
    for item in INVENTORY_ITEMS.get(category, []):
        if item['key'] == item_key:
            return item
    return None


def get_all_items_flat() -> dict[str, dict]:
    """Returnează toate itemele ca dict {item_key: item_data} pentru lookup rapid."""
    result = {}
    for cat_items in INVENTORY_ITEMS.values():
        for item in cat_items:
            result[item['key']] = item
    return result

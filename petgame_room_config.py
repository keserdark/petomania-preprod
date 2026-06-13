# ─────────────────────────────────────────────
# petgame_room_config.py
# Config pentru upgrade-urile camerei din Petomania.
# Editeaza DOAR acest fisier pentru a adauga item-uri noi.
# Codul din petgame_app.py nu trebuie modificat.
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# STRUCTURA UNUI ITEM:
#
# {
#     'key':      'Wall1-Wood',        # ID unic — folosit in DB si logica
#     'name':     'Perete din Lemn',   # Nume afisat in shop
#     'desc':     'Descriere scurta',  # Descriere in shop
#     'price':    0,                   # Pret in Dacoins (0 = gratuit/default)
#     'file':     'Room1-Wall1-Wood.png', # Fisier PNG din PetGame/static/room1/
#     'default':  True,                # True = activ la inceput fara cumparare
#
#     # OPTIONAL — variante secrete afisate in camera in functie de ce are userul activ
#     # Userul vede mereu acelasi item in shop, dar in camera apare alt PNG
#     # Format: { 'key_alt_item_activ': 'fisier_alternativ.png', ... }
#     'variants': {
#         'Wall3-Window': 'Room1-Floor1-Wood-Sunshine.png',
#     },
#
#     # OPTIONAL — upgrade liniar
#     # Daca True si userul nu are 'requires', itemul e ascuns complet din shop
#     # Daca False sau absent, itemul e mereu vizibil (chiar daca locked)
#     'linear': True,
# }
#
# NOTA: ordinea in lista = ordinea in shop
# ─────────────────────────────────────────────

ROOM_ITEMS = {

    # ── PERETI ──────────────────────────────────
    'wall': [
        {
            'key':     'Wall1-Wood',
            'name':    'Perete din Lemn',
            'desc':    'Peretele default din lemn cald.',
            'price':   0,
            'file':    'Room1-Wall1-Wood.png',
            'default': True,
            'linear':  True,
        },
        {
            'key':     'Wall2-Wood',
            'name':    'Fereastră Lemn Lustruit',
            'desc':    'Lemn de calitate superioară, lustruit si lustruit.',
            'price':   150,
            'file':    'Room1-Wall2-Wood.png',
            'default': False,
            'linear':  True,
        },
        {
            'key':     'Wall3-Wood',
            'name':    'A doua Fereastră Lemn Lustruit',
            'desc':    'Lemn de calitate superioară, lustruit si lustruit.',
            'price':   150,
            'file':    'Room1-Wall3-Wood.png',
            'default': False,
            'requires': 'Wall2-Wood',
            'linear':   True,
        },
        {
            'key':     'Wall4-Wood',
            'name':    'Perete din caramidă',
            'desc':    'Construcție solidă, aspect rafinat.',
            'price':   300,
            'file':    'Room1-Wall4-Wood.png',
            'default': False,
            'requires': 'Wall3-Wood',
            'linear':   True,
        },
    ],

    # ── PARDOSEALA ──────────────────────────────
    'floor': [
        {
            'key':     'Floor1-Wood',
            'name':    'Parchet din Lemn',
            'file':    'Room1-Floor1-Wood.png',
            'default': True,
            'variants': {
                'Wall2-Wood': 'Room1-Floor1Wall2-Wood.png',  # reflexie fereastra
                'Wall3-Wood': 'Room1-Floor1Wall3-Wood.png',
                'Wall4-Wood': 'Room1-Floor1Wall3-Wood.png',
            },
        },
    ],

    # ── SEMINEU ─────────────────────────────────
    'chimney': [
        {
            'key':     'Chimney1-Stone',
            'name':    'Semineu din Piatră',
            'desc':    'Semineu clasic din piatră.',
            'price':   0,
            'file':    'Room1-Chimney1-Stone.png',
            'default': True,
        },

        # Adauga Chimney2 cu foc etc. aici
    ],

    # ── OBIECTE CAMERA ───────────────────────────
    # Obiecte plasate vizual in camera. Pot fi decorative sau clickabile.
    #
    # Campuri specifice obiectelor:
    #   'clickable': True/False      — daca poate fi apasat
    #   'action':    'loadout' | 'companicon' | None  — ce se intampla la click
    #   'pos_x':     0-100           — pozitie orizontala (% din latimea camerei)
    #   'pos_y':     0-100           — pozitie verticala (% din inaltimea camerei)
    #   'width':     5-50            — latime obiect (% din latimea camerei)
    #   'z_index':   5               — layer (5 = in fata petului care e z-index 4)
    #
    # Obiectele cumparate sunt stocate in coloana 'items' din room_config (JSON list de keys).
    # ─────────────────────────────────────────────
    'obiecte': [
        {
            'key':       'masa1',
            'name':      'Masă din Lemn',
            'desc':      'O masă simplă din lemn lăcuit.',
            'price':     150,
            'file':      'Masa1.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   5,
            'linear':    True,
        },
        {
            'key':       'Companicon',
            'name':      'Companicon Upgrade',
            'desc':      'Plătește un mag să-ți deblocheze o funcție în Companicon.',
            'price':     350,
            'file':      'CompaniconUpgrade.png',
            'default':   False,
            'clickable': True,
            'action':    'loadout',
            'pos_x':     83.9,
            'pos_y':     13.4,
            'width':     16,
            'z_index':   8,
            'linear':    True,
        },
        {
            'key':       'draperii',
            'name':      'Draperii',
            'desc':      'Draperii din catifea roșie.',
            'price':     500,
            'file':      'draperii.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   7,
            'linear':    True,
        },
        {
            'key':       'fotoliu',
            'name':      'Fotoliu',
            'desc':      'Fotoliu cu masută de cafea.',
            'price':     700,
            'file':      'fotoliu.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   8,
            'linear':    True,
        },
        {
            'key':       'carti',
            'name':      'Raft cu Cărți',
            'desc':      'Un raft cu cărți.',
            'price':     500,
            'file':      'carti.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   9,
            'linear':    True,
        },
        {
            'key':       'Candelabru',
            'name':      'Candelabru',
            'desc':      'Candelabru din alamă aurie.',
            'price':     700,
            'file':      'candelabru.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   10,
            'linear':    True,
        },
        {
            'key':       'Covor',
            'name':      'Covor',
            'desc':      'Covor persan, țesut manual.',
            'price':     1000,
            'file':      'covor.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   2,
            'linear':    True,
        },
        {
            'key':       'gratii',
            'name':      'Gratii',
            'desc':      'Gratii la semineu.',
            'price':     300,
            'file':      'gratii.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   4,
            'linear':    True,
        },
        {
            'key':       'focsub',
            'name':      'Foc',
            'desc':      'Aprinde focul în semineu.',
            'price':     300,
            'file':      'focsub.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   4,
            'linear':    True,
        },
        {
            'key':       'foc',
            'name':      'Focgif',
            'desc':      'Aprinde focul în semineu.',
            'price':     0,
            'file':      'focgif.gif',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     79,
            'pos_y':     32,
            'width':     11,
            'z_index':   5,
            'linear':    True,
            'hidden_in_shop': True,
        },
        
        {
            'key':       'focdeasupra',
            'name':      'Foc Deasupra',
            'desc':      '',
            'price':     0,
            'file':      'focdeasupra.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   6,
            'linear':    True,
            'requires':  'foc',
            'hidden_in_shop': True,
        },
        {
            'key':       'lumanari',
            'name':      'Lumanari',
            'desc':      'Lumanari deasupra la semineu',
            'price':     150,
            'file':      'lumanari.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   5,
        },
        {
            'key':       'glob',
            'name':      'Glob Pamantesc',
            'desc':      'Glob Pamantesc.',
            'price':     300,
            'file':      'glob.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   5,
        },
        {
            'key':       'scut',
            'name':      'Scut',
            'desc':      'Scut Regnum Dacorum.',
            'price':     500,
            'file':      'scut.png',
            'default':   False,
            'clickable': False,
            'action':    None,
            'pos_x':     0,
            'pos_y':     0,
            'width':     100,
            'z_index':   5,
        },
    ],
}

# ─────────────────────────────────────────────
# ITEM_BUNDLES
# Daca userul cumpara cheia trigger, se adauga automat si cheile din bundle.
# Nu modifica logica din petgame_app.py — adauga doar aici.
# ─────────────────────────────────────────────
ITEM_BUNDLES = {
    'focsub': ['foc', 'focdeasupra'],
}

# ─────────────────────────────────────────────
# HELPER — conversie lista -> dict pentru lookup rapid
# Nu modifica aceasta functie
# ─────────────────────────────────────────────

def get_item(category: str, key: str) -> dict | None:
    """Returneaza un item dupa categorie si cheie."""
    for item in ROOM_ITEMS.get(category, []):
        if item['key'] == key:
            return item
    return None

def get_default(category: str) -> str:
    """Returneaza cheia item-ului default din categorie."""
    for item in ROOM_ITEMS.get(category, []):
        if item.get('default'):
            return item['key']
    return ''

def resolve_file(category: str, key: str, room: dict) -> str:
    """
    Returneaza fisierul PNG corect pentru un item,
    tinand cont de variantele secrete.

    Args:
        category: 'wall', 'floor', 'chimney'
        key:      cheia item-ului activ (ex. 'Floor1-Wood')
        room:     dict-ul complet al configuratiei camerei userului
                  {'wall': '...', 'floor': '...', 'chimney': '...'}

    Returns:
        Numele fisierului PNG de folosit (fara path).
    """
    item = get_item(category, key)
    if not item:
        return f'{key}.png'

    # Verifica variantele secrete
    variants = item.get('variants', {})
    for trigger_key, variant_file in variants.items():
        # Cauta trigger_key in oricare categorie a camerei
        for cat_val in room.values():
            if cat_val == trigger_key:
                return variant_file

    return item['file']

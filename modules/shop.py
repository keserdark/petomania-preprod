"""
modules/shop.py
Logica magazin: listare iteme, cumpărare cu confirmare, validare stoc.
"""
from modules.db import get_db, get_dacoins, spend_dacoins
from modules.inventory import inv_add
from inventory_config import get_item as inv_get_item, CATEGORY_NAMES
from shop_config import get_shop


def build_shop_context(shop_id: str) -> dict | None:
    """
    Construieste contextul complet al unui magazin pentru frontend.
    Returnează None dacă shop_id nu există.
    """
    shop = get_shop(shop_id)
    if not shop:
        return None

    categories = []
    for cat_key in shop['categories']:
        item_keys = shop['items'].get(cat_key, [])
        items = []
        for key in item_keys:
            item_cfg = inv_get_item(cat_key, key)
            if item_cfg and item_cfg.get('price', 0) > 0:
                items.append({
                    'item_key': key,
                    'name':     item_cfg['name'],
                    'desc':     item_cfg['desc'],
                    'icon':     item_cfg.get('img') or item_cfg['icon'],
                    'img':      item_cfg.get('img'),
                    'price':    item_cfg['price'],
                    'category': cat_key,
                })
        categories.append({
            'key':   cat_key,
            'name':  CATEGORY_NAMES.get(cat_key, cat_key),
            'items': items,
        })

    return {
        'shop_id':    shop_id,
        'name':       shop['name'],
        'npc':        shop['npc'],
        'npc_icon':   shop['npc_icon'],
        'desc':       shop['desc'],
        'categories': categories,
    }


def shop_buy(user_id: int, shop_id: str, category: str, item_key: str, qty: int = 1) -> dict:
    """
    Cumpără qty bucăți dintr-un item.
    Verifică: magazin valid, item în magazin, preț > 0, dacoins suficiente, slot disponibil.
    """
    if qty < 1 or qty > 12:
        return {'ok': False, 'error': 'Cantitate invalidă (1–12).'}

    shop = get_shop(shop_id)
    if not shop:
        return {'ok': False, 'error': 'Magazin inexistent.'}

    # Verifică că itemul e în acest magazin
    allowed_keys = shop['items'].get(category, [])
    if item_key not in allowed_keys:
        return {'ok': False, 'error': 'Itemul nu se vinde în acest magazin.'}

    item_cfg = inv_get_item(category, item_key)
    if not item_cfg:
        return {'ok': False, 'error': 'Item necunoscut.'}

    price = item_cfg.get('price', 0)
    if price <= 0:
        return {'ok': False, 'error': 'Itemul nu este de vânzare.'}

    total_cost = price * qty
    balance    = get_dacoins(user_id)
    if balance < total_cost:
        return {'ok': False, 'error': f'Dacoins insuficienți. Ai {balance} ✦, costul este {total_cost} ✦.'}

    # Încearcă să adauge în inventar înainte să scadă dacoins
    add_result = inv_add(user_id, category, item_key, qty)
    if not add_result['ok']:
        return {'ok': False, 'error': add_result['error']}

    # Scade dacoins
    spent = spend_dacoins(user_id, total_cost)
    if not spent:
        # Rollback inventar
        from modules.inventory import inv_remove
        inv_remove(user_id, category, item_key, qty)
        return {'ok': False, 'error': 'Eroare la procesarea plății.'}

    return {
        'ok':        True,
        'item_name': item_cfg['name'],
        'item_icon': item_cfg.get('img') or item_cfg['icon'],
        'qty':       qty,
        'cost':      total_cost,
        'balance':   get_dacoins(user_id),
    }

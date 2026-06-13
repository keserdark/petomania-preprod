"""
modules/inventory.py
Rucsac: inv_add, inv_remove, inv_build_context, use_item, rename_pet.
"""
import json
from inventory_config import (
    CATEGORY_SLOTS, STACK_MAX,
    CATEGORY_NAMES, CATEGORY_ORDER, USE_STUB_MESSAGES,
    get_item as inv_get_item,
)
from cogs.petgame_stats import get_stats_at_level
from modules.db import get_db
from modules.pets import get_pet, get_form
from modules.loadout import get_loadout


def inv_get_all(user_id: int) -> dict:
    conn = get_db()
    rows = conn.execute(
        'SELECT category, item_key, quantity FROM inventory WHERE user_id = ? ORDER BY rowid',
        (user_id,)
    ).fetchall()
    conn.close()
    result = {cat: [] for cat in CATEGORY_ORDER}
    for r in rows:
        cat = r['category']
        if cat in result:
            result[cat].append({'item_key': r['item_key'], 'quantity': r['quantity']})
    return result


def inv_add(user_id: int, category: str, item_key: str, qty: int = 1) -> dict:
    if qty < 1:
        return {'ok': False, 'error': 'Cantitate invalidă.'}
    item_data = inv_get_item(category, item_key)
    if not item_data:
        return {'ok': False, 'error': f'Item necunoscut: {item_key}'}
    conn = get_db()
    existing = conn.execute(
        'SELECT quantity FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?',
        (user_id, category, item_key)
    ).fetchone()
    if existing:
        new_qty = existing['quantity'] + qty
        if new_qty > STACK_MAX:
            conn.close()
            return {'ok': False, 'error': f'Stack plin ({STACK_MAX} max).'}
        conn.execute(
            'UPDATE inventory SET quantity = ? WHERE user_id = ? AND category = ? AND item_key = ?',
            (new_qty, user_id, category, item_key)
        )
    else:
        slot_count = conn.execute(
            'SELECT COUNT(*) as cnt FROM inventory WHERE user_id = ? AND category = ?',
            (user_id, category)
        ).fetchone()['cnt']
        if slot_count >= CATEGORY_SLOTS:
            conn.close()
            return {'ok': False, 'error': f'Categoria "{CATEGORY_NAMES.get(category, category)}" este plină.'}
        if qty > STACK_MAX:
            conn.close()
            return {'ok': False, 'error': f'Cantitate depășește stack-ul maxim ({STACK_MAX}).'}
        conn.execute(
            'INSERT INTO inventory (user_id, category, item_key, quantity) VALUES (?, ?, ?, ?)',
            (user_id, category, item_key, qty)
        )
    conn.commit()
    conn.close()
    return {'ok': True}


def inv_remove(user_id: int, category: str, item_key: str, qty: int = 1) -> dict:
    conn = get_db()
    existing = conn.execute(
        'SELECT quantity FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?',
        (user_id, category, item_key)
    ).fetchone()
    if not existing or existing['quantity'] < qty:
        conn.close()
        return {'ok': False, 'error': 'Cantitate insuficientă.'}
    new_qty = existing['quantity'] - qty
    if new_qty == 0:
        conn.execute(
            'DELETE FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?',
            (user_id, category, item_key)
        )
    else:
        conn.execute(
            'UPDATE inventory SET quantity = ? WHERE user_id = ? AND category = ? AND item_key = ?',
            (new_qty, user_id, category, item_key)
        )
    conn.commit()
    conn.close()
    return {'ok': True}


def inv_build_context(user_id: int) -> list:
    raw = inv_get_all(user_id)
    categories = []
    for cat_key in CATEGORY_ORDER:
        items_in_cat = raw.get(cat_key, [])
        slots = []
        for slot_data in items_in_cat:
            item_cfg = inv_get_item(cat_key, slot_data['item_key'])
            if item_cfg:
                slots.append({
                    'item_key':              slot_data['item_key'],
                    'quantity':              slot_data['quantity'],
                    'name':                  item_cfg['name'],
                    'desc':                  item_cfg['desc'],
                    'icon':                  item_cfg.get('img') or item_cfg['icon'],
                    'is_img':                bool(item_cfg.get('img')),
                    'quest_item':            item_cfg.get('quest_item', False),
                    'usable_outside_battle': item_cfg.get('usable_outside_battle', True),
                    'usable_in_zone':        item_cfg.get('usable_in_zone', False),
                    'capture_item':          item_cfg.get('capture_item', False),
                })
        while len(slots) < CATEGORY_SLOTS:
            slots.append(None)
        categories.append({
            'key':        cat_key,
            'name':       CATEGORY_NAMES[cat_key],
            'slots':      slots,
            'slots_used': len(items_in_cat),
        })
    return categories


def _get_hp_max(p: dict) -> int:
    form  = get_form(p['level'])
    stats = get_stats_at_level(p['species'], p.get('nature'), p['level'], form)
    return stats['hp']


def _apply_effects(p: dict, effects: dict, category: str) -> list:
    """Aplica efectele unui item pe un dict de pet. Returneaza lista de changed."""
    changed = []
    hp_max = _get_hp_max(p)

    if 'hp' in effects and category in ('medical', 'potiuni', 'mancare'):
        old_hp = p.get('hp_current', 0)
        new_hp = min(hp_max, old_hp + effects['hp'])
        healed = new_hp - old_hp
        if healed > 0:
            p['hp_current'] = new_hp
            changed.append(f"HP +{healed}")
        elif category in ('medical', 'potiuni'):
            return []  # semnaleaza "deja plin"

    if 'hunger' in effects:
        p['hunger'] = min(100, p.get('hunger', 0) + effects['hunger'])
        changed.append(f"Foame +{effects['hunger']}")

    if 'energy' in effects:
        p['energy'] = min(100, p.get('energy', 0) + effects['energy'])
        changed.append(f"Energie +{effects['energy']}")

    if 'mp' in effects:
        mp_restore = effects['mp']
        try:
            mp_dict = json.loads(p.get('mp_json') or '{}')
        except Exception:
            mp_dict = {}
        # Restaureaza mp_restore pe fiecare abilitate, pana la max_mp
        from moves_config import get_moveset, get_move
        moveset = get_moveset(p['species'], p.get('nature'), p['level'])
        restored = 0
        for m in moveset:
            max_mp = m.get('max_mp', 15)
            current = mp_dict.get(m['key'], max_mp)
            new_val = min(max_mp, current + mp_restore)
            if new_val > current:
                restored += new_val - current
            mp_dict[m['key']] = new_val
        p['mp_json'] = json.dumps(mp_dict)
        if restored > 0:
            changed.append(f"MP +{mp_restore} per abilitate")
        else:
            return []  # toate la max

    return changed


def use_item(user_id: int, category: str, item_key: str, target_slot: int = 0) -> dict:
    """
    Foloseste un item.
    target_slot: 0 = pet activ, 1-4 = slot menajerie din loadout
    """
    item_cfg = inv_get_item(category, item_key)
    if not item_cfg:
        return {'ok': False, 'msg': 'Item necunoscut.'}
    if item_cfg.get('quest_item'):
        return {'ok': False, 'msg': 'Acest item nu poate fi folosit direct.'}
    if item_cfg.get('usable_in_zone'):
        return {'ok': False, 'msg': USE_STUB_MESSAGES.get(category, 'Necesita zona specifica.')}
    if category in USE_STUB_MESSAGES and category not in ('mancare', 'medical', 'potiuni'):
        return {'ok': False, 'msg': USE_STUB_MESSAGES[category]}

    effects = item_cfg.get('effects', {})

    # ── Target slot 0 = pet activ ──
    if target_slot == 0:
        pet = get_pet(user_id)
        if not pet:
            return {'ok': False, 'msg': 'Nu ai un companion activ.'}
        p = dict(pet)
        changed = _apply_effects(p, effects, category)
        if not changed:
            return {'ok': False, 'msg': 'HP-ul companionului este deja plin.' if 'hp' in effects else 'Acest item nu are efect momentan.'}
        conn = get_db()
        conn.execute(
            'UPDATE pets SET hunger = ?, energy = ?, hp_current = ?, mp_json = ? WHERE user_id = ?',
            (p['hunger'], p['energy'], p['hp_current'], p.get('mp_json', '{}'), user_id)
        )
        conn.commit()
        conn.close()
        inv_remove(user_id, category, item_key, 1)
        return {
            'ok': True,
            'msg': '✅ ' + ' · '.join(changed),
            'new_hp': p['hp_current'],
            'new_stats': {
                'hunger':      p.get('hunger', 0),
                'happiness':   p.get('happiness', 0),
                'cleanliness': p.get('cleanliness', 0),
                'energy':      p.get('energy', 0),
            }
        }

    # ── Target slot 1-4 = menajerie din loadout ──
    loadout = get_loadout(user_id)
    slot_key = f'slot_{target_slot + 1}'
    men_id = loadout.get(slot_key)
    if not men_id:
        return {'ok': False, 'msg': 'Slot gol.'}
    conn = get_db()
    row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (men_id, user_id)).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'msg': 'Companion negasit.'}
    p = dict(row)
    changed = _apply_effects(p, effects, category)
    if not changed:
        conn.close()
        return {'ok': False, 'msg': 'HP-ul companionului este deja plin.' if 'hp' in effects else 'Acest item nu are efect momentan.'}
    conn.execute(
        'UPDATE menagerie SET hunger = ?, energy = ?, hp_current = ?, mp_json = ? WHERE id = ?',
        (p['hunger'], p['energy'], p['hp_current'], p.get('mp_json', '{}'), men_id)
    )
    conn.commit()
    conn.close()
    inv_remove(user_id, category, item_key, 1)
    return {'ok': True, 'msg': '✅ ' + ' · '.join(changed), 'new_hp': p['hp_current']}


def rename_pet(user_id: int, new_name: str, pet_id: int = 0) -> dict:
    new_name = new_name.strip()[:24]
    if len(new_name) < 2:
        return {'ok': False, 'error': 'Numele trebuie să aibă cel puțin 2 caractere.'}
    conn = get_db()
    if pet_id and pet_id != 0:
        # Pet din menajerie
        row = conn.execute('SELECT id FROM menagerie WHERE id = ? AND user_id = ?', (pet_id, user_id)).fetchone()
        if not row:
            conn.close()
            return {'ok': False, 'error': 'Companion negăsit.'}
        conn.execute('UPDATE menagerie SET name = ? WHERE id = ? AND user_id = ?', (new_name, pet_id, user_id))
    else:
        # Pet activ
        pet = get_pet(user_id)
        if not pet:
            conn.close()
            return {'ok': False, 'error': 'Nu ai un companion activ.'}
        conn.execute('UPDATE pets SET name = ? WHERE user_id = ?', (new_name, user_id))
    conn.commit()
    conn.close()
    return {'ok': True, 'name': new_name}

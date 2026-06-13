"""
modules/loadout.py
Loadout: get_loadout, save_loadout, build_loadout_context, build_menagerie_for_loadout.
"""
from cogs.petgame_config import SPECIES
from cogs.petgame_natures import NATURES
from cogs.petgame_stats import get_stats_at_level
from modules.db import get_db
from modules.pets import get_form, get_state, get_image_url

STATIC_BASE = '/static'
NEXUS_BASE  = f"{STATIC_BASE}/items"


def get_loadout(user_id: int) -> dict:
    conn = get_db()
    row  = conn.execute('SELECT * FROM loadout WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    if row:
        return {'slot_2': row['slot_2'], 'slot_3': row['slot_3'],
                'slot_4': row['slot_4'], 'slot_5': row['slot_5']}
    return {'slot_2': None, 'slot_3': None, 'slot_4': None, 'slot_5': None}


def save_loadout(user_id: int, slot_2=None, slot_3=None, slot_4=None, slot_5=None):
    conn = get_db()
    conn.execute(
        'INSERT OR REPLACE INTO loadout (user_id, slot_2, slot_3, slot_4, slot_5) VALUES (?, ?, ?, ?, ?)',
        (user_id, slot_2, slot_3, slot_4, slot_5)
    )
    conn.commit()
    conn.close()


def build_loadout_slot(pet_row, slot_num: int) -> dict:
    if not pet_row:
        return {'empty': True, 'slot': slot_num}
    p        = dict(pet_row)
    form     = get_form(p['level'])
    state    = get_state(p['hunger'], p['happiness'], p['cleanliness'], p['energy'], bool(p['sleeping']))
    nat_key  = p.get('nature')
    nat_data = NATURES.get(nat_key) if nat_key else None
    return {
        'empty':       False,
        'slot':        slot_num,
        'id':          p.get('id'),
        'name':        p['name'],
        'species':     SPECIES.get(p['species'], {}).get('name', p['species']),
        'species_key': p['species'],
        'nature_key':  nat_key,
        'level':       p['level'],
        'form':        form,
        'gender':      p['gender'],
        'gender_icon': '♂️' if p['gender'] == 'male' else '♀️',
        'image_url':   get_image_url(p['species'], form, state, p['gender']),
        'nat_data':    nat_data,
        'hp_current':  p.get('hp_current', 0),
        'hp_max':      get_stats_at_level(p['species'], nat_key, p['level'], form)['hp'],
    }


def build_loadout_context(user_id: int) -> list:
    loadout = get_loadout(user_id)
    conn    = get_db()
    pet_row = conn.execute('SELECT * FROM pets WHERE user_id = ?', (user_id,)).fetchone()
    slots   = [build_loadout_slot(pet_row, 1)]
    for i, slot_key in enumerate(['slot_2', 'slot_3', 'slot_4', 'slot_5'], start=2):
        men_id = loadout[slot_key]
        if men_id:
            row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (men_id, user_id)).fetchone()
            slots.append(build_loadout_slot(row, i))
        else:
            slots.append({'empty': True, 'slot': i})
    conn.close()
    return slots


def build_menagerie_for_loadout(user_id: int, exclude_ids: list) -> list:
    conn = get_db()
    rows = conn.execute('SELECT * FROM menagerie WHERE user_id = ? ORDER BY level DESC', (user_id,)).fetchall()
    conn.close()
    result = []
    for row in rows:
        if row['id'] in exclude_ids:
            continue
        p        = dict(row)
        form     = get_form(p['level'])
        state    = get_state(p['hunger'], p['happiness'], p['cleanliness'], p['energy'], bool(p['sleeping']))
        nat_data = NATURES.get(p.get('nature')) if p.get('nature') else None
        result.append({
            'id':          p['id'],
            'name':        p['name'],
            'species':     SPECIES.get(p['species'], {}).get('name', p['species']),
            'species_key': p['species'],
            'level':       p['level'],
            'form':        form,
            'gender_icon': '♂️' if p['gender'] == 'male' else '♀️',
            'image_url':   get_image_url(p['species'], form, state, p['gender']),
            'nat_data':    nat_data,
        })
    return result

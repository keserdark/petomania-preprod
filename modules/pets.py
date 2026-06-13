"""
modules/pets.py
Helpers pentru pet: decay, XP, sync, build_pet_context, image_url.
"""
import time
from datetime import datetime, timezone

from cogs.petgame_config import SPECIES
from cogs.petgame_natures import NATURES
from cogs.petgame_stats import get_stats_at_level, FORM_MULTIPLIERS
from petgame_room_config import get_item, resolve_file
from modules.db import get_db

# Constante gameplay
DECAY_INTERVAL   = 60
SLEEP_REGEN      = 2
HP_SLEEP_REGEN   = 10   # HP regenerat per minut dormit
MP_SLEEP_REGEN   = 3    # MP regenerat per minut dormit (per abilitate)
FEED_AMOUNT      = 10
WASH_AMOUNT      = 10
PLAY_HAPPINESS   = 10
PLAY_ENERGY_COST = 5
PLAY_HUNGER_COST = 5
XP_PER_MINUTE    = 1
XP_TICK          = 60

STATIC_BASE = '/static'


# ── FORM / STATE ──────────────────────────────────────────

def get_form(level: int) -> int:
    if level < 15: return 1
    if level < 30: return 2
    return 3


def xp_for_level(level: int) -> int:
    return level * 60


def get_state(hunger, happiness, cleanliness, energy, sleeping) -> str:
    if sleeping:          return 'Sleep'
    if cleanliness < 30:  return 'Dirty'
    if hunger < 30:       return 'Hungry'
    if happiness < 30:    return 'Sad'
    if energy < 30:       return 'Sleep'
    return 'Basic'


# ── IMAGE URLs ────────────────────────────────────────────

def get_image_url(species: str, form: int, state: str, gender: str = 'male') -> str:
    base = f"{STATIC_BASE}/00transparent/{species}"
    if species in ('duck', 'fox', 'rhino') and form == 1:
        return f"{base}/Stage{form}-{state}-Form.png"
    if species in ('goldfish', 'verdian'):
        return f"{base}/Stage{form}-{state}-Form.png"
    if species in ('blackcat', 'dog', 'duck', 'fox', 'rhino', 'toadisimo'):
        gender_suffix = 'Male' if gender == 'male' else 'Female'
        return f"{base}/Stage{form}-{state}-Form-{gender_suffix}.png"
    return f"{base}/Stage{form}-{state}-Form.png"


def get_room_url(category: str, key: str, room: dict = None) -> str:
    if room:
        filename = resolve_file(category, key, room)
    else:
        item = get_item(category, key)
        filename = item['file'] if item else f'{key}.png'
    return f"{STATIC_BASE}/room1/{filename}"


# ── AGE ───────────────────────────────────────────────────

def format_age(born_at: int) -> str:
    now  = datetime.now(timezone.utc)
    born = datetime.fromtimestamp(born_at, tz=timezone.utc)
    days = (now - born).days
    years, months = days // 365, (days % 365) // 30
    if years > 0:
        return f"{years} {'an' if years == 1 else 'ani'}, {(days % 365) // 30} luni"
    if months > 0:
        return f"{months} {'lună' if months == 1 else 'luni'}, {days % 30} zile"
    return f"{days} {'zi' if days == 1 else 'zile'}"


# ── DB HELPERS ────────────────────────────────────────────

def get_pet(user_id: int):
    conn = get_db()
    pet  = conn.execute('SELECT * FROM pets WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return pet


def get_menagerie(user_id: int):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM menagerie WHERE user_id = ? ORDER BY stored_at DESC', (user_id,)
    ).fetchall()
    conn.close()
    return rows


def update_pet(user_id: int, **kwargs):
    conn = get_db()
    sets = ', '.join(f'{k}=?' for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    conn.execute(f'UPDATE pets SET {sets} WHERE user_id = ?', vals)
    conn.commit()
    conn.close()


# ── DECAY / XP ────────────────────────────────────────────

def apply_decay(pet) -> dict:
    now     = int(time.time())
    elapsed = now - pet['last_decay']
    ticks   = elapsed // DECAY_INTERVAL
    if ticks <= 0:
        return dict(pet)
    p = dict(pet)
    if p['sleeping']:
        sleep_minutes    = elapsed // 60
        p['energy']      = min(100, p['energy'] + sleep_minutes * SLEEP_REGEN)
        p['hunger']      = max(0, p['hunger']      - ticks)
        p['happiness']   = max(0, p['happiness']   - ticks)
        p['cleanliness'] = max(0, p['cleanliness'] - ticks)
        # HP regen la somn — doar daca nu e mort
        if sleep_minutes > 0:
            from cogs.petgame_stats import get_stats_at_level
            form   = get_form(p['level'])
            stats  = get_stats_at_level(p['species'], p.get('nature'), p['level'], form)
            hp_max = stats['hp']
            regen  = sleep_minutes * HP_SLEEP_REGEN
            p['hp_current'] = min(hp_max, p.get('hp_current', 0) + regen)
            # MP regen la somn — 3 per minut per abilitate
            import json
            from moves_config import get_move
            mp = {}
            try:
                mp = json.loads(p.get('mp_json') or '{}')
            except Exception:
                mp = {}
            mp_regen = sleep_minutes * MP_SLEEP_REGEN
            for key in list(mp.keys()):
                move = get_move(key)
                max_mp = move.get('max_mp', 15) if move else 15
                mp[key] = min(max_mp, mp.get(key, 0) + mp_regen)
            p['mp_json'] = json.dumps(mp)
        if p['energy'] >= 100 and p.get('hp_current', 0) >= hp_max:
            p['sleeping']      = 0
            p['sleep_started'] = None
            p['energy']        = 100
    else:
        p['hunger']      = max(0, p['hunger']      - ticks)
        p['happiness']   = max(0, p['happiness']   - ticks)
        p['cleanliness'] = max(0, p['cleanliness'] - ticks)
        p['energy']      = max(0, p['energy']      - ticks)
    p['last_decay'] = now
    return p


def apply_xp_tick(p: dict) -> dict:
    now     = int(time.time())
    if p['sleeping']:
        p['last_xp_tick'] = now
        return p
    elapsed = now - p['last_xp_tick']
    minutes = elapsed // XP_TICK
    if minutes <= 0:
        return p
    if p['hunger'] > 30 and p['happiness'] > 30 and p['cleanliness'] > 30 and p['energy'] > 30:
        p['xp'] += minutes * XP_PER_MINUTE
        while True:
            needed = xp_for_level(p['level'])
            if p['xp'] >= needed and p['level'] < 100:
                p['xp']    -= needed
                p['level'] += 1
            else:
                break
    p['last_xp_tick'] = now
    return p


def sync_pet(user_id: int):
    pet = get_pet(user_id)
    if not pet:
        return None
    p = apply_decay(pet)
    p = apply_xp_tick(p)
    update_pet(user_id,
        hunger=p['hunger'], happiness=p['happiness'],
        cleanliness=p['cleanliness'], energy=p['energy'],
        sleeping=p['sleeping'], sleep_started=p['sleep_started'],
        level=p['level'], xp=p['xp'],
        last_decay=p['last_decay'], last_xp_tick=p['last_xp_tick'],
        hp_current=p.get('hp_current', 0),
        mp_json=p.get('mp_json', '{}'),
    )
    return p


def sync_pet_hp(user_id: int):
    pet = get_pet(user_id)
    if not pet:
        return
    p      = dict(pet)
    form   = get_form(p['level'])
    stats  = get_stats_at_level(p['species'], p.get('nature'), p['level'], form)
    hp_max = stats['hp']
    # Nu resetam hp_current daca e 0 (pet mort) — pastram cum e in DB
    hp_cur = min(p['hp_current'], hp_max)
    conn = get_db()
    conn.execute('UPDATE pets SET hp = ?, hp_current = ? WHERE user_id = ?', (hp_max, hp_cur, user_id))
    conn.commit()
    conn.close()


def sync_menagerie_hp(user_id: int):
    """Initializeaza hp_current in menagerie unde e negativ (coruptie date).
    hp=0 inseamna pet mort — nu se atinge.
    hp>0 inseamna pet viu — nu se atinge.
    Aceasta functie nu mai face nimic; HP-ul e setat corect la INSERT.
    Ramane pentru compatibilitate cu apelurile existente.
    """
    pass


# ── CONTEXT ───────────────────────────────────────────────

def build_pet_context(p, get_signed_url_fn) -> dict:
    """
    Construieste contextul complet al unui pet pentru template.
    get_signed_url_fn: functia get_signed_url din app (evita import circular)
    """
    p         = dict(p)
    form      = get_form(p['level'])
    state     = get_state(p['hunger'], p['happiness'], p['cleanliness'], p['energy'], bool(p['sleeping']))
    image_url = get_image_url(p['species'], form, state, p['gender'])
    nature    = p.get('nature')
    nat_data  = NATURES.get(nature) if nature else None
    xp_needed = xp_for_level(p['level'])
    xp_pct    = round((p['xp'] / xp_needed) * 100) if xp_needed > 0 else 100
    stats     = get_stats_at_level(p['species'], nature, p['level'], form)
    bonus_stat = nat_data['bonus_stat'] if nat_data else None
    state_labels = {
        'Basic':  ('😊', 'Fericit'),
        'Hungry': ('🍖', 'Flămând'),
        'Dirty':  ('🤢', 'Murdar'),
        'Sad':    ('😢', 'Trist'),
        'Sleep':  ('😴', 'Adormit' if p['sleeping'] else 'Obosit'),
    }
    return {
        **p,
        'form':         form,
        'form_max':     len(FORM_MULTIPLIERS),
        'state':        state,
        'state_label':  state_labels.get(state, ('❓', state)),
        'image_url':    get_signed_url_fn(image_url),
        'nat_data':     nat_data,
        'xp_needed':    xp_needed,
        'xp_pct':       xp_pct,
        'stats':        stats,
        'bonus_stat':   bonus_stat,
        'age':          format_age(p['born_at']),
        'gender_icon':  '♂️' if p['gender'] == 'male' else '♀️',
        'species_name': SPECIES.get(p['species'], {}).get('name', p['species']),
    }


# ── BATTLE XP ────────────────────────────────────────────

def add_battle_xp(user_id: int, xp_amount: int, participant_ids: list) -> list:
    """Adauga XP dupa lupta, impartit egal intre participanti.
    participant_ids: 0 = pet activ (pets table), >0 = menagerie id
    Returneaza lista de dicts {name, xp, leveled_up}
    """
    if not participant_ids or xp_amount <= 0:
        return []
    xp_each = max(1, xp_amount // len(participant_ids))
    conn = get_db()
    results = []
    for pid in participant_ids:
        if pid == 0:
            row = conn.execute('SELECT name, level, xp FROM pets WHERE user_id = ?', (user_id,)).fetchone()
            if not row:
                continue
            old_level = row['level']
            level, xp = row['level'], row['xp'] + xp_each
            while True:
                needed = xp_for_level(level)
                if xp >= needed and level < 100:
                    xp -= needed
                    level += 1
                else:
                    break
            conn.execute('UPDATE pets SET xp = ?, level = ? WHERE user_id = ?', (xp, level, user_id))
            results.append({'name': row['name'], 'xp': xp_each, 'leveled_up': level > old_level})
        else:
            row = conn.execute('SELECT name, level, xp FROM menagerie WHERE id = ? AND user_id = ?', (pid, user_id)).fetchone()
            if not row:
                continue
            old_level = row['level']
            level, xp = row['level'], row['xp'] + xp_each
            while True:
                needed = xp_for_level(level)
                if xp >= needed and level < 100:
                    xp -= needed
                    level += 1
                else:
                    break
            conn.execute('UPDATE menagerie SET xp = ?, level = ? WHERE id = ?', (xp, level, pid))
            results.append({'name': row['name'], 'xp': xp_each, 'leveled_up': level > old_level})
    conn.commit()
    conn.close()
    return results

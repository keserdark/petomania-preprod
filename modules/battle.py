"""
modules/battle.py
Sistemul de lupta PvE Arena.
"""
import random
import math
from modules.db import get_db
from modules.pets import get_pet, get_form, get_image_url, get_state
from cogs.petgame_stats import get_stats_at_level
from cogs.petgame_natures import get_interaction
from moves_config import get_moveset, get_move


# ─────────────────────────────────────────────
# GENERARE NPC INAMIC
# ─────────────────────────────────────────────

SPECIES_LIST   = ['dog', 'cat', 'blackcat', 'duck', 'fox', 'rhino', 'goldfish', 'verdian', 'toadisimo']
NATURES_LIST   = ['fire', 'water', 'nature', 'earth', 'storm', 'ice', 'shadow', 'crystal', 'steel', 'light', 'dragon']
SPECIES_NAMES  = {'dog': 'Câine', 'cat': 'Pisică', 'blackcat': 'Pisică Neagră', 'duck': 'Rață', 'fox': 'Vulpe', 'rhino': 'Rinocer', 'goldfish': 'Peștișor', 'verdian': 'Verdian', 'toadisimo': 'Toadisimo'}
from npc_names_config import get_npc_name


def generate_npc(player_level: int, zone: str = 'arena') -> dict:
    """Genereaza un NPC random cu nivel apropriat (+-3 fata de player), filtrat dupa zona."""
    from cogs.petgame_config import SPECIES as SPECIES_CONFIG
    from zone_config import get_zone_pool, weighted_choice

    pool    = get_zone_pool(zone)
    species = weighted_choice(pool['species'])

    # Intersecteaza available_natures ale speciei cu naturile din pool
    available_natures = SPECIES_CONFIG.get(species, {}).get('available_natures', [e[0] for e in pool['natures']])
    pool_natures = [(key, rar) for key, rar in pool['natures'] if key in available_natures]
    # Daca intersectia e goala, folosim available_natures speciei cu weight 'common'
    if not pool_natures:
        pool_natures = [(n, 'common') for n in available_natures] or pool['natures']
    nature = weighted_choice(pool_natures)

    level   = max(1, player_level + random.randint(-3, 3))
    form    = get_form(level)
    stats   = get_stats_at_level(species, nature, level, form)
    moveset = get_moveset(species, nature, level)
    name    = get_npc_name(nature)
    gender  = random.choice(['male', 'female'])

    return {
        'id':           f'npc_{random.randint(10000, 99999)}',
        'name':         name,
        'species':      species,
        'species_name': SPECIES_NAMES.get(species, species),
        'nature':       nature,
        'level':        level,
        'form':         form,
        'gender':       gender,
        'hp_max':       stats['hp'],
        'hp_current':   stats['hp'],
        'stats':        stats,
        'moveset':      [m['key'] for m in moveset],
        'mp':           {m['key']: m.get('max_mp', 15) for m in moveset},
        'image_url':    get_image_url(species, form, 'Basic', gender),
        'is_npc':       True,
        'status':       None,  # stun, burn, poison, freeze
        'status_turns': 0,
        'status_value': 0,
        'shield':       0,
        'speed_mod':    0,
        'attack_mod':   0,
        'evasion_mod':  0,
    }


# ─────────────────────────────────────────────
# MP HELPERS
# ─────────────────────────────────────────────

def _load_mp(mp_json: str, moveset: list) -> dict:
    """Incarca MP din DB, completand cu max_mp pentru moves noi."""
    import json
    try:
        saved = json.loads(mp_json or '{}')
    except Exception:
        saved = {}
    return {m['key']: saved.get(m['key'], m.get('max_mp', 15)) for m in moveset}


def _get_primary_nature(nature):
    """Returneaza natura primara pentru moveset (primul element daca e lista)."""
    if isinstance(nature, list):
        return nature[0] if nature else None
    return nature


def save_combatant_mp(combatant: dict, user_id: int):
    """Salveaza MP-ul combatantului in DB."""
    import json
    mp_json = json.dumps(combatant.get('mp', {}))
    pid = combatant.get('id', 0)
    conn = get_db()
    if pid and pid != 0:
        conn.execute('UPDATE menagerie SET mp_json = ? WHERE id = ?', (mp_json, pid))
    else:
        conn.execute('UPDATE pets SET mp_json = ? WHERE user_id = ?', (mp_json, user_id))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# ACTIVE MOVES — citeste din DB sau fallback get_moveset
# ─────────────────────────────────────────────

def _get_active_moveset(user_id: int, pet_id: int, species: str, nature: str, level: int) -> list:
    """
    Returneaza moveset-ul activ al unui pet.
    Daca are active_moves in DB, le foloseste.
    Altfel fallback la get_moveset (self-taught bazat pe nivel).
    """
    from modules.db import get_db
    conn = get_db()
    rows = conn.execute(
        'SELECT slot, move_key FROM active_moves WHERE user_id = ? AND pet_id = ? ORDER BY slot',
        (user_id, pet_id)
    ).fetchall()
    conn.close()

    if rows:
        moves = []
        for r in rows:
            m = get_move(r['move_key'])
            if m:
                moves.append(m)
        if moves:
            return moves

    # Fallback: get_moveset standard
    return get_moveset(species, nature, level)


# ─────────────────────────────────────────────
# BUILD COMBATANT din pet DB
# ─────────────────────────────────────────────

def build_combatant(pet: dict) -> dict:
    """Construieste structura de combatant din datele petului."""
    level   = pet['level']
    form    = get_form(level)
    species = pet['species']
    nature  = pet.get('nature')
    primary_nature = _get_primary_nature(nature)
    stats   = get_stats_at_level(species, primary_nature, level, form)
    moveset = _get_active_moveset(pet.get('user_id', 0), pet.get('id', 0), species, primary_nature, level)

    gender    = pet.get('gender', 'male')
    image_url = get_image_url(species, form, 'Basic', gender)

    return {
        'id':           pet.get('id', 0),
        'name':         pet['name'],
        'species':      species,
        'species_name': SPECIES_NAMES.get(species, species),
        'nature':       nature,
        'level':        level,
        'form':         form,
        'hp_max':       stats['hp'],
        'hp_current':   min(pet.get('hp_current', stats['hp']), stats['hp']),
        'stats':        stats,
        'moveset':      [m['key'] for m in moveset],
        'mp':           _load_mp(pet.get('mp_json', '{}'), moveset),
        'image_url':    image_url,
        'is_npc':       False,
        'status':       None,
        'status_turns': 0,
        'status_value': 0,
        'shield':       0,
        'speed_mod':    0,
        'attack_mod':   0,
        'evasion_mod':  0,
    }


# ─────────────────────────────────────────────
# CALCUL DAMAGE
# ─────────────────────────────────────────────

def calculate_damage(attacker: dict, defender: dict, move: dict) -> tuple[int, str]:
    """
    Calculeaza damage-ul unui move.
    Returneaza (damage, effectiveness_label).
    """
    if move['type'] in ('status', 'heal'):
        return 0, ''

    base_attack  = attacker['stats']['attack'] + attacker['attack_mod']
    base_defense = max(1, defender['stats']['defense'])
    power        = move['power']

    # Interactiune natura (suporta single string sau lista pentru dual-nature)
    effectiveness = 1.0
    label = ''
    if move.get('nature') and defender.get('nature'):
        def_natures = defender['nature'] if isinstance(defender['nature'], list) else [defender['nature']]
        for def_nat in def_natures:
            result = get_interaction(move['nature'], def_nat)
            effectiveness *= result['multiplier']
        if effectiveness == 0.0:
            label = 'Imun!'
        elif effectiveness >= 4.0:
            label = 'Super eficace!'
        elif effectiveness == 2.0:
            label = 'Super eficace!'
        elif effectiveness <= 0.25:
            label = 'Ineficace!'
        elif effectiveness == 0.5:
            label = 'Ineficace!'
        if effectiveness == 0.0:
            return 0, label

    # Formula damage
    damage = math.floor(base_attack * power * effectiveness / base_defense * 10)
    damage = max(1, damage)

    # Random variance ±10%
    damage = math.floor(damage * random.uniform(0.9, 1.1))

    # Scade shield daca exista
    if defender['shield'] > 0:
        absorbed = min(defender['shield'], damage)
        damage   = damage - absorbed

    return max(0, damage), label


# ─────────────────────────────────────────────
# APLICA EFECT
# ─────────────────────────────────────────────

def apply_effect(target: dict, effect: dict) -> str | None:
    """Aplica efectul unui move pe target. Returneaza mesaj sau None."""
    if not effect:
        return None
    if random.random() > effect['chance']:
        return None

    etype = effect['type']
    val   = effect.get('value', 0)
    turns = effect.get('turns', 0)

    # Nu suprascrie un status activ cu alt status
    status_effects = ('stun', 'burn', 'poison', 'freeze')
    if etype in status_effects and target.get('status') in status_effects:
        return None

    if etype == 'stun':
        target['status'] = 'stun'
        target['status_turns'] = turns
        return f'{target["name"]} este amețit!'

    elif etype == 'burn':
        target['status'] = 'burn'
        target['status_turns'] = turns
        target['status_value'] = val
        return f'{target["name"]} este în flăcări! (-{val} HP/tur)'

    elif etype == 'poison':
        target['status'] = 'poison'
        target['status_turns'] = turns
        target['status_value'] = val
        return f'{target["name"]} este otrăvit! (-{val} HP/tur)'

    elif etype == 'freeze':
        target['status'] = 'freeze'
        target['status_turns'] = turns
        return f'{target["name"]} este înghețat!'

    elif etype == 'heal':
        healed = math.floor(target['hp_max'] * val / 100)
        target['hp_current'] = min(target['hp_max'], target['hp_current'] + healed)
        return f'{target["name"]} s-a vindecat cu {healed} HP!'

    elif etype == 'shield':
        target['shield'] = val
        return f'{target["name"]} are un scut de {val}!'

    elif etype == 'speed_down':
        target['speed_mod'] = -val
        target['status_turns'] = max(target['status_turns'], turns)
        return f'Viteza lui {target["name"]} a scăzut!'

    elif etype == 'speed_up':
        target['speed_mod'] = val
        return f'Viteza lui {target["name"]} a crescut!'

    elif etype == 'attack_down':
        target['attack_mod'] = -val
        return f'Atacul lui {target["name"]} a scăzut!'

    elif etype == 'evasion_up':
        target['evasion_mod'] = val
        return f'Eludarea lui {target["name"]} a crescut!'

    elif etype == 'lifesteal':
        steal = math.floor(target['hp_current'] * val / 100)
        return f'life_steal:{steal}'  # procesat de caller

    elif etype == 'reflect':
        target['shield'] = val
        return f'{target["name"]} reflectă {val}% din damage!'

    return None


# ─────────────────────────────────────────────
# PROCESEAZA TUR STATUS
# ─────────────────────────────────────────────

def process_status_tick(combatant: dict) -> list[str]:
    """Aplica damage/efecte de status la inceput de tur. Returneaza log."""
    log = []
    status = combatant.get('status')

    if status in ('burn', 'poison') and combatant['status_turns'] > 0:
        dmg = combatant['status_value']
        combatant['hp_current'] = max(0, combatant['hp_current'] - dmg)
        combatant['status_turns'] -= 1
        label = '🔥' if status == 'burn' else '☠️'
        log.append(f'{label} {combatant["name"]} pierde {dmg} HP din {status}!')
        if combatant['status_turns'] == 0:
            combatant['status'] = None

    # stun si freeze NU sunt procesate aici — execute_move le consuma

    return log


# ─────────────────────────────────────────────
# EXECUTA MOVE
# ─────────────────────────────────────────────

def execute_move(attacker: dict, defender: dict, move_key: str) -> dict:
    """
    Executa un move. Returneaza log-ul actiunii.
    """
    move = get_move(move_key)
    if not move:
        return {'log': [f'{attacker["name"]} nu cunoaște move-ul!'], 'hit': False}

    log    = []
    result = {'log': log, 'hit': False, 'damage': 0, 'effectiveness': '', 'effect_msg': None}

    # Verifica MP
    mp = attacker.get('mp', {})
    if mp.get(move_key, 0) <= 0:
        result['no_mp'] = True
        return result
    attacker['mp'][move_key] = mp.get(move_key, move.get('max_mp', 15)) - 1

    # Stun/freeze blocheaza atacul si consuma un tur
    if attacker.get('status') in ('stun', 'freeze'):
        log.append(f'{attacker["name"]} nu poate acționa! ({attacker["status"]})')
        attacker['status_turns'] -= 1
        if attacker['status_turns'] <= 0:
            attacker['status'] = None
            attacker['status_turns'] = 0
        return result

    # Accuracy check
    evasion_bonus = defender.get('evasion_mod', 0) / 100
    hit_chance    = move['accuracy'] * (1 - evasion_bonus * 0.5)
    if random.random() > hit_chance:
        log.append(f'{attacker["name"]} a ratat!')
        return result

    result['hit'] = True

    if move['type'] == 'heal':
        effect_msg = apply_effect(attacker, move.get('effect'))
        if effect_msg:
            log.append(effect_msg)
        result['effect_msg'] = effect_msg

    elif move['type'] == 'status':
        log.append(f'{attacker["name"]} folosește {move["name"]}!')
        effect_type = move.get('effect', {}).get('type', '')
        # Self-buff: heal, shield → pe attacker; restul (poison, stun, burn, freeze, speed_down) → pe defender
        self_buff_types = ('heal', 'shield')
        effect_target = attacker if effect_type in self_buff_types else defender
        effect_msg = apply_effect(effect_target, move.get('effect'))
        if effect_msg:
            log.append(effect_msg)
        result['effect_msg'] = effect_msg

    else:  # attack
        damage, eff_label = calculate_damage(attacker, defender, move)
        result['damage']        = damage
        result['effectiveness'] = eff_label

        if eff_label == 'Imun!':
            log.append(f'{attacker["name"]} folosește {move["name"]} — {eff_label}')
        else:
            defender['hp_current'] = max(0, defender['hp_current'] - damage)
            log.append(f'{attacker["name"]} folosește {move["name"]}! (-{damage} HP{" — " + eff_label if eff_label else ""})')

            # Aplica efect
            if move.get('effect'):
                effect_type = move['effect'].get('type', '')
                # heal si shield pe attack moves = self-buff pentru attacker
                effect_target = attacker if effect_type in ('heal', 'shield') else defender
                effect_msg = apply_effect(effect_target, move['effect'])
                if effect_msg:
                    if effect_msg.startswith('life_steal:'):
                        steal = int(effect_msg.split(':')[1])
                        attacker['hp_current'] = min(attacker['hp_max'], attacker['hp_current'] + steal)
                        log.append(f'{attacker["name"]} absoarbe {steal} HP!')
                    else:
                        log.append(effect_msg)
                    result['effect_msg'] = effect_msg

    return result


# ─────────────────────────────────────────────
# TUR COMPLET (player move + npc ai)
# ─────────────────────────────────────────────

def get_speed(combatant: dict) -> int:
    return combatant['stats']['speed'] + combatant.get('speed_mod', 0)


def npc_choose_move(npc: dict, player: dict) -> str:
    """AI simplu — alege random din moveset, cu preferinta pentru attack."""
    mp = npc.get('mp', {})
    moveset = [m for m in npc['moveset'] if mp.get(m, 15) > 0]
    if not moveset:
        moveset = npc['moveset']  # fallback daca toate sunt epuizate
    attacks = [m for m in moveset if get_move(m) and get_move(m)['type'] == 'attack']
    if attacks and random.random() < 0.7:
        return random.choice(attacks)
    return random.choice(moveset)


def execute_turn(player: dict, npc: dict, player_move_key: str) -> dict:
    """
    Executa un tur complet:
    1. Status tick pentru amandoi
    2. Decide ordinea (speed)
    3. Primul atacator executa
    4. Daca adversarul e in viata, executa al doilea
    5. Returneaza starea dupa tur
    """
    log = []

    # Status ticks
    p_status_log = process_status_tick(player)
    n_status_log = process_status_tick(npc)
    log.extend(p_status_log)
    log.extend(n_status_log)

    # NPC alege move
    npc_move_key = npc_choose_move(npc, player)

    # Ordine atac
    player_speed = get_speed(player)
    npc_speed    = get_speed(npc)

    if player_speed >= npc_speed:
        first, second         = player, npc
        first_move, sec_move  = player_move_key, npc_move_key
    else:
        first, second         = npc, player
        first_move, sec_move  = npc_move_key, player_move_key

    # Primul atac
    r1 = execute_move(first, second, first_move)
    log.extend(r1['log'])

    # Al doilea atac (daca al doilea e in viata)
    r2 = {'log': [], 'damage': 0}
    if second['hp_current'] > 0:
        r2 = execute_move(second, first, sec_move)
        log.extend(r2['log'])

    # Determine winner
    winner = None
    if player['hp_current'] <= 0:
        winner = 'npc'
        log.append(f'💀 {player["name"]} a căzut!')
    elif npc['hp_current'] <= 0:
        winner = 'player'
        log.append(f'🏆 {npc["name"]} a fost înfrânt!')

    return {
        'log':          log,
        'player':       _combatant_snapshot(player),
        'npc':          _combatant_snapshot(npc),
        'winner':       winner,
        'npc_move_key': npc_move_key,
    }


def _combatant_snapshot(c: dict) -> dict:
    """Snapshot minimal pentru frontend."""
    return {
        'id':           c['id'],
        'name':         c['name'],
        'level':        c.get('level', 1),
        'hp_current':   c['hp_current'],
        'hp_max':       c['hp_max'],
        'image_url':    c.get('image_url', ''),
        'status':       c.get('status'),
        'shield':       c.get('shield', 0),
        'speed_mod':    c.get('speed_mod', 0),
        'attack_mod':   c.get('attack_mod', 0),
        'evasion_mod':  c.get('evasion_mod', 0),
        'mp':           c.get('mp', {}),
        'nature':       c.get('nature'),
        'moveset':      c.get('moveset', []),
        'gender':       c.get('gender', 'male'),
    }


# ─────────────────────────────────────────────
# RECOMPENSE DUPA LUPTA
# ─────────────────────────────────────────────

def calculate_reward(player_level: int, npc_level: int, won: bool) -> int:
    """Calculeaza dacoins castigati."""
    if not won:
        return 0
    base   = 50 + npc_level * 10
    bonus  = max(0, npc_level - player_level) * 20
    return base + bonus + random.randint(0, 50)

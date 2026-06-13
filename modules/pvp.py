"""
modules/pvp.py
Sistem PvP 1v1 cu matchmaking automat.
"""
import json
import time
import random
from modules.db import get_db
from modules.battle import (
    build_combatant, execute_move, process_status_tick,
    get_speed, calculate_reward, _combatant_snapshot
)
from cogs.petgame_stats import get_stats_at_level

TURN_TIMEOUT = 30   # secunde per tur
QUEUE_TIMEOUT = 120 # secunde max in queue


# ─────────────────────────────────────────────
# QUEUE
# ─────────────────────────────────────────────

def queue_join(user_id: int, loadout_snapshot: list, size: int = 1) -> dict:
    """
    Adauga userul in queue sau gaseste un adversar.
    Returneaza: {status: 'waiting'|'matched', match_id: int|None}
    """
    conn = get_db()

    # Curata queue-ul de entries expirate
    expire_time = int(time.time()) - QUEUE_TIMEOUT
    conn.execute('DELETE FROM pvp_queue WHERE joined_at < ?', (expire_time,))

    # Verifica daca userul e deja intr-un match activ
    existing = conn.execute(
        '''SELECT id FROM pvp_match
           WHERE (player1_id = ? OR player2_id = ?)
           AND state = "active"''',
        (user_id, user_id)
    ).fetchone()
    if existing:
        conn.close()
        return {'status': 'already_in_match', 'match_id': existing['id']}

    # Cauta adversar in queue cu acelasi size
    opponent = conn.execute(
        '''SELECT * FROM pvp_queue
           WHERE user_id != ?
           AND json_extract(loadout_snapshot, '$.size') = ?
           ORDER BY joined_at ASC LIMIT 1''',
        (user_id, size)
    ).fetchone()

    if opponent:
        opp_id       = opponent['user_id']
        opp_data     = json.loads(opponent['loadout_snapshot'])
        opp_snapshot = opp_data['pets']

        session_data = _build_match_session(
            user_id, loadout_snapshot,
            opp_id,  opp_snapshot,
            size
        )

        conn.execute('DELETE FROM pvp_queue WHERE user_id = ?', (opp_id,))
        conn.execute('DELETE FROM pvp_queue WHERE user_id = ?', (user_id,))

        conn.execute(
            '''INSERT INTO pvp_match (player1_id, player2_id, state, session_data, created_at, updated_at)
               VALUES (?, ?, "active", ?, ?, ?)''',
            (user_id, opp_id, json.dumps(session_data), int(time.time()), int(time.time()))
        )
        conn.commit()
        match_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']
        conn.close()
        return {'status': 'matched', 'match_id': match_id}

    else:
        # Salveaza size impreuna cu snapshot
        payload = json.dumps({'pets': loadout_snapshot, 'size': size})
        conn.execute(
            'INSERT OR REPLACE INTO pvp_queue (user_id, loadout_snapshot, joined_at) VALUES (?, ?, ?)',
            (user_id, payload, int(time.time()))
        )
        conn.commit()
        conn.close()
        return {'status': 'waiting', 'match_id': None}
    """
    Adauga userul in queue sau gaseste un adversar.
    Returneaza: {status: 'waiting'|'matched', match_id: int|None}
    """
    conn = get_db()

    # Curata queue-ul de entries expirate
    expire_time = int(time.time()) - QUEUE_TIMEOUT
    conn.execute('DELETE FROM pvp_queue WHERE joined_at < ?', (expire_time,))

    # Verifica daca userul e deja intr-un match activ
    existing = conn.execute(
        '''SELECT id FROM pvp_match
           WHERE (player1_id = ? OR player2_id = ?)
           AND state = "active"''',
        (user_id, user_id)
    ).fetchone()
    if existing:
        conn.close()
        return {'status': 'already_in_match', 'match_id': existing['id']}

    # Cauta adversar in queue (primul din queue care nu e userul curent)
    opponent = conn.execute(
        'SELECT * FROM pvp_queue WHERE user_id != ? ORDER BY joined_at ASC LIMIT 1',
        (user_id,)
    ).fetchone()

    if opponent:
        # Match gasit — creeaza match
        opp_id       = opponent['user_id']
        opp_snapshot = json.loads(opponent['loadout_snapshot'])

        # Construieste session_data initiala
        session_data = _build_match_session(
            user_id, loadout_snapshot,
            opp_id,  opp_snapshot
        )

        conn.execute('DELETE FROM pvp_queue WHERE user_id = ?', (opp_id,))
        conn.execute('DELETE FROM pvp_queue WHERE user_id = ?', (user_id,))

        conn.execute(
            '''INSERT INTO pvp_match (player1_id, player2_id, state, session_data, created_at, updated_at)
               VALUES (?, ?, "active", ?, ?, ?)''',
            (user_id, opp_id, json.dumps(session_data), int(time.time()), int(time.time()))
        )
        conn.commit()
        match_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']
        conn.close()
        return {'status': 'matched', 'match_id': match_id}

    else:
        # Nimeni in queue — adauga userul
        conn.execute(
            'INSERT OR REPLACE INTO pvp_queue (user_id, loadout_snapshot, joined_at) VALUES (?, ?, ?)',
            (user_id, json.dumps(loadout_snapshot), int(time.time()))
        )
        conn.commit()
        conn.close()
        return {'status': 'waiting', 'match_id': None}


def queue_leave(user_id: int):
    """Scoate userul din queue."""
    conn = get_db()
    conn.execute('DELETE FROM pvp_queue WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def queue_poll(user_id: int) -> dict:
    """
    Polling din pagina de queue.
    Returneaza: {status: 'waiting'|'matched'|'not_in_queue', match_id: int|None}
    """
    conn = get_db()

    # Verifica match activ
    match = conn.execute(
        '''SELECT id FROM pvp_match
           WHERE (player1_id = ? OR player2_id = ?)
           AND state = "active"''',
        (user_id, user_id)
    ).fetchone()
    if match:
        conn.close()
        return {'status': 'matched', 'match_id': match['id']}

    # Verifica daca e in queue
    in_queue = conn.execute(
        'SELECT joined_at FROM pvp_queue WHERE user_id = ?', (user_id,)
    ).fetchone()
    conn.close()

    if in_queue:
        waited = int(time.time()) - in_queue['joined_at']
        return {'status': 'waiting', 'waited': waited}

    return {'status': 'not_in_queue'}


# ─────────────────────────────────────────────
# MATCH SESSION
# ─────────────────────────────────────────────

def _build_match_session(p1_id: int, p1_snapshot: list, p2_id: int, p2_snapshot: list, size: int = 1) -> dict:
    """Construieste session_data initiala pentru un match."""
    p1_combatant = _snapshot_to_combatant(p1_snapshot[0], p1_id)
    p2_combatant = _snapshot_to_combatant(p2_snapshot[0], p2_id)

    # Bench — restul petilor din snapshot (pentru 5v5)
    p1_bench = [_snapshot_to_combatant(p, p1_id) for p in p1_snapshot[1:]]
    p2_bench = [_snapshot_to_combatant(p, p2_id) for p in p2_snapshot[1:]]

    return {
        'p1_id':        p1_id,
        'p2_id':        p2_id,
        'size':         size,
        'p1':           p1_combatant,
        'p2':           p2_combatant,
        'p1_bench':     p1_bench,
        'p2_bench':     p2_bench,
        'p1_move':      None,
        'p2_move':      None,
        'turn_started': int(time.time()),
        'turn':         1,
        'log':          [],
        'winner':       None,
        'state':        'choosing',
    }


def _snapshot_to_combatant(pet_data: dict, user_id: int) -> dict:
    """Converteste un pet snapshot din loadout in combatant."""
    from modules.battle import build_combatant as _bc
    if not isinstance(pet_data, dict):
        pet_data = dict(pet_data)
    pet_data['user_id'] = user_id
    return _bc(pet_data)


def get_match(match_id: int) -> dict | None:
    """Returneaza match-ul cu session_data parsed."""
    conn = get_db()
    row = conn.execute('SELECT * FROM pvp_match WHERE id = ?', (match_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id':         row['id'],
        'player1_id': row['player1_id'],
        'player2_id': row['player2_id'],
        'state':      row['state'],
        'session':    json.loads(row['session_data']),
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def save_match_session(match_id: int, session: dict, state: str = 'active'):
    """Salveaza session_data inapoi in DB."""
    conn = get_db()
    conn.execute(
        'UPDATE pvp_match SET session_data = ?, state = ?, updated_at = ? WHERE id = ?',
        (json.dumps(session), state, int(time.time()), match_id)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# TURN
# ─────────────────────────────────────────────

def submit_move(match_id: int, user_id: int, move_key: str) -> dict:
    """
    Userul isi trimite mutarea.
    Daca amandoi au ales, executa turul.
    Returneaza starea curenta a match-ului.
    """
    match = get_match(match_id)
    if not match:
        return {'ok': False, 'error': 'Match inexistent.'}

    session = match['session']

    if session.get('state') == 'finished':
        return {'ok': False, 'error': 'Match terminat.'}

    # Verifica ca userul e in match
    is_p1 = (user_id == match['player1_id'])
    is_p2 = (user_id == match['player2_id'])
    if not is_p1 and not is_p2:
        return {'ok': False, 'error': 'Nu ești în acest match.'}

    # Verifica ca move-ul e valid
    combatant_key = 'p1' if is_p1 else 'p2'
    combatant = session[combatant_key]
    if move_key not in combatant.get('moveset', []):
        return {'ok': False, 'error': 'Move invalid.'}

    # Seteaza mutarea
    move_field = 'p1_move' if is_p1 else 'p2_move'
    if session.get(move_field) is not None:
        return {'ok': False, 'error': 'Ai trimis deja mutarea.'}

    session[move_field] = move_key

    # Verifica daca amandoi au ales
    if session.get('p1_move') and session.get('p2_move'):
        session = _resolve_turn(session)
    else:
        save_match_session(match_id, session)

    save_match_session(
        match_id, session,
        state='finished' if session.get('state') == 'finished' else 'active'
    )

    return {'ok': True, 'session': _session_snapshot(session, user_id, match)}


def _resolve_turn(session: dict) -> dict:
    """Executa turul cand ambii jucatori au ales."""
    p1 = session['p1']
    p2 = session['p2']
    p1_move = session['p1_move']
    p2_move = session['p2_move']

    log = []

    # Status ticks
    log.extend(process_status_tick(p1))
    log.extend(process_status_tick(p2))

    # Ordine atac dupa speed
    p1_speed = get_speed(p1)
    p2_speed = get_speed(p2)

    if p1_speed >= p2_speed:
        first, second     = p1, p2
        first_move, sec_move = p1_move, p2_move
    else:
        first, second     = p2, p1
        first_move, sec_move = p2_move, p1_move

    r1 = execute_move(first, second, first_move)
    log.extend(r1['log'])

    r2 = {'log': [], 'damage': 0}
    if second['hp_current'] > 0 and not r1.get('no_mp'):
        r2 = execute_move(second, first, sec_move)
        log.extend(r2['log'])

    # Determine winner
    winner = None
    if p1['hp_current'] <= 0 and p2['hp_current'] <= 0:
        winner = 'draw'
        log.append('⚔️ Egalitate!')
    elif p1['hp_current'] <= 0:
        winner = session['p2_id']
        log.append(f'💀 {p1["name"]} a căzut!')
    elif p2['hp_current'] <= 0:
        winner = session['p1_id']
        log.append(f'🏆 {p2["name"]} a fost înfrâns!')

    session['p1'] = p1
    session['p2'] = p2
    session['log'] = log
    session['turn'] += 1
    session['p1_move'] = None
    session['p2_move'] = None
    session['turn_started'] = int(time.time())

    if winner is not None:
        session['winner'] = winner
        session['state']  = 'finished'
    else:
        session['state'] = 'choosing'

    return session


def check_timeout(match_id: int) -> dict:
    """
    Verifica daca un tur a expirat (30s).
    Daca da, auto-alege prima mutare disponibila pentru jucatorul care n-a ales.
    """
    match = get_match(match_id)
    if not match:
        return {'ok': False}

    session = match['session']
    if session.get('state') != 'choosing':
        return {'ok': True, 'session': session}

    elapsed = int(time.time()) - session.get('turn_started', 0)
    if elapsed < TURN_TIMEOUT:
        return {'ok': True, 'session': session}

    # Auto-choose pentru cei care n-au ales
    for pid, pkey, mkey in [
        (match['player1_id'], 'p1', 'p1_move'),
        (match['player2_id'], 'p2', 'p2_move'),
    ]:
        if session.get(mkey) is None:
            moveset = session[pkey].get('moveset', [])
            mp      = session[pkey].get('mp', {})
            available = [m for m in moveset if mp.get(m, 1) > 0]
            auto_move = available[0] if available else (moveset[0] if moveset else None)
            if auto_move:
                session[mkey] = auto_move
                session['log'] = session.get('log', []) + [
                    f'⏰ {session[pkey]["name"]} a depășit timpul — s-a ales automat!'
                ]

    if session.get('p1_move') and session.get('p2_move'):
        session = _resolve_turn(session)

    save_match_session(
        match_id, session,
        state='finished' if session.get('state') == 'finished' else 'active'
    )
    return {'ok': True, 'session': session}


# ─────────────────────────────────────────────
# ABANDON
# ─────────────────────────────────────────────

def abandon_match(match_id: int, user_id: int) -> dict:
    """Userul abandoneaza — adversarul castiga automat."""
    match = get_match(match_id)
    if not match:
        return {'ok': False}

    session = match['session']
    if session.get('state') == 'finished':
        return {'ok': True}  # deja terminat

    is_p1 = (user_id == match['player1_id'])
    winner_id = match['player2_id'] if is_p1 else match['player1_id']
    loser_key = 'p1' if is_p1 else 'p2'

    session['winner'] = winner_id
    session['state']  = 'finished'
    session['log']    = session.get('log', []) + [
        f'🏳️ {session[loser_key]["name"]} a abandonat!'
    ]

    save_match_session(match_id, session, state='finished')
    return {'ok': True, 'winner_id': winner_id}


# ─────────────────────────────────────────────
# RECOMPENSE
# ─────────────────────────────────────────────

def grant_pvp_reward(match_id: int, user_id: int) -> dict:
    """
    Acorda recompensa dupa match.
    Returneaza {dacoins, xp, already_claimed}.
    """
    match = get_match(match_id)
    if not match:
        return {'ok': False}

    session = match['session']
    if session.get('state') != 'finished':
        return {'ok': False, 'error': 'Match nu e terminat.'}

    winner_id = session.get('winner')
    won = (winner_id == user_id)

    # Nivelul adversarului
    is_p1 = (user_id == match['player1_id'])
    opp_key  = 'p2' if is_p1 else 'p1'
    opp_level = session[opp_key].get('level', 1)
    my_level  = session['p1' if is_p1 else 'p2'].get('level', 1)

    dacoins = calculate_reward(my_level, opp_level, won) if won else 0

    # Acorda dacoins
    if dacoins > 0:
        from modules.db import get_db
        conn = get_db()
        conn.execute(
            'INSERT OR IGNORE INTO dacoins (user_id, balance) VALUES (?, 300)',
            (user_id,)
        )
        conn.execute(
            'UPDATE dacoins SET balance = balance + ? WHERE user_id = ?',
            (dacoins, user_id)
        )
        conn.commit()
        conn.close()

    return {'ok': True, 'won': won, 'dacoins': dacoins}


# ─────────────────────────────────────────────
# POLL MATCH STATE
# ─────────────────────────────────────────────

def poll_match(match_id: int, user_id: int) -> dict:
    """
    Polling din pagina de battle PvP.
    Verifica timeout, returneaza starea curenta.
    """
    # Verifica timeout
    check_timeout(match_id)

    match = get_match(match_id)
    if not match:
        return {'ok': False, 'error': 'Match inexistent.'}

    session = match['session']

    # Verifica ca userul e in match
    if user_id not in (match['player1_id'], match['player2_id']):
        return {'ok': False, 'error': 'Nu ești în acest match.'}

    return {'ok': True, 'session': _session_snapshot(session, user_id, match)}


def _get_moveset_data(moveset: list) -> list:
    """Returneaza date complete pentru moves (nume, icon, power, nature)."""
    from moves_config import get_move
    result = []
    for key in moveset:
        m = get_move(key)
        if m:
            result.append({
                'key':    key,
                'name':   m.get('name', key),
                'icon':   m.get('icon', '⚔️'),
                'power':  m.get('power', 0),
                'nature': m.get('nature', ''),
                'type':   m.get('type', 'attack'),
            })
    return result


def _session_snapshot(session: dict, user_id: int, match: dict) -> dict:
    """
    Snapshot al sesiunii pentru frontend.
    Returneaza date din perspectiva userului curent.
    """
    is_p1   = (user_id == match['player1_id'])
    me_key  = 'p1' if is_p1 else 'p2'
    opp_key = 'p2' if is_p1 else 'p1'

    me  = session[me_key]
    opp = session[opp_key]

    # Timp ramas in tur
    elapsed     = int(time.time()) - session.get('turn_started', int(time.time()))
    time_left   = max(0, TURN_TIMEOUT - elapsed)

    # Am ales deja?
    my_move_field = 'p1_move' if is_p1 else 'p2_move'
    i_chose = session.get(my_move_field) is not None

    return {
        'state':        session.get('state'),
        'turn':         session.get('turn', 1),
        'time_left':    time_left,
        'i_chose':      i_chose,
        'winner':       session.get('winner'),
        'log':          session.get('log', []),
        'me':           _combatant_snapshot(me),
        'opponent':     _combatant_snapshot(opp),
        'opp_name':     opp.get('name', '?'),
        'moveset_data': _get_moveset_data(me.get('moveset', [])),
    }

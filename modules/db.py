"""
modules/db.py
Conexiune DB, init_db, dacoins, room_config.
"""
import sqlite3
import json
from datetime import datetime

DB_PATH = '/root/village-bot/village-bot/stats.db'


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS dacoins (
            user_id    INTEGER PRIMARY KEY,
            balance    INTEGER NOT NULL DEFAULT 300,
            updated_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS room_config (
            user_id       INTEGER PRIMARY KEY,
            wall          TEXT NOT NULL DEFAULT "Wall1-Wood",
            floor         TEXT NOT NULL DEFAULT "Floor1-Wood",
            chimney       TEXT NOT NULL DEFAULT "Chimney1-Stone",
            items         TEXT NOT NULL DEFAULT "{}",
            room_version  INTEGER NOT NULL DEFAULT 1
        )
    ''')
    try:
        c.execute('ALTER TABLE room_config ADD COLUMN room_version INTEGER NOT NULL DEFAULT 1')
    except Exception:
        pass
    c.execute('''
        CREATE TABLE IF NOT EXISTS lady_interactions (
            user_id           INTEGER PRIMARY KEY,
            first_interaction INTEGER NOT NULL DEFAULT 1,
            player_name       TEXT,
            has_companicon    INTEGER NOT NULL DEFAULT 0
        )
    ''')
    try:
        c.execute('ALTER TABLE lady_interactions ADD COLUMN has_companicon INTEGER NOT NULL DEFAULT 0')
    except Exception:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id              INTEGER PRIMARY KEY,
            concesiunevanatoare  INTEGER NOT NULL DEFAULT 0,
            daiana_warned        INTEGER NOT NULL DEFAULT 0
        )
    ''')
    for col in ('concesiunevanatoare', 'daiana_warned'):
        try:
            c.execute(f'ALTER TABLE user_permissions ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0')
        except Exception:
            pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            category    TEXT NOT NULL,
            item_key    TEXT NOT NULL,
            quantity    INTEGER NOT NULL DEFAULT 1,
            UNIQUE(user_id, category, item_key)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            badge_key TEXT NOT NULL,
            earned_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            UNIQUE(user_id, badge_key)
        )
    ''')
    for col in ('hp', 'hp_current'):
        try:
            c.execute(f'ALTER TABLE pets ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0')
        except Exception:
            pass
    for col in ('hp', 'hp_current'):
        try:
            c.execute(f'ALTER TABLE menagerie ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0')
        except Exception:
            pass
    try:
        c.execute("ALTER TABLE pets ADD COLUMN mp_json TEXT NOT NULL DEFAULT '{}'")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE menagerie ADD COLUMN mp_json TEXT NOT NULL DEFAULT '{}'")
    except Exception:
        pass
    c.execute('''
        CREATE TABLE IF NOT EXISTS loadout (
            user_id    INTEGER PRIMARY KEY,
            slot_2     INTEGER,
            slot_3     INTEGER,
            slot_4     INTEGER,
            slot_5     INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS known_moves (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            pet_id     INTEGER NOT NULL,
            move_key   TEXT NOT NULL,
            learned_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            UNIQUE(user_id, pet_id, move_key)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS active_moves (
            user_id    INTEGER NOT NULL,
            pet_id     INTEGER NOT NULL,
            slot       INTEGER NOT NULL,
            move_key   TEXT NOT NULL,
            PRIMARY KEY (user_id, pet_id, slot)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS pvp_queue (
            user_id           INTEGER PRIMARY KEY,
            loadout_snapshot  TEXT NOT NULL,
            joined_at         INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS pvp_match (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            player1_id   INTEGER NOT NULL,
            player2_id   INTEGER NOT NULL,
            state        TEXT NOT NULL DEFAULT 'active',
            session_data TEXT NOT NULL DEFAULT '{}',
            created_at   INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            updated_at   INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        )
    ''')

    conn.commit()
    conn.close()


# ── DACOINS ──────────────────────────────────────────────

def get_dacoins(user_id: int) -> int:
    conn = get_db()
    row = conn.execute('SELECT balance FROM dacoins WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    if not row:
        conn = get_db()
        conn.execute(
            'INSERT OR IGNORE INTO dacoins (user_id, balance, updated_at) VALUES (?, 300, ?)',
            (user_id, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return 300
    return row['balance']


def spend_dacoins(user_id: int, amount: int) -> bool:
    conn = get_db()
    row = conn.execute('SELECT balance FROM dacoins WHERE user_id = ?', (user_id,)).fetchone()
    if not row or row['balance'] < amount:
        conn.close()
        return False
    conn.execute(
        'UPDATE dacoins SET balance = balance - ?, updated_at = ? WHERE user_id = ?',
        (amount, datetime.now().isoformat(), user_id)
    )
    conn.commit()
    conn.close()
    return True


# ── USER PERMISSIONS ────────────────────────────────────────

def get_user_permissions(user_id: int) -> dict:
    conn = get_db()
    conn.execute('INSERT OR IGNORE INTO user_permissions (user_id) VALUES (?)', (user_id,))
    conn.commit()
    row = conn.execute('SELECT * FROM user_permissions WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(row)


def set_user_permission(user_id: int, key: str, value: int):
    conn = get_db()
    conn.execute('INSERT OR IGNORE INTO user_permissions (user_id) VALUES (?)', (user_id,))
    conn.execute(f'UPDATE user_permissions SET {key} = ? WHERE user_id = ?', (value, user_id))
    conn.commit()
    conn.close()


# ── ROOM CONFIG ──────────────────────────────────────────

def get_room_config(user_id: int) -> dict:
    conn = get_db()
    row = conn.execute('SELECT * FROM room_config WHERE user_id = ?', (user_id,)).fetchone()
    if not row:
        conn.execute('INSERT OR IGNORE INTO room_config (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()
        return {'wall': 'Wall1-Wood', 'floor': 'Floor1-Wood', 'chimney': 'Chimney1-Stone', 'items': {}}
    conn.close()
    return {
        'wall':         row['wall'],
        'floor':        row['floor'],
        'chimney':      row['chimney'],
        'items':        json.loads(row['items'] or '{}'),
        'room_version': row['room_version'] if 'room_version' in row.keys() else 1,
    }


def save_room_config(user_id: int, wall: str, floor: str, chimney: str, items: dict):
    conn = get_db()
    conn.execute(
        'INSERT OR REPLACE INTO room_config (user_id, wall, floor, chimney, items) VALUES (?, ?, ?, ?, ?)',
        (user_id, wall, floor, chimney, json.dumps(items))
    )
    conn.commit()
    conn.close()


def bump_room_version(user_id: int):
    """Incrementeaza versiunea camerei pentru cache busting."""
    conn = get_db()
    conn.execute('UPDATE room_config SET room_version = room_version + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

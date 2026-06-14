"""
Regnum Dacorum — Petomania Web
================================
Flask app independent pe portul 5002.
OAuth Discord propriu — redirect URI: https://regnum-dacorum.ro/joc/petomania/callback

Rulare:
    python3 petgame_app.py

In productie:
    screen -dmS petomania python3 petgame_app.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import secrets
import requests
import time
import io
import threading
import urllib.request
import concurrent.futures
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, abort, Response
)
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# ── MODULES ──────────────────────────────────────────────────────────
from modules.db       import get_db, init_db, get_dacoins, spend_dacoins, get_room_config, save_room_config, bump_room_version
from modules.pets     import (get_pet, get_menagerie, get_form, get_state, get_image_url,
                               get_room_url, sync_pet, sync_pet_hp, sync_menagerie_hp, update_pet, build_pet_context, add_battle_xp,
                               format_age, xp_for_level,
                               DECAY_INTERVAL, FEED_AMOUNT, WASH_AMOUNT,
                               PLAY_HAPPINESS, PLAY_ENERGY_COST, PLAY_HUNGER_COST)
from modules.inventory    import (inv_build_context, inv_add, inv_remove, use_item, rename_pet)
from modules.loadout      import (get_loadout, save_loadout, build_loadout_slot,
                                   build_loadout_context, build_menagerie_for_loadout)
from modules.companicon   import build_companicon_entries, _img_url as companicon_img_url
from modules.discord_helpers import (get_member_roles, get_lady_interaction,
                                      build_lady_dialog, build_lady_pet_text)
from inventory_config     import get_item as inv_get_item
from shop_config          import get_shop
from modules.shop         import build_shop_context, shop_buy
from petgame_room_config  import ROOM_ITEMS, ITEM_BUNDLES
from cogs.petgame_config  import SPECIES
from cogs.petgame_natures import NATURES
from cogs.petgame_stats   import get_stats_at_level

# ── FLASK APP ─────────────────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.getenv('PETOMANIA_SECRET_KEY', secrets.token_hex(32))

# ── CONFIG ────────────────────────────────────────────────────────────

DISCORD_CLIENT_ID     = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_API           = 'https://discord.com/api/v10'
DISCORD_OAUTH_AUTHORIZE = 'https://discord.com/oauth2/authorize'
DISCORD_OAUTH_TOKEN     = f'{DISCORD_API}/oauth2/token'
REDIRECT_URI = os.getenv('PETOMANIA_REDIRECT_URI', 'http://204.168.179.80:5002/joc/petomania/callback')

STATIC_BASE = '/static'

SHOP_ITEMS = {cat: {item['key']: item for item in items} for cat, items in ROOM_ITEMS.items()}

# ── TOKEN STORE (signed image URLs) ──────────────────────────────────

def get_static_url(path: str) -> str:
    """Converteste un path relativ la static URL direct."""
    # path poate fi 'room1/Wall1.png' sau 'static/room1/Wall1.png'
    if path.startswith('http'):
        # E un URL GitHub vechi — extragem calea relativa
        for prefix in [
            'https://raw.githubusercontent.com/keserdark/petomania/main/static/',
            'https://raw.githubusercontent.com/keserdark/village-bot/main/PetGame/static/',
        ]:
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
    if path.startswith('/static/'):
        return path
    return f'/static/{path}'


# Patch build_pet_context to use our get_static_url
def _build_pet_context(p):
    return build_pet_context(p, get_static_url)


# ── DISK CACHE (PIL render) ───────────────────────────────────────────

CACHE_DIR = '/tmp/petomania_imgcache'
CACHE_TTL  = 300
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(url: str) -> str:
    import hashlib
    return hashlib.md5(url.encode()).hexdigest() + '.png'


def _cache_path(url: str) -> str:
    return os.path.join(CACHE_DIR, _cache_key(url))


def _invalidate_cache(url: str):
    path = _cache_path(url)
    if os.path.exists(path):
        os.remove(path)


def _fetch_image(url: str):
    try:
        from PIL import Image
        # Path pe disk
        if url and (url.startswith('/') or (len(url) > 2 and url[1] == ':')):
            return Image.open(url).convert('RGBA')
        # URL HTTP
        req = urllib.request.Request(url, headers={'User-Agent': 'PetomaniaBotRender/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        return Image.open(io.BytesIO(data)).convert('RGBA')
    except Exception as e:
        print(f"⚠️ _fetch_image error {url}: {e}")
        return None


def _fetch_image_cached(url: str, ttl: int = CACHE_TTL, resize: tuple = (1280, 720)):
    from PIL import Image
    cache_file = _cache_path(url)
    now = time.time()
    if os.path.exists(cache_file):
        age = now - os.path.getmtime(cache_file)
        if age < ttl:
            try:
                return Image.open(cache_file).convert('RGBA')
            except Exception:
                pass
    img = _fetch_image(url)
    if img:
        if resize:
            img = img.resize(resize, Image.LANCZOS)
        try:
            img.save(cache_file, format='PNG')
        except Exception:
            pass
    return img


def _fetch_pet_cached(url: str):
    return _fetch_image_cached(url, ttl=60, resize=None)


# ── AUTH ──────────────────────────────────────────────────────────────

def get_current_user():
    if 'user_id' not in session:
        return None
    return {'id': session['user_id'], 'username': session.get('username', ''), 'avatar': session.get('avatar')}


def avatar_url(user_id, avatar, size=64):
    if avatar:
        ext = 'gif' if avatar.startswith('a_') else 'png'
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.{ext}?size={size}"
    default = (int(user_id) >> 22) % 6
    return f"https://cdn.discordapp.com/embed/avatars/{default}.png"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_globals():
    user = get_current_user()
    if user:
        from datetime import datetime
        user['avatar_url']     = avatar_url(user['id'], user['avatar'])
        user['dacoins']        = get_dacoins(int(user['id']))
        interaction            = get_lady_interaction(int(user['id']))
        user['has_companicon'] = interaction['has_companicon']
    from datetime import datetime
    return {'current_user': user, 'now': datetime.now()}


# ── OAUTH ─────────────────────────────────────────────────────────────

@app.route('/joc/petomania/login')
def login():
    state = secrets.token_urlsafe(24)
    session['oauth_state'] = state
    params = {
        'client_id':     DISCORD_CLIENT_ID,
        'redirect_uri':  REDIRECT_URI,
        'response_type': 'code',
        'scope':         'identify',
        'state':         state,
        'prompt':        'none',
    }
    query = '&'.join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return redirect(f"{DISCORD_OAUTH_AUTHORIZE}?{query}")


@app.route('/joc/petomania/callback')
def oauth_callback():
    state          = request.args.get('state')
    expected_state = session.pop('oauth_state', None)
    if not state or state != expected_state:
        return render_template('error.html', error="State OAuth invalid.")
    code = request.args.get('code')
    if not code:
        return render_template('error.html', error="Nu am primit codul OAuth.")
    try:
        token_resp = requests.post(
            DISCORD_OAUTH_TOKEN,
            data={'client_id': DISCORD_CLIENT_ID, 'client_secret': DISCORD_CLIENT_SECRET,
                  'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10,
        )
    except requests.RequestException as e:
        return render_template('error.html', error=f"Eroare conexiune Discord: {e}")
    if token_resp.status_code != 200:
        return render_template('error.html', error="Discord a respins codul OAuth.")
    access_token = token_resp.json()['access_token']
    try:
        user_resp = requests.get(f"{DISCORD_API}/users/@me",
                                  headers={'Authorization': f"Bearer {access_token}"}, timeout=10)
        user_resp.raise_for_status()
    except requests.RequestException:
        return render_template('error.html', error="Nu am putut prelua datele tale Discord.")
    user_data           = user_resp.json()
    session['user_id']  = user_data['id']
    session['username'] = user_data.get('global_name') or user_data['username']
    session['avatar']   = user_data.get('avatar')
    uid = int(user_data['id'])
    get_dacoins(uid)
    get_room_config(uid)
    return redirect(session.pop('next_url', url_for('acasa')))


@app.route('/joc/petomania/logout')
def logout():
    session.clear()
    return redirect(url_for('acasa'))


# serve_img nu mai e necesar — imaginile sunt servite direct din static/


# ── PAGINI ────────────────────────────────────────────────────────────

@app.route('/joc/petomania/sw.js')
def service_worker():
    from flask import send_from_directory
    response = send_from_directory('static', 'service_worker.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/joc/petomania/'
    return response


@app.route('/joc/petomania/')
@app.route('/joc/petomania')
@login_required
def acasa():
    user = get_current_user()
    uid  = int(user['id'])
    p    = sync_pet(uid)
    pet  = _build_pet_context(p) if p else None
    room = get_room_config(uid)

    v = room.get('room_version', 1)
    room_urls = {
        'wall':    get_static_url(get_room_url('wall',    room['wall'],    room)) + f'?v={v}',
        'floor':   get_static_url(get_room_url('floor',   room['floor'],   room)) + f'?v={v}',
        'chimney': get_static_url(get_room_url('chimney', room['chimney'], room)) + f'?v={v}',
    }
    owned_items  = room.get('items', {})
    # Bundle keys: daca userul are cheia trigger, se adauga automat si cele din bundle
    effective_items = set(owned_items.keys())
    for trigger_key, bundle_keys in ITEM_BUNDLES.items():
        if trigger_key in effective_items:
            effective_items.update(bundle_keys)

    room_objects = []
    for obj_key, obj_cfg in SHOP_ITEMS.get('obiecte', {}).items():
        if obj_key in effective_items:
            room_objects.append({
                'key':       obj_key,
                'file':      obj_cfg.get('file', ''),
                'url':       get_static_url(f"room1/{obj_cfg.get('file', '')}"),
                'clickable': obj_cfg.get('clickable', False),
                'action':    obj_cfg.get('action'),
                'pos_x':     obj_cfg.get('pos_x', 50),
                'pos_y':     obj_cfg.get('pos_y', 50),
                'width':     obj_cfg.get('width', 15),
                'z_index':   obj_cfg.get('z_index', 5),
                'name':      obj_cfg.get('name', ''),
            })
    return render_template('acasa.html', pet=pet, room=room, room_urls=room_urls, room_objects=room_objects)


@app.route('/joc/petomania/menajerie')
@login_required
def menajerie():
    user       = get_current_user()
    uid        = int(user['id'])
    active     = sync_pet(uid)
    active_ctx = _build_pet_context(active) if active else None
    rows          = get_menagerie(uid)
    loadout_slots = build_loadout_context(uid)
    # Exclude pets care sunt in loadout
    loadout_ids = {s['id'] for s in loadout_slots if not s.get('empty') and s.get('id')}
    men_pets    = [_build_pet_context(dict(r)) for r in rows if r['id'] not in loadout_ids]
    return render_template('menajerie.html', active=active_ctx, men_pets=men_pets, loadout_slots=loadout_slots)


@app.route('/joc/petomania/imbunatatiri')
@login_required
def imbunatatiri():
    user    = get_current_user()
    uid     = int(user['id'])
    room    = get_room_config(uid)
    dacoins = get_dacoins(uid)
    return render_template('imbunatatiri.html', room=room, dacoins=dacoins, shop=ROOM_ITEMS)


# ── API — INGRIJIRE ───────────────────────────────────────────────────

@app.route('/joc/petomania/api/action', methods=['POST'])
@login_required
def api_action():
    user   = get_current_user()
    uid    = int(user['id'])
    action = request.json.get('action')
    p      = sync_pet(uid)
    if not p:
        return jsonify({'ok': False, 'error': 'Nu ai un animal activ.'})
    now = int(time.time())
    msg = ''
    if action == 'feed':
        if p['hunger'] >= 100:
            return jsonify({'ok': False, 'error': 'Animalul nu e flămând!'})
        update_pet(uid, hunger=min(100, p['hunger'] + FEED_AMOUNT), last_action=now)
        msg = f"🍖 Ai hrănit {p['name']}!"
    elif action == 'wash':
        if p['cleanliness'] >= 100:
            return jsonify({'ok': False, 'error': 'Animalul e deja curat!'})
        update_pet(uid, cleanliness=min(100, p['cleanliness'] + WASH_AMOUNT), last_action=now)
        msg = f"🧼 Ai spălat {p['name']}!"
    elif action == 'play':
        state = get_state(p['hunger'], p['happiness'], p['cleanliness'], p['energy'], bool(p['sleeping']))
        if p['energy'] <= 30 or state == 'Hungry' or p['happiness'] >= 100:
            return jsonify({'ok': False, 'error': 'Nu poți juca acum!'})
        update_pet(uid,
            happiness=min(100, p['happiness'] + PLAY_HAPPINESS),
            energy=max(0, p['energy'] - PLAY_ENERGY_COST),
            hunger=max(0, p['hunger'] - PLAY_HUNGER_COST),
            last_action=now)
        msg = f"🎮 Te-ai jucat cu {p['name']}!"
    elif action == 'sleep':
        state = get_state(p['hunger'], p['happiness'], p['cleanliness'], p['energy'], bool(p['sleeping']))
        if state == 'Dirty':
            return jsonify({'ok': False, 'error': 'Trebuie să-l speli înainte!'})
        if p['sleeping']:
            return jsonify({'ok': False, 'error': 'Doarme deja!'})
        update_pet(uid, sleeping=1, sleep_started=now, last_action=now, last_decay=now)
        msg = f"😴 {p['name']} doarme acum."
    elif action == 'wake':
        if not p['sleeping']:
            return jsonify({'ok': False, 'error': 'Nu doarme!'})
        if p['energy'] < 50:
            return jsonify({'ok': False, 'error': 'Are nevoie de cel puțin 50 energie!'})
        update_pet(uid, sleeping=0, sleep_started=None, last_action=now)
        msg = f"☀️ {p['name']} s-a trezit!"
    else:
        return jsonify({'ok': False, 'error': 'Acțiune necunoscută.'})
    p_new = sync_pet(uid)
    ctx   = _build_pet_context(p_new)
    raw_url = get_image_url(p_new['species'], get_form(p_new['level']),
                             get_state(p_new['hunger'], p_new['happiness'],
                                       p_new['cleanliness'], p_new['energy'],
                                       bool(p_new['sleeping'])), p_new['gender'])
    ctx['image_url'] = get_static_url(raw_url)
    return jsonify({'ok': True, 'msg': msg, 'pet': ctx})


@app.route('/joc/petomania/api/activa', methods=['POST'])
@login_required
def api_activa():
    user         = get_current_user()
    uid          = int(user['id'])
    menagerie_id = request.json.get('id')
    if not menagerie_id:
        return jsonify({'ok': False, 'error': 'ID lipsă.'})
    conn    = get_db()
    pet_men = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (menagerie_id, uid)).fetchone()
    if not pet_men:
        conn.close()
        return jsonify({'ok': False, 'error': 'Animal negăsit.'})
    active = conn.execute('SELECT * FROM pets WHERE user_id = ?', (uid,)).fetchone()
    now = int(time.time())
    if active:
        conn.execute('''
            INSERT INTO menagerie
            (user_id, name, gender, species, nature, level, xp, hunger, happiness,
             cleanliness, energy, sleeping, sleep_started, last_decay, last_xp_tick, born_at, stored_at, hp_current)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (active['user_id'], active['name'], active['gender'], active['species'],
              active['nature'], active['level'], active['xp'], active['hunger'],
              active['happiness'], active['cleanliness'], active['energy'],
              active['sleeping'], active['sleep_started'], active['last_decay'],
              active['last_xp_tick'], active['born_at'], now, active['hp_current'] if 'hp_current' in active.keys() else 0))
        # Salveaza active_moves si known_moves ale petului activ in menajerie
        new_men_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']
        move_rows = conn.execute('SELECT slot, move_key FROM active_moves WHERE user_id = ? AND pet_id = 0', (uid,)).fetchall()
        for r in move_rows:
            conn.execute('INSERT OR REPLACE INTO active_moves (user_id, pet_id, slot, move_key) VALUES (?, ?, ?, ?)',
                         (uid, new_men_id, r['slot'], r['move_key']))
        known_rows = conn.execute('SELECT move_key FROM known_moves WHERE user_id = ? AND pet_id = 0', (uid,)).fetchall()
        for r in known_rows:
            conn.execute('INSERT OR IGNORE INTO known_moves (user_id, pet_id, move_key) VALUES (?, ?, ?)',
                         (uid, new_men_id, r['move_key']))
        conn.execute('DELETE FROM active_moves WHERE user_id = ? AND pet_id = 0', (uid,))
        conn.execute('DELETE FROM known_moves WHERE user_id = ? AND pet_id = 0', (uid,))
        conn.execute('DELETE FROM pets WHERE user_id = ?', (uid,))
    # Copiaza active_moves si known_moves ale noului pet activ (din menagerie_id -> pet_id=0)
    new_active = conn.execute('SELECT slot, move_key FROM active_moves WHERE user_id = ? AND pet_id = ?', (uid, menagerie_id)).fetchall()
    for r in new_active:
        conn.execute('INSERT OR REPLACE INTO active_moves (user_id, pet_id, slot, move_key) VALUES (?, ?, ?, ?)',
                     (uid, 0, r['slot'], r['move_key']))
    new_known = conn.execute('SELECT move_key FROM known_moves WHERE user_id = ? AND pet_id = ?', (uid, menagerie_id)).fetchall()
    for r in new_known:
        conn.execute('INSERT OR IGNORE INTO known_moves (user_id, pet_id, move_key) VALUES (?, ?, ?)',
                     (uid, 0, r['move_key']))
    conn.execute('''
        INSERT OR REPLACE INTO pets
        (user_id, name, gender, species, nature, level, xp, hunger, happiness,
         cleanliness, energy, sleeping, sleep_started, last_decay, last_action, last_xp_tick, born_at, hp_current)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
    ''', (uid, pet_men['name'], pet_men['gender'], pet_men['species'], pet_men['nature'],
          pet_men['level'], pet_men['xp'], pet_men['hunger'], pet_men['happiness'],
          pet_men['cleanliness'], pet_men['energy'], pet_men['sleeping'],
          pet_men['sleep_started'], now, now, pet_men['born_at'],
          pet_men['hp_current'] if 'hp_current' in pet_men.keys() else 0))
    conn.execute('DELETE FROM menagerie WHERE id = ?', (menagerie_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'msg': f"{pet_men['name']} este acum activ!"})


@app.route('/joc/petomania/api/cumpara', methods=['POST'])
@login_required
def api_cumpara():
    user     = get_current_user()
    uid      = int(user['id'])
    category = request.json.get('category')
    key      = request.json.get('key')

    if category not in SHOP_ITEMS:
        return jsonify({'ok': False, 'error': 'Categorie invalida.'})
    if key not in SHOP_ITEMS[category]:
        return jsonify({'ok': False, 'error': 'Item inexistent.'})

    item  = SHOP_ITEMS[category][key]
    price = item.get('price', 0)
    room  = get_room_config(uid)

    if category == 'obiecte':
        owned_objects = room.get('items', {})
        if key in owned_objects:
            return jsonify({'ok': False, 'error': 'Ai deja acest obiect!'})
        if price > 0 and not spend_dacoins(uid, price):
            return jsonify({'ok': False, 'error': 'Dacoins insuficienti!'})
        owned_objects[key] = True
        save_room_config(uid, room['wall'], room['floor'], room['chimney'], owned_objects)
        bump_room_version(uid)
        return jsonify({
            'ok': True, 'msg': f"✅ {item['name']} plasat în cameră!",
            'new_balance': get_dacoins(uid), 'category': category, 'key': key,
            'obj_data': {
                'file': item.get('file', ''), 'clickable': item.get('clickable', False),
                'action': item.get('action'), 'pos_x': item.get('pos_x', 50),
                'pos_y': item.get('pos_y', 50), 'width': item.get('width', 15),
                'z_index': item.get('z_index', 5),
            },
        })

    if room[category] == key:
        return jsonify({'ok': False, 'error': 'Ai deja acest upgrade!'})
    requires = item.get('requires')
    if requires and room[category] != requires:
        return jsonify({'ok': False, 'error': 'Trebuie sa detii upgrade-ul anterior!'})
    if price > 0 and not spend_dacoins(uid, price):
        return jsonify({'ok': False, 'error': 'Dacoins insuficienti!'})

    room[category] = key
    save_room_config(uid, room['wall'], room['floor'], room['chimney'], room['items'])
    bump_room_version(uid)
    _invalidate_cache(get_room_url(category, room[category], room))
    _invalidate_cache(get_room_url(category, key, room))

    return jsonify({
        'ok': True, 'msg': f"✅ {item['name']} aplicat!",
        'new_balance': get_dacoins(uid), 'new_url': get_room_url(category, key), 'category': category,
    })


# ── RENDER PIL ────────────────────────────────────────────────────────

@app.route('/joc/petomania/render/<int:user_id>')
def render_pet(user_id: int):
    try:
        from PIL import Image
    except ImportError:
        return Response('Pillow not installed', status=500)
    W, H = 1280, 720
    room    = get_room_config(user_id)
    pet_row = get_pet(user_id)
    if pet_row:
        p       = dict(pet_row)
        form    = get_form(p['level'])
        state   = get_state(p['hunger'], p['happiness'], p['cleanliness'], p['energy'], bool(p['sleeping']))
        _pet_url_raw = get_image_url(p['species'], form, state, p.get('gender', 'male'))
        # Citeste direct de pe disk in loc de HTTP request
        if _pet_url_raw.startswith('/static/'):
            pet_url = os.path.join(os.path.dirname(os.path.abspath(__file__)), _pet_url_raw.lstrip('/'))
        elif _pet_url_raw.startswith('/'):
            pet_url = f"https://regnum-dacorum.ro{_pet_url_raw}"
        else:
            pet_url = _pet_url_raw
    else:
        form    = 1
        pet_url = None
    def _to_disk(url):
        if url and url.startswith('/static/'):
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), url.lstrip('/'))
        return url

    wall_url    = _to_disk(get_room_url('wall',    room['wall'],    room))
    floor_url   = _to_disk(get_room_url('floor',   room['floor'],   room))
    chimney_url = _to_disk(get_room_url('chimney', room['chimney'], room))
    canvas = Image.new('RGBA', (W, H), (10, 10, 16, 255))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        f_wall    = executor.submit(_fetch_image_cached, wall_url)
        f_floor   = executor.submit(_fetch_image_cached, floor_url)
        f_chimney = executor.submit(_fetch_image_cached, chimney_url)
        f_pet     = executor.submit(_fetch_pet_cached, pet_url) if pet_url else None
        wall_img    = f_wall.result()
        floor_img   = f_floor.result()
        chimney_img = f_chimney.result()
        pet_img     = f_pet.result() if f_pet else None
    # Separam obiectele in doua grupuri: z_index < 20 (sub pet) si >= 20 (peste pet)
    from petgame_room_config import ROOM_ITEMS as _ROOM_ITEMS, ITEM_BUNDLES as _ITEM_BUNDLES
    owned_items = room.get('items', {})

    # Aplica bundles
    effective_items = set(owned_items.keys())
    for trigger_key, bundle_keys in _ITEM_BUNDLES.items():
        if trigger_key in effective_items:
            effective_items.update(bundle_keys)

    obj_layers_under = []  # z_index < 20
    obj_layers_over  = []  # z_index >= 20

    for obj in _ROOM_ITEMS.get('obiecte', []):
        key = obj['key']
        if key not in effective_items:
            continue
        obj_path = _to_disk(f"/static/room1/{obj['file']}")
        z = obj.get('z_index', 5)
        pos_x = obj.get('pos_x', 0) / 100.0
        pos_y_bottom = obj.get('pos_y', 0) / 100.0
        width_pct = obj.get('width', 100) / 100.0
        if z < 20:
            obj_layers_under.append((z, obj_path, pos_x, pos_y_bottom, width_pct))
        else:
            obj_layers_over.append((z, obj_path, pos_x, pos_y_bottom, width_pct))

    # Sorteaza dupa z_index
    obj_layers_under.sort(key=lambda x: x[0])
    obj_layers_over.sort(key=lambda x: x[0])

    def paste_obj(canvas, obj_path, pos_x, pos_y_bottom, width_pct):
        img = _fetch_image_cached(obj_path, ttl=3600, resize=None)
        if not img:
            return
        obj_w = int(W * width_pct)
        obj_h = int(obj_w * img.size[1] / img.size[0])
        x = int(pos_x * W)
        # Converteste bottom% la top pixels
        y = int(H - pos_y_bottom * H - obj_h)
        img = img.resize((obj_w, obj_h), Image.LANCZOS)
        if img.mode == 'RGBA':
            canvas.paste(img, (x, y), img)
        else:
            canvas.paste(img, (x, y))

    for img in [wall_img, floor_img, chimney_img]:
        if img:
            canvas.paste(img, (0, 0), img)

    # Obiecte sub pet
    for (_, op, px, py, wp) in obj_layers_under:
        paste_obj(canvas, op, px, py, wp)

    if pet_img:
        pct   = {1: 0.22, 2: 0.32, 3: 0.46}.get(form, 0.28)
        pet_w = int(W * pct)
        pet_h = int(pet_w * pet_img.size[1] / pet_img.size[0])
        pet_img = pet_img.resize((pet_w, pet_h), Image.LANCZOS)
        canvas.paste(pet_img, ((W - pet_w) // 2, H - pet_h), pet_img)

    # Obiecte peste pet
    for (_, op, px, py, wp) in obj_layers_over:
        paste_obj(canvas, op, px, py, wp)
    output = io.BytesIO()
    canvas.convert('RGB').save(output, format='PNG', optimize=True)
    output.seek(0)
    return Response(output.getvalue(), mimetype='image/png',
                    headers={'Cache-Control': 'no-store, no-cache, must-revalidate', 'Pragma': 'no-cache'})


# ── ORAS ──────────────────────────────────────────────────────────────

@app.route('/joc/petomania/oras')
@login_required
def oras():
    return render_template('oras.html',
        city_url     = f"{STATIC_BASE}/city/city.png",
        castel_url   = f"{STATIC_BASE}/city/castel.png",
        biserica_url = f"{STATIC_BASE}/city/biserica.png",
        piata_url    = f"{STATIC_BASE}/city/piata.png",
        aventura_url = f"{STATIC_BASE}/city/aventura.png",
    )


@app.route('/joc/petomania/castel')
@login_required
def castel():
    return render_template('castel.html')


@app.route('/joc/petomania/biserica')
@login_required
def biserica():
    user    = get_current_user()
    uid     = int(user['id'])
    dacoins = get_dacoins(uid)
    return render_template('biserica.html', dacoins=dacoins)


@app.route('/joc/petomania/piata')
@login_required
def piata():
    return render_template('piata.html')


@app.route('/joc/petomania/aventura')
@login_required
def aventura():
    return render_template('aventura.html')


# city_img nu mai e necesar — fisierele sunt in static/city/


# piata_img nu mai e necesar — fisierele sunt in static/piata/


# assets_img nu mai e necesar — fisierele sunt in static/Assets/


@app.route('/joc/petomania/assets')
@login_required
def assets():
    return render_template('assets.html')


@app.route('/joc/petomania/consumable')
@login_required
def consumable():
    return render_template('consumable.html')


# ── LADY / ASSETS API ─────────────────────────────────────────────────

@app.route('/joc/petomania/api/lady', methods=['GET'])
@login_required
def api_lady():
    user = get_current_user()
    uid  = int(user['id'])
    dialog = build_lady_dialog(uid, user['username'])
    return jsonify({'ok': True, 'dialog': dialog})


@app.route('/joc/petomania/api/lady/pet', methods=['GET'])
@login_required
def api_lady_pet():
    user        = get_current_user()
    uid         = int(user['id'])
    interaction = get_lady_interaction(uid)
    name        = interaction['player_name'] or user['username']
    text        = build_lady_pet_text(uid, name)
    return jsonify({'ok': True, 'text': text})


@app.route('/joc/petomania/api/lady/companicon', methods=['POST'])
@login_required
def api_lady_companicon():
    user = get_current_user()
    uid  = int(user['id'])
    conn = get_db()
    conn.execute('''
        INSERT INTO lady_interactions (user_id, first_interaction, has_companicon)
        VALUES (?, 0, 1)
        ON CONFLICT(user_id) DO UPDATE SET has_companicon = 1
    ''', (uid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/joc/petomania/api/lady/name', methods=['POST'])
@login_required
def api_lady_name():
    user = get_current_user()
    uid  = int(user['id'])
    name = request.json.get('name', '').strip()[:50]
    if not name:
        return jsonify({'ok': False, 'error': 'Nume invalid.'})
    conn = get_db()
    conn.execute('''
        INSERT INTO lady_interactions (user_id, first_interaction, player_name)
        VALUES (?, 0, ?)
        ON CONFLICT(user_id) DO UPDATE SET first_interaction = 0, player_name = excluded.player_name
    ''', (uid, name))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'name': name})


# ── COMPANICON ────────────────────────────────────────────────────────

# companicon_img nu mai e necesar — fisierele sunt in static/


@app.route('/joc/petomania/api/companicon')
@login_required
def api_companicon():
    user    = get_current_user()
    uid     = int(user['id'])
    entries = build_companicon_entries(uid)
    return jsonify({'ok': True, 'entries': entries})


@app.route('/joc/petomania/companicon')
@login_required
def companicon():
    return render_template('companicon.html')


# ── RUCSAC ────────────────────────────────────────────────────────────

@app.route('/joc/petomania/api/rucsac/data')
@login_required
def api_rucsac_data():
    user = get_current_user()
    uid  = int(user['id'])
    sync_pet(uid)
    sync_pet_hp(uid)
    pet        = get_pet(uid)
    pet_ctx    = _build_pet_context(pet) if pet else None
    categories = inv_build_context(uid)
    companions = [None, None, None, None, None]

    if pet_ctx and pet:
        p      = dict(pet)
        hp_max = pet_ctx['stats']['hp']
        hp_cur = p['hp_current']
        companions[0] = {
            'id': 0,
            'name': pet_ctx['name'], 'species': pet_ctx['species_name'],
            'level': pet_ctx['level'], 'form': pet_ctx['form'],
            'nature': pet_ctx['nat_data']['name'] if pet_ctx['nat_data'] else None,
            'nature_icon': pet_ctx['nat_data']['icon'] if pet_ctx['nat_data'] else None,
            'gender_icon': pet_ctx['gender_icon'], 'species_key': p['species'],
            'hp_current': hp_cur, 'hp_max': hp_max, 'active': True,
            'image_url': pet_ctx['image_url'],
        }

    loadout = get_loadout(uid)
    conn = get_db()
    for i, slot_key in enumerate(['slot_2', 'slot_3', 'slot_4', 'slot_5'], start=1):
        men_id = loadout[slot_key]
        if men_id:
            row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (men_id, uid)).fetchone()
            if row:
                mp    = dict(row)
                mform = get_form(mp['level'])
                mstate = get_state(mp['hunger'], mp['happiness'], mp['cleanliness'],
                                   mp['energy'], bool(mp['sleeping']))
                mnat   = NATURES.get(mp.get('nature')) if mp.get('nature') else None
                mhp_max = get_stats_at_level(mp['species'], mp.get('nature'), mp['level'], mform)['hp']
                mhp_cur = mp['hp_current']
                companions[i] = {
                    'id': men_id,
                    'name': mp['name'],
                    'species': SPECIES.get(mp['species'], {}).get('name', mp['species']),
                    'level': mp['level'], 'form': mform,
                    'nature': mnat['name'] if mnat else None,
                    'nature_icon': mnat['icon'] if mnat else None,
                    'gender_icon': '♂️' if mp['gender'] == 'male' else '♀️',
                    'species_key': mp['species'],
                    'hp_current': mhp_cur, 'hp_max': mhp_max, 'active': False,
                    'image_url': get_image_url(mp['species'], mform, mstate, mp['gender']),
                }
    conn.close()
    return jsonify({'ok': True, 'categories': categories, 'companions': companions, 'dacoins': get_dacoins(uid)})


@app.route('/joc/petomania/api/rucsac/use', methods=['POST'])
@login_required
def api_rucsac_use():
    user        = get_current_user()
    uid         = int(user['id'])
    data        = request.json or {}
    category    = data.get('category', '')
    item_key    = data.get('item_key', '')
    target_slot = int(data.get('target_slot', 0))
    if not category or not item_key:
        return jsonify({'ok': False, 'msg': 'Date lipsă.'})

    # Nexus in battle -> redirectioneaza catre captură
    if category == 'nexus' and session.get('battle_npc'):
        from flask import redirect
        request._cached_json = (data | {'item_key': item_key}, True)
        return api_battle_capture()

    # Nexus in vanatoare -> redirectioneaza catre captura vanatoare
    if category == 'nexus' and session.get('vanatoare_npc'):
        request._cached_json = (data | {'item_key': item_key}, True)
        return api_vanatoare_capture()

    # Nexus in pescuit -> redirectioneaza catre captura pescuit
    if category == 'nexus' and session.get('pescuit_npc'):
        request._cached_json = (data | {'item_key': item_key}, True)
        return api_pescuit_capture()

    return jsonify(use_item(uid, category, item_key, target_slot=target_slot))


@app.route('/joc/petomania/api/rucsac/drop', methods=['POST'])
@login_required
def api_rucsac_drop():
    user     = get_current_user()
    uid      = int(user['id'])
    data     = request.json or {}
    category = data.get('category', '')
    item_key = data.get('item_key', '')
    qty      = int(data.get('qty', 1))
    if not category or not item_key:
        return jsonify({'ok': False, 'msg': 'Date lipsă.'})
    item_cfg = inv_get_item(category, item_key)
    if item_cfg and item_cfg.get('quest_item'):
        return jsonify({'ok': False, 'msg': 'Quest item-urile nu pot fi aruncate.'})
    return jsonify(inv_remove(uid, category, item_key, qty))


@app.route('/joc/petomania/api/rucsac/rename', methods=['POST'])
@login_required
def api_rucsac_rename():
    user     = get_current_user()
    uid      = int(user['id'])
    body     = request.json or {}
    new_name = body.get('name', '').strip()
    pet_id   = int(body.get('pet_id', 0))
    return jsonify(rename_pet(uid, new_name, pet_id))


@app.route('/joc/petomania/api/rucsac/comp_stats', methods=['GET'])
@login_required
def api_rucsac_comp_stats():
    user = get_current_user()
    uid  = int(user['id'])
    pet  = get_pet(uid)
    if not pet:
        return jsonify({'ok': False, 'msg': 'Niciun companion activ.'})
    p        = dict(pet)
    form     = get_form(p['level'])
    nature   = p.get('nature')
    stats    = get_stats_at_level(p['species'], nature, p['level'], form)
    nat_data = NATURES.get(nature) if nature else None
    hp_max   = stats['hp']
    hp_cur   = p['hp_current']
    return jsonify({
        'ok': True, 'name': p['name'],
        'species': SPECIES.get(p['species'], {}).get('name', p['species']),
        'species_key': p['species'], 'level': p['level'], 'form': form,
        'gender_icon': '♂️' if p['gender'] == 'male' else '♀️',
        'nature': nat_data['name'] if nat_data else None,
        'nature_icon': nat_data['icon'] if nat_data else None,
        'nature_color': nat_data['color'] if nat_data else None,
        'bonus_stat': nat_data['bonus_stat'] if nat_data else None,
        'hp_current': hp_cur, 'hp_max': hp_max,
        'stats': {k: stats[k] for k in ['hp','attack','defense','speed','evasion','healing','control','reflection']},
    })


# ── LOADOUT ───────────────────────────────────────────────────────────

@app.route('/joc/petomania/loadout')
@login_required
def loadout():
    user = get_current_user()
    uid  = int(user['id'])
    sync_pet(uid)
    sync_pet_hp(uid)
    slots        = build_loadout_context(uid)
    loadout_data = get_loadout(uid)
    exclude_ids  = [v for v in loadout_data.values() if v]
    menagerie    = build_menagerie_for_loadout(uid, exclude_ids)
    return render_template('loadout.html', slots=slots, menagerie=menagerie,
                           nexus_inferior=f"{STATIC_BASE}/items/NexusInferior.png",
                           nexus_superior=f"{STATIC_BASE}/items/NexusSuperior.png")


@app.route('/joc/petomania/api/loadout/set', methods=['POST'])
@login_required
def api_loadout_set():
    user   = get_current_user()
    uid    = int(user['id'])
    data   = request.json or {}
    slot   = int(data.get('slot', 0))
    men_id = data.get('men_id')
    if slot < 2 or slot > 5:
        return jsonify({'ok': False, 'error': 'Slot invalid.'})
    if men_id:
        conn = get_db()
        row  = conn.execute('SELECT id FROM menagerie WHERE id = ? AND user_id = ?', (men_id, uid)).fetchone()
        conn.close()
        if not row:
            return jsonify({'ok': False, 'error': 'Companion negăsit.'})
    current = get_loadout(uid)
    for k, v in current.items():
        if v == men_id and men_id is not None:
            current[k] = None
    current[f'slot_{slot}'] = men_id
    save_loadout(uid, current['slot_2'], current['slot_3'], current['slot_4'], current['slot_5'])
    conn = get_db()
    row  = conn.execute('SELECT * FROM menagerie WHERE id = ?', (men_id,)).fetchone() if men_id else None
    conn.close()
    return jsonify({'ok': True, 'slot': build_loadout_slot(row, slot)})


@app.route('/joc/petomania/api/loadout/clear', methods=['POST'])
@login_required
def api_loadout_clear():
    user = get_current_user()
    uid  = int(user['id'])
    slot = int((request.json or {}).get('slot', 0))
    if slot < 2 or slot > 5:
        return jsonify({'ok': False, 'error': 'Slot invalid.'})
    current = get_loadout(uid)
    current[f'slot_{slot}'] = None
    save_loadout(uid, current['slot_2'], current['slot_3'], current['slot_4'], current['slot_5'])
    return jsonify({'ok': True})



# ── MAGAZIN ───────────────────────────────────────────────────────────

@app.route('/joc/petomania/api/shop/<shop_id>')
@login_required
def api_shop_data(shop_id):
    ctx = build_shop_context(shop_id)
    if not ctx:
        return jsonify({'ok': False, 'error': 'Magazin inexistent.'})
    user    = get_current_user()
    dacoins = get_dacoins(int(user['id']))
    return jsonify({'ok': True, 'shop': ctx, 'dacoins': dacoins})


@app.route('/joc/petomania/api/shop/<shop_id>/buy', methods=['POST'])
@login_required
def api_shop_buy(shop_id):
    user     = get_current_user()
    uid      = int(user['id'])
    data     = request.json or {}
    category = data.get('category', '')
    item_key = data.get('item_key', '')
    qty      = int(data.get('qty', 1))
    if not category or not item_key:
        return jsonify({'ok': False, 'error': 'Date lipsă.'})
    return jsonify(shop_buy(uid, shop_id, category, item_key, qty))


# ── ARENA ────────────────────────────────────────────────────────────

@app.route('/joc/petomania/arena')
@login_required
def arena():
    return render_template('arena.html')



# ── CORVIN VARGAN ─────────────────────────────────────────────────────

@app.route('/joc/petomania/api/corvin')
@login_required
def api_corvin():
    user = get_current_user()
    uid  = int(user['id'])
    conn = get_db()
    row  = conn.execute('SELECT talked FROM corvin_interactions WHERE user_id = ?', (uid,)).fetchone()
    conn.close()
    first_time = (row is None or not row['talked'])
    return jsonify({'ok': True, 'first_time': first_time})


@app.route('/joc/petomania/api/corvin/talked', methods=['POST'])
@login_required
def api_corvin_talked():
    user = get_current_user()
    uid  = int(user['id'])
    conn = get_db()
    conn.execute('''
        INSERT INTO corvin_interactions (user_id, talked)
        VALUES (?, 1)
        ON CONFLICT(user_id) DO UPDATE SET talked = 1
    ''', (uid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})



# ── BATTLE ARENA ─────────────────────────────────────────────────────


def _save_bench_hp(bench: list):
    """Salveaza HP-ul curent al pets din bench in menagerie."""
    if not bench:
        return
    conn = get_db()
    for p in bench:
        if p.get('id'):
            conn.execute('UPDATE menagerie SET hp_current = ? WHERE id = ?',
                         (max(0, p.get('hp_current', 0)), p['id']))
    conn.commit()
    conn.close()


def _save_player_hp(player: dict, uid: int, hp_override: int = None):
    """Salveaza HP playerului in DB — pets daca e petul activ, menagerie daca e din bench."""
    hp = hp_override if hp_override is not None else max(0, player.get('hp_current', 0))
    player_id = player.get('id', 0)
    conn = get_db()
    if player_id and player_id != 0:
        conn.execute('UPDATE menagerie SET hp_current = ? WHERE id = ?', (hp, player_id))
    else:
        conn.execute('UPDATE pets SET hp_current = ? WHERE user_id = ?', (hp, uid))
    conn.commit()
    conn.close()

@app.route('/joc/petomania/api/battle/start', methods=['POST'])
@login_required
def api_battle_start():
    from modules.battle import build_combatant, generate_npc, save_combatant_mp
    from moves_config import get_move
    from modules.pets import sync_pet, get_form, get_state
    user = get_current_user()
    uid  = int(user['id'])

    data_req     = request.json or {}
    battle_size  = min(max(int(data_req.get('size', 1)), 1), 3)

    # Petul activ (slot 1)
    pet = sync_pet(uid)
    if not pet:
        return jsonify({'ok': False, 'error': 'Nu ai un companion activ.'})
    pet = dict(pet)
    pet.setdefault('id', 0)
    pet.setdefault('user_id', uid)

    player = build_combatant(pet)

    # Initializeaza HP in menagerie pentru pets care nu au luptat niciodata
    sync_menagerie_hp(uid)

    # Loadout complet pentru switch
    loadout_raw = build_loadout_context(uid)

    # Numara pets vii din loadout (inclusiv petul activ)
    alive_count = (1 if player['hp_current'] > 0 else 0)
    for slot in loadout_raw:
        if not slot.get('empty') and slot.get('slot') != 1 and slot.get('hp_current', 0) > 0:
            alive_count += 1
    if alive_count == 0:
        return jsonify({'ok': False, 'error': 'Toți companionii tăi sunt KO. Vindecă-i înainte de luptă.'})
    if alive_count < battle_size:
        return jsonify({'ok': False, 'error': f'Ai nevoie de {battle_size} companioi cu HP pentru acest mod. Ai doar {alive_count}.'})
    bench = []  # petii de pe bancă — max battle_size-1 pets, doar cu HP > 0
    for slot in loadout_raw:
        if slot.get('empty') or slot.get('slot') == 1:
            continue
        if len(bench) >= battle_size - 1:
            break
        if slot['hp_current'] <= 0:
            continue
        bench.append({
            'id':        slot['id'],
            'name':      slot['name'],
            'level':     slot['level'],
            'hp_max':    slot['hp_max'],
            'hp_current':slot['hp_current'],
            'image_url': slot['image_url'],
            'species':   slot['species_key'],
            'nature':    slot['nature_key'],
            'gender':    slot.get('gender', 'male'),
        })

    # Daca petul activ e mort, inlocuieste-l cu primul din loadout cu HP > 0
    if player['hp_current'] <= 0:
        # Cauta in tot loadout-ul (nu doar in bench limitat)
        all_bench = []
        for slot in loadout_raw:
            if slot.get('empty') or slot.get('slot') == 1:
                continue
            all_bench.append(slot)
        alive_slots = [s for s in all_bench if s.get('hp_current', 0) > 0]
        if not alive_slots:
            return jsonify({'ok': False, 'error': 'Toți companionii tăi sunt KO. Vindecă-i înainte de luptă.'})
        first = alive_slots[0]
        conn_b = get_db()
        row_b  = conn_b.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (first['id'], uid)).fetchone()
        conn_b.close()
        if not row_b:
            return jsonify({'ok': False, 'error': 'Companion negăsit.'})
        row_b_dict = dict(row_b)
        row_b_dict.setdefault('user_id', uid)
        player = build_combatant(row_b_dict)
        # Reconstruieste bench fara noul player
        bench = []
        for slot in loadout_raw:
            if slot.get('empty') or slot.get('slot') == 1:
                continue
            if str(slot['id']) == str(first['id']):
                continue
            if len(bench) >= battle_size - 1:
                break
            bench.append({
                'id':        slot['id'],
                'name':      slot['name'],
                'level':     slot['level'],
                'hp_max':    slot['hp_max'],
                'hp_current':slot['hp_current'],
                'image_url': slot['image_url'],
                'species':   slot['species_key'],
                'nature':    slot['nature_key'],
                'gender':    slot.get('gender', 'male'),
            })

    npc = generate_npc(player['level'], zone='arena')

    moveset_data = []
    for mk in player['moveset']:
        m = get_move(mk)
        if m:
            moveset_data.append({'key': m['key'], 'name': m['name'], 'icon': m['icon'], 'type': m['type'], 'power': m['power'], 'mp': player['mp'].get(m['key'], 15), 'max_mp': m.get('max_mp', 15), 'nature': m.get('nature')})

    session['battle_player']             = player
    session['battle_npc']                = npc
    session['battle_bench']              = bench
    session['battle_size']               = battle_size
    session['battle_npc_index']          = 1
    session['battle_accumulated_reward'] = 0
    session['battle_participants']          = [player['id']]

    return jsonify({
        'ok': True,
        'player': {
            'id': player['id'], 'name': player['name'], 'species': player['species'],
            'nature': player['nature'], 'level': player['level'],
            'hp_max': player['hp_max'], 'hp_current': player['hp_current'],
            'image_url': player['image_url'], 'moveset': moveset_data,
            'status': None, 'shield': 0,
        },
        'npc': {
            'id': npc['id'], 'name': npc['name'], 'species': npc['species'],
            'nature': npc['nature'], 'level': npc['level'],
            'hp_max': npc['hp_max'], 'hp_current': npc['hp_current'],
            'image_url': npc['image_url'], 'status': None, 'shield': 0,
        },
        'bench': bench,
    })




@app.route('/joc/petomania/api/battle/turn', methods=['POST'])
@login_required
def api_battle_turn():
    from modules.battle import execute_turn, calculate_reward, save_combatant_mp
    user   = get_current_user()
    uid    = int(user['id'])
    player = session.get('battle_player')
    npc    = session.get('battle_npc')
    if not player or not npc:
        return jsonify({'ok': False, 'error': 'Nicio bătălie activă.'})

    # Re-citeste HP din DB inainte de tur doar daca playerul e petul activ (id=None = din pets)
    # Daca e din menagerie (id != None), HP-ul lui e in sesiune, nu in tabela pets
    if player.get('id') is None or player.get('id') == 0:
        conn = get_db()
        fresh = conn.execute('SELECT hp_current FROM pets WHERE user_id = ?', (uid,)).fetchone()
        conn.close()
        if fresh:
            player['hp_current'] = fresh['hp_current']

    move_key = (request.json or {}).get('move_key', 'scratch')
    result   = execute_turn(player, npc, move_key)

    # Salveaza HP si MP dupa fiecare tur in DB
    _save_player_hp(player, uid)
    save_combatant_mp(player, uid)

    session['battle_player'] = player
    session['battle_npc']    = npc

    reward = 0
    if result['winner'] == 'player':
        npc_index   = session.get('battle_npc_index', 1)
        battle_size = session.get('battle_size', 1)

        if npc_index < battle_size:
            # Mai sunt NPC-uri — genereaza urmatorul
            from modules.battle import generate_npc as _gen_npc
            new_npc = _gen_npc(player['level'], zone='arena')
            partial_reward = calculate_reward(player['level'], npc['level'], True)
            session['battle_accumulated_reward'] = session.get('battle_accumulated_reward', 0) + partial_reward
            session['battle_npc']       = new_npc
            session['battle_npc_index'] = npc_index + 1
            session['battle_player']    = player
            return jsonify({
                'ok': True, 'log': result['log'],
                'player': result['player'],
                'npc': {
                    'id': new_npc['id'], 'name': new_npc['name'],
                    'species': new_npc['species'], 'nature': new_npc['nature'],
                    'level': new_npc['level'], 'hp_max': new_npc['hp_max'],
                    'hp_current': new_npc['hp_current'],
                    'image_url': new_npc['image_url'], 'status': None, 'shield': 0,
                },
                'winner': None,
                'next_npc': True,
                'reward': 0,
            })

        # Ultimul NPC doborat — victorie finala
        reward = calculate_reward(player['level'], npc['level'], True)
        reward += session.get('battle_accumulated_reward', 0)
        if reward > 0:
            conn = get_db()
            conn.execute('UPDATE dacoins SET balance = balance + ? WHERE user_id = ?', (reward, uid))
            conn.commit()
            conn.close()
        _save_bench_hp(session.get('battle_bench', []))
        # Acorda XP participantilor
        xp_total = max(1, reward // 3)
        participants = session.get('battle_participants', [player['id']])
        xp_results = add_battle_xp(uid, xp_total, participants)
        session.pop('battle_player', None)
        session.pop('battle_npc', None)
        session.pop('battle_size', None)
        session.pop('battle_npc_index', None)
        session.pop('battle_accumulated_reward', None)
        session.pop('battle_participants', None)
    elif result['winner'] == 'npc':
        _save_player_hp(player, uid, hp_override=0)
        bench = session.get('battle_bench', [])
        alive = [p for p in bench if p.get('hp_current', 0) > 0]
        if alive:
            # Mai sunt pets in bench — lasa sesiunea activa pentru switch
            session['battle_player'] = player
        else:
            # Niciun pet disponibil — lupta pierduta
            _save_bench_hp(bench)
            session.pop('battle_player', None)
            session.pop('battle_npc', None)
            session.pop('battle_size', None)
            session.pop('battle_npc_index', None)
            session.pop('battle_accumulated_reward', None)
            session.pop('battle_participants', None)

    return jsonify({
        'ok': True, 'log': result['log'],
        'player': result['player'], 'npc': result['npc'],
        'winner': result['winner'], 'reward': reward,
        'bench': session.get('battle_bench', []),
        'xp_results': locals().get('xp_results', []),
    })


@app.route('/joc/petomania/api/battle/flee', methods=['POST'])
@login_required
def api_battle_flee():
    user   = get_current_user()
    uid    = int(user['id'])
    player = session.get('battle_player')
    if player:
        hp_flee = max(1, player.get('hp_current', 1))
        _save_player_hp(player, uid, hp_override=hp_flee)
    session.pop('battle_player', None)
    session.pop('battle_npc', None)
    return jsonify({'ok': True})



# ── BATTLE PAGE ───────────────────────────────────────────────────────

@app.route('/joc/petomania/battle')
@login_required
def battle():
    return render_template('battle.html')


@app.route('/joc/petomania/api/battle/switch', methods=['POST'])
@login_required
def api_battle_switch():
    from modules.battle import build_combatant, save_combatant_mp
    from moves_config import get_move
    user   = get_current_user()
    uid    = int(user['id'])
    pet_id = (request.json or {}).get('pet_id')
    bench  = session.get('battle_bench', [])

    pet_data = next((p for p in bench if str(p['id']) == str(pet_id)), None)
    if not pet_data:
        return jsonify({'ok': False, 'error': 'Pet negasit pe bancă.'})
    if pet_data['hp_current'] <= 0:
        return jsonify({'ok': False, 'error': 'Acest companion a căzut.'})

    # Construieste noul combatant
    from modules.db import get_db
    conn = get_db()
    if pet_data.get('from_pets') or str(pet_data['id']) == '0':
        row = conn.execute('SELECT *, ? as user_id, 0 as id FROM pets WHERE user_id = ?', (uid, uid)).fetchone()
    else:
        row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (pet_data['id'], uid)).fetchone()
    conn.close()
    if not row:
        return jsonify({'ok': False, 'error': 'Pet negasit în DB.'})

    new_player_dict = dict(row)
    new_player_dict.setdefault('user_id', uid)
    new_player = build_combatant(new_player_dict)
    moveset_data = []
    for mk in new_player['moveset']:
        m = get_move(mk)
        if m:
            moveset_data.append({'key': m['key'], 'name': m['name'], 'icon': m['icon'], 'type': m['type'], 'power': m['power'], 'mp': new_player['mp'].get(m['key'], 15), 'max_mp': m.get('max_mp', 15), 'nature': m.get('nature')})

    # Salveaza HP-ul petului care iese din arena
    old_player = session.get('battle_player')
    if old_player:
        old_id = old_player.get('id', 0)
        old_hp = max(0, old_player.get('hp_current', 0))
        conn2 = get_db()
        if old_id and old_id != 0:
            conn2.execute('UPDATE menagerie SET hp_current = ? WHERE id = ?', (old_hp, old_id))
        else:
            conn2.execute('UPDATE pets SET hp_current = ? WHERE user_id = ?', (old_hp, uid))
        conn2.commit()
        conn2.close()
        # Salveaza MP petului care iese
        if old_player:
            save_combatant_mp(old_player, uid)

        # Daca petul care iese e viu (switch voluntar), il adaugam inapoi in bench
        new_bench = [p for p in bench if str(p['id']) != str(pet_id)]
        if old_hp > 0:
            already_in_bench = any(str(p.get('id')) == str(old_id) for p in new_bench)
            if not already_in_bench:
                new_bench.append({
                    'id':        old_id,
                    'name':      old_player.get('name'),
                    'level':     old_player.get('level'),
                    'hp_max':    old_player.get('hp_max'),
                    'hp_current':old_hp,
                    'image_url': old_player.get('image_url', ''),
                    'species':   old_player.get('species', ''),
                    'nature':    old_player.get('nature'),
                    'gender':    old_player.get('gender', 'male'),
                    'from_pets': (old_id == 0),
                })
        bench = new_bench

    # Scoate din bench
    session['battle_bench']  = bench
    session['battle_player'] = new_player
    # Adauga noul player in lista de participanti daca nu e deja
    participants = session.get('battle_participants', [])
    if new_player['id'] not in participants:
        participants.append(new_player['id'])
    session['battle_participants'] = participants

    return jsonify({
        'ok': True,
        'player': {
            'id': new_player['id'], 'name': new_player['name'],
            'species': new_player['species'], 'nature': new_player['nature'],
            'level': new_player['level'], 'hp_max': new_player['hp_max'],
            'hp_current': new_player['hp_current'], 'image_url': new_player['image_url'],
            'moveset': moveset_data, 'status': None, 'shield': 0,
        },
        'bench': session.get('battle_bench', []),
    })



# ── BATTLE STATE ─────────────────────────────────────────────────────

@app.route('/joc/petomania/api/battle/state')
@login_required
def api_battle_state():
    from moves_config import get_move
    player = session.get('battle_player')
    npc    = session.get('battle_npc')
    bench  = session.get('battle_bench', [])
    if not player or not npc:
        return jsonify({'ok': False, 'active': False})

    moveset_data = []
    for mk in player.get('moveset', []):
        m = get_move(mk)
        if m:
            moveset_data.append({'key': m['key'], 'name': m['name'], 'icon': m['icon'], 'type': m['type'], 'power': m['power'], 'mp': player.get('mp', {}).get(m['key'], 15), 'max_mp': m.get('max_mp', 15), 'nature': m.get('nature')})

    # Re-citeste HP din DB — poate fi modificat de potiuni intre tururi
    conn = get_db()
    fresh = conn.execute('SELECT hp_current FROM pets WHERE user_id = ?', (int(get_current_user()['id']),)).fetchone()
    conn.close()
    if fresh:
        player['hp_current'] = fresh['hp_current']
        session['battle_player'] = player

    return jsonify({
        'ok': True, 'active': True,
        'player': {
            'id': player['id'], 'name': player['name'],
            'level': player.get('level', 1),
            'hp_max': player['hp_max'], 'hp_current': player['hp_current'],
            'image_url': player.get('image_url', ''),
            'moveset': moveset_data, 'status': player.get('status'), 'shield': player.get('shield', 0),
        },
        'npc': {
            'id': npc['id'], 'name': npc['name'],
            'level': npc.get('level', 1),
            'hp_max': npc['hp_max'], 'hp_current': npc['hp_current'],
            'image_url': npc.get('image_url', ''),
            'status': npc.get('status'), 'shield': npc.get('shield', 0),
        },
        'bench': bench,
    })



# ── BATTLE ABANDON ────────────────────────────────────────────────────

@app.route('/joc/petomania/api/battle/abandon', methods=['POST'])
@login_required
def api_battle_abandon():
    """Curata sesiunea de lupta fara a salva HP."""
    session.pop('battle_player', None)
    session.pop('battle_npc', None)
    session.pop('battle_bench', None)
    return jsonify({'ok': True})



# ── LOADOUT COUNT ────────────────────────────────────────────────────

@app.route('/joc/petomania/api/loadout/count')
@login_required
def api_loadout_count():
    uid   = int(get_current_user()['id'])
    slots = build_loadout_context(uid)
    count       = sum(1 for s in slots if not s.get('empty'))
    alive_count = sum(1 for s in slots if not s.get('empty') and s.get('hp_current', 0) > 0)
    return jsonify({'ok': True, 'count': count, 'alive': alive_count})


# ── RUN ───────────────────────────────────────────────────────────────


# ── TRAINING SYSTEM ──────────────────────────────────────────────────────

@app.route('/joc/petomania/api/training/loadout')
@login_required
def api_training_loadout():
    from modules.loadout import get_loadout, build_loadout_slot
    from modules.pets import get_pet
    user = get_current_user()
    uid  = int(user['id'])

    pets = []
    # Pet activ (id=0)
    active = get_pet(uid)
    if active:
        p = dict(active)
        pets.append({'id': 0, 'name': p['name'], 'level': p['level'], 'nature': p.get('nature'), 'species': p.get('species')})

    # Menajerie din loadout
    loadout = get_loadout(uid)
    conn = get_db()
    for slot_key in ['slot_2','slot_3','slot_4','slot_5']:
        men_id = loadout.get(slot_key)
        if not men_id: continue
        row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (men_id, uid)).fetchone()
        if row:
            pets.append({'id': men_id, 'name': row['name'], 'level': row['level'], 'nature': row['nature'] if 'nature' in row.keys() else None, 'species': row['species'] if 'species' in row.keys() else None})
    conn.close()
    return jsonify({'ok': True, 'pets': pets})


@app.route('/joc/petomania/api/training/pet_moves')
@login_required
def api_training_pet_moves():
    from moves_config import MOVES, get_moveset
    user   = get_current_user()
    uid    = int(user['id'])
    pet_id = request.args.get('pet_id', 0, type=int)

    # Obtine pet info
    if pet_id == 0:
        from modules.pets import get_pet
        pet = get_pet(uid)
        if not pet:
            return jsonify({'ok': False, 'error': 'Pet negăsit.'})
        nature  = pet['nature']
        level   = pet['level']
        species = pet['species']
    else:
        conn = get_db()
        row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (pet_id, uid)).fetchone()
        conn.close()
        if not row:
            return jsonify({'ok': False, 'error': 'Pet negăsit.'})
        nature  = row['nature']
        level   = row['level']
        species = row['species']

    def move_data(key):
        m = MOVES.get(key, {})
        return {
            'key':          key,
            'name':         m.get('name', key),
            'icon':         m.get('icon', '⚡'),
            'power':        m.get('power', 0),
            'unlock_level': m.get('unlock_level', 1),
            'type':         m.get('type', 'attack'),
        }

    # Active moves din DB sau fallback get_moveset
    conn = get_db()
    active_rows = conn.execute(
        'SELECT slot, move_key FROM active_moves WHERE user_id = ? AND pet_id = ? ORDER BY slot',
        (uid, pet_id)
    ).fetchall()

    if active_rows:
        active_moves = [move_data(r['move_key']) for r in active_rows]
    else:
        moveset = get_moveset(species, nature, level)
        active_moves = [move_data(m['key']) for m in moveset]

    # Known moves din DB
    known_rows = conn.execute(
        'SELECT move_key FROM known_moves WHERE user_id = ? AND pet_id = ?',
        (uid, pet_id)
    ).fetchall()
    conn.close()

    known_keys = [r['move_key'] for r in known_rows]

    # Adauga si self-taught deblocate (nu sunt in known_moves)
    self_taught = get_moveset(species, nature, level)
    self_taught_keys = [m['key'] for m in self_taught]
    all_known_keys = list(dict.fromkeys(self_taught_keys + known_keys))

    known_moves = [move_data(k) for k in all_known_keys if k in MOVES]

    return jsonify({'ok': True, 'active_moves': active_moves, 'known_moves': known_moves})


@app.route('/joc/petomania/api/training/moves')
@login_required
def api_training_moves():
    from moves_config import MOVES
    user = get_current_user()
    uid  = int(user['id'])
    pet_id = request.args.get('pet_id', 0, type=int)
    zone   = request.args.get('zone', 'incepator')

    ZONE_RANGES = {
        'incepator': (0,  20),
        'ucenic':    (20, 40),
        'adept':     (40, 60),
        'expert':    (60, 80),
        'maestru':   (80, 100),
    }
    if zone not in ZONE_RANGES:
        return jsonify({'ok': False, 'error': 'Zonă invalidă.'})

    zmin, zmax = ZONE_RANGES[zone]

    # Obtine natura petului
    if pet_id == 0:
        from modules.pets import get_pet
        pet = get_pet(uid)
        nature = pet['nature'] if pet else None
        level  = pet['level'] if pet else 1
    else:
        conn = get_db()
        row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (pet_id, uid)).fetchone()
        conn.close()
        if not row:
            return jsonify({'ok': False, 'error': 'Pet negăsit.'})
        nature = row['nature']
        level  = row['level']

    if level < zmin:
        return jsonify({'ok': True, 'moves': [], 'locked': True, 'level': level, 'zone_min': zmin})

    # Known moves pentru acest pet (cumparate + self-taught deblocate)
    from moves_config import get_moveset
    conn = get_db()
    known_rows = conn.execute('SELECT move_key FROM known_moves WHERE user_id = ? AND pet_id = ?', (uid, pet_id)).fetchall()
    conn.close()
    known_keys = {r['move_key'] for r in known_rows}

    # Adauga si self-taught deblocate la known
    if pet_id == 0:
        from modules.pets import get_pet as _gp
        _pet = _gp(uid)
        _species = _pet['species'] if _pet else None
    else:
        _conn = get_db()
        _row = _conn.execute('SELECT species FROM menagerie WHERE id = ? AND user_id = ?', (pet_id, uid)).fetchone()
        _conn.close()
        _species = _row['species'] if _row else None
    self_taught_moves = get_moveset(_species, nature, level)
    for _m in self_taught_moves:
        known_keys.add(_m['key'])

    # Filtreaza moves: natura potrivita, trainable, in zona de nivel, necunoscute
    moves_out = []
    for key, m in MOVES.items():
        if not m.get('trainable'): continue
        if m.get('nature') != nature: continue
        lvl = m.get('unlock_level', 0)
        if lvl <= zmin or lvl > zmax: continue
        if lvl > level: continue  # petul nu are inca nivelul necesar
        if key in known_keys: continue  # deja cunoscut
        moves_out.append({
            'key':            key,
            'name':           m['name'],
            'icon':           m.get('icon', '⚡'),
            'power':          m['power'],
            'unlock_level':   lvl,
            'trainable_cost': m.get('trainable_cost', 0),
            'known':          key in known_keys,
        })

    moves_out.sort(key=lambda x: x['unlock_level'])
    return jsonify({'ok': True, 'moves': moves_out, 'locked': False})


@app.route('/joc/petomania/api/training/buy', methods=['POST'])
@login_required
def api_training_buy():
    from moves_config import MOVES
    user     = get_current_user()
    uid      = int(user['id'])
    data     = request.json
    pet_id   = data.get('pet_id', 0)
    move_key = data.get('move_key')

    if not move_key or move_key not in MOVES:
        return jsonify({'ok': False, 'error': 'Move invalid.'})

    move = MOVES[move_key]
    cost = move.get('trainable_cost', 0)

    # Verifica daca stie deja
    conn = get_db()
    already = conn.execute('SELECT 1 FROM known_moves WHERE user_id = ? AND pet_id = ? AND move_key = ?',
                           (uid, pet_id, move_key)).fetchone()
    if already:
        conn.close()
        return jsonify({'ok': False, 'error': 'Abilitatea este deja cunoscută.'})

    # Scade dacoins
    if not spend_dacoins(uid, cost):
        conn.close()
        return jsonify({'ok': False, 'error': 'Dacoins insuficienți.'})

    # Adauga in known_moves
    conn.execute('INSERT OR IGNORE INTO known_moves (user_id, pet_id, move_key) VALUES (?, ?, ?)',
                 (uid, pet_id, move_key))
    conn.commit()

    # Returneaza active moves curente (cele 4 slots)
    active_rows = conn.execute('SELECT slot, move_key FROM active_moves WHERE user_id = ? AND pet_id = ? ORDER BY slot',
                               (uid, pet_id)).fetchall()
    conn.close()

    # Daca nu are inca active_moves in DB, luam din get_moveset (self-taught)
    if not active_rows:
        from moves_config import get_moveset
        if pet_id == 0:
            from modules.pets import get_pet
            pet = get_pet(uid)
            nature = pet['nature'] if pet else None
            level  = pet['level'] if pet else 1
            species = pet['species'] if pet else None
        else:
            conn2 = get_db()
            row = conn2.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (pet_id, uid)).fetchone()
            conn2.close()
            nature  = row['nature']
            level   = row['level']
            species = row['species']
        moveset = get_moveset(species, nature, level)
        active_moves = [{'key': m['key'], 'name': m['name'], 'icon': m.get('icon','⚡'), 'slot': i+1}
                        for i, m in enumerate(moveset)]
    else:
        from moves_config import MOVES as MV
        active_moves = []
        for r in active_rows:
            m = MV.get(r['move_key'], {})
            active_moves.append({'key': r['move_key'], 'name': m.get('name','?'), 'icon': m.get('icon','⚡'), 'slot': r['slot']})

    return jsonify({'ok': True, 'active_moves': active_moves})


@app.route('/joc/petomania/api/training/swap', methods=['POST'])
@login_required
def api_training_swap():
    from moves_config import MOVES, get_moveset
    user         = get_current_user()
    uid          = int(user['id'])
    data         = request.json
    pet_id       = data.get('pet_id', 0)
    old_move_key = data.get('old_move_key')
    new_move_key = data.get('new_move_key')

    if not old_move_key or not new_move_key:
        return jsonify({'ok': False, 'error': 'Date incomplete.'})

    # Obtine active moves curente
    conn = get_db()
    active_rows = conn.execute('SELECT slot, move_key FROM active_moves WHERE user_id = ? AND pet_id = ? ORDER BY slot',
                               (uid, pet_id)).fetchall()

    if not active_rows:
        # Initializeaza din get_moveset
        if pet_id == 0:
            from modules.pets import get_pet
            pet = get_pet(uid)
            nature = pet['nature'] if pet else None
            level  = pet['level'] if pet else 1
            species = pet['species'] if pet else None
        else:
            row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (pet_id, uid)).fetchone()
            nature  = row['nature']
            level   = row['level']
            species = row['species']
        moveset = get_moveset(species, nature, level)
        for i, m in enumerate(moveset):
            conn.execute('INSERT OR REPLACE INTO active_moves (user_id, pet_id, slot, move_key) VALUES (?, ?, ?, ?)',
                         (uid, pet_id, i+1, m['key']))
        conn.commit()
        active_rows = conn.execute('SELECT slot, move_key FROM active_moves WHERE user_id = ? AND pet_id = ? ORDER BY slot',
                                   (uid, pet_id)).fetchall()

    # Gaseste slot-ul cu old_move
    slot_to_replace = None
    for r in active_rows:
        if r['move_key'] == old_move_key:
            slot_to_replace = r['slot']
            break

    if slot_to_replace is None:
        # old_move_key nu e in active_moves — poate fi un move self-taught care n-a fost niciodata in DB
        # Inlocuim slot 1 ca fallback
        slot_to_replace = active_rows[0]['slot'] if active_rows else 1

    conn.execute('UPDATE active_moves SET move_key = ? WHERE user_id = ? AND pet_id = ? AND slot = ?',
                 (new_move_key, uid, pet_id, slot_to_replace))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})




@app.route('/joc/petomania/api/biserica/vindeca', methods=['POST'])
@login_required
def api_biserica_vindeca():
    import json
    from moves_config import get_moveset, MOVES
    from modules.pets import get_pet
    from cogs.petgame_stats import get_stats_at_level
    from modules.pets import get_form

    user = get_current_user()
    uid  = int(user['id'])
    COST = 500

    if not spend_dacoins(uid, COST):
        return jsonify({'ok': False, 'error': 'Dacoins insuficienți. Ai nevoie de 500 Dacoins.'})

    conn = get_db()

    # Vindeca pet activ
    pet = get_pet(uid)
    if pet:
        p      = dict(pet)
        form   = get_form(p['level'])
        stats  = get_stats_at_level(p['species'], p.get('nature'), p['level'], form)
        hp_max = stats['hp']

        # Reseteaza MP la max
        moveset  = get_moveset(p['species'], p.get('nature'), p['level'])
        mp_dict  = {m['key']: m.get('max_mp', 15) for m in moveset}
        # Include si active_moves custom
        active_rows = conn.execute(
            'SELECT move_key FROM active_moves WHERE user_id = ? AND pet_id = 0', (uid,)
        ).fetchall()
        for r in active_rows:
            m = MOVES.get(r['move_key'])
            if m:
                mp_dict[r['move_key']] = m.get('max_mp', 15)
        # Include known_moves
        known_rows = conn.execute(
            'SELECT move_key FROM known_moves WHERE user_id = ? AND pet_id = 0', (uid,)
        ).fetchall()
        for r in known_rows:
            m = MOVES.get(r['move_key'])
            if m:
                mp_dict[r['move_key']] = m.get('max_mp', 15)

        conn.execute(
            'UPDATE pets SET hp_current = ?, mp_json = ? WHERE user_id = ?',
            (hp_max, json.dumps(mp_dict), uid)
        )

    # Vindeca toti din menajerie
    men_rows = conn.execute('SELECT * FROM menagerie WHERE user_id = ?', (uid,)).fetchall()
    for row in men_rows:
        p      = dict(row)
        form   = get_form(p['level'])
        stats  = get_stats_at_level(p['species'], p.get('nature'), p['level'], form)
        hp_max = stats['hp']
        men_id = p['id']

        moveset = get_moveset(p['species'], p.get('nature'), p['level'])
        mp_dict = {m['key']: m.get('max_mp', 15) for m in moveset}
        active_rows = conn.execute(
            'SELECT move_key FROM active_moves WHERE user_id = ? AND pet_id = ?', (uid, men_id)
        ).fetchall()
        for r in active_rows:
            m = MOVES.get(r['move_key'])
            if m:
                mp_dict[r['move_key']] = m.get('max_mp', 15)
        known_rows = conn.execute(
            'SELECT move_key FROM known_moves WHERE user_id = ? AND pet_id = ?', (uid, men_id)
        ).fetchall()
        for r in known_rows:
            m = MOVES.get(r['move_key'])
            if m:
                mp_dict[r['move_key']] = m.get('max_mp', 15)

        conn.execute(
            'UPDATE menagerie SET hp_current = ?, mp_json = ? WHERE id = ? AND user_id = ?',
            (hp_max, json.dumps(mp_dict), men_id, uid)
        )

    conn.commit()
    conn.close()

    return jsonify({'ok': True, 'new_balance': get_dacoins(uid)})


# ── CAPTURĂ NEXUS ────────────────────────────────────────────────────────

@app.route('/joc/petomania/api/battle/capture', methods=['POST'])
@login_required
def api_battle_capture():
    import json, random, time
    from cogs.petgame_config import SPECIES
    from inventory_config import INVENTORY_ITEMS

    user = get_current_user()
    uid  = int(user['id'])

    # Captura blocata in arena — Corvin nu permite
    return jsonify({'ok': False, 'caught': False, 'blocked': True,
                    'msg': 'Captura nu este permisă în Arenă.'})

    # Verifica ca suntem in lupta
    npc = session.get('battle_npc')
    if not npc:
        return jsonify({'ok': False, 'msg': 'Nu ești în luptă.'})

    data     = request.json or {}
    item_key = data.get('item_key', 'nexus_basic')

    # Verifica ca playerul are nexus in inventar
    conn = get_db()
    inv_row = conn.execute(
        'SELECT quantity FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?',
        (uid, 'nexus', item_key)
    ).fetchone()
    if not inv_row or inv_row['quantity'] < 1:
        conn.close()
        return jsonify({'ok': False, 'msg': 'Nu ai acest Nexus în inventar.'})

    # Nexus multiplier
    NEXUS_MULTIPLIERS = {
        'nexus_basic': 1.0,
    }
    nexus_mult = NEXUS_MULTIPLIERS.get(item_key, 1.0)

    # NPC stats
    hp_current = npc.get('hp_current', 1)
    hp_max     = npc.get('hp_max', 1)
    status     = npc.get('status')

    # Calcul rata de captură
    # Base: 30% × nexus_mult
    base_rate = 0.30 * nexus_mult

    # HP modifier: cu cat mai mic HP, cu atat mai mare sansa (max +50%)
    hp_ratio    = hp_current / max(hp_max, 1)
    hp_modifier = (1.0 - hp_ratio) * 0.50

    # Status modifier
    STATUS_BONUSES = {
        'stun':       0.15,
        'freeze':     0.15,
        'sleep':      0.15,
        'burn':       0.10,
        'poison':     0.10,
        'speed_down': 0.05,
    }
    status_modifier = STATUS_BONUSES.get(status, 0.0)

    capture_rate = min(0.90, base_rate + hp_modifier + status_modifier)
    roll         = random.random()
    success      = roll <= capture_rate

    # Scade nexus din inventar indiferent de rezultat
    new_qty = inv_row['quantity'] - 1
    if new_qty == 0:
        conn.execute('DELETE FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?',
                     (uid, 'nexus', item_key))
    else:
        conn.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND category = ? AND item_key = ?',
                     (new_qty, uid, 'nexus', item_key))
    conn.commit()

    if not success:
        conn.close()
        return jsonify({
            'ok':      True,
            'caught':  False,
            'rate':    round(capture_rate * 100),
            'msg':     f'Nexusul s-a spart! {npc["name"]} a scăpat. (Șansă: {round(capture_rate*100)}%)',
        })

    # Capturat — adauga in menajerie
    species = npc.get('species', 'cat')
    nature  = npc.get('nature')
    level   = npc.get('level', 1)
    gender  = npc.get('gender', 'male')  # din NPC generat

    # Genereaza nume din species
    species_data = SPECIES.get(species, {})
    from modules.pets import get_form
    form = get_form(level)
    entry = species_data.get('entries', {}).get(form, {})
    default_name = entry.get('name', species_data.get('name', 'Companion'))

    # Stats initiale
    from cogs.petgame_stats import get_stats_at_level
    stats  = get_stats_at_level(species, nature, level, form)
    hp_max_new = stats['hp']

    now = int(time.time())
    conn.execute(
        """INSERT INTO menagerie
           (user_id, species, nature, name, level, xp, gender,
            hunger, happiness, cleanliness, energy, sleeping,
            born_at, stored_at, hp, hp_current)
           VALUES (?,?,?,?,?,0,?,100,100,100,100,0,?,?,?,?)""",
        (uid, species, nature, default_name, level, gender,
         now, now, hp_max_new, hp_max_new)
    )
    conn.commit()
    men_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']
    conn.close()

    # Sync companicon
    from modules.companicon import sync_companicon_discovered
    sync_companicon_discovered(uid)

    # Termina lupta
    session.pop('battle_npc', None)
    session.pop('battle_bench', None)
    session.pop('battle_accumulated_reward', None)
    session.pop('battle_participants', None)
    session.pop('battle_size', None)

    return jsonify({
        'ok':      True,
        'caught':  True,
        'rate':    round(capture_rate * 100),
        'name':    default_name,
        'species': species_data.get('name', species),
        'nature':  nature,
        'level':   level,
        'gender':  gender,
        'msg':     f'{default_name} a fost capturat!',
    })


@app.route('/joc/petomania/api/menajerie/delete', methods=['POST'])
@login_required
def api_menajerie_delete():
    user   = get_current_user()
    uid    = int(user['id'])
    data   = request.json or {}
    men_id = data.get('id')
    if not men_id:
        return jsonify({'ok': False, 'error': 'ID lipsă.'})
    conn = get_db()
    row = conn.execute('SELECT id FROM menagerie WHERE id = ? AND user_id = ?', (men_id, uid)).fetchone()
    if not row:
        conn.close()
        return jsonify({'ok': False, 'error': 'Companion negăsit.'})
    # Scoate din loadout daca e acolo
    conn.execute('''UPDATE loadout SET
        slot_2 = CASE WHEN slot_2 = ? THEN NULL ELSE slot_2 END,
        slot_3 = CASE WHEN slot_3 = ? THEN NULL ELSE slot_3 END,
        slot_4 = CASE WHEN slot_4 = ? THEN NULL ELSE slot_4 END,
        slot_5 = CASE WHEN slot_5 = ? THEN NULL ELSE slot_5 END
        WHERE user_id = ?''', (men_id, men_id, men_id, men_id, uid))
    # Sterge known_moves si active_moves
    conn.execute('DELETE FROM known_moves WHERE user_id = ? AND pet_id = ?', (uid, men_id))
    conn.execute('DELETE FROM active_moves WHERE user_id = ? AND pet_id = ?', (uid, men_id))
    # Sterge din menajerie
    conn.execute('DELETE FROM menagerie WHERE id = ? AND user_id = ?', (men_id, uid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})



# ── VÂNĂTOARE (CLONA BATTLE) ────────────────────────────────────────────

@app.route('/joc/petomania/api/vanatoare/start', methods=['POST'])
@login_required
def api_vanatoare_start():
    from modules.battle import build_combatant, generate_npc, save_combatant_mp
    from moves_config import get_move
    from modules.pets import sync_pet, get_form, get_state
    user = get_current_user()
    uid  = int(user['id'])

    data_req     = request.json or {}
    battle_size  = min(max(int(data_req.get('size', 1)), 1), 3)

    # Petul activ (slot 1)
    pet = sync_pet(uid)
    if not pet:
        return jsonify({'ok': False, 'error': 'Nu ai un companion activ.'})
    pet = dict(pet)
    pet.setdefault('id', 0)
    pet.setdefault('user_id', uid)

    player = build_combatant(pet)

    # Initializeaza HP in menagerie pentru pets care nu au luptat niciodata
    sync_menagerie_hp(uid)

    # Loadout complet pentru switch
    loadout_raw = build_loadout_context(uid)

    # Numara pets vii din loadout (inclusiv petul activ)
    alive_count = (1 if player['hp_current'] > 0 else 0)
    for slot in loadout_raw:
        if not slot.get('empty') and slot.get('slot') != 1 and slot.get('hp_current', 0) > 0:
            alive_count += 1
    if alive_count == 0:
        return jsonify({'ok': False, 'error': 'Toți companionii tăi sunt KO. Vindecă-i înainte de luptă.'})
    if alive_count < battle_size:
        return jsonify({'ok': False, 'error': f'Ai nevoie de {battle_size} companioi cu HP pentru acest mod. Ai doar {alive_count}.'})
    bench = []  # petii de pe bancă — max battle_size-1 pets, doar cu HP > 0
    for slot in loadout_raw:
        if slot.get('empty') or slot.get('slot') == 1:
            continue
        if len(bench) >= battle_size - 1:
            break
        if slot['hp_current'] <= 0:
            continue
        bench.append({
            'id':        slot['id'],
            'name':      slot['name'],
            'level':     slot['level'],
            'hp_max':    slot['hp_max'],
            'hp_current':slot['hp_current'],
            'image_url': slot['image_url'],
            'species':   slot['species_key'],
            'nature':    slot['nature_key'],
            'gender':    slot.get('gender', 'male'),
        })

    # Daca petul activ e mort, inlocuieste-l cu primul din loadout cu HP > 0
    if player['hp_current'] <= 0:
        # Cauta in tot loadout-ul (nu doar in bench limitat)
        all_bench = []
        for slot in loadout_raw:
            if slot.get('empty') or slot.get('slot') == 1:
                continue
            all_bench.append(slot)
        alive_slots = [s for s in all_bench if s.get('hp_current', 0) > 0]
        if not alive_slots:
            return jsonify({'ok': False, 'error': 'Toți companionii tăi sunt KO. Vindecă-i înainte de luptă.'})
        first = alive_slots[0]
        conn_b = get_db()
        row_b  = conn_b.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (first['id'], uid)).fetchone()
        conn_b.close()
        if not row_b:
            return jsonify({'ok': False, 'error': 'Companion negăsit.'})
        row_b_dict = dict(row_b)
        row_b_dict.setdefault('user_id', uid)
        player = build_combatant(row_b_dict)
        # Reconstruieste bench fara noul player
        bench = []
        for slot in loadout_raw:
            if slot.get('empty') or slot.get('slot') == 1:
                continue
            if str(slot['id']) == str(first['id']):
                continue
            if len(bench) >= battle_size - 1:
                break
            bench.append({
                'id':        slot['id'],
                'name':      slot['name'],
                'level':     slot['level'],
                'hp_max':    slot['hp_max'],
                'hp_current':slot['hp_current'],
                'image_url': slot['image_url'],
                'species':   slot['species_key'],
                'nature':    slot['nature_key'],
                'gender':    slot.get('gender', 'male'),
            })

    npc = generate_npc(player['level'], zone=session.get('aventura_zone', 'vanatoare'))

    moveset_data = []
    for mk in player['moveset']:
        m = get_move(mk)
        if m:
            moveset_data.append({'key': m['key'], 'name': m['name'], 'icon': m['icon'], 'type': m['type'], 'power': m['power'], 'mp': player['mp'].get(m['key'], 15), 'max_mp': m.get('max_mp', 15), 'nature': m.get('nature')})

    session['battle_player']             = player
    session['vanatoare_npc']                = npc
    session['vanatoare_bench']              = bench
    session['vanatoare_size']               = battle_size
    session['vanatoare_npc_index']          = 1
    session['vanatoare_accumulated_reward'] = 0
    session['vanatoare_participants']          = [player['id']]

    return jsonify({
        'ok': True,
        'player': {
            'id': player['id'], 'name': player['name'], 'species': player['species'],
            'nature': player['nature'], 'level': player['level'],
            'hp_max': player['hp_max'], 'hp_current': player['hp_current'],
            'image_url': player['image_url'], 'moveset': moveset_data,
            'status': None, 'shield': 0,
        },
        'npc': {
            'id': npc['id'], 'name': npc['name'], 'species': npc['species'],
            'nature': npc['nature'], 'level': npc['level'],
            'hp_max': npc['hp_max'], 'hp_current': npc['hp_current'],
            'image_url': npc['image_url'], 'status': None, 'shield': 0,
        },
        'bench': bench,
    })




@app.route('/joc/petomania/api/vanatoare/turn', methods=['POST'])
@login_required
def api_vanatoare_turn():
    from modules.battle import execute_turn, calculate_reward, save_combatant_mp
    user   = get_current_user()
    uid    = int(user['id'])
    player = session.get('battle_player')
    npc    = session.get('vanatoare_npc')
    if not player or not npc:
        return jsonify({'ok': False, 'error': 'Nicio bătălie activă.'})

    # Re-citeste HP din DB inainte de tur doar daca playerul e petul activ (id=None = din pets)
    # Daca e din menagerie (id != None), HP-ul lui e in sesiune, nu in tabela pets
    if player.get('id') is None or player.get('id') == 0:
        conn = get_db()
        fresh = conn.execute('SELECT hp_current FROM pets WHERE user_id = ?', (uid,)).fetchone()
        conn.close()
        if fresh:
            player['hp_current'] = fresh['hp_current']

    move_key = (request.json or {}).get('move_key', 'scratch')
    result   = execute_turn(player, npc, move_key)

    # Salveaza HP si MP dupa fiecare tur in DB
    _save_player_hp(player, uid)
    save_combatant_mp(player, uid)

    session['battle_player'] = player
    session['vanatoare_npc']    = npc

    reward = 0
    if result['winner'] == 'player':
        npc_index   = session.get('vanatoare_npc_index', 1)
        battle_size = session.get('vanatoare_size', 1)

        if npc_index < battle_size:
            # Mai sunt NPC-uri — genereaza urmatorul
            from modules.battle import generate_npc as _gen_npc
            new_npc = _gen_npc(player['level'], zone=session.get('aventura_zone', 'vanatoare'))
            pass  # fara dacoins la vanatoare
            session['vanatoare_npc']       = new_npc
            session['vanatoare_npc_index'] = npc_index + 1
            session['battle_player']    = player
            return jsonify({
                'ok': True, 'log': result['log'],
                'player': result['player'],
                'npc': {
                    'id': new_npc['id'], 'name': new_npc['name'],
                    'species': new_npc['species'], 'nature': new_npc['nature'],
                    'level': new_npc['level'], 'hp_max': new_npc['hp_max'],
                    'hp_current': new_npc['hp_current'],
                    'image_url': new_npc['image_url'], 'status': None, 'shield': 0,
                },
                'winner': None,
                'next_npc': True,
                'reward': 0,
            })

        # Ultimul NPC doborat — victorie finala
        reward = 0
        _save_bench_hp(session.get('vanatoare_bench', []))
        # Acorda XP participantilor
        xp_total = max(1, calculate_reward(player['level'], npc['level'], True) // 3)
        participants = session.get('vanatoare_participants', [player['id']])
        xp_results = add_battle_xp(uid, xp_total, participants)
        session.pop('battle_player', None)
        session.pop('vanatoare_npc', None)
        session.pop('vanatoare_size', None)
        session.pop('vanatoare_npc_index', None)
        session.pop('vanatoare_accumulated_reward', None)
        session.pop('vanatoare_participants', None)
        # 5% sansa de trigger Daiana Solaris
        import random as _random
        if _random.random() < 0.05:
            session['daiana_trigger'] = True
    elif result['winner'] == 'npc':
        _save_player_hp(player, uid, hp_override=0)
        bench = session.get('vanatoare_bench', [])
        alive = [p for p in bench if p.get('hp_current', 0) > 0]
        if alive:
            # Mai sunt pets in bench — lasa sesiunea activa pentru switch
            session['battle_player'] = player
        else:
            # Niciun pet disponibil — lupta pierduta
            _save_bench_hp(bench)
            session.pop('battle_player', None)
            session.pop('vanatoare_npc', None)
            session.pop('vanatoare_size', None)
            session.pop('vanatoare_npc_index', None)
            session.pop('vanatoare_accumulated_reward', None)
            session.pop('vanatoare_participants', None)
            import random as _random3
            if _random3.random() < 0.05:
                session['daiana_trigger'] = True

    return jsonify({
        'ok': True, 'log': result['log'],
        'player': result['player'], 'npc': result['npc'],
        'winner': result['winner'], 'reward': reward,
        'bench': session.get('vanatoare_bench', []),
        'xp_results': locals().get('xp_results', []),
    })


@app.route('/joc/petomania/api/vanatoare/flee', methods=['POST'])
@login_required
def api_vanatoare_flee():
    user   = get_current_user()
    uid    = int(user['id'])
    player = session.get('battle_player')
    if player:
        hp_flee = max(1, player.get('hp_current', 1))
        _save_player_hp(player, uid, hp_override=hp_flee)
    session.pop('battle_player', None)
    session.pop('vanatoare_npc', None)
    import random as _random
    if _random.random() < 0.05:
        session['daiana_trigger'] = True
    return jsonify({'ok': True})



# ── BATTLE PAGE ───────────────────────────────────────────────────────

@app.route('/joc/petomania/vanatoare')
@login_required
def vanatoare():
    zone = request.args.get('zone', 'vanatoare')
    session['aventura_zone'] = zone
    session['from_aventura'] = zone != 'vanatoare'
    return render_template('vanatoare.html')


@app.route('/joc/petomania/api/vanatoare/switch', methods=['POST'])
@login_required
def api_vanatoare_switch():
    from modules.battle import build_combatant, save_combatant_mp
    from moves_config import get_move
    user   = get_current_user()
    uid    = int(user['id'])
    pet_id = (request.json or {}).get('pet_id')
    bench  = session.get('vanatoare_bench', [])

    pet_data = next((p for p in bench if str(p['id']) == str(pet_id)), None)
    if not pet_data:
        return jsonify({'ok': False, 'error': 'Pet negasit pe bancă.'})
    if pet_data['hp_current'] <= 0:
        return jsonify({'ok': False, 'error': 'Acest companion a căzut.'})

    # Construieste noul combatant
    from modules.db import get_db
    conn = get_db()
    if pet_data.get('from_pets') or str(pet_data['id']) == '0':
        row = conn.execute('SELECT *, ? as user_id, 0 as id FROM pets WHERE user_id = ?', (uid, uid)).fetchone()
    else:
        row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (pet_data['id'], uid)).fetchone()
    conn.close()
    if not row:
        return jsonify({'ok': False, 'error': 'Pet negasit în DB.'})

    new_player_dict = dict(row)
    new_player_dict.setdefault('user_id', uid)
    new_player = build_combatant(new_player_dict)
    moveset_data = []
    for mk in new_player['moveset']:
        m = get_move(mk)
        if m:
            moveset_data.append({'key': m['key'], 'name': m['name'], 'icon': m['icon'], 'type': m['type'], 'power': m['power'], 'mp': new_player['mp'].get(m['key'], 15), 'max_mp': m.get('max_mp', 15), 'nature': m.get('nature')})

    # Salveaza HP-ul petului care iese din arena
    old_player = session.get('battle_player')
    if old_player:
        old_id = old_player.get('id', 0)
        old_hp = max(0, old_player.get('hp_current', 0))
        conn2 = get_db()
        if old_id and old_id != 0:
            conn2.execute('UPDATE menagerie SET hp_current = ? WHERE id = ?', (old_hp, old_id))
        else:
            conn2.execute('UPDATE pets SET hp_current = ? WHERE user_id = ?', (old_hp, uid))
        conn2.commit()
        conn2.close()
        # Salveaza MP petului care iese
        if old_player:
            save_combatant_mp(old_player, uid)

        # Daca petul care iese e viu (switch voluntar), il adaugam inapoi in bench
        new_bench = [p for p in bench if str(p['id']) != str(pet_id)]
        if old_hp > 0:
            already_in_bench = any(str(p.get('id')) == str(old_id) for p in new_bench)
            if not already_in_bench:
                new_bench.append({
                    'id':        old_id,
                    'name':      old_player.get('name'),
                    'level':     old_player.get('level'),
                    'hp_max':    old_player.get('hp_max'),
                    'hp_current':old_hp,
                    'image_url': old_player.get('image_url', ''),
                    'species':   old_player.get('species', ''),
                    'nature':    old_player.get('nature'),
                    'gender':    old_player.get('gender', 'male'),
                    'from_pets': (old_id == 0),
                })
        bench = new_bench

    # Scoate din bench
    session['vanatoare_bench']  = bench
    session['battle_player'] = new_player
    # Adauga noul player in lista de participanti daca nu e deja
    participants = session.get('vanatoare_participants', [])
    if new_player['id'] not in participants:
        participants.append(new_player['id'])
    session['vanatoare_participants'] = participants

    return jsonify({
        'ok': True,
        'player': {
            'id': new_player['id'], 'name': new_player['name'],
            'species': new_player['species'], 'nature': new_player['nature'],
            'level': new_player['level'], 'hp_max': new_player['hp_max'],
            'hp_current': new_player['hp_current'], 'image_url': new_player['image_url'],
            'moveset': moveset_data, 'status': None, 'shield': 0,
        },
        'bench': session.get('vanatoare_bench', []),
    })



# ── BATTLE STATE ─────────────────────────────────────────────────────

@app.route('/joc/petomania/api/vanatoare/state')
@login_required
def api_vanatoare_state():
    from moves_config import get_move
    player = session.get('battle_player')
    npc    = session.get('vanatoare_npc')
    bench  = session.get('vanatoare_bench', [])
    if not player or not npc:
        return jsonify({'ok': False, 'active': False})

    moveset_data = []
    for mk in player.get('moveset', []):
        m = get_move(mk)
        if m:
            moveset_data.append({'key': m['key'], 'name': m['name'], 'icon': m['icon'], 'type': m['type'], 'power': m['power'], 'mp': player.get('mp', {}).get(m['key'], 15), 'max_mp': m.get('max_mp', 15), 'nature': m.get('nature')})

    # Re-citeste HP din DB — poate fi modificat de potiuni intre tururi
    conn = get_db()
    fresh = conn.execute('SELECT hp_current FROM pets WHERE user_id = ?', (int(get_current_user()['id']),)).fetchone()
    conn.close()
    if fresh:
        player['hp_current'] = fresh['hp_current']
        session['battle_player'] = player

    return jsonify({
        'ok': True, 'active': True,
        'player': {
            'id': player['id'], 'name': player['name'],
            'level': player.get('level', 1),
            'hp_max': player['hp_max'], 'hp_current': player['hp_current'],
            'image_url': player.get('image_url', ''),
            'moveset': moveset_data, 'status': player.get('status'), 'shield': player.get('shield', 0),
        },
        'npc': {
            'id': npc['id'], 'name': npc['name'],
            'level': npc.get('level', 1),
            'hp_max': npc['hp_max'], 'hp_current': npc['hp_current'],
            'image_url': npc.get('image_url', ''),
            'status': npc.get('status'), 'shield': npc.get('shield', 0),
        },
        'bench': bench,
    })



# ── BATTLE ABANDON ────────────────────────────────────────────────────

@app.route('/joc/petomania/api/vanatoare/abandon', methods=['POST'])
@login_required
def api_vanatoare_abandon():
    """Curata sesiunea de lupta fara a salva HP."""
    session.pop('battle_player', None)
    session.pop('vanatoare_npc', None)
    session.pop('vanatoare_bench', None)
    import random as _random2
    if _random2.random() < 0.05:
        session['daiana_trigger'] = True
    return jsonify({'ok': True})


@app.route('/joc/petomania/api/vanatoare/capture', methods=['POST'])
@login_required
def api_vanatoare_capture():
    import json, random, time
    from cogs.petgame_config import SPECIES
    from inventory_config import INVENTORY_ITEMS

    user = get_current_user()
    uid  = int(user['id'])

    # Verifica ca suntem in lupta
    npc = session.get('vanatoare_npc')
    if not npc:
        return jsonify({'ok': False, 'msg': 'Nu ești în luptă.'})

    data     = request.json or {}
    item_key = data.get('item_key', 'nexus_basic')

    # Verifica ca playerul are nexus in inventar
    conn = get_db()
    inv_row = conn.execute(
        'SELECT quantity FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?',
        (uid, 'nexus', item_key)
    ).fetchone()
    if not inv_row or inv_row['quantity'] < 1:
        conn.close()
        return jsonify({'ok': False, 'msg': 'Nu ai acest Nexus în inventar.'})

    # Nexus multiplier
    NEXUS_MULTIPLIERS = {
        'nexus_basic': 1.0,
    }
    nexus_mult = NEXUS_MULTIPLIERS.get(item_key, 1.0)

    # NPC stats
    hp_current = npc.get('hp_current', 1)
    hp_max     = npc.get('hp_max', 1)
    status     = npc.get('status')

    # Calcul rata de captură
    # Base: 30% × nexus_mult
    base_rate = 0.30 * nexus_mult

    # HP modifier: cu cat mai mic HP, cu atat mai mare sansa (max +50%)
    hp_ratio    = hp_current / max(hp_max, 1)
    hp_modifier = (1.0 - hp_ratio) * 0.50

    # Status modifier
    STATUS_BONUSES = {
        'stun':       0.15,
        'freeze':     0.15,
        'sleep':      0.15,
        'burn':       0.10,
        'poison':     0.10,
        'speed_down': 0.05,
    }
    status_modifier = STATUS_BONUSES.get(status, 0.0)

    capture_rate = min(0.90, base_rate + hp_modifier + status_modifier)
    roll         = random.random()
    success      = roll <= capture_rate

    # Scade nexus din inventar indiferent de rezultat
    new_qty = inv_row['quantity'] - 1
    if new_qty == 0:
        conn.execute('DELETE FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?',
                     (uid, 'nexus', item_key))
    else:
        conn.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND category = ? AND item_key = ?',
                     (new_qty, uid, 'nexus', item_key))
    conn.commit()

    if not success:
        conn.close()
        return jsonify({
            'ok':      True,
            'caught':  False,
            'rate':    round(capture_rate * 100),
            'msg':     f'Nexusul s-a spart! {npc["name"]} a scăpat. (Șansă: {round(capture_rate*100)}%)',
        })

    # Capturat — adauga in menajerie
    species = npc.get('species', 'cat')
    nature  = npc.get('nature')
    level   = npc.get('level', 1)
    gender  = npc.get('gender', 'male')  # din NPC generat

    # Genereaza nume din species
    species_data = SPECIES.get(species, {})
    from modules.pets import get_form
    form = get_form(level)
    entry = species_data.get('entries', {}).get(form, {})
    default_name = entry.get('name', species_data.get('name', 'Companion'))

    # Stats initiale
    from cogs.petgame_stats import get_stats_at_level
    stats  = get_stats_at_level(species, nature, level, form)
    hp_max_new = stats['hp']

    now = int(time.time())
    conn.execute(
        """INSERT INTO menagerie
           (user_id, species, nature, name, level, xp, gender,
            hunger, happiness, cleanliness, energy, sleeping,
            born_at, stored_at, hp, hp_current)
           VALUES (?,?,?,?,?,0,?,100,100,100,100,0,?,?,?,?)""",
        (uid, species, nature, default_name, level, gender,
         now, now, hp_max_new, hp_max_new)
    )
    conn.commit()
    men_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']
    conn.close()

    # Sync companicon
    from modules.companicon import sync_companicon_discovered
    sync_companicon_discovered(uid)

    # Termina lupta
    session.pop('vanatoare_npc', None)
    session.pop('vanatoare_bench', None)
    session.pop('vanatoare_accumulated_reward', None)
    session.pop('vanatoare_participants', None)
    session.pop('vanatoare_size', None)

    return jsonify({
        'ok':      True,
        'caught':  True,
        'rate':    round(capture_rate * 100),
        'name':    default_name,
        'species': species_data.get('name', species),
        'nature':  nature,
        'level':   level,
        'gender':  gender,
        'msg':     f'{default_name} a fost capturat!',
    })

# ── PESCUIT APĂ DULCE ────────────────────────────────────────────────────

@app.route('/joc/petomania/pescuit')
@login_required
def pescuit():
    return render_template('pescuit.html')


@app.route('/joc/petomania/api/pescuit/start', methods=['POST'])
@login_required
def api_pescuit_start():
    from modules.battle import build_combatant, generate_npc, save_combatant_mp
    from moves_config import get_move
    from modules.pets import sync_pet
    import random as _rand
    user = get_current_user()
    uid  = int(user['id'])

    # Roll sansa aparitie — goldfish e legendary in zone_config (1%), verdian/toadisimo sunt common
    if _rand.random() > 0.40:
        return jsonify({'ok': True, 'appeared': False, 'msg': 'Liniște... Nimic nu a mușcat. Încearcă din nou.'})

    pet = sync_pet(uid)
    if not pet:
        return jsonify({'ok': False, 'error': 'Nu ai un companion activ.'})
    pet = dict(pet)
    pet.setdefault('id', 0)
    pet.setdefault('user_id', uid)

    player = build_combatant(pet)

    # Daca petul activ e KO, cauta primul viu din loadout
    if player['hp_current'] <= 0:
        from modules.loadout import build_loadout_context
        loadout_raw = build_loadout_context(uid)
        alive = [s for s in loadout_raw if not s.get('empty') and s.get('slot') != 1 and s.get('hp_current', 0) > 0]
        if not alive:
            return jsonify({'ok': False, 'error': 'Toți companionii tăi sunt KO. Vindecă-i la Biserică.'})
        first = alive[0]
        conn_b = get_db()
        row_b  = conn_b.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (first['id'], uid)).fetchone()
        conn_b.close()
        if not row_b:
            return jsonify({'ok': False, 'error': 'Companion negăsit.'})
        row_b_dict = dict(row_b)
        row_b_dict.setdefault('user_id', uid)
        player = build_combatant(row_b_dict)

    npc = generate_npc(player['level'], zone='pescuit')

    moveset_data = []
    for mk in player['moveset']:
        m = get_move(mk)
        if m:
            moveset_data.append({'key': m['key'], 'name': m['name'], 'icon': m['icon'],
                                  'type': m['type'], 'power': m['power'],
                                  'mp': player['mp'].get(m['key'], 15),
                                  'max_mp': m.get('max_mp', 15), 'nature': m.get('nature')})

    session['battle_player']          = player
    session['pescuit_npc']            = npc
    session['pescuit_participants']   = [player['id']]

    return jsonify({
        'ok': True, 'appeared': True,
        'player': {
            'id': player['id'], 'name': player['name'], 'species': player['species'],
            'nature': player['nature'], 'level': player['level'],
            'hp_max': player['hp_max'], 'hp_current': player['hp_current'],
            'image_url': player['image_url'], 'moveset': moveset_data,
            'status': None, 'shield': 0,
        },
        'npc': {
            'id': npc['id'], 'name': npc['name'], 'species': npc['species'],
            'nature': npc['nature'], 'level': npc['level'],
            'hp_max': npc['hp_max'], 'hp_current': npc['hp_current'],
            'image_url': npc['image_url'], 'status': None, 'shield': 0,
        },
    })


@app.route('/joc/petomania/api/pescuit/state')
@login_required
def api_pescuit_state():
    from moves_config import get_move
    player = session.get('battle_player')
    npc    = session.get('pescuit_npc')
    if not player or not npc:
        return jsonify({'ok': False, 'active': False})

    moveset_data = []
    for mk in player.get('moveset', []):
        m = get_move(mk)
        if m:
            moveset_data.append({'key': m['key'], 'name': m['name'], 'icon': m['icon'],
                                  'type': m['type'], 'power': m['power'],
                                  'mp': player.get('mp', {}).get(m['key'], 15),
                                  'max_mp': m.get('max_mp', 15), 'nature': m.get('nature')})

    conn = get_db()
    fresh = conn.execute('SELECT hp_current FROM pets WHERE user_id = ?',
                         (int(get_current_user()['id']),)).fetchone()
    conn.close()
    if fresh:
        player['hp_current'] = fresh['hp_current']
        session['battle_player'] = player

    return jsonify({
        'ok': True, 'active': True,
        'player': {
            'id': player['id'], 'name': player['name'],
            'level': player.get('level', 1),
            'hp_max': player['hp_max'], 'hp_current': player['hp_current'],
            'image_url': player.get('image_url', ''),
            'moveset': moveset_data, 'status': player.get('status'), 'shield': player.get('shield', 0),
        },
        'npc': {
            'id': npc['id'], 'name': npc['name'],
            'level': npc.get('level', 1),
            'hp_max': npc['hp_max'], 'hp_current': npc['hp_current'],
            'image_url': npc.get('image_url', ''),
            'status': npc.get('status'), 'shield': npc.get('shield', 0),
        },
    })


@app.route('/joc/petomania/api/pescuit/turn', methods=['POST'])
@login_required
def api_pescuit_turn():
    from modules.battle import execute_turn, calculate_reward, save_combatant_mp
    user   = get_current_user()
    uid    = int(user['id'])
    player = session.get('battle_player')
    npc    = session.get('pescuit_npc')
    if not player or not npc:
        return jsonify({'ok': False, 'error': 'Nicio bătălie activă.'})

    if player.get('id') is None or player.get('id') == 0:
        conn = get_db()
        fresh = conn.execute('SELECT hp_current FROM pets WHERE user_id = ?', (uid,)).fetchone()
        conn.close()
        if fresh:
            player['hp_current'] = fresh['hp_current']

    move_key = (request.json or {}).get('move_key', 'scratch')
    result   = execute_turn(player, npc, move_key)

    _save_player_hp(player, uid)
    save_combatant_mp(player, uid)

    session['battle_player'] = player
    session['pescuit_npc']   = npc

    if result['winner'] == 'player':
        xp_total     = max(1, calculate_reward(player['level'], npc['level'], True) // 3)
        participants = session.get('pescuit_participants', [player['id']])
        xp_results   = add_battle_xp(uid, xp_total, participants)
        session.pop('battle_player', None)
        session.pop('pescuit_npc', None)
        session.pop('pescuit_participants', None)
        return jsonify({
            'ok': True, 'log': result['log'],
            'player': result['player'], 'npc': result['npc'],
            'winner': 'player', 'reward': 0, 'xp_results': xp_results,
        })

    if result['winner'] == 'npc':
        _save_bench_hp([])
        session.pop('battle_player', None)
        session.pop('pescuit_npc', None)
        session.pop('pescuit_participants', None)
        return jsonify({
            'ok': True, 'log': result['log'],
            'player': result['player'], 'npc': result['npc'],
            'winner': 'npc', 'reward': 0,
        })

    return jsonify({
        'ok': True, 'log': result['log'],
        'player': result['player'], 'npc': result['npc'],
        'winner': None, 'reward': 0,
    })


@app.route('/joc/petomania/api/pescuit/flee', methods=['POST'])
@login_required
def api_pescuit_flee():
    session.pop('battle_player', None)
    session.pop('pescuit_npc', None)
    session.pop('pescuit_participants', None)
    return jsonify({'ok': True})


@app.route('/joc/petomania/api/pescuit/abandon', methods=['POST'])
@login_required
def api_pescuit_abandon():
    session.pop('battle_player', None)
    session.pop('pescuit_npc', None)
    session.pop('pescuit_participants', None)
    return jsonify({'ok': True})


@app.route('/joc/petomania/api/pescuit/capture', methods=['POST'])
@login_required
def api_pescuit_capture():
    import json, random, time
    from cogs.petgame_config import SPECIES
    user = get_current_user()
    uid  = int(user['id'])

    npc = session.get('pescuit_npc')
    if not npc:
        return jsonify({'ok': False, 'msg': 'Nu ești în luptă.'})

    data     = request.json or {}
    item_key = data.get('item_key', 'nexus_basic')

    conn = get_db()
    inv_row = conn.execute(
        'SELECT quantity FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?',
        (uid, 'nexus', item_key)
    ).fetchone()
    if not inv_row or inv_row['quantity'] < 1:
        conn.close()
        return jsonify({'ok': False, 'msg': 'Nu ai acest Nexus în inventar.'})

    hp_current = npc.get('hp_current', 1)
    hp_max     = npc.get('hp_max', 1)
    status     = npc.get('status')

    base_rate   = 0.30
    hp_ratio    = hp_current / max(hp_max, 1)
    hp_modifier = (1.0 - hp_ratio) * 0.50
    STATUS_BONUSES = {'stun': 0.15, 'freeze': 0.15, 'sleep': 0.15, 'burn': 0.10, 'poison': 0.10, 'speed_down': 0.05}
    status_modifier = STATUS_BONUSES.get(status, 0.0)
    capture_rate = min(0.90, base_rate + hp_modifier + status_modifier)
    success      = random.random() <= capture_rate

    new_qty = inv_row['quantity'] - 1
    if new_qty == 0:
        conn.execute('DELETE FROM inventory WHERE user_id = ? AND category = ? AND item_key = ?', (uid, 'nexus', item_key))
    else:
        conn.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND category = ? AND item_key = ?', (new_qty, uid, 'nexus', item_key))
    conn.commit()

    if not success:
        conn.close()
        return jsonify({'ok': True, 'caught': False, 'rate': round(capture_rate * 100),
                        'msg': f'Nexusul s-a spart! {npc["name"]} a scăpat. (Șansă: {round(capture_rate*100)}%)'})

    species      = npc.get('species', 'goldfish')
    nature       = npc.get('nature')
    level        = npc.get('level', 1)
    # Preia gender-ul din NPC — asexuate (goldfish, verdian) stocam 'male' ca default
    gender       = npc.get('gender', 'male')

    species_data = SPECIES.get(species, {})
    from modules.pets import get_form
    form         = get_form(level)
    entry        = species_data.get('entries', {}).get(form, {})
    default_name = entry.get('name', species_data.get('name', 'Companion'))

    from cogs.petgame_stats import get_stats_at_level
    stats     = get_stats_at_level(species, nature, level, form)
    hp_max_new = stats['hp']

    now = int(time.time())
    conn.execute(
        """INSERT INTO menagerie
           (user_id, species, nature, name, level, xp, gender,
            hunger, happiness, cleanliness, energy, sleeping,
            born_at, stored_at, hp, hp_current)
           VALUES (?,?,?,?,?,0,?,100,100,100,100,0,?,?,?,?)""",
        (uid, species, nature, default_name, level, gender, now, now, hp_max_new, hp_max_new)
    )
    conn.commit()
    conn.close()

    from modules.companicon import sync_companicon_discovered
    sync_companicon_discovered(uid)

    session.pop('pescuit_npc', None)
    session.pop('battle_player', None)
    session.pop('pescuit_participants', None)

    nat_icon = {'water': '💧', 'dragon': '🐉'}.get(nature, '')
    return jsonify({
        'ok': True, 'caught': True, 'rate': round(capture_rate * 100),
        'name': default_name, 'species': species_data.get('name', species),
        'nature': nature, 'level': level, 'gender': gender,
        'msg': f'{default_name} a fost capturat!',
    })


@app.route('/joc/petomania/padure')
@login_required
def padure():
    return render_template('padure.html')


@app.route('/joc/petomania/paduremid')
@login_required
def paduremid():
    return render_template('paduremid.html')


@app.route('/joc/petomania/paduredeep')
@login_required
def paduredeep():
    return render_template('paduredeep.html')

# ── CASTEL ────────────────────────────────────────────────────────────────

@app.route('/joc/petomania/api/castel/aldric', methods=['GET'])
@login_required
def api_castel_aldric():
    from modules.db import get_user_permissions, get_dacoins
    user = get_current_user()
    uid  = int(user['id'])
    perms = get_user_permissions(uid)
    balance = get_dacoins(uid)
    return jsonify({
        'ok': True,
        'concesiunevanatoare': perms.get('concesiunevanatoare', 0),
        'balance': balance,
    })


@app.route('/joc/petomania/api/castel/concesiune', methods=['POST'])
@login_required
def api_castel_concesiune():
    from modules.db import get_user_permissions, spend_dacoins, set_user_permission
    user = get_current_user()
    uid  = int(user['id'])
    perms = get_user_permissions(uid)
    if perms.get('concesiunevanatoare', 0):
        return jsonify({'ok': False, 'already': True})
    ok = spend_dacoins(uid, 5000)
    if not ok:
        return jsonify({'ok': False, 'insufficient': True})
    set_user_permission(uid, 'concesiunevanatoare', 1)
    return jsonify({'ok': True})


# ── DAIANA SOLARIS ────────────────────────────────────────────────────────

@app.route('/joc/petomania/api/daiana/check')
@login_required
def api_daiana_check():
    from modules.db import get_user_permissions, get_dacoins
    user  = get_current_user()
    uid   = int(user['id'])
    # Nu triggerăm Daiana dacă venim din aventură
    if session.get('from_aventura'):
        session.pop('daiana_trigger', None)
        return jsonify({'trigger': False})
    trigger = session.pop('daiana_trigger', False)
    if not trigger:
        return jsonify({'trigger': False})
    perms   = get_user_permissions(uid)
    balance = get_dacoins(uid)
    return jsonify({
        'trigger':              True,
        'concesiunevanatoare':  perms.get('concesiunevanatoare', 0),
        'daiana_warned':        perms.get('daiana_warned', 0),
        'balance':              balance,
    })


@app.route('/joc/petomania/api/daiana/amenda', methods=['POST'])
@login_required
def api_daiana_amenda():
    from modules.db import get_user_permissions, get_dacoins, set_user_permission, spend_dacoins
    user  = get_current_user()
    uid   = int(user['id'])
    perms = get_user_permissions(uid)

    # Markeaza ca a fost avertizat
    set_user_permission(uid, 'daiana_warned', 1)

    balance = get_dacoins(uid)
    amenda  = min(1000, balance)
    if amenda > 0:
        spend_dacoins(uid, amenda)

    return jsonify({'ok': True, 'amenda': amenda, 'balance_ramas': balance - amenda})




@app.route('/joc/petomania/api/aventura/zuno/status')
@login_required
def api_zuno_status():
    import time
    from modules.db import get_db
    user = get_current_user()
    uid  = int(user['id'])
    conn = get_db()

    # Verifica daca quest-ul e facut azi
    today = time.strftime('%Y-%m-%d')
    quest_done     = session.get(f'zuno_done_{uid}') == today
    quest_accepted = session.get(f'zuno_accepted_{uid}', False)

    # Verifica daca are lapte in inventar
    row = conn.execute(
        'SELECT quantity FROM inventory WHERE user_id=? AND category=? AND item_key=?',
        (uid, 'mancare', 'lapte')
    ).fetchone()
    conn.close()
    has_milk = bool(row and row['quantity'] > 0)

    return jsonify({
        'quest_done':     quest_done,
        'quest_accepted': quest_accepted,
        'has_milk':       has_milk,
    })


@app.route('/joc/petomania/api/aventura/zuno/accept', methods=['POST'])
@login_required
def api_zuno_accept():
    user = get_current_user()
    uid  = int(user['id'])
    session[f'zuno_accepted_{uid}'] = True
    return jsonify({'ok': True})


@app.route('/joc/petomania/api/aventura/zuno/deliver', methods=['POST'])
@login_required
def api_zuno_deliver():
    import time
    from modules.db import get_db
    user = get_current_user()
    uid  = int(user['id'])

    # Verifica daca quest-ul e deja facut azi
    today = time.strftime('%Y-%m-%d')
    if session.get(f'zuno_done_{uid}') == today:
        return jsonify({'ok': False, 'msg': 'Ai făcut deja asta azi.'})

    # Verifica daca are lapte
    conn = get_db()
    row = conn.execute(
        'SELECT quantity FROM inventory WHERE user_id=? AND category=? AND item_key=?',
        (uid, 'mancare', 'lapte')
    ).fetchone()
    if not row or row['quantity'] < 1:
        conn.close()
        return jsonify({'ok': False, 'msg': 'Nu ai lapte în inventar.'})

    # Scade laptele
    new_qty = row['quantity'] - 1
    if new_qty == 0:
        conn.execute('DELETE FROM inventory WHERE user_id=? AND category=? AND item_key=?',
                     (uid, 'mancare', 'lapte'))
    else:
        conn.execute('UPDATE inventory SET quantity=? WHERE user_id=? AND category=? AND item_key=?',
                     (new_qty, uid, 'mancare', 'lapte'))

    # Acorda 150 dacoins
    conn.execute('INSERT OR IGNORE INTO dacoins (user_id, balance) VALUES (?, 300)', (uid,))
    conn.execute('UPDATE dacoins SET balance = balance + 150 WHERE user_id=?', (uid,))
    conn.commit()
    conn.close()

    # Marcheaza quest-ul ca facut azi
    session[f'zuno_done_{uid}'] = today
    session[f'zuno_accepted_{uid}'] = False

    return jsonify({'ok': True, 'reward': 150})


@app.route('/joc/petomania/api/aventura/mulge', methods=['POST'])
@login_required
def api_aventura_mulge():
    import time
    from modules.inventory import inv_add
    user = get_current_user()
    uid  = int(user['id'])

    # Cooldown 5 minute per user
    cooldown_key = f'vaca_cooldown_{uid}'
    last_mulge = session.get(cooldown_key, 0)
    now = time.time()
    if now - last_mulge < 300:
        remaining = int(300 - (now - last_mulge))
        mins = remaining // 60
        secs = remaining % 60
        return jsonify({'ok': False, 'msg': f'⏳ Vaca are nevoie de odihnă. Mai așteaptă {mins}m {secs}s.'})

    session[cooldown_key] = now
    inv_add(uid, 'mancare', 'lapte', 1)
    return jsonify({'ok': True, 'msg': '🥛 Ai muls vaca și ai primit Lapte Proaspăt!'})


# ── PVP ───────────────────────────────────────────────────────────────────

@app.route('/joc/petomania/pvp/queue')
@login_required
def pvp_queue_page():
    return render_template('pvp_queue.html')


@app.route('/joc/petomania/pvp/battle/<int:match_id>')
@login_required
def pvp_battle_page(match_id):
    from modules.pvp import get_match
    user = get_current_user()
    uid  = int(user['id'])
    match = get_match(match_id)
    if not match or uid not in (match['player1_id'], match['player2_id']):
        return redirect(url_for('arena'))
    return render_template('pvp_battle.html', match_id=match_id)


@app.route('/joc/petomania/api/pvp/queue/join', methods=['POST'])
@login_required
def api_pvp_queue_join():
    from modules.pvp import queue_join
    from modules.loadout import get_loadout
    user = get_current_user()
    uid  = int(user['id'])
    body = request.json or {}
    size = int(body.get('size', 1))
    size = max(1, min(5, size))  # clamp 1-5

    # Construieste loadout snapshot
    # slot_1 = pet activ din tabela pets
    # slot_2..5 = menajerie din tabela loadout
    loadout = get_loadout(uid)
    conn = get_db()
    pets = []

    # Slot 1 — pet activ
    p = get_pet(uid)
    if p:
        p = dict(p)
        p['user_id'] = uid
        pets.append(p)

    # Slot 2-5 — menajerie
    for i in range(2, 6):
        pid = loadout.get(f'slot_{i}')
        if pid:
            row = conn.execute('SELECT * FROM menagerie WHERE id = ? AND user_id = ?', (pid, uid)).fetchone()
            if row:
                p = dict(row)
                p['user_id'] = uid
                pets.append(p)
    conn.close()
    slots = pets

    if not slots:
        return jsonify({'ok': False, 'error': 'Nu ai companioni în loadout.'})

    # Filtreaza petii cu HP 0
    slots = [p for p in slots if (p.get('hp_current') or 0) > 0]
    if not slots:
        return jsonify({'ok': False, 'error': 'Toți companionii tăi sunt KO! Vindecă-i la Biserică înainte de PvP.'})

    # Verifica ca are destui peti pentru formatul ales
    if len(slots) < size:
        return jsonify({'ok': False, 'error': f'Ai nevoie de cel puțin {size} companioni valizi pentru acest format.'})

    # Trimite doar primii `size` peti
    slots = slots[:size]

    result = queue_join(uid, slots, size)
    return jsonify({'ok': True, **result})


@app.route('/joc/petomania/api/pvp/queue/leave', methods=['POST'])
@login_required
def api_pvp_queue_leave():
    from modules.pvp import queue_leave
    user = get_current_user()
    queue_leave(int(user['id']))
    return jsonify({'ok': True})


@app.route('/joc/petomania/api/pvp/queue/poll')
@login_required
def api_pvp_queue_poll():
    from modules.pvp import queue_poll
    user = get_current_user()
    return jsonify(queue_poll(int(user['id'])))


@app.route('/joc/petomania/api/pvp/match/<int:match_id>/poll')
@login_required
def api_pvp_match_poll(match_id):
    from modules.pvp import poll_match
    user = get_current_user()
    return jsonify(poll_match(match_id, int(user['id'])))


@app.route('/joc/petomania/api/pvp/match/<int:match_id>/move', methods=['POST'])
@login_required
def api_pvp_match_move(match_id):
    from modules.pvp import submit_move
    user     = get_current_user()
    uid      = int(user['id'])
    data     = request.json or {}
    move_key = data.get('move_key')
    if not move_key:
        return jsonify({'ok': False, 'error': 'move_key lipsește.'})
    return jsonify(submit_move(match_id, uid, move_key))


@app.route('/joc/petomania/api/pvp/match/<int:match_id>/abandon', methods=['POST'])
@login_required
def api_pvp_match_abandon(match_id):
    from modules.pvp import abandon_match
    user = get_current_user()
    return jsonify(abandon_match(match_id, int(user['id'])))


@app.route('/joc/petomania/api/pvp/match/<int:match_id>/reward', methods=['POST'])
@login_required
def api_pvp_match_reward(match_id):
    from modules.pvp import grant_pvp_reward
    user = get_current_user()
    return jsonify(grant_pvp_reward(match_id, int(user['id'])))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5002, debug=False)

"""
modules/discord_helpers.py
Discord API helpers: get_member_roles, get_lady_interaction, build_lady_dialog.
"""
import os
import requests as req_lib
from modules.db import get_db
from modules.pets import get_pet, get_form

DISCORD_API    = 'https://discord.com/api/v10'
BOT_TOKEN      = os.getenv('TOKEN')
GUILD_ID       = os.getenv('GUILD_ID', '1499052609523986535')

ROLE_NEW       = '1499053171656495224'
ROLES_VETERAN  = ['1499053556383350945','1499053668769726617','1499053737178828991',
                  '1499053813414236270','1499053921459765479','1499053999436071053']
ROLES_CHAMPION = ['1511642120862302270','1500078293721022655']
ROLE_NAMES     = {
    '1499053556383350945': ('Explorator', '#71c9f8'),
    '1499053668769726617': ('Veteran',    '#5865f2'),
    '1499053737178828991': ('Erou',       '#57f287'),
    '1499053813414236270': ('Maestru',    '#fee75c'),
    '1499053921459765479': ('Legend',     '#f47fff'),
    '1499053999436071053': ('Mitic',      '#eb459e'),
    '1511642120862302270': ('Campion',    '#ffd700'),
    '1500078293721022655': ('Mare Campion','#ffd700'),
}


def get_member_roles(user_id: int) -> list:
    if not BOT_TOKEN or not GUILD_ID:
        return []
    try:
        url  = f"{DISCORD_API}/guilds/{GUILD_ID}/members/{user_id}"
        resp = req_lib.get(url, headers={'Authorization': f'Bot {BOT_TOKEN}'}, timeout=5)
        if resp.status_code == 200:
            return resp.json().get('roles', [])
    except Exception as e:
        print(f"⚠️ get_member_roles error: {e}")
    return []


def get_lady_interaction(user_id: int) -> dict:
    conn = get_db()
    row  = conn.execute('SELECT * FROM lady_interactions WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    if row:
        return {
            'first_interaction': row['first_interaction'],
            'player_name':       row['player_name'],
            'has_companicon':    row['has_companicon'],
        }
    return {'first_interaction': 1, 'player_name': None, 'has_companicon': 0}


def build_lady_dialog(uid: int, username: str) -> dict:
    """Construieste dialogul Lunarei in functie de rol si istoricul interactiunii."""
    interaction = get_lady_interaction(uid)
    first       = interaction['first_interaction']
    saved_name  = interaction['player_name']
    roles       = get_member_roles(uid)

    if not first:
        name = saved_name or username
        return {
            'variant':       'return',
            'text':          f'*Lunara Silvermist își ridică privirea dintr-o carte veche și îți zâmbește când te vede intrând pe ușa magazinului.*\nAh, {name}! Bine ai revenit la „Luna Argintie". Este o plăcere să te văd din nou în umilul meu magazin. Sper că drumul ți-a fost liniștit și că stelele ți-au fost favorabile de la ultima noastră întâlnire.\nSpune-mi, cu ce te pot ajuta astăzi?',
            'show_name_btn': False,
            'player_name':   name,
        }

    role_info = None
    for rid in ROLES_CHAMPION:
        if rid in roles:
            rdata = ROLE_NAMES.get(rid, ('Campion', '#ffd700'))
            role_info = {'id': rid, 'name': rdata[0], 'color': rdata[1], 'type': 'champion'}
            break
    if not role_info:
        for rid in ROLES_VETERAN:
            if rid in roles:
                rdata = ROLE_NAMES.get(rid, ('Veteran', '#5865f2'))
                role_info = {'id': rid, 'name': rdata[0], 'color': rdata[1], 'type': 'veteran'}
                break
    if not role_info and ROLE_NEW in roles:
        role_info = {'id': ROLE_NEW, 'name': 'Nou Venit', 'color': '#ffffff', 'type': 'new'}

    if role_info and role_info['type'] == 'champion':
        rname = role_info['name']
        text  = (
            f'*O femeie cu părul argintiu își ridică privirea dintre tomurile vechi și pare pregătită să te întâmpine ca pe un simplu călător. În clipa următoare, observă însemnele tale și face o reverență respectuoasă.*\n'
            f'Pe toate stelele ce veghează acest regat... te rog să-mi ierți neatenția. Pentru o clipă am crezut că am în față un nou venit, însă abia acum am observat titlul tău de {rname}.\n'
            f'Eu sunt Lunara Silvermist, păstrătoarea magazinului magic Luna Argintie. Faptele unui Campion răsună până și între aceste rafturi pline de artefacte și grimorii. Este o adevărată onoare să te primesc în pragul modestului meu magazin.\n'
            f'Dar spune-mi, sire... cum te numești?'
        )
        variant = 'champion'
    elif role_info and role_info['type'] == 'veteran':
        rname = role_info['name']
        text  = (
            f'*O femeie cu părul argintiu își ridică privirea dintre tomurile vechi și pare pregătită să te întâmpine ca pe un nou venit. După o clipă, observă însemnele rangului tău și își înclină respectuos capul.*\n'
            f'Ah... îmi cer scuze. Pentru o clipă am crezut că ești nou în Regat, însă abia acum am observat rangul tău de {rname}. Se pare că am în fața mea un aventurier cu experiență și renume.\n'
            f'Eu sunt Lunara Silvermist, păstrătoarea magazinului magic Luna Argintie. Este o onoare să te întâlnesc.\n'
            f'Spune-mi, cum te numești?'
        )
        variant = 'veteran'
    else:
        text    = '*O femeie cu părul argintiu își ridică privirea dintre tomurile vechi și îți oferă un zâmbet cald.*\nBine ai venit în Regat, călătorule. Eu sunt Lunara Silvermist, păstrătoarea magazinului magic „Luna Argintie". Nu cred că ne-am mai întâlnit până acum, așa că îți urez bun venit pe aceste meleaguri. Fie ca drumul tău să fie presărat cu aventuri, comori și povești vrednice de cronicile regatului.\nSpune-mi, cum te numești?'
        variant = 'new'
        role_info = {'color': '#ffffff'}

    return {
        'variant':       variant,
        'text':          text,
        'show_name_btn': True,
        'username':      username,
        'role_color':    role_info['color'] if role_info else '#ffffff',
    }


def build_lady_pet_text(uid: int, player_name: str) -> str:
    """Construieste textul dialogului cu petul."""
    p = get_pet(uid)
    if p:
        form    = get_form(p['level'])
        petcode = f"{p['species'].upper()}-{str(form).zfill(3)}"
        return (
            f'*Lunara Silvermist își mută privirea către companionul care te însoțește și zâmbește ușor.*\n'
            f'Ah, văd că nu călătorești singur, {player_name}. Ai un companion alături de tine. '
            f'Dacă nu mă înșel, este un {petcode}, nu-i așa?\n'
            f'*Își apropie privirea cu interes, studiind creatura.*\n'
            f'O alegere interesantă. Se vede că între voi există o legătură puternică.'
        )
    return (
        f'*Lunara Silvermist privește în jur cu curiozitate.*\n'
        f'Hmm, {player_name}... Nu văd niciun companion lângă tine. '
        f'Poate vei găsi unul curând pe aceste meleaguri.'
    )

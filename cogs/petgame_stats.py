# ─────────────────────────────────────────────
# petgame_stats.py
# Modul independent — stats de baza, crestere per nivel, modificatori natura.
# Nu importa nimic din bot — poate fi folosit si de un flash game.
# ─────────────────────────────────────────────

from cogs.petgame_natures import NATURES


# ─────────────────────────────────────────────
# BASE STATS LA NIVEL 1 (scara 1–100)
#
# Câine  / Pământ  — tanc:           HP mare, Apărare mare, Viteză mică
# Pisică Neagră / Umbră — assassin:  Atac mare, Eludare mare, HP mic
# Rață   / Apă    — balanced-speed:  Viteză mare, HP mediu, echilibrat
# Pisică / Lumină — suport:          Vindecare mare, HP mediu, Apărare medie
# ─────────────────────────────────────────────

BASE_STATS: dict[str, dict[str, int]] = {
    'dog': {
        'hp':       80,
        'attack':   50,
        'defense':  70,
        'speed':    30,
        'evasion':  20,
        'healing':  35,
        'control':  25,
        'reflection': 20,
    },
    'blackcat': {
        'hp':       40,
        'attack':   75,
        'defense':  35,
        'speed':    65,
        'evasion':  80,
        'healing':  20,
        'control':  40,
        'reflection': 30,
    },
    'duck': {
        'hp':       55,
        'attack':   50,
        'defense':  50,
        'speed':    75,
        'evasion':  50,
        'healing':  45,
        'control':  35,
        'reflection': 40,
    },
    'cat': {
        'hp':       55,
        'attack':   45,
        'defense':  55,
        'speed':    55,
        'evasion':  45,
        'healing':  70,
        'control':  40,
        'reflection': 50,
    },
    'rhino': {
        'hp':       85,
        'attack':   55,
        'defense':  80,
        'speed':    20,
        'evasion':  15,
        'healing':  30,
        'control':  20,
        'reflection': 35,
    },
    'fox': {
        'hp':       45,
        'attack':   70,
        'defense':  35,
        'speed':    70,
        'evasion':  60,
        'healing':  25,
        'control':  30,
        'reflection': 20,
    },
    'goldfish': {
        'hp':       40,
        'attack':   55,
        'defense':  40,
        'speed':    75,
        'evasion':  55,
        'healing':  35,
        'control':  45,
        'reflection': 30,
    },
    'verdian': {
        'hp':       50,
        'attack':   45,
        'defense':  55,
        'speed':    60,
        'evasion':  40,
        'healing':  40,
        'control':  50,
        'reflection': 35,
    },
    'toadisimo': {
        'hp':       70,
        'attack':   45,
        'defense':  60,
        'speed':    25,
        'evasion':  30,
        'healing':  50,
        'control':  65,
        'reflection': 30,
    },
}


# ─────────────────────────────────────────────
# CRESTERE PER NIVEL
# Valori adaugate la fiecare nivel castigat.
# ─────────────────────────────────────────────

STAT_GROWTH: dict[str, dict[str, float]] = {
    'dog': {
        'hp':         2.5,
        'attack':     1.2,
        'defense':    2.0,
        'speed':      0.6,
        'evasion':    0.4,
        'healing':    0.8,
        'control':    0.5,
        'reflection': 0.4,
    },
    'blackcat': {
        'hp':         1.0,
        'attack':     2.2,
        'defense':    0.8,
        'speed':      1.8,
        'evasion':    2.0,
        'healing':    0.4,
        'control':    1.0,
        'reflection': 0.6,
    },
    'duck': {
        'hp':         1.5,
        'attack':     1.3,
        'defense':    1.3,
        'speed':      2.0,
        'evasion':    1.2,
        'healing':    1.1,
        'control':    0.9,
        'reflection': 1.0,
    },
    'cat': {
        'hp':         1.5,
        'attack':     1.1,
        'defense':    1.4,
        'speed':      1.4,
        'evasion':    1.1,
        'healing':    1.8,
        'control':    1.0,
        'reflection': 1.2,
    },
    'rhino': {
        'hp':         2.8,
        'attack':     1.3,
        'defense':    2.5,
        'speed':      0.4,
        'evasion':    0.3,
        'healing':    0.7,
        'control':    0.4,
        'reflection': 0.8,
    },
    'fox': {
        'hp':         1.2,
        'attack':     2.0,
        'defense':    0.7,
        'speed':      1.9,
        'evasion':    1.6,
        'healing':    0.5,
        'control':    0.7,
        'reflection': 0.4,
    },
    'goldfish': {
        'hp':         2.0,
        'attack':     1.8,
        'defense':    1.0,
        'speed':      1.8,
        'evasion':    1.2,
        'healing':    0.8,
        'control':    1.0,
        'reflection': 0.8,
    },
    'verdian': {
        'hp':         1.8,
        'attack':     1.6,
        'defense':    1.8,
        'speed':      1.4,
        'evasion':    1.0,
        'healing':    1.0,
        'control':    1.4,
        'reflection': 1.0,
    },
    'toadisimo': {
        'hp':         2.4,
        'attack':     1.2,
        'defense':    2.0,
        'speed':      0.5,
        'evasion':    0.6,
        'healing':    1.5,
        'control':    2.0,
        'reflection': 0.8,
    },
}


# ─────────────────────────────────────────────
# MODIFICATORI DIN NATURA
# Multiplica stat-ul de baza al speciei.
# bonus_stat din NATURES primeste 1.25 — restul raman la 1.0
# exceptie: stat-ul opus primeste 0.85 (mica penalizare pentru flavour)
# ─────────────────────────────────────────────

# Stat opus — penalizare de flavour
_OPPOSITE_STAT: dict[str, str] = {
    'attack':     'defense',
    'defense':    'speed',
    'speed':      'defense',
    'hp':         'evasion',
    'evasion':    'hp',
    'healing':    'attack',
    'control':    'speed',
    'reflection': 'attack',
}

def _build_nature_modifiers() -> dict[str, dict[str, float]]:
    modifiers = {}
    for key, data in NATURES.items():
        bonus = data['bonus_stat']
        opposite = _OPPOSITE_STAT.get(bonus)
        mods = {stat: 1.0 for stat in BASE_STATS['dog']}  # toate staturile la 1.0
        mods[bonus] = 1.25
        if opposite:
            mods[opposite] = 0.85
        modifiers[key] = mods
    return modifiers

NATURE_MODIFIERS: dict[str, dict[str, float]] = _build_nature_modifiers()


# ─────────────────────────────────────────────
# MULTIPLICATORI FORMA (evolutie)
# Forma 1 = baza, Forma 2 = ×1.3, Forma 3 = ×1.6
# Adauga Forma 4 aici daca extinzi in viitor.
# ─────────────────────────────────────────────

FORM_MULTIPLIERS: dict[int, float] = {
    1: 1.0,
    2: 1.3,
    3: 1.6,
}


# ─────────────────────────────────────────────
# FUNCTII PUBLICE
# ─────────────────────────────────────────────

def get_stats_at_level(species: str, nature: str | None, level: int, form: int = 1) -> dict[str, int]:
    """
    Calculeaza stats-urile complete ale unui pet la un nivel si forma date.

    Args:
        species:  cheia speciei ('dog', 'cat', 'blackcat', 'duck')
        nature:   cheia naturii ('fire', 'earth', ...) sau None
        level:    nivelul petului (1–100)
        form:     forma evolutiva (1, 2, 3 — sau 4+ daca extinzi)

    Returns:
        Dict cu valorile finale ale fiecarui stat, rotunjite la int.
    """
    base = BASE_STATS.get(species)
    if not base:
        raise ValueError(f"Specie necunoscuta: {species}")

    growth = STAT_GROWTH.get(species, {})
    modifiers = NATURE_MODIFIERS.get(nature, {}) if nature else {}
    form_mult = FORM_MULTIPLIERS.get(form, 1.0)

    result = {}
    for stat, base_val in base.items():
        grown = base_val + growth.get(stat, 0) * (level - 1)
        modifier = modifiers.get(stat, 1.0)
        result[stat] = max(1, round(grown * modifier * form_mult))

    return result


def get_bonus_stat_name(nature: str) -> str | None:
    """Returneaza numele stat-ului bonus pentru o natura. None daca natura nu exista."""
    nat = NATURES.get(nature)
    return nat['bonus_stat'] if nat else None


def stat_summary(species: str, nature: str | None, level: int, form: int = 1) -> str:
    """
    Returneaza un string formatat cu stats-urile petului — util pentru embed Discord.
    """
    stats = get_stats_at_level(species, nature, level, form)
    lines = [
        f"❤️ HP: {stats['hp']}",
        f"⚔️ Atac: {stats['attack']}",
        f"🛡️ Apărare: {stats['defense']}",
        f"💨 Viteză: {stats['speed']}",
        f"🌀 Eludare: {stats['evasion']}",
        f"💚 Vindecare: {stats['healing']}",
        f"🔮 Control: {stats['control']}",
        f"💠 Reflecție: {stats['reflection']}",
    ]
    return '\n'.join(lines)

"""
modules/companicon.py
Companicon: sync_discovered, get_discovered, build_entries, _img_url.
"""
from cogs.petgame_config import SPECIES
from cogs.petgame_natures import NATURES
from modules.db import get_db
from modules.pets import get_form

GENDERED_SPECIES = {
    'blackcat':  [1, 2, 3],
    'dog':       [1, 2, 3],
    'duck':      [2, 3],
    'fox':       [2, 3],
    'rhino':     [2, 3],
    'toadisimo': [1, 2, 3],
    # goldfish, verdian — asexuate, nicio forma nu are gen
}


def _img_url(species, form, gender):
    if species in ('blackcat', 'dog', 'toadisimo'):
        suffix = 'Male' if gender == 'male' else 'Female'
        return f"/static/00transparent/{species}/Stage{form}-Basic-Form-{suffix}.png"
    elif species in ('duck', 'fox', 'rhino') and form > 1:
        suffix = 'Male' if gender == 'male' else 'Female'
        return f"/static/00transparent/{species}/Stage{form}-Basic-Form-{suffix}.png"
    else:
        return f"/static/00transparent/{species}/Stage{form}-Basic-Form.png"


def sync_companicon_discovered(user_id: int):
    conn = get_db()
    try:
        conn.execute('ALTER TABLE companicon_discovered ADD COLUMN gender TEXT NOT NULL DEFAULT "male"')
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_comp_disc ON companicon_discovered(user_id, species, form, gender)')
        conn.commit()
    except Exception:
        pass

    def insert(species, form, gender):
        conn.execute(
            'INSERT OR IGNORE INTO companicon_discovered (user_id, species, form, gender) VALUES (?,?,?,?)',
            (user_id, species, form, gender)
        )

    pet = conn.execute('SELECT species, level, gender FROM pets WHERE user_id = ?', (user_id,)).fetchone()
    if pet:
        for f in range(1, get_form(pet['level']) + 1):
            insert(pet['species'], f, pet['gender'])

    rows = conn.execute('SELECT species, level, gender FROM menagerie WHERE user_id = ?', (user_id,)).fetchall()
    for row in rows:
        for f in range(1, get_form(row['level']) + 1):
            insert(row['species'], f, row['gender'])

    conn.commit()
    conn.close()


def get_discovered(user_id: int) -> set:
    conn = get_db()
    rows = conn.execute(
        'SELECT species, form, gender FROM companicon_discovered WHERE user_id = ?', (user_id,)
    ).fetchall()
    conn.close()
    return {(r['species'], r['form'], r['gender']) for r in rows}


def build_companicon_entries(user_id: int) -> list:
    sync_companicon_discovered(user_id)
    discovered = get_discovered(user_id)
    entries = []
    for species_key, species_data in SPECIES.items():
        species_entries = species_data.get('entries', {})
        nature_key = species_data.get('available_natures', [None])[0]
        nat_data   = NATURES.get(nature_key, {}) if nature_key else {}
        gendered_forms = GENDERED_SPECIES.get(species_key, [])

        for form, entry_data in species_entries.items():
            has_gender = form in gendered_forms
            if has_gender:
                male_disc   = (species_key, form, 'male')   in discovered
                female_disc = (species_key, form, 'female') in discovered
                is_discovered = male_disc or female_disc
            else:
                is_discovered = (species_key, form, 'male') in discovered or (species_key, form, 'female') in discovered
                male_disc = female_disc = is_discovered

            entries.append({
                'species':           species_key,
                'species_name':      species_data['name'],
                'form':              form,
                'code':              entry_data['code'],
                'name':              entry_data['name'],
                'description':       entry_data['description'],
                'lore':              entry_data.get('lore', ''),
                'discovered':        is_discovered,
                'has_gender':        has_gender,
                'male_discovered':   male_disc,
                'female_discovered': female_disc,
                'img_url_male':      _img_url(species_key, form, 'male'),
                'img_url_female':    _img_url(species_key, form, 'female') if has_gender else None,
                'nature_name':       nat_data.get('name', ''),
                'nature_icon':       nat_data.get('icon', ''),
                'nature_color':      nat_data.get('color', '#ffffff'),
            })
    return entries

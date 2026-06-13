# ─────────────────────────────────────────────
# npc_names_config.py
# Nume NPC per natura pentru sistemul de battle.
# ─────────────────────────────────────────────

NPC_NAMES_BY_NATURE = {
    'fire': [
        'Jarok', 'Vulkar', 'Ignar', 'Pyrgon', 'Scorion',
        'Incendor', 'Flăcăruș', 'Magmaris', 'Cărbunel', 'Focar',
        'Emberon', 'Solkar', 'Lavaron', 'Fulgaris', 'Cinderox',
    ],
    'water': [
        'Nereon', 'Aqualis', 'Hydros', 'Valdor', 'Undaris',
        'Izvoran', 'Okeon', 'Murmur', 'Talmar', 'Rivoran',
        'Delphor', 'Aquiron', 'Marinus', 'Tideon', 'Coralis',
    ],
    'nature': [
        'Frunzar', 'Sylvan', 'Verdeon', 'Crengor', 'Florinox',
        'Arborel', 'Mossor', 'Lianor', 'Brumel', 'Stejaris',
        'Petalor', 'Vineris', 'Thornik', 'Rootar', 'Fernox',
    ],
    'earth': [
        'Granox', 'Petran', 'Bolgar', 'Stâncar', 'Terrak',
        'Rocmar', 'Munthor', 'Golemir', 'Cragor', 'Bouldor',
        'Cliffor', 'Basalor', 'Gravok', 'Stonek', 'Quarryx',
    ],
    'storm': [
        'Voltik', 'Fulgar', 'Scânteion', 'Zappor', 'Tunor',
        'Fulgor', 'Electris', 'Raykon', 'Stormik', 'Tempor',
        'Voltaris', 'Sparkon', 'Thundor', 'Zaptrix', 'Arcion',
    ],
    'ice': [
        'Glacior', 'Frigorn', 'Nivor', 'Cryon', 'Polarix',
        'Geron', 'Frozar', 'Albor', 'Brumar', 'Hibern',
        'Iceon', 'Snowrik', 'Frostal', 'Blizzardon', 'Chillor',
    ],
    'shadow': [
        'Umbros', 'Noctar', 'Tenebris', 'Morvax', 'Shadeon',
        'Corvix', 'Noxar', 'Umbrel', 'Duskor', 'Ravnok',
        'Shadowen', 'Grimor', 'Nightor', 'Vesperix', 'Crowdark',
    ],
    'crystal': [
        'Prismor', 'Crystar', 'Diamor', 'Shardon', 'Gemir',
        'Lustris', 'Quartzor', 'Opalon', 'Vitreon', 'Glimmer',
        'Crystalix', 'Jewelor', 'Sparkleon', 'Shimeris', 'Faceton',
    ],
    'steel': [
        'Ferron', 'Titanor', 'Oțelar', 'Cromar', 'Forgon',
        'Magnetor', 'Bronzar', 'Ironik', 'Metalis', 'Steelfang',
        'Alloyx', 'Rivetor', 'Gearon', 'Machinox', 'Ferrox',
    ],
    'light': [
        'Lumion', 'Solaris', 'Aurion', 'Radiant', 'Luxor',
        'Dawnor', 'Aurelis', 'Halion', 'Strălucis', 'Celestor',
        'Sunaris', 'Glorion', 'Beacon', 'Lumenor', 'Starion',
    ],
    'dragon': [
        'Balaur', 'Zmeor', 'Draconis', 'Ariptor', 'Solzmar',
        'Focbalaur', 'Cerbalaur', 'Umbrazmeu', 'Fulgerdrac', 'Zamdrake',
        'Strajdrac', 'Drahor', 'Solzar', 'Vârfdrac', 'Cronbalaur',
    ],
}

# Fallback generic daca natura nu e definita
NPC_NAMES_GENERIC = [
    'Jarok', 'Nereon', 'Frunzar', 'Granox', 'Voltik',
    'Glacior', 'Umbros', 'Prismor', 'Ferron', 'Lumion', 'Balaur',
]


def get_npc_name(nature: str = None) -> str:
    """Returneaza un nume random de NPC bazat pe natura."""
    import random
    names = NPC_NAMES_BY_NATURE.get(nature, NPC_NAMES_GENERIC)
    return random.choice(names)

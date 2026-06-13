# ─────────────────────────────────────────────
# petgame_config.py
# Adauga animale noi doar aici — fara sa modifici petgame_cog.py
# ─────────────────────────────────────────────

GITHUB_BASE = "https://raw.githubusercontent.com/keserdark/village-bot/main/PetGame/static/00transparent"

NATURES = {
    'fire': {
        'name': 'Foc', 'icon': '🔥', 'color': '#f97316',
        'flavor': 'Agresiv, energie înaltă, arde scurt și puternic.',
        'bonus_stat': 'Atac',
        'strong_against': ['nature', 'ice', 'steel', 'shadow'],
        'weak_against': ['water', 'earth', 'storm'],
        'vulnerable_to': ['water', 'earth'],
        'resists_from': ['fire', 'nature', 'ice', 'steel'],
        'immune_to': [], 'evo_line': ['Flăcărică', 'Ignar', 'Volcadon'],
    },
    'water': {
        'name': 'Apă', 'icon': '💧', 'color': '#3b82f6',
        'flavor': 'Adaptabil, rezistent, controlează fluxul luptei.',
        'bonus_stat': 'Viteză',
        'strong_against': ['fire', 'earth', 'crystal'],
        'weak_against': ['storm', 'nature'],
        'vulnerable_to': ['storm', 'nature'],
        'resists_from': ['fire', 'water', 'ice'],
        'immune_to': [], 'evo_line': ['Stropel', 'Curentix', 'Abismara'],
    },
    'nature': {
        'name': 'Natură', 'icon': '🌿', 'color': '#22c55e',
        'flavor': 'Răbdător, regenerativ, câștigă prin uzură.',
        'bonus_stat': 'Viață',
        'strong_against': ['water', 'earth', 'crystal'],
        'weak_against': ['fire', 'ice', 'shadow', 'storm'],
        'vulnerable_to': ['fire', 'ice'],
        'resists_from': ['water', 'earth', 'nature'],
        'immune_to': [], 'evo_line': ['Mugur', 'Florun', 'Dendrix'],
    },
    'earth': {
        'name': 'Pământ', 'icon': '🪨', 'color': '#a16207',
        'flavor': 'Stabil, apărare ridicată, lent dar implacabil.',
        'bonus_stat': 'Apărare',
        'strong_against': ['fire', 'storm', 'steel', 'shadow'],
        'weak_against': ['water', 'nature', 'ice'],
        'vulnerable_to': ['water', 'nature'],
        'resists_from': ['fire', 'steel', 'earth'],
        'immune_to': ['storm'], 'evo_line': ['Bolovan', 'Stânex', 'Tectoran'],
    },
    'storm': {
        'name': 'Furtună', 'icon': '⚡', 'color': '#eab308',
        'flavor': 'Rapid, imprevizibil, combo-uri electrizante.',
        'bonus_stat': 'Viteză',
        'strong_against': ['water', 'nature', 'steel'],
        'weak_against': ['earth', 'crystal'],
        'vulnerable_to': ['earth'],
        'resists_from': ['storm', 'fire', 'nature'],
        'immune_to': [], 'evo_line': ['Scânteiuț', 'Fulgeran', 'Tempestix'],
    },
    'ice': {
        'name': 'Gheață', 'icon': '❄️', 'color': '#67e8f9',
        'flavor': 'Control și lentire, răcește orice amenințare.',
        'bonus_stat': 'Control',
        'strong_against': ['nature', 'water', 'crystal', 'shadow'],
        'weak_against': ['fire', 'steel', 'storm'],
        'vulnerable_to': ['fire', 'steel'],
        'resists_from': ['ice', 'crystal'],
        'immune_to': [], 'evo_line': ['Fulgușor', 'Crionar', 'Glacidra'],
    },
    'shadow': {
        'name': 'Umbră', 'icon': '🌑', 'color': '#6d28d9',
        'flavor': 'Imprevizibil, misterios, evită atacuri cu abilități psihice.',
        'bonus_stat': 'Eludare',
        'strong_against': ['crystal', 'storm', 'fire'],
        'weak_against': ['nature', 'earth', 'light'],
        'vulnerable_to': ['light', 'nature'],
        'resists_from': ['shadow', 'storm', 'fire'],
        'immune_to': ['crystal'], 'evo_line': ['Penumbrix', 'Obscuran', 'Voidmara'],
    },
    'crystal': {
        'name': 'Cristal', 'icon': '💎', 'color': '#c084fc',
        'flavor': 'Echilibrat, versatil, reflectă o parte din daune.',
        'bonus_stat': 'Reflecție',
        'strong_against': ['shadow', 'ice', 'storm'],
        'weak_against': ['fire', 'water', 'nature'],
        'vulnerable_to': ['fire', 'nature'],
        'resists_from': ['crystal', 'shadow', 'ice'],
        'immune_to': [], 'evo_line': ['Schijă', 'Prismax', 'Gemalodon'],
    },
    'steel': {
        'name': 'Metal', 'icon': '⚙️', 'color': '#94a3b8',
        'flavor': 'Tanc pur, rezistențe multiple, daune constante.',
        'bonus_stat': 'Apărare',
        'strong_against': ['ice', 'crystal', 'nature'],
        'weak_against': ['fire', 'earth', 'storm'],
        'vulnerable_to': ['fire', 'earth'],
        'resists_from': ['steel', 'ice', 'crystal', 'nature', 'shadow'],
        'immune_to': [], 'evo_line': ['Bolțar', 'Fierotex', 'Ferromax'],
    },
    'light': {
        'name': 'Lumină', 'icon': '✨', 'color': '#fbbf24',
        'flavor': 'Suport și vindecare, contracarează Umbra.',
        'bonus_stat': 'Vindecare',
        'strong_against': ['shadow', 'ice', 'crystal'],
        'weak_against': ['earth', 'steel'],
        'vulnerable_to': ['shadow', 'earth'],
        'resists_from': ['light', 'fire', 'nature'],
        'immune_to': [], 'evo_line': ['Licarix', 'Auroraan', 'Radioss'],
    },
    'dragon': {
        'name': 'Dragon', 'icon': '🐉', 'color': '#dc2626',
        'flavor': 'Primordial, devastator, descendent din cei mai vechi stăpâni ai lumii.',
        'bonus_stat': 'Atac',
        'strong_against': ['nature', 'steel', 'earth', 'water'],
        'weak_against': ['ice', 'crystal'],
        'vulnerable_to': ['ice', 'crystal'],
        'resists_from': ['fire', 'nature', 'steel'],
        'immune_to': ['fire'], 'evo_line': ['Drakling', 'Draconix', 'Drakonar'],
    },
}

# ─────────────────────────────────────────────
# SPECII
# ─────────────────────────────────────────────

SPECIES = {
    'cat': {
        'starter': True,
        'name': 'Pisică', 'emoji': '🐱', 'button_label': '🐱 Pisică',
        'codes': {1: 'CAT-001', 2: 'CAT-002', 3: 'CAT-003'},
        'available_natures': ['light'],
        'entries': {
            1: {
                'code': 'CAT-001',
                'name': 'Pisicuță',
                'description': 'O pisică tânără, curioasă și plină de energie. Prima formă a companionului de lumină.',
                'lore': 'Acesta este unul din companionii îmblânziți de regat, prin artele magice ale acestora, o pisică simplă poate evolua în forme neașteptate.\n\nAgilă, inteligentă și loială, această mică felină este mai mult decât un simplu prieten de drum. Are un simț aparte pentru magie și un instinct protector puternic față de partenerul său.\n\nDeși la început pare doar o pisică obișnuită, cu timpul își poate dezvolta abilități unice, influențate de legătura sa cu stăpânul și de experiențele trăite împreună.',
            },
            2: {
                'code': 'CAT-002',
                'name': 'Pisică',
                'description': 'Pisica a crescut și a câștigat mai multă forță. Legătura cu natura luminii devine mai puternică.',
                'lore': 'Odată o simplă pisică, acum o ființă atinsă de magia Luminii.\n\nAcesta este unul dintre companionii îmblânziți de Regat. Prin artele magice ale acestora, o pisică obișnuită poate evolua în forme neașteptate.\n\nLoială și curajoasă, își însoțește stăpânul în aventurile sale, iar puterea sa continuă să crească odată cu legătura dintre ei.',
            },
            3: {
                'code': 'CAT-003',
                'name': 'Pisică Înțeleaptă',
                'description': 'Forma finală a pisicii de lumină. O creatură maiestuoasă cu puteri de vindecare extraordinare.',
                'lore': 'O ființă legendară, întruchiparea supremă a Luminii și a legăturii dintre companion și stăpân.\n\nAcesta este unul dintre companionii îmblânziți de Regat. Prin artele magice ale acestora, o simplă pisică poate evolua în forme de neimaginat.\n\nAripile sale strălucitoare și aura sa cerească sunt pomenite în vechile cronici ale Regatului.',
            },
        },
        'images': {
            1: {
                'Basic':  f'{GITHUB_BASE}/cat/Stage1-Basic-Form.png',
                'Hungry': f'{GITHUB_BASE}/cat/Stage1-Hungry-Form.png',
                'Dirty':  f'{GITHUB_BASE}/cat/Stage1-Dirty-Form.png',
                'Sad':    f'{GITHUB_BASE}/cat/Stage1-Sad-Form.png',
                'Sleep':  f'{GITHUB_BASE}/cat/Stage1-Sleep-Form.png',
            },
            2: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/cat/Stage2-Basic-Form.png',
                    'Hungry': f'{GITHUB_BASE}/cat/Stage2-Hungry-Form.png',
                    'Dirty':  f'{GITHUB_BASE}/cat/Stage2-Dirty-Form.png',
                    'Sad':    f'{GITHUB_BASE}/cat/Stage2-Sad-Form.png',
                    'Sleep':  f'{GITHUB_BASE}/cat/Stage2-Sleep-Form.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/cat/Stage2-Basic-Form.png',
                    'Hungry': f'{GITHUB_BASE}/cat/Stage2-Hungry-Form.png',
                    'Dirty':  f'{GITHUB_BASE}/cat/Stage2-Dirty-Form.png',
                    'Sad':    f'{GITHUB_BASE}/cat/Stage2-Sad-Form.png',
                    'Sleep':  f'{GITHUB_BASE}/cat/Stage2-Sleep-Form.png',
                },
            },
            3: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/cat/Stage3-Basic-Form.png',
                    'Hungry': f'{GITHUB_BASE}/cat/Stage3-Hungry-Form.png',
                    'Dirty':  f'{GITHUB_BASE}/cat/Stage3-Dirty-Form.png',
                    'Sad':    f'{GITHUB_BASE}/cat/Stage3-Sad-Form.png',
                    'Sleep':  f'{GITHUB_BASE}/cat/Stage3-Sleep-Form.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/cat/Stage3-Basic-Form.png',
                    'Hungry': f'{GITHUB_BASE}/cat/Stage3-Hungry-Form.png',
                    'Dirty':  f'{GITHUB_BASE}/cat/Stage3-Dirty-Form.png',
                    'Sad':    f'{GITHUB_BASE}/cat/Stage3-Sad-Form.png',
                    'Sleep':  f'{GITHUB_BASE}/cat/Stage3-Sleep-Form.png',
                },
            },
        }
    },

    'duck': {
        'starter': True,
        'name': 'Rață', 'emoji': '🦆', 'button_label': '🦆 Rață',
        'codes': {1: 'DUCK-001', 2: 'DUCK-002', 3: 'DUCK-003'},
        'available_natures': ['water'],
        'entries': {
            1: {
                'code': 'DUCK-001',
                'name': 'Boboc',
                'description': 'Un boboc simpatic care abia a descoperit apa. Natura sa de Apă îl face un înotător natural.',
                'lore': 'O rățușcă tânără, curioasă și plină de energie. Prima formă a acestui companion de Apă.\n\nAcesta este unul dintre companionii îmblânziți de Regat. Prin artele magice ale acestora, o simplă rățușcă poate evolua în forme neașteptate.\n\nJucăușă și prietenoasă, își urmează stăpânul oriunde, plutind cu grație și aducând noroc în călătorii.',
            },
            2: {
                'code': 'DUCK-002',
                'name': 'Rățușcă',
                'description': 'A crescut și stăpânește acum curenții de apă cu ușurință. Diferențe clare între mascul și femelă.',
                'lore': 'Diferențele între mascul și femelă devin vizibile în această formă. Amândoi stăpânesc curenții de apă cu o ușurință fascinantă.\n\nPoate crea scuturi de apă și poate accelera vindecarea aliaților prin contact cu apa purificată de magia sa.',
            },
            3: {
                'code': 'DUCK-003',
                'name': 'Rață Maestră',
                'description': 'Forma finală. Controlează apa cu precizie extraordinară și poate prezice furtunile viitoare.',
                'lore': 'Maestrul apelor a atins forma sa perfectă. Poate controla precipitațiile într-o rază largă și prezice furtunile cu zile înainte.\n\nÎn luptă, creează torente devastatoare. În pace, poate purifica otrăvurile și tămădui răni grave prin puterea apei sacre pe care o canalizează.',
            },
        },
        'images': {
            1: {
                'Basic':  f'{GITHUB_BASE}/duck/Stage1-Basic-Form.png',
                'Hungry': f'{GITHUB_BASE}/duck/Stage1-Hungry-Form.png',
                'Dirty':  f'{GITHUB_BASE}/duck/Stage1-Dirty-Form.png',
                'Sad':    f'{GITHUB_BASE}/duck/Stage1-Sad-Form.png',
                'Sleep':  f'{GITHUB_BASE}/duck/Stage1-Sleep-Form.png',
            },
            2: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/duck/Stage2-Basic-Form-Male.png',
                    'Hungry': f'{GITHUB_BASE}/duck/Stage2-Hungry-Form-Male.png',
                    'Dirty':  f'{GITHUB_BASE}/duck/Stage2-Dirty-Form-Male.png',
                    'Sad':    f'{GITHUB_BASE}/duck/Stage2-Sad-Form-Male.png',
                    'Sleep':  f'{GITHUB_BASE}/duck/Stage2-Sleep-Form-Male.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/duck/Stage2-Basic-Form-Female.png',
                    'Hungry': f'{GITHUB_BASE}/duck/Stage2-Hungry-Form-Female.png',
                    'Dirty':  f'{GITHUB_BASE}/duck/Stage2-Dirty-Form-Female.png',
                    'Sad':    f'{GITHUB_BASE}/duck/Stage2-Sad-Form-Female.png',
                    'Sleep':  f'{GITHUB_BASE}/duck/Stage2-Sleep-Form-Female.png',
                },
            },
            3: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/duck/Stage3-Basic-Form-Male.png',
                    'Hungry': f'{GITHUB_BASE}/duck/Stage3-Hungry-Form-Male.png',
                    'Dirty':  f'{GITHUB_BASE}/duck/Stage3-Dirty-Form-Male.png',
                    'Sad':    f'{GITHUB_BASE}/duck/Stage3-Sad-Form-Male.png',
                    'Sleep':  f'{GITHUB_BASE}/duck/Stage3-Sleep-Form-Male.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/duck/Stage3-Basic-Form-Female.png',
                    'Hungry': f'{GITHUB_BASE}/duck/Stage3-Hungry-Form-Female.png',
                    'Dirty':  f'{GITHUB_BASE}/duck/Stage3-Dirty-Form-Female.png',
                    'Sad':    f'{GITHUB_BASE}/duck/Stage3-Sad-Form-Female.png',
                    'Sleep':  f'{GITHUB_BASE}/duck/Stage3-Sleep-Form-Female.png',
                },
            },
        }
    },

    'blackcat': {
        'starter': True,
        'name': 'Pisică Neagră', 'emoji': '🐱', 'button_label': '🐱 Pisică Neagră',
        'codes': {1: 'BLACKCAT-001', 2: 'BLACKCAT-002', 3: 'BLACKCAT-003'},
        'available_natures': ['shadow'],
        'entries': {
            1: {
                'code': 'BLACKCAT-001',
                'name': 'Pisicuță Neagră',
                'description': 'O pisică neagră misterioasă cu ochi ce strălucesc în întuneric. Natura Umbrei o face greu de detectat.',
                'lore': 'Născută din umbra lunii pline, această pisică poartă în ea secretele nopții. Ochii săi văd dincolo de aparențe, detectând magia ascunsă și intențiile ascunse ale celor din jur.\n\nEste tăcută, imprevizibilă și extrem de inteligentă. Aleargă prin umbre fără să lase urme și poate deveni aproape invizibilă în întuneric.',
            },
            2: {
                'code': 'BLACKCAT-002',
                'name': 'Pisică Neagră',
                'description': 'Stăpânește umbrele cu abilitate crescută. Se mișcă fără zgomot și poate dispărea din priviri.',
                'lore': 'Umbrele ascultă acum de voința sa. Poate crea iluzii întunecate și poate teleporta scurte distanțe prin umbra sa.\n\nPartenerii săi beneficiază de camuflaj în luptă, iar dușmanii se trezesc derutați de umbrele care par să se miște de unele singure.',
            },
            3: {
                'code': 'BLACKCAT-003',
                'name': 'Pisică Umbrelor',
                'description': 'Forma supremă a umbrei feline. Poate traversa întunericul și este imună la atacurile de cristal.',
                'lore': 'A atins forma în care granița dintre lumea fizică și tărâmul umbrelor devine fluidă. Poate traversa pereți prin umbra lor și este complet imună la atacurile de cristal.\n\nSe spune că această pisică poate chiar să fure umbrele dușmanilor, lăsându-i complet dezorientați și lipsiți de instinct de luptă.',
            },
        },
        'images': {
            1: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/blackcat/Stage1-Basic-Form-Male.png',
                    'Hungry': f'{GITHUB_BASE}/blackcat/Stage1-Hungry-Form-Male.png',
                    'Dirty':  f'{GITHUB_BASE}/blackcat/Stage1-Dirty-Form-Male.png',
                    'Sad':    f'{GITHUB_BASE}/blackcat/Stage1-Sad-Form-Male.png',
                    'Sleep':  f'{GITHUB_BASE}/blackcat/Stage1-Sleep-Form-Male.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/blackcat/Stage1-Basic-Form-Female.png',
                    'Hungry': f'{GITHUB_BASE}/blackcat/Stage1-Hungry-Form-Female.png',
                    'Dirty':  f'{GITHUB_BASE}/blackcat/Stage1-Dirty-Form-Female.png',
                    'Sad':    f'{GITHUB_BASE}/blackcat/Stage1-Sad-Form-Female.png',
                    'Sleep':  f'{GITHUB_BASE}/blackcat/Stage1-Sleep-Form-Female.png',
                },
            },
            2: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/blackcat/Stage2-Basic-Form-Male.png',
                    'Hungry': f'{GITHUB_BASE}/blackcat/Stage2-Hungry-Form-Male.png',
                    'Dirty':  f'{GITHUB_BASE}/blackcat/Stage2-Dirty-Form-Male.png',
                    'Sad':    f'{GITHUB_BASE}/blackcat/Stage2-Sad-Form-Male.png',
                    'Sleep':  f'{GITHUB_BASE}/blackcat/Stage2-Sleep-Form-Male.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/blackcat/Stage2-Basic-Form-Female.png',
                    'Hungry': f'{GITHUB_BASE}/blackcat/Stage2-Hungry-Form-Female.png',
                    'Dirty':  f'{GITHUB_BASE}/blackcat/Stage2-Dirty-Form-Female.png',
                    'Sad':    f'{GITHUB_BASE}/blackcat/Stage2-Sad-Form-Female.png',
                    'Sleep':  f'{GITHUB_BASE}/blackcat/Stage2-Sleep-Form-Female.png',
                },
            },
            3: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/blackcat/Stage3-Basic-Form-Male.png',
                    'Hungry': f'{GITHUB_BASE}/blackcat/Stage3-Hungry-Form-Male.png',
                    'Dirty':  f'{GITHUB_BASE}/blackcat/Stage3-Dirty-Form-Male.png',
                    'Sad':    f'{GITHUB_BASE}/blackcat/Stage3-Sad-Form-Male.png',
                    'Sleep':  f'{GITHUB_BASE}/blackcat/Stage3-Sleep-Form-Male.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/blackcat/Stage3-Basic-Form-Female.png',
                    'Hungry': f'{GITHUB_BASE}/blackcat/Stage3-Hungry-Form-Female.png',
                    'Dirty':  f'{GITHUB_BASE}/blackcat/Stage3-Dirty-Form-Female.png',
                    'Sad':    f'{GITHUB_BASE}/blackcat/Stage3-Sad-Form-Female.png',
                    'Sleep':  f'{GITHUB_BASE}/blackcat/Stage3-Sleep-Form-Female.png',
                },
            },
        }
    },

    'dog': {
        'starter': True,
        'name': 'Câine', 'emoji': '🐶', 'button_label': '🐶 Câine',
        'codes': {1: 'DOG-001', 2: 'DOG-002', 3: 'DOG-003'},
        'available_natures': ['earth'],
        'entries': {
            1: {
                'code': 'DOG-001',
                'name': 'Cățeluș',
                'description': 'Un cățeluș loial și energic. Natura Pământului îi conferă o rezistență naturală la atacuri.',
                'lore': 'Cel mai loial dintre toți companionii, cățelușul de pământ este primul ales de mulți aventurieri. Energia sa este inepuizabilă, iar devotamentul față de stăpân este absolut.\n\nChiar și în această formă timpurie, pielea sa absoarbe loviturile cu o rezistență surprinzătoare, iar lătratele sale pot speria inamicii mai slabi.',
            },
            2: {
                'code': 'DOG-002',
                'name': 'Câine',
                'description': 'A crescut și a câștigat forță considerabilă. Un protector devotat cu apărare ridicată.',
                'lore': 'Acum un protector de temut, câinele de pământ poate crea bariere de piatră și pământ pentru a-și apăra stăpânul.\n\nForța sa fizică a crescut exponențial, iar mușcătura sa poate zdrobi armuri ușoare. Loialitatea sa transformă fiecare bătălie într-o misiune personală.',
            },
            3: {
                'code': 'DOG-003',
                'name': 'Câine Guardian',
                'description': 'Forma finală a gardianului de pământ. Imun la furtuni și capabil să respingă atacuri puternice.',
                'lore': 'Gardianul suprem al regatului. Această formă finală transformă câinele într-o fortăreață vie, imună la furtuni și capabilă să absoarbă atacuri magice puternice.\n\nPoare convoca terenul însuși în apărarea stăpânului, ridicând ziduri de piatră și creând cutremure locale. Un Câine Guardian lângă tine înseamnă că nu ești niciodată singur în fața pericolului.',
            },
        },
        'images': {
            1: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/dog/Stage1-Basic-Form-Male.png',
                    'Hungry': f'{GITHUB_BASE}/dog/Stage1-Hungry-Form-Male.png',
                    'Dirty':  f'{GITHUB_BASE}/dog/Stage1-Dirty-Form-Male.png',
                    'Sad':    f'{GITHUB_BASE}/dog/Stage1-Sad-Form-Male.png',
                    'Sleep':  f'{GITHUB_BASE}/dog/Stage1-Sleep-Form-Male.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/dog/Stage1-Basic-Form-Female.png',
                    'Hungry': f'{GITHUB_BASE}/dog/Stage1-Hungry-Form-Female.png',
                    'Dirty':  f'{GITHUB_BASE}/dog/Stage1-Dirty-Form-Female.png',
                    'Sad':    f'{GITHUB_BASE}/dog/Stage1-Sad-Form-Female.png',
                    'Sleep':  f'{GITHUB_BASE}/dog/Stage1-Sleep-Form-Female.png',
                },
            },
            2: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/dog/Stage2-Basic-Form-Male.png',
                    'Hungry': f'{GITHUB_BASE}/dog/Stage2-Hungry-Form-Male.png',
                    'Dirty':  f'{GITHUB_BASE}/dog/Stage2-Dirty-Form-Male.png',
                    'Sad':    f'{GITHUB_BASE}/dog/Stage2-Sad-Form-Male.png',
                    'Sleep':  f'{GITHUB_BASE}/dog/Stage2-Sleep-Form-Male.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/dog/Stage2-Basic-Form-Female.png',
                    'Hungry': f'{GITHUB_BASE}/dog/Stage2-Hungry-Form-Female.png',
                    'Dirty':  f'{GITHUB_BASE}/dog/Stage2-Dirty-Form-Female.png',
                    'Sad':    f'{GITHUB_BASE}/dog/Stage2-Sad-Form-Female.png',
                    'Sleep':  f'{GITHUB_BASE}/dog/Stage2-Sleep-Form-Female.png',
                },
            },
            3: {
                'male': {
                    'Basic':  f'{GITHUB_BASE}/dog/Stage3-Basic-Form-Male.png',
                    'Hungry': f'{GITHUB_BASE}/dog/Stage3-Hungry-Form-Male.png',
                    'Dirty':  f'{GITHUB_BASE}/dog/Stage3-Dirty-Form-Male.png',
                    'Sad':    f'{GITHUB_BASE}/dog/Stage3-Sad-Form-Male.png',
                    'Sleep':  f'{GITHUB_BASE}/dog/Stage3-Sleep-Form-Male.png',
                },
                'female': {
                    'Basic':  f'{GITHUB_BASE}/dog/Stage3-Basic-Form-Female.png',
                    'Hungry': f'{GITHUB_BASE}/dog/Stage3-Hungry-Form-Female.png',
                    'Dirty':  f'{GITHUB_BASE}/dog/Stage3-Dirty-Form-Female.png',
                    'Sad':    f'{GITHUB_BASE}/dog/Stage3-Sad-Form-Female.png',
                    'Sleep':  f'{GITHUB_BASE}/dog/Stage3-Sleep-Form-Female.png',
                },
            },
        }
    },

    'rhino': {
        'starter': False,
        'name': 'Rinocer', 'emoji': '🦏', 'button_label': '🦏 Rinocer',
        'codes': {1: 'RHINO-001', 2: 'RHINO-002', 3: 'RHINO-003'},
        'available_natures': ['steel'],
        'entries': {
            1: {
                'code': 'RHINO-001',
                'name': 'Ferrok',
                'description': 'Un pui de rinocer cu pielea deja acoperită de plăci metalice rudimentare. Lent, dar de neclintit.',
                'lore': 'Ferrok este prima formă a rinocerului de Metal — o creatură care pare fragilă la prima vedere, dar ale cărei plăci metalice cresc odată cu ea.\n\nSe spune că rinocerii de Metal s-au format în adâncurile minelor părăsite ale Regnum Dacorum, acolo unde fierul și viața s-au contopit în secole de întuneric.\n\nFerrok nu fuge niciodată. Nu pentru că nu poate — ci pentru că nu vede niciun motiv să o facă.',
            },
            2: {
                'code': 'RHINO-002',
                'name': 'Titanok',
                'description': 'Plăcile metalice s-au extins și întărit. Titanok este o forță a naturii — lent, dar aproape imposibil de doborât.',
                'lore': 'Titanok marchează transformarea din pui în luptător. Coarnele sale au acum un miez de oțel pur, iar pașii săi lasă urme adânci în piatră.\n\nÎn tradiția dacică, un Titanok care te urmează înseamnă că ai câștigat respectul munților înșiși.\n\nDiferențele dintre mascul și femelă devin clare — masculul are plăci mai groase și colțuri ascuțite, femela are o armură mai suplă, dar la fel de rezistentă.',
            },
            3: {
                'code': 'RHINO-003',
                'name': 'Golemrhon',
                'description': 'Forma finală. Un colos de metal viu care poate rezista la orice atac și zdrobi orice obstacol din calea sa.',
                'lore': 'Golemrhon este legendă în Regnum Dacorum. Se spune că doar trei au existat vreodată, și că fiecare a schimbat cursul unei bătălii majore.\n\nArmura sa completă nu mai e simplă piele — e un aliaj viu care se repară singur, absorb loviturile și le transformă în putere.\n\nZamolxe ar fi spus că Golemrhon nu este un animal, ci un principiu — ideea că rezistența absolută este ea însăși o formă de înțelepciune.',
            },
        },
    },

    'fox': {
        'starter': False,
        'name': 'Vulpe', 'emoji': '🦊', 'button_label': '🦊 Vulpe',
        'codes': {1: 'FOX-001', 2: 'FOX-002', 3: 'FOX-003'},
        'available_natures': ['fire'],
        'entries': {
            1: {
                'code': 'FOX-001',
                'name': 'Vixar',
                'description': 'O vulpiță tânără cu blana roșie ca flacăra. Natura sa de Foc o face imprevizibilă și iute.',
                'lore': 'Vixar este prima formă a vulpii de Foc — o creatură mică, dar cu o energie arzătoare în privire.\n\nSe spune că vulpile de Foc s-au născut din scânteile unui incendiu de pădure care a durat trei zile și trei nopți. Supraviețuitorii acelui foc au ieșit schimbați, cu blana de culoarea jarului și ochii strălucind ca tăciunele.\n\nVixar este jucăuș și curios, dar temperamentul său se aprinde rapid. Un companion loial pentru cei care îi câștigă încrederea.',
            },
            2: {
                'code': 'FOX-002',
                'name': 'Foxar',
                'description': 'Vulpea a crescut și stăpânește acum flăcările cu pricepere. Blana sa arde cu nuanțe de portocaliu și roșu.',
                'lore': 'În forma a doua, Foxar devine un hunter redutabil. Cozile sale emit căldură perceptibilă, iar urmele sale lasă pâraie de scântei pe pământ.\n\nVulpile Foxar sunt respectate în regat ca mesageri ai Soarelui. Unii spun că pot vedea destinul în flăcările pe care le invocă.\n\nDiferențele dintre mascul și femelă devin vizibile — masculul are blana mai închisă, femela strălucește cu flăcări alb-aurii.',
            },
            3: {
                'code': 'FOX-003',
                'name': 'Emberfox',
                'description': 'Forma finală a vulpii de Foc. O creatură legendară cu cozi de flăcări, temută și respectată în egală măsură.',
                'lore': 'Emberfox este o legendă vie în regat. Forma sa finală se atinge doar după ani de luptă și devotament față de stăpân.\n\nSe spune că apariția unui Emberfox anunță schimbări mari — fie victoria absolută, fie o catastrofă de proporții. Flăcările pure care o înconjoară reprezintă fiecare luptă câștigată.\n\nZamolxe însuși ar fi binecuvântat prima vulpe de Foc, dăruindu-i nemurirea prin flacără. Emberfox nu moare — se transformă în scântei și renaște din propria cenușă.',
            },
        },
    },

    'goldfish': {
        'starter': False,
        'name': 'Peștișor', 'emoji': '🐟', 'button_label': '🐟 Peștișor',
        'codes': {1: 'GOLD-001', 2: 'GOLD-002', 3: 'GOLD-003'},
        'available_natures': ['water', 'dragon'],
        'entries': {
            1: {
                'code': 'GOLD-001',
                'name': 'Aurel',
                'description': 'Un peștișor auriu nevinovat, înoată fericit în bolul său. Nimeni nu bănuiește ce putere doarme în el.',
                'lore': 'Aurel este o enigmă printre companioni. La prima vedere e un simplu peștișor auriu — ochii mari, înotătoare delicate, mișcări line ca apa liniștită.\n\nSe spune că peștișorii de aur sunt urmașii dragonilor marini primordiali care au ales să se retragă în adâncuri, luând forma cea mai mică și umilă pentru a nu fi vânați.\n\nCei care îl aleg ca starter sunt considerați fie nebuni, fie înzestrați cu o intuiție ieșită din comun. Aurel nu impresionează — deocamdată.',
            },
            2: {
                'code': 'GOLD-002',
                'name': 'Koishar',
                'description': 'Transformarea a început. Solzii aurului s-au întărit, înotătoarele s-au extins, iar în ochi arde o flacără albastră.',
                'lore': 'Koishar marchează trezirea — momentul în care peștișorul banal începe să-și amintească ce a fost cândva.\n\nSolzii săi reflectă lumina în pattern-uri care seamănă cu scrierile dragonice vechi. Magicienii curții au confirmat că aceste pattern-uri nu sunt decorative — sunt rune vii.\n\nKoishar poate supraviețui în afara apei pentru perioade scurte, iar valurile de energie pe care le emite pot fi simțite de companioanele din jur. Este asexuat — forma sa transcende orice categorie.',
            },
            3: {
                'code': 'GOLD-003',
                'name': 'Dracaurul',
                'description': 'Transformarea completă. Dragonul marin primordial s-a trezit — solzi de aur și abis, puterea apei și a dragonului unite.',
                'lore': 'Dracaurul este una dintre cele mai rare și mai temute creaturi din Regnum Dacorum. Forma sa finală combină grația peștilor cu devastarea dragonilor marini.\n\nSe spune că apariția unui Dracaurul anunță fie o mare furtună pe mare, fie nașterea unui nou erou în regat. Nu există cale de mijloc.\n\nZamolxe ar fi spus că Dracaurul nu aparține nici lumii de sus, nici celei de jos — el este puntea dintre Apă și Dragon, dintre origine și destin. Cei care îl dețin poartă o responsabilitate pe care puțini o înțeleg.',
            },
        },
    },

    'verdian': {
        'starter': False,
        'name': 'Verdian', 'emoji': '🐟', 'button_label': '🐟 Verdian',
        'codes': {1: 'VERD-001', 2: 'VERD-002', 3: 'VERD-003'},
        'available_natures': ['water'],
        'entries': {
            1: {
                'code': 'VERD-001',
                'name': 'Verdian',
                'description': 'Un pește verde de apă dulce, simplu și neremarcabil. Înoată liniștit prin apele Regnum Dacorum.',
                'lore': 'Verdian este cel mai comun pește din apele dulci ale regatului. Nimeni nu îl vânează, nimeni nu îl caută — și tocmai de aceea a supraviețuit atâtea secole.\n\nSe spune că Verdian a trăit în aceleași râuri înainte ca Regnum Dacorum să existe. Nu are ambiții, nu are dușmani, nu are legende.\n\nDar cei care îl privesc îndelung în ochi spun că ascunde ceva — o liniște prea adâncă pentru un pește atât de mic.',
            },
            2: {
                'code': 'VERD-002',
                'name': 'Verdian Furtunii',
                'description': 'Apele l-au schimbat. Solzii au căpătat o strălucire ciudată, iar curenții par să-l urmeze.',
                'lore': 'Nu toți Verdian evoluează. Cei care o fac au petrecut ani întregi în apele subterane ale regatului, acolo unde curenții au memorie și apa cântă în frecvențe pe care urechea umană nu le poate auzi.\n\nVerdian Furtunii nu mai e pește comun. Solzii săi emit o luminescență slabă la adâncime, iar prezența sa calmează alte creaturi acvatice.\n\nMagicienii curții l-au studiat și au concluzionat că evoluția sa e legată de un fenomen inexplicabil: apa din jurul lui are altă compoziție.',
            },
            3: {
                'code': 'VERD-003',
                'name': 'Aquarion',
                'description': 'Forma finală. Un războinic al apelor cu armură vie și trident cristalizat — gardianul râurilor regatului.',
                'lore': 'Aquarion este o anomalie. Nimeni nu știe când a apărut primul, nimeni nu a documentat transformarea completă.\n\nCe se știe: Aquarion poartă o armură formată din solzi cristalizați de-a lungul deceniilor, iar tridentul său nu e o armă — e o extensie a corpului, format din minerale dizolvate în apa regatului.\n\nZamolxe ar fi spus că Aquarion este dovada că și cel mai umil lucru poate deveni extraordinar dacă i se dă suficient timp. Gardianul tăcut al apelor dulci — văzut rar, temut mult.',
            },
        },
    },

    'toadisimo': {
        'starter': False,
        'name': 'Toadisimo', 'emoji': '🐸', 'button_label': '🐸 Toadisimo',
        'codes': {1: 'TOAD-001', 2: 'TOAD-002', 3: 'TOAD-003'},
        'available_natures': ['nature'],
        'entries': {
            1: {
                'code': 'TOAD-001',
                'name': 'Toadisimo',
                'description': 'O broască jovială din mlaștinile Regnum Dacorum. Aparent inofensivă, dar cu o privire care ascunde mai mult decât pare.',
                'lore': 'Toadisimo trăiește la marginea mlaștinilor regatului, acolo unde pădurile se topesc în nămol și nimeni nu vine fără motiv serios.\n\nMasculii sunt verzi și discreți — se camuflează perfect în vegetație și observă totul fără să fie văzuți. Femelele sunt violet și nu se ascund deloc — știu că nimeni nu le va ataca primul.\n\nAmândoi secretă o toxină ușoară din glande, suficientă să descurajeze prădătorii. În Regnum Dacorum se spune: nu deranja o broască dacă nu știi ce culoare are.',
            },
            2: {
                'code': 'TOAD-002',
                'name': 'Toadisimo Rex',
                'description': 'A crescut, a absorbit toxinele mlaștinii și a devenit ceva mai mult decât o broască. Natura o respectă.',
                'lore': 'Toadisimo Rex marchează momentul în care broasca încetează să mai fie pradă și devine parte din echilibrul naturii.\n\nCorpul său a absorbit ani de plante toxice, ciuperci otrăvitoare și rădăcini rare — acum el însuși e parte din ecosistem. Plantele cresc mai repede în preajma lui, iar insectele îl ocolesc instinctiv.\n\nFemelele dezvoltă un colier natural din excrescențe perlate — nu decorativ, ci funcțional: emit vibrații ce perturbă inamicii. Masculii devin mai masivi și mai lenți, dar lovitura lor paralizează.',
            },
            3: {
                'code': 'TOAD-003',
                'name': 'Toadisimo Regalis',
                'description': 'Forma finală. Stăpânul mlaștinii — o creatură care a fuzionat cu natura până la punctul în care e greu de spus unde se termină broasca și unde începe pădurea.',
                'lore': 'Toadisimo Regalis nu mai locuiește în mlaștină — mlaștina locuiește în el.\n\nCorpul său e acoperit de mușchi, flori și ciuperci care cresc direct din piele, vii și funcționale. Nu e parazitism — e simbioză perfectă. Plantele îl hrănesc, el le protejează.\n\nZamolxe ar fi recunoscut în Toadisimo Regalis spiritul naturii pure — nu blând, nu crud, ci pur și simplu complet. Cei care îl dețin sunt considerați în Regnum Dacorum drept prieteni ai pădurii, primiți oriunde fără întrebări.',
            },
        },
    },
}

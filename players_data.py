"""Catálogo de jogadores disponíveis na loja.

Cada jogador é um dicionário com: name, position (GK/MC/ST), overall, rarity, price, image.
"image" é o nome do arquivo dentro de assets/cards/ (ou None se não tiver card ainda).

Além disso, jogadores podem ter atributos detalhados usados pelo simulador de
partidas (ver simulador_partida.py):
  - Goleiros (GK): POS, KIC, PAS, REF, DIV, VIS
  - Jogadores de linha (MC/ST): POS, SHO, PAS, DRI, DEF, VIS

Jogadores sem esses atributos ainda funcionam normalmente — o simulador usa o
overall como proxy nesse caso.
"""

PLAYERS_CATALOG = [
    {"name": "Jhanz",   "position": "ST", "overall": 63, "rarity": "Ouro", "estrelas": 0.4, "gacha_chance": 1.0, "country": "Brasil",      "price": 50,  "image": "jhanz.png",
     "POS": 64, "SHO": 67, "PAS": 55, "DRI": 59, "DEF": 38, "VIS": 58},
    {"name": "Minato",  "position": "GK", "overall": 69, "rarity": "Ouro", "estrelas": 0.5, "gacha_chance": 1.0, "country": "Brasil",      "price": 65,  "image": "minato.png",
     "POS": 70, "KIC": 57, "PAS": 61, "REF": 72, "DIV": 69, "VIS": 56},
    {"name": "Pingu",   "position": "ST", "overall": 62, "rarity": "Ouro", "estrelas": 0.9, "gacha_chance": 1.0, "country": "Brasil",      "price": 45,  "image": "pingu.png",
     "POS": 60, "SHO": 65, "PAS": 53, "DRI": 55, "DEF": 35, "VIS": 56},
    {"name": "Migz",   "position": "ST", "overall": 61, "rarity": "Ouro", "estrelas": 1, "gacha_chance": 1.0, "country": "Brasil",      "price": 45,  "image": "migz.png",
     "POS": 64, "SHO": 63, "PAS": 62, "DRI": 56, "DEF": 41, "VIS": 50},
    {"name": "Gonzaloplatito",   "position": "ST", "overall": 65, "rarity": "Ouro", "estrelas": 1, "gacha_chance": 1.0, "country": "Brasil",      "price": 58,  "image": "gonzaloplatito.png",
     "POS": 60, "SHO": 65, "PAS": 53, "DRI": 55, "DEF": 35, "VIS": 56},

    {"name": "Sommer",  "position": "GK", "overall": 74, "rarity": "Elite", "estrelas": 1.5, "gacha_chance": 1.0, "country": "Brasil",     "price": 73,  "image": "sommer.png",
     "POS": 76, "KIC": 65, "PAS": 62, "REF": 78, "DIV": 76, "VIS": 66},
    {"name": "L7wz",    "position": "MC", "overall": 71, "rarity": "Elite", "estrelas": 1, "gacha_chance": 1.0, "country": "Brasil",     "price": 70,  "image": "l7wz.png",
     "POS": 73, "SHO": 54, "PAS": 72, "DRI": 67, "DEF": 75, "VIS": 70},
    {"name": "Porko",   "position": "MC", "overall": 70, "rarity": "Elite", "estrelas": 1.5, "gacha_chance": 1.0, "country": "Brasil",     "price": 68,  "image": "porko.png",
     "POS": 69, "SHO": 57, "PAS": 75, "DRI": 69, "DEF": 61, "VIS": 68},
    {"name": "Fado",    "position": "ST", "overall": 74, "rarity": "Elite", "estrelas": 1.5, "gacha_chance": 1.0, "country": "Brasil",     "price": 73, "image": "fado.png",
     "POS": 72, "SHO": 77, "PAS": 61, "DRI": 75, "DEF": 40, "VIS": 57},
    {"name": "Danni",   "position": "ST", "overall": 74, "rarity": "Elite", "estrelas": 1.5, "gacha_chance": 1.0, "country": "Brasil",     "price": 71, "image": "danni.png",
     "POS": 77, "SHO": 78, "PAS": 63, "DRI": 72, "DEF": 42, "VIS": 60},
    {"name": "Edu",     "position": "ST", "overall": 74, "rarity": "Elite", "estrelas": 1.5, "gacha_chance": 1.0, "country": "Brasil",     "price": 73, "image": "edu.png",
     "POS": 75, "SHO": 81, "PAS": 59, "DRI": 73, "DEF": 36, "VIS": 55},
    {"name": "Gelo",    "position": "ST", "overall": 74, "rarity": "Elite", "estrelas": 1.5, "gacha_chance": 1.0, "country": "Brasil",     "price": 70, "image": "gelo.png",
     "POS": 79, "SHO": 75, "PAS": 64, "DRI": 68, "DEF": 35, "VIS": 65},
    {"name": "Loh",     "position": "ST", "overall": 74, "rarity": "Elite", "estrelas": 1.5, "gacha_chance": 1, "country": "Brasil", "price": 73,  "image": "loh.png",
     "POS": 73, "SHO": 75, "PAS": 77, "DRI": 63, "DEF": 40, "VIS": 65},
    {"name": "Bre",     "position": "GK", "overall": 74, "rarity": "Elite", "estrelas": 1.5, "gacha_chance": 1, "country": "Brasil", "price": 72,  "image": "bre.png",
     "POS": 75, "KIC": 78, "PAS": 72, "REF": 73, "DIV": 64, "VIS": 68},

    {"name": "Spy",     "position": "ST", "overall": 77, "rarity": "Dominante", "estrelas": 2.5, "gacha_chance": 0.6, "country": "Brasil", "price": 80,  "image": "spy.png",
     "POS": 79, "SHO": 82, "PAS": 67, "DRI": 73, "DEF": 42, "VIS": 65},
    {"name": "Lumi",    "position": "MC", "overall": 76, "rarity": "Dominante", "estrelas": 2.4, "gacha_chance": 1.0, "country": "Brasil", "price": 80,  "image": "lumi.png",
     "POS": 78, "SHO": 60, "PAS": 79, "DRI": 72, "DEF": 77, "VIS": 76},
    {"name": "Sasuke",  "position": "GK", "overall": 76, "rarity": "Dominante", "estrelas": 2.3, "gacha_chance": 1.0, "country": "Brasil", "price": 75,  "image": "sasuke.png",
     "POS": 78, "KIC": 69, "PAS": 58, "REF": 82, "DIV": 77, "VIS": 61},
    {"name": "Rickzin", "position": "GK", "overall": 79, "rarity": "Dominante", "estrelas": 2.7, "gacha_chance": 0.4, "country": "Brasil", "price": 85,  "image": "rick.png",
     "POS": 81, "KIC": 75, "PAS": 67, "REF": 84, "DIV": 79, "VIS": 70},
    {"name": "Rafi",    "position": "ST", "overall": 76, "rarity": "Dominante", "estrelas": 2.3, "gacha_chance": 1.0, "country": "Canadá", "price": 81,  "image": "rafi.png",
     "POS": 78, "SHO": 84, "PAS": 58, "DRI": 77, "DEF": 40, "VIS": 62},
    {"name": "Nokp",    "position": "ST", "overall": 79, "rarity": "Dominante", "estrelas": 2.8, "gacha_chance": 0.3, "country": "Chile", "price": 86,  "image": "nokp.png",
     "POS": 80, "SHO": 82, "PAS": 68, "DRI": 84, "DEF": 42, "VIS": 66},
    {"name": "Carlin",  "position": "ST", "overall": 76, "rarity": "Dominante", "estrelas": 2, "gacha_chance": 1.0, "country": "Brasil", "price": 79,  "image": "carlin.png",
     "POS": 79, "SHO": 73, "PAS": 69, "DRI": 72, "DEF": 46, "VIS": 70},
    {"name": "Kuia",    "position": "MC", "overall": 79, "rarity": "Dominante", "estrelas": 2.7, "gacha_chance": 0.6, "country": "Brasil", "price": 84,  "image": "kuia.png",
     "POS": 79, "SHO": 66, "PAS": 81, "DRI": 79, "DEF": 75, "VIS": 73},
    {"name": "Haala",   "position": "ST", "overall": 77, "rarity": "Dominante", "estrelas": 2.4, "gacha_chance": 0.4, "country": "Brasil", "price": 80,  "image": "haala.png",
     "POS": 82, "SHO": 70, "PAS": 67, "DRI": 79, "DEF": 43, "VIS": 64},
    {"name": "Mec",     "position": "GK", "overall": 79, "rarity": "Dominante", "estrelas": 2.6, "gacha_chance": 0.6, "country": "Brasil", "price": 87,  "image": "mec.png",
     "POS": 79, "KIC": 82, "PAS": 73, "REF": 85, "DIV": 80, "VIS": 77},
    {"name": "Super",   "position": "MC", "overall": 76, "rarity": "Dominante", "estrelas": 2.3, "gacha_chance": 1.0, "country": "Peru", "price": 78,  "image": "super.png",
     "POS": 74, "SHO": 53, "PAS": 80, "DRI": 73, "DEF": 75, "VIS": 72},
    {"name": "Atom",    "position": "MC", "overall": 79, "rarity": "Dominante", "estrelas": 2.9, "gacha_chance": 0.7, "country": "Brasil", "price": 87,  "image": "atom.png",
     "POS": 80, "SHO": 65, "PAS": 83, "DRI": 77, "DEF": 80, "VIS": 76},
    {"name": "Eod2",    "position": "MC", "overall": 78, "rarity": "Dominante", "estrelas": 2.5, "gacha_chance": 1.0, "country": "Brasil", "price": 82,  "image": "eod2.png",
     "POS": 79, "SHO": 63, "PAS": 82, "DRI": 75, "DEF": 70, "VIS": 79},
    {"name": "Cloudz",  "position": "GK", "overall": 79, "rarity": "Dominante", "estrelas": 2.8, "gacha_chance": 0.6, "country": "Brasil", "price": 79,  "image": "cloudz.png",
     "POS": 82, "KIC": 80, "PAS": 66, "REF": 86, "DIV": 78, "VIS": 72},
    {"name": "Rxthur",  "position": "MC", "overall": 77, "rarity": "Dominante", "estrelas": 2.4, "gacha_chance": 1.0, "country": "Brasil",     "price": 81,  "image": "rxthur.png",
     "POS": 79, "SHO": 69, "PAS": 78, "DRI": 67, "DEF": 80, "VIS": 72},
    {"name": "Zyph",    "position": "MC", "overall": 79, "rarity": "Dominante", "estrelas": 2.9, "gacha_chance": 0.8, "country": "Brasil",  "price": 88, "image": "zyph.png",
     "POS": 40, "SHO": 30, "PAS": 82, "DRI": 85, "DEF": 83, "VIS": 78},
    {"name": "Vitadd",    "position": "ST", "overall": 79, "rarity": "Dominante", "estrelas": 2.9, "gacha_chance": 0.8, "country": "Brasil",  "price": 89, "image": "vitadd.png",
     "POS": 84, "SHO": 83, "PAS": 72, "DRI": 65, "DEF": 40, "VIS": 70},

    {"name": "Ryu",     "position": "MC", "overall": 84, "rarity": "Immortal", "estrelas": 3.5, "gacha_chance": 0.7, "country": "Brasil",  "price": 110, "image": "ryu.png",
     "POS": 83, "SHO": 68, "PAS": 84, "DRI": 87, "DEF": 87, "VIS": 82},
    {"name": "Turzin",  "position": "ST", "overall": 83, "rarity": "Immortal", "estrelas": 3.2, "gacha_chance": 1.0, "country": "Brasil",  "price": 105, "image": "turzin.png",
     "POS": 85, "SHO": 86, "PAS": 69, "DRI": 85, "DEF": 43, "VIS": 66},
    {"name": "Asulata", "position": "MC", "overall": 84, "rarity": "Immortal", "estrelas": 3.5, "gacha_chance": 0.8, "country": "Brasil", "price": 108, "image": "asulata.png",
     "POS": 86, "SHO": 62, "PAS": 85, "DRI": 78, "DEF": 86, "VIS": 88},
    {"name": "Aaron",   "position": "ST", "overall": 82, "rarity": "Immortal", "estrelas": 3, "gacha_chance": 1.0, "country": "Porto Rico", "price": 98,  "image": "aaron.png",
     "POS": 79, "SHO": 84, "PAS": 85, "DRI": 83, "DEF": 42, "VIS": 76},
    {"name": "Ryan",    "position": "ST", "overall": 82, "rarity": "Immortal", "estrelas": 3, "gacha_chance": 1.0, "country": "Canadá", "price": 103, "image": "ryan.png",
     "POS": 84, "SHO": 89, "PAS": 66, "DRI": 82, "DEF": 42, "VIS": 69},
    {"name": "Veeni",   "position": "GK", "overall": 84, "rarity": "Immortal", "estrelas": 3.6, "gacha_chance": 0.4, "country": "Brasil", "price": 112, "image": "veeni.png",
     "POS": 87, "KIC": 86, "PAS": 70, "REF": 89, "DIV": 84, "VIS": 73},
    {"name": "Flaz",    "position": "ST", "overall": 83, "rarity": "Immortal", "estrelas": 3.2, "gacha_chance": 0.2, "country": "Holanda", "price": 111, "image": "flaz.png",
     "POS": 82, "SHO": 90, "PAS": 70, "DRI": 84, "DEF": 44, "VIS": 69},
    {"name": "Ezzy", "position": "MC", "overall": 81, "rarity": "Immortal", "estrelas": 3, "gacha_chance": 0.8, "country": "Brasil", "price": 108, "image": "ezzy.png",
     "POS": 75, "SHO": 70, "PAS": 83, "DRI": 85, "DEF": 80, "VIS": 80},

    {"name": "Nxy",     "position": "MC", "overall": 88, "rarity": "Lendário", "estrelas": 4.9, "gacha_chance": 0.1, "country": "Brasil",  "price": 125, "image": "nxy.png",
     "POS": 89, "SHO": 76, "PAS": 91, "DRI": 87, "DEF": 91, "VIS": 89},
    {"name": "Drive",   "position": "ST", "overall": 87, "rarity": "Lendário", "estrelas": 4.5, "gacha_chance": 0.5, "country": "Brasil",  "price": 118, "image": "drive.png",
     "POS": 90, "SHO": 91, "PAS": 72, "DRI": 84, "DEF": 45, "VIS": 76},
    {"name": "Shadix",  "position": "GK", "overall": 87, "rarity": "Lendário", "estrelas": 4.6, "gacha_chance": 0.6, "country": "Argentina",  "price": 125, "image": "shadix.png",
     "POS": 88, "KIC": 84, "PAS": 72, "REF": 90, "DIV": 89, "VIS": 78},
    {"name": "Rfer",    "position": "ST", "overall": 85, "rarity": "Lendário", "estrelas": 4, "gacha_chance": 1.0, "country": "Brasil",  "price": 118, "image": "rfer.png",
     "POS": 87, "SHO": 87, "PAS": 74, "DRI": 86, "DEF": 48, "VIS": 72},
    {"name": "Moon",    "position": "GK", "overall": 87, "rarity": "Lendário", "estrelas": 4.6, "gacha_chance": 0.6, "country": "Argentina",  "price": 123, "image": "moon.png",
     "POS": 89, "KIC": 87, "PAS": 70, "REF": 91, "DIV": 89, "VIS": 80},
    {"name": "Nsz",     "position": "MC", "overall": 85, "rarity": "Lendário", "estrelas": 4.2, "gacha_chance": 1.0, "country": "Brasil",  "price": 120, "image": "nsz.png",
     "POS": 82, "SHO": 72, "PAS": 87, "DRI": 82, "DEF": 85, "VIS": 80},
    {"name": "Cleitin", "position": "MC", "overall": 87, "rarity": "Lendário", "estrelas": 4.8, "gacha_chance": 0.3, "country": "Brasil",  "price": 122, "image": "cleitin.png",
     "POS": 86, "SHO": 69, "PAS": 92, "DRI": 89, "DEF": 90, "VIS": 83},
    {"name": "Guipro",     "position": "MC", "overall": 85, "rarity": "Lendário", "estrelas": 4.2, "gacha_chance": 1.0, "country": "Brasil",  "price": 120, "image": "guipro.png",
     "POS": 86, "SHO": 68, "PAS": 81, "DRI": 83, "DEF": 87, "VIS": 80},
    {"name": "Starzy",     "position": "GK", "overall": 85, "rarity": "Lendário", "estrelas": 4.2, "gacha_chance": 1.0, "country": "Brasil",  "price": 120, "image": "starzy.png",
     "POS": 83, "KIC": 81, "PAS": 79, "REF": 86, "DIV": 82, "VIS": 76},

    {"name": "Aby",     "position": "ST", "overall": 91, "rarity": "Mítico", "estrelas": 5.3, "gacha_chance": 0.3, "country": "Brasil",    "price": 150, "image": "aby.png",
     "POS": 93, "SHO": 95, "PAS": 78, "DRI": 87, "DEF": 43, "VIS": 76},
    {"name": "Shanks",  "position": "MC", "overall": 93, "rarity": "Mítico", "estrelas": 6, "gacha_chance": 0.01, "country": "Brasil",    "price": 170, "image": "shanks.png",
     "POS": 92, "SHO": 79, "PAS": 96, "DRI": 94, "DEF": 94, "VIS": 95},
    {"name": "Coco",    "position": "MC", "overall": 90, "rarity": "Mítico", "estrelas": 5, "gacha_chance": 1.0, "country": "Argentina",    "price": 145, "image": "coco.png",
     "POS": 88, "SHO": 75, "PAS": 92, "DRI": 91, "DEF": 92, "VIS": 89},
    {"name": "Snw",     "position": "ST", "overall": 90, "rarity": "Mítico", "estrelas": 5.3, "gacha_chance": 1.0, "country": "Chile",    "price": 146, "image": "snw.png",
     "POS": 91, "SHO": 94, "PAS": 76, "DRI": 92, "DEF": 42, "VIS": 75},
    {"name": "J3",      "position": "MC", "overall": 91, "rarity": "Mítico", "estrelas": 5.5, "gacha_chance": 0.5, "country": "Brasil",    "price": 155, "image": "j3.png",
     "POS": 91, "SHO": 76, "PAS": 95, "DRI": 88, "DEF": 96, "VIS": 94},

    {"name": "Bolsonaro", "position": "ST", "overall": 91, "rarity": "Limited", "estrelas": 6, "country": "Brasil", "price": 500, "image": "bolsonaro.png",
     "POS": 90, "SHO": 87, "PAS": 91, "DRI": 90, "DEF": 42, "VIS": 84, "obtainable": False},
    {"name": "Lula",      "position": "ST", "overall": 91, "rarity": "Limited", "estrelas": 6, "country": "Brasil", "price": 500, "image": "lula.png",
     "POS": 90, "SHO": 87, "PAS": 91, "DRI": 90, "DEF": 42, "VIS": 84, "obtainable": False},
    {"name": "Xhino", "position": "MC", "overall": 89, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "xhinofs.png",
     "POS": 88, "SHO": 72, "PAS": 91, "DRI": 88, "DEF": 78, "VIS": 90},

    {"name": "Turzin", "position": "ST", "overall": 88, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "turzinfs.png",
     "POS": 89, "SHO": 91, "PAS": 78, "DRI": 88, "DEF": 38, "VIS": 73},

    {"name": "Zyph", "position": "MC", "overall": 86, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "zyphfs.png",
     "POS": 85, "SHO": 68, "PAS": 88, "DRI": 85, "DEF": 75, "VIS": 87},

    {"name": "Eod2", "position": "ST", "overall": 87, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "eod2fs.png",
     "POS": 88, "SHO": 90, "PAS": 77, "DRI": 86, "DEF": 37, "VIS": 72},

    {"name": "Kok", "position": "ST", "overall": 85, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "kokfs.png",
     "POS": 86, "SHO": 88, "PAS": 75, "DRI": 84, "DEF": 35, "VIS": 70},

    {"name": "Rxthur", "position": "MC", "overall": 86, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "rxthurfs.png",
     "POS": 84, "SHO": 69, "PAS": 87, "DRI": 86, "DEF": 76, "VIS": 88},

    {"name": "Vitadd", "position": "ST", "overall": 87, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "vitaddfs.png",
     "POS": 88, "SHO": 89, "PAS": 77, "DRI": 87, "DEF": 37, "VIS": 72},

    {"name": "Rickzin", "position": "GK", "overall": 87, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "rickzinfs.png",
     "POS": 86, "REF": 90, "DIV": 88, "KIC": 82, "DEF": 84, "VIS": 78},

    {"name": "Cleitin", "position": "MC", "overall": 95, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 800, "image": "cleitinflashback.png",
     "POS": 96, "SHO": 82, "PAS": 98, "DRI": 96, "DEF": 91, "VIS": 97},

    {"name": "J3", "position": "ST", "overall": 95, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 800, "image": "j3flashback.png",
     "POS": 96, "SHO": 97, "PAS": 86, "DRI": 95, "DEF": 43, "VIS": 82},

    {"name": "Dfirri", "position": "MC", "overall": 94, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 780, "image": "dfirriflashback.png",
     "POS": 94, "SHO": 79, "PAS": 96, "DRI": 94, "DEF": 88, "VIS": 95},

    {"name": "Retsub", "position": "MC", "overall": 95, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 800, "image": "retsubflashback.png",
     "POS": 95, "SHO": 80, "PAS": 97, "DRI": 95, "DEF": 89, "VIS": 96},

    {"name": "Xel", "position": "MC", "overall": 93, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 750, "image": "xelflashback.png",
     "POS": 92, "SHO": 77, "PAS": 94, "DRI": 92, "DEF": 86, "VIS": 93},

    {"name": "Bakon", "position": "ST", "overall": 95, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 800, "image": "bakonflashback.png",
     "POS": 95, "SHO": 97, "PAS": 84, "DRI": 94, "DEF": 42, "VIS": 80},

    {"name": "Codyz", "position": "MC", "overall": 92, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 700, "image": "codyzflashback.png",
     "POS": 91, "SHO": 76, "PAS": 93, "DRI": 90, "DEF": 84, "VIS": 92},

    {"name": "Roxo", "position": "MC", "overall": 94, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 780, "image": "roxoflashback.png",
     "POS": 93, "SHO": 78, "PAS": 96, "DRI": 93, "DEF": 87, "VIS": 95},


    {"name": "Lipe", "position": "ST", "overall": 88, "rarity": "Special", "estrelas": 6, "country": "Brasil", "price": 300, "image": "lipejst.png",
     "POS": 89, "SHO": 92, "PAS": 75, "DRI": 88, "DEF": 40, "VIS": 72, "obtainable": True},
    {"name": "Fast", "position": "MC", "overall": 88, "rarity": "Special", "estrelas": 6, "country": "Brasil", "price": 300, "image": "fastjst.png",
     "POS": 88, "SHO": 72, "PAS": 91, "DRI": 89, "DEF": 87, "VIS": 90, "obtainable": True},
    {"name": "Edu", "position": "GK", "overall": 88, "rarity": "Special", "estrelas": 6, "country": "Brasil", "price": 300, "image": "edujst.png",
     "POS": 89, "KIC": 82, "PAS": 75, "REF": 92, "DIV": 89, "VIS": 78, "obtainable": True},
    {"name": "Nagi", "position": "ST", "overall": 88, "rarity": "Special", "estrelas": 6, "country": "Brasil", "price": 300, "image": "nagijst.png",
     "POS": 90, "SHO": 89, "PAS": 79, "DRI": 91, "DEF": 44, "VIS": 76, "obtainable": True},
  
    {"name": "Mzfps", "position": "GK", "overall": 93, "rarity": "Special", "estrelas": 6, "gacha_chance": 0.5, "country": "Brasil", "price": 500, "image": "mzfpswc.png",
     "POS": 94, "KIC": 87, "PAS": 78, "REF": 96, "DIV": 93, "VIS": 86, "obtainable": False},
    {"name": "Pedrogod", "position": "MC", "overall": 88, "rarity": "Special", "estrelas": 6, "gacha_chance": 0.5, "country": "Brasil", "price": 500, "image": "pedrogodwc.png",
     "POS": 91, "SHO": 70, "PAS": 86, "DRI": 80, "DEF": 90, "VIS": 85, "obtainable": False},
    {"name": "Nxy", "position": "MC", "overall": 92, "rarity": "Special", "estrelas": 6, "gacha_chance": 0.8, "country": "Brasil", "price": 500, "image": "nxywc.png",
   "POS": 91, "SHO": 78, "PAS": 94, "DRI": 90, "DEF": 93, "VIS": 92, "obtainable": False},
    {"name": "Rfer", "position": "ST", "overall": 90, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "rferwc.png",
     "POS": 91, "SHO": 93, "PAS": 76, "DRI": 89, "DEF": 47, "VIS": 74, "obtainable": False},
    {"name": "Cleitin", "position": "MC", "overall": 91, "rarity": "Special", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 500, "image": "cleitinwc.png",
     "POS": 89, "SHO": 72, "PAS": 95, "DRI": 91, "DEF": 92, "VIS": 87, "obtainable": False},

  
    {"name": "Trick",
     "position": "ST",
     "overall": 92,
     "rarity": "Limited",
     "estrelas": 6,
     "country": "Romênia",
     "price": 500,
     "image": "TricK.png",
     "POS": 96, "SHO": 98, "PAS": 90, "DRI": 98, "DEF": 42, "VIS": 92, "obtainable": True
    },

    {"name": "Baller",
     "position": "MC",
     "overall": 92,
     "rarity": "Limited",
     "estrelas": 6,
     "country": "México",
     "price": 500,
     "image": "baller.png",
     "POS": 96, "SHO": 78, "PAS": 96, "DRI": 96, "DEF": 98, "VIS": 95, "obtainable": True
    },

    {"name": "Fang",
     "position": "ST",
     "overall": 91,
     "rarity": "Limited",
     "estrelas": 6,
     "country": "Alemanha",
     "price": 500,
     "image": "FANG.png",
     "POS": 89, "SHO": 91, "PAS": 88, "DRI": 90, "DEF": 48, "VIS": 79, "obtainable": True
    },
  
    {"name": "Shanks", "position": "MC", "overall": 94, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 800, "image": "shanksbig3.png",
     "POS": 97, "SHO": 85, "PAS": 99, "DRI": 98, "DEF": 97, "VIS": 99, "obtainable": False},
    {"name": "Aby", "position": "ST", "overall": 94, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 800, "image": "abybig3.png",
     "POS": 98, "SHO": 99, "PAS": 84, "DRI": 96, "DEF": 44, "VIS": 81, "obtainable": False},
    {"name": "J3", "position": "MC", "overall": 94, "rarity": "Limited", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 800, "image": "j3big3.png",
     "POS": 97, "SHO": 83, "PAS": 98, "DRI": 94, "DEF": 99, "VIS": 98, "obtainable": False},

    {"name": "Pitbull", "position": "ST", "overall": 95, "rarity": "Icon", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 1000, "image": "pitbullicon.png",
     "POS": 96, "SHO": 99, "PAS": 82, "DRI": 96, "DEF": 45, "VIS": 80, "obtainable": True},
    {"name": "Roxo", "position": "MC", "overall": 95, "rarity": "Icon", "estrelas": 6.5, "gacha_chance": 1.0, "country": "Brasil", "price": 1000, "image": "roxoicon.png",
     "POS": 96, "SHO": 84, "PAS": 98, "DRI": 96, "DEF": 96, "VIS": 97, "obtainable": True},
    {"name": "Brmaluco", "position": "MC", "overall": 95, "rarity": "Icon", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 1000, "image": "brmalucoicon.png",
     "POS": 95, "SHO": 82, "PAS": 97, "DRI": 95, "DEF": 98, "VIS": 96, "obtainable": True},
    {"name": "Guipro", "position": "GK", "overall": 95, "rarity": "Icon", "estrelas": 6, "gacha_chance": 1.0, "country": "Brasil", "price": 1000, "image": "guiproicon.png",
     "POS": 98, "KIC": 91, "PAS": 84, "REF": 99, "DIV": 97, "VIS": 91, "obtainable": True},
]

COUNTRY_FLAGS = {
    "Brasil": "🇧🇷",
    "Argentina": "🇦🇷",
    "Canadá": "🇨🇦",
    "Chile": "🇨🇱",
    "Peru": "🇵🇪",
    "Porto Rico": "🇵🇷",
    "Holanda": "🇳🇱",
    "Romênia": "🇷🇴",
    "México": "🇲🇽",
    "Alemanha": "🇩🇪",
}

def get_country_display(country):
    if not country:
        return "🌎 Desconhecido"

    flag = COUNTRY_FLAGS.get(country, "🌎")
    return f"{flag} {country}"

# País padrão do catálogo atual.
# O projeto ainda não tinha nacionalidade individual cadastrada; por isso,
# as cartas existentes usam Brasil até que nacionalidades específicas sejam
# definidas para cada jogador.
for _jogador in PLAYERS_CATALOG:
    _jogador.setdefault("country", "Brasil")
    # Chance individual do gacha (peso relativo dentro da própria raridade/pool).
    # 1.0 = chance padrão; você pode trocar por qualquer valor positivo.
    _jogador.setdefault("gacha_chance", 1.0)
    # Valor visual das estrelas da carta. Altere individualmente em cada jogador.
    _jogador.setdefault("estrelas", 1.0)



# Cartas que existem no catálogo, mas NÃO podem ser obtidas pelos métodos
# normais (giro/pacotes, /claim e /weekly). O nome fica bloqueado mesmo se
# alguém esquecer de colocar "obtainable": False na carta.
CARTAS_NAO_OBTIVEIS = {"bolsonaro", "lula"}


def jogador_obtivel(jogador: dict, chave_pacote: str | None = None) -> bool:
    """True quando a carta está liberada para obtenção.

    ``chave_pacote`` é mantido por compatibilidade com chamadas antigas,
    mas não existe mais restrição de carta por pacote. A disponibilidade
    por pacote agora é controlada exclusivamente pelos pesos de raridade
    definidos em ``config.PACOTES``.
    """
    nome = str(jogador.get("name", "")).strip().lower()
    if nome in CARTAS_NAO_OBTIVEIS:
        return False
    return jogador.get("obtainable", True)


def buscar_jogador_catalogo(nome: str, raridade: str | None = None, overall: int | None = None):
    """Busca uma carta no catálogo.

    Quando raridade e/ou overall são informados, a busca fica específica
    para aquela variante. Isso é importante para jogadores que possuem
    mais de uma carta com o mesmo nome, como Edu Elite e Edu Special.
    """
    nome_lower = nome.strip().lower()
    for jogador in PLAYERS_CATALOG:
        if jogador["name"].lower() != nome_lower:
            continue
        if raridade is not None and jogador.get("rarity", "").lower() != str(raridade).strip().lower():
            continue
        if overall is not None and jogador.get("overall") != overall:
            continue
        return jogador
    return None


def jogadores_por_posicao(posicao: str):
    """Retorna todos os jogadores do catálogo de uma posição específica."""
    return [j for j in PLAYERS_CATALOG if j["position"] == posicao.upper()]

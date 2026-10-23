"""Configurações gerais do bot DreamTeam."""

# Nome da moeda fictícia do jogo
MOEDA_NOME = "LP"
MOEDA_EMOJI = "<:lpcoin:1552316613980594219>"

# Economia
SALDO_INICIAL = 200
SALARIO_MIN = 60
SALARIO_MAX = 75
SALARIO_COOLDOWN_MINUTOS = 30
DIARIO_VALOR = 100
DIARIO_COOLDOWN_HORAS = 24

# Inventário
INVENTARIO_LIMITE_BASE = 8  # quantas cartas distintas cabem sem comprar espaço extra
EXPANSAO_INVENTARIO_SLOTS = 4  # quantos espaços cada compra de expansão adiciona
EXPANSAO_INVENTARIO_PRECO = 150  # preço em Robux de cada expansão

# Anti-autoclick para abertura de pacotes
# A cada 5 pacotes abertos, o próximo exige uma verificação.
ANTIBOT_ABERTURAS = 5
ANTIBOT_TIMEOUT_SEGUNDOS = 90
ANTIBOT_SIMBOLOS = ("▲", "●", "■", "◆", "★", "✦")

# Cargo que pode usar o Pacote Booster.
# Coloque aqui o ID do cargo Server Booster se quiser travar pelo ID.
# Se ficar 0, o bot procura pelo nome exato "Server Booster".
BOOSTER_ROLE_ID = 1542316048194478203
BOOSTER_ROLE_NOME = "Server Booster"

# Usuários que podem usar o Pacote Booster mesmo sem o cargo.
# Coloque os IDs das pessoas entre as chaves. Pode adicionar quantos quiser.
# Exemplo: BOOSTER_USER_IDS = {123456789012345678, 987654321098765432}
BOOSTER_USER_IDS = {1312443810294399037, 1012120096552013944}

# Pacote Pro
PRO_PRECO = 5000
PRO_DURACAO_DIAS = 7
PRO_ROLE_NOME = "Pro"

# Estrelas das cartas
# O valor de "estrelas" de cada jogador fica em players_data.py.
# Exemplos: 3.0 = 3 completas, 3.5 = 3 completas + meia,
# 3.25 = 3 completas + fração pequena, 3.75 = 3 completas + quase completa.
ESTRELA_1 = "<:estrela1:1552325829084713010>"  # meia estrela (0.5)
ESTRELA_2 = "<:estrela2:1552325944935579653>"  # estrela completa (1.0)
ESTRELA_3 = "<:estrela3:1552326043115716750>"  # fração abaixo de 0.5
ESTRELA_4 = "<:estrela4:1552326135650459729>"  # fração acima de 0.5 e abaixo de 1.0
ESTRELA_5 = "<:estrela5:1552326211760291903>"  # estrela extra de Limited


def formatar_estrelas(valor, limited=False):
    """Converte o valor numérico de estrelas nos emojis configurados."""
    try:
        valor = max(0.0, float(valor))
    except (TypeError, ValueError):
        valor = 0.0

    completas = int(valor)
    fracao = valor - completas
    partes = [ESTRELA_2] * completas

    # Tolerância pequena para evitar problemas de ponto flutuante.
    if abs(fracao - 0.5) < 0.001:
        partes.append(ESTRELA_1)
    elif 0 < fracao < 0.5:
        partes.append(ESTRELA_3)
    elif 0.5 < fracao < 1.0:
        partes.append(ESTRELA_4)

    if limited:
        partes.append(ESTRELA_5)

    return "".join(partes)


# Gacha — pacotes disponíveis (comprados na loja e abertos pelo inventário)
PACOTES = {
    "basico": {
        "nome": "Pacote Básico",
        "na_loja": True,
        "emoji": "<:pacotebasico:1552145322887872603>",
        "emoji_name": "pacotebasico",
        "emoji_id": 1552145322887872603,
        "preco": 75,
        "pesos": {
            "Ouro": 58,
            "Elite": 28,
            "Dominante": 11,
            "Immortal": 2.7,
            "Lendário": 0.3,
        },
        "pesos_booster": {
            "Ouro": 54,
            "Elite": 29,
            "Dominante": 13,
            "Immortal": 3,
            "Lendário": 0.5,
        },
    },
    "premium": {
        "nome": "Pacote Premium",
        "na_loja": True,
        "emoji": "<:pacotepremium:1552145357700595803>",
        "emoji_name": "pacotepremium",
        "emoji_id": 1552145357700595803,
        "preco": 150,
        "pesos": {
            "Dominante": 55,
            "Immortal": 31,
            "Lendário": 8.86,
            "Mítico": 0.08,
            "Special": 0.05,
        },
        "pesos_booster": {
            "Dominante": 51,
            "Immortal": 32,
            "Lendário": 11.86,
            "Mítico": 0.1,
            "Special": 0.08,
        },
    },
    "booster": {
        "nome": "Pacote Booster",
        "na_loja": False,
        "emoji": "<:booster:1552145534079471688>",
        "emoji_name": "booster",
        "emoji_id": 1552145534079471688,
        "preco": 120,
        "pesos": {
            "Immortal": 85,
            "Lendário": 15,
            "Mítico": 0.8,
            "Limited": 0.08,
        },
    },
    "pro": {
        "nome": "Pacote Pro",
        "na_loja": True,
        "emoji": "<:proicon:1552484891738902652>",
        "emoji_name": "Pro",
        "emoji_id": "1552484891738902652",
        "preco": 150,
        "pesos": {
            "Immortal": 45,
            "Lendário": 54.65,
            "Mítico": 0.25,
            "Special": 0.08,
            "Limited": 0.08,
        },  # Configure as porcentagens do Pro aqui.
        "pesos_booster": {
            "Immortal": 41,
            "Lendário": 56.65,
            "Mítico": 0.75,
            "Special": 0.11,
            "Limited": 0.09,
        },
    },
    "icon": {
        "nome": "Pacote Icon",
        "na_loja": False,
        "preco": 300,
        "emoji": "🇧🇷",
        "emoji_name": "icon",
        "emoji_id": None,

        "raridades": [
            "Lendário",
            "Mítico",
            "Icon",
        ],

        "pesos": {
            "Lendário": 96,
            "Mítico": 0.1,
            "Icon": 0.05,
        },
    },
}

# COMO COLOCAR UMA RARIDADE EM UM PACOTE:
# Basta adicionar a raridade dentro de "pesos" do pacote desejado.
# Exemplo:
# "pesos": {
#     "Immortal": 90,
#     "Limited": 5,
#     "Special": 4,
#     "Icon": 1,
# }
# O jogador também precisa ter "rarity": "Limited", "Special" ou "Icon"
# no PLAYERS_CATALOG para poder ser sorteado.
#
# Benefício Booster por pacote:
# Adicione "pesos_booster" dentro de um pacote para substituir os pesos normais
# quando um Server Booster abrir aquele mesmo pacote. Sem esse campo,
# o Booster usa os pesos normais de "pesos".
# Exemplo:
# "pesos_booster": {"Ouro": 80, "Mítico": 5, "Limited": 1},

# Controle da exclusividade de cartas Special/Limited.
# True  = mantém a regra de exclusividade atual.
# False = Special/Limited podem ser obtidos novamente normalmente.
LIMITAR_SPECIAL_LIMITED = False


# Claim gratuito (cooldown curto, sorteia entre TODAS as 27 cartas do catálogo)
CLAIM_COOLDOWN_MINUTOS = 20
CLAIM_PESOS_RARIDADE = {
    "Ouro": 72,
    "Elite": 20,
    "Dominante": 6,
    "Immortal": 1.5,
    "Lendário": 0.45,
    "Mítico": 0.05,
}

# Pacote semanal (não é comprável nem aparece na loja)
WEEKLY_COOLDOWN_DIAS = 7
WEEKLY_OVERALL_MINIMO = 80  # pelo menos 1 das 3 cartas deve ter este overall ou mais
WEEKLY_PESOS_RARIDADE = {
    "Elite": 45,
    "Dominante": 30,
    "Immortal": 18,
    "Lendário": 6,
    "Mítico": 1,
}


# Formações disponíveis: modo -> posição -> quantidade de slots
FORMACOES = {
    "4v4": {"GK": 1, "MC": 1, "ST": 2},
    "7v7": {"GK": 1, "MC": 3, "ST": 3},
}

# Ordem de exibição das posições
ORDEM_POSICOES = ["GK", "MC", "ST"]

# Ordem de raridade (da mais fraca pra mais forte), usada pra ordenar a loja
ORDEM_RARIDADE = ["Ouro", "Elite", "Dominante", "Immortal", "Lendário", "Mítico", "Special", "Limited", "Icon", "Big Time"]

# Cor por raridade (usada nos embeds)
COR_RARIDADE = {
    "Ouro": 0xE67E22,
    "Elite": 0x90EE90,
    "Dominante": 0xC8A2C8,
    "Immortal": 0xF08060,
    "Lendário": 0xD8B25C,
    "Mítico": 0xB8B0C8,
    "Special": 0x58D68D,
    "Limited": 0xF4D03F,
    "Icon": 0xFFFFFF,
    "Big Time": 0x1ABC9C,
}

EMOJI_RARIDADE = {
    "Ouro": "🔹",
    "Elite": "🔹",
    "Dominante": "🔹",
    "Immortal": "🔹",
    "Lendário": "🔹",
    "Mítico": "🔹",
    "Limited": "⌛",
    "Special": "🍀",
    "Icon": "🇧🇷",
    "Big Time": "🕰️",
}


# Textos do /about. Edite somente os valores entre aspas.
# As chaves de raridade são detectadas automaticamente pelo catálogo/config.
ABOUT_RARIDADES = {
    "Ouro": "Representa jogadores competentes, mas que ainda estão em um nível mais básico de habilidade. São cartas de jogadores que conseguem desempenhar bem, mas possuem limitações claras.",
    "Elite": "Jogadores acima da média, com boa consistência e domínio das principais habilidades. São capazes de se destacar em partidas competitivas.",
    "Dominante": "Jogadores extremamente habilidosos, capazes de controlar partidas e fazer uma grande diferença dentro de campo. Sua presença costuma ser decisiva.",
    "Immortal": "Representa um nível excepcional de habilidade. Jogadores desse rank possuem grande consistência, domínio técnico e capacidade de atuar entre os melhores.",
    "Lendário": "Reservado para jogadores de nível extraordinário, reconhecidos por performances marcantes e habilidades que poucos conseguem alcançar.",
    "Mítico": "O mais alto nível de raridade. Representa jogadores excepcionais, cuja habilidade e impacto os colocam em uma categoria própria, acima dos demais ranks.",
    "Special": "A carta pode ser obtida novamente, mas somente se o jogador não possuir mais nenhuma cópia dela. Caso a pessoa venda ou troque a carta e fique sem ela, poderá obtê-la novamente. Enquanto ainda possuir a carta, não poderá conseguir outra cópia.",
    "Limited": "A carta só pode ser obtida uma única vez por jogador. Depois que a pessoa obtém a carta, ela nunca mais poderá pegá-la novamente, mesmo que venda, troque ou fique sem ela no inventário.",
}

# Para cada jogador Limited, coloque a história/descrição que quiser.
# O card é encontrado automaticamente no PLAYERS_CATALOG e exibido junto.
ABOUT_LIMITED = {
    "Bolsonaro": "**Ex-Presidente do Brasil pelo Partido Social Liberal (PSL)** no ano de 2018.",
    "Lula": "Atual **Presidente do Brasil pelo Partido dos Trabalhadores (PT)**, foi também eleito nos anos de 2002 e 2006.",
    "Trick": "**Trick** is a Romanian forward and one of the oldest and most legendary players in the game. Throughout his career, he won numerous titles in leagues such as TSW and remained in Division 1 since its earliest days. Known for his consistency and experience, Trick built a legacy that few players could match. Although he is now retired, his name remains remembered as one of the greats of his era.",
    "Baller": "**Baller** was one of the most influential defenders in the history of the game, known for revolutionizing the way the position was played. He was among the first defenders to adopt a much more offensive style, fearlessly using Neros while still maintaining his role at the back. His unique approach changed the way people viewed defending and inspired a new generation of players. Baller’s impact went far beyond his own performances, leaving behind a legacy that shaped the game itself.",
    "Fang": "**Fang** is one of the long-standing names in the community, known for his consistency at the highest divisions of TSW. Throughout the years, he has remained a respected presence within the European community, consistently competing at a high level. His longevity and dedication have made him a recognizable figure among the old generation of players, leaving a lasting mark on the community.",
    "Shanks": "**Shanks** é um dos jogadores mais vitoriosos, longevos e impactantes da história do Brasil. Considerado o melhor jogador do país desde 2025, manteve seu nível de desempenho ao longo dos anos e continua competindo em alto nível contra alguns dos melhores jogadores do mundo. Sua trajetória inclui passagens marcantes pelas principais ligas, como TSW e ATF, além de diversos títulos conquistados nas maiores competições. Sua consistência, longevidade e coleção de conquistas fizeram de Shanks um dos nomes mais importantes da história da comunidade brasileira.",
    "Aby": "**Aby** é um dos jogadores mais antigos e respeitados da comunidade, tendo provado sua capacidade tanto no futebol de gerações passadas quanto no cenário atual. Mesmo enfrentando jogadores da nova geração, Aby continua demonstrando seu nível e sua capacidade de adaptação. Sua longevidade e consistência fazem dele um verdadeiro exemplo de jogador atemporal, capaz de se adaptar às mudanças do jogo sem perder sua relevância.",
    "J3": "**J3** é um jogador extremamente criativo, conhecido por sua capacidade de se reinventar e encontrar novas formas de se destacar dentro do jogo. Essa versatilidade ficou evidente em 2025, quando alcançou o topo do cenário brasileiro mesmo competindo ao lado de nomes como Pitbull, Aby e Shanks. Sua criatividade, adaptação e constante evolução fizeram de J3 um dos jogadores mais marcantes de sua geração.",
    # Se adicionar outro Limited ao catálogo, acrescente:
    # "NomeDoLimited": "Descrição sobre esse Limited.",
}

# Abertura de vários pacotes
ABRIR_QUANTIDADE_MAX = 10
ABRIR_QUANTIDADE_MAX_BOOSTER = 20
ABRIR_QUANTIDADE_COOLDOWN_MINUTOS = 1

# Pacote Icon
# Só pode ser aberto individualmente e possui cooldown próprio.
ICON_COOLDOWN_MINUTOS = 10

# Nomes personalizados
NOME_TIME_PADRAO = "Time Sem Nome"
NOME_ESTADIO_PADRAO = "Meu Estádio"

# Transfer Market
TRANSFER_MARKET_MAX_ANUNCIOS = 20

# Minigames
ADIVINHE_RECOMPENSA_BASE = 20
ADIVINHE_RECOMPENSA_POS_5 = 40
ADIVINHE_RECOMPENSA_POS_10 = 60
ADIVINHE_MAX_TENTATIVAS = 4
ADIVINHE_TIMEOUT_ATE_5 = 30
ADIVINHE_TIMEOUT_5_ATE_10 = 15
ADIVINHE_TIMEOUT_POS_10 = 5
ADIVINHE_COOLDOWN_MINUTOS = 30
DRAFT_OPCOES_POR_RODADA = 4
DRAFT_RODADAS = 4
DRAFT_TIMEOUT_SEGUNDOS = 180
DRAFT_MAQUINA_MEDIA_MIN = 80
DRAFT_MAQUINA_MEDIA_MAX = 85
DRAFT_RECOMPENSA_VITORIA = 50
DRAFT_COOLDOWN_MINUTOS = 15
DRAFT_POSICOES = ["GK", "MC", "ST", "ST"]

# Batalha
BATALHA_TIMEOUT_CONFIRMACAO = 60  # segundos que o oponente tem pra aceitar o desafio

# Amistoso (era "campeonato" — renomeado; contra a máquina, partida única)
AMISTOSO_MEDIA_ALVO = 85  # overall médio que o time da máquina tenta ter
AMISTOSO_FATOR_DIFICULDADE = 2.0  # o quanto a média abaixo do alvo reduz os ratings do time (não o placar)
AMISTOSO_RECOMPENSA = 30  # Robux ganhos ao vencer
AMISTOSO_COOLDOWN_MINUTOS = 15

# Campeonato (torneio de mata-mata: quartas -> semis -> final, contra a máquina)
# Reaproveita o mesmo fator de dificuldade do amistoso, só muda o overall médio
# alvo da máquina a cada fase.
CAMPEONATO_FASES = [
    {"nome": "Quartas de Final", "media_alvo": 70},
    {"nome": "Semifinal", "media_alvo": 75},
    {"nome": "Final", "media_alvo": 80},]
CAMPEONATO_RECOMPENSA_FINAL = 300  # Robux ganhos só ao vencer a Final (ser campeão)
CAMPEONATO_COOLDOWN_MINUTOS = 90  # cooldown pra INICIAR um campeonato novo (não afeta trocar de fase)

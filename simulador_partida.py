"""Simulador de partidas — attribute based.

IMPORTANTE:
- As posições originais são mantidas: ST, MC e GK.
- Nenhuma posição nova é criada.
- O placar é consequência da simulação.
- Os atributos individuais são a principal fonte de diferença.
- O random existe para representar a imprevisibilidade do futebol.

ATRIBUTOS:
GK: POS, KIC, PAS, REF, DIV, VIS
Linha: POS, SHO, PAS, DRI, DEF, VIS

COMO BALANCEAR:
Altere principalmente CONFIG no começo do arquivo.
"""

import random


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

CONFIG = {
    # Atributos praticamente dominam a partida.
    "peso_atributos": 0.97,
    "peso_random": 0.03,

    # Diferenças de força passam a ter MUITO mais peso.
    "forca_diferenca": 1.80,

    # Momento continua existindo, mas não consegue destruir
    # uma diferença grande de qualidade.
    "forca_momento": 0.05,

    # ------------------------------------------------------------
    # IMPORTÂNCIA DOS ATRIBUTOS
    # ------------------------------------------------------------

    "criacao": {
        "PAS": 0.35,
        "VIS": 0.25,
        "DRI": 0.20,
        "POS": 0.20,
    },

    "finalizacao": {
        "SHO": 0.65,
        "POS": 0.20,
        "DRI": 0.15,
    },

    "goleiro": {
        "REF": 0.45,
        "DIV": 0.35,
        "POS": 0.20,
    },

    "posse": {
        "PAS": 0.45,
        "VIS": 0.30,
        "POS": 0.25,
    },

    "defesa": {
        "DEF": 0.55,
        "POS": 0.25,
        "VIS": 0.20,
    },

    # ------------------------------------------------------------
    # FREQUÊNCIA DAS CHANCES
    # ------------------------------------------------------------

    "chance_base": 0.30,
    "chance_min": 0.05,
    "chance_max": 0.90,

    "chance_clara_base": 0.22,
    "chance_clara_min": 0.02,
    "chance_clara_max": 0.80,

    "no_alvo_normal": 0.40,
    "no_alvo_clara": 0.68,

    "gol_normal_base": 0.14,
    "gol_claro_base": 0.36,

    "gol_min": 0.01,
    "gol_max": 0.90,
}

ATRIBUTOS_GK = ("POS", "KIC", "PAS", "REF", "DIV", "VIS")
ATRIBUTOS_LINHA = ("POS", "SHO", "PAS", "DRI", "DEF", "VIS")


# ============================================================================
# UTILITÁRIOS
# ============================================================================

def _clamp(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def _media(valores):
    return sum(valores) / len(valores) if valores else 0.0


def _media_por_posicao(jogadores, posicao):
    valores = [
        j["overall"]
        for j in jogadores
        if j["position"] == posicao
    ]

    if valores:
        return _media(valores)

    return _media([j["overall"] for j in jogadores])


def _attr(jogador, atributo):
    """Usa o atributo; se ele ainda não existir, usa overall como fallback."""
    return float(
        jogador.get(
            atributo,
            jogador.get("overall", 50)
        )
    )


def _media_attr(jogadores, atributo, fallback=50):
    if not jogadores:
        return fallback

    return _media([
        _attr(j, atributo)
        for j in jogadores
    ])


def _score_ponderado(jogador, pesos):
    total = 0.0
    peso_total = 0.0

    for atributo, peso in pesos.items():
        total += _attr(jogador, atributo) * peso
        peso_total += peso

    if peso_total == 0:
        return _attr(jogador, "overall")

    return total / peso_total


def _tem_atributos_detalhados(jogador):
    return (
        any(chave in jogador for chave in ATRIBUTOS_GK)
        or any(chave in jogador for chave in ATRIBUTOS_LINHA)
    )


# ============================================================================
# ESCOLHA DOS JOGADORES
# ============================================================================

def _escolher_melhor_por_atributos(jogadores, pesos):
    if not jogadores:
        return None

    scores = [
        _score_ponderado(j, pesos)
        for j in jogadores
    ]

    maior = max(scores)

    # O melhor jogador é escolhido na grande maioria das vezes.
    # Só jogadores praticamente equivalentes podem disputar a escolha.
    candidatos = [
        j
        for j, score in zip(jogadores, scores)
        if score >= maior - 2
    ]

    if len(candidatos) == 1:
        return candidatos[0]

    # Mesmo entre jogadores próximos, favorece fortemente o melhor.
    candidatos.sort(
        key=lambda j: _score_ponderado(j, pesos),
        reverse=True
    )

    if random.random() < 0.92:
        return candidatos[0]

    return random.choice(candidatos)

def _escolher_criador(jogadores):
    # Mantém SOMENTE as posições originais.
    candidatos = [
        j for j in jogadores
        if j["position"] == "MC"
    ]

    if not candidatos:
        candidatos = [
            j for j in jogadores
            if j["position"] == "ST"
        ]

    return _escolher_melhor_por_atributos(
        candidatos,
        CONFIG["criacao"]
    )


def _escolher_finalizador(jogadores):
    # ST continua sendo a posição principal de finalização.
    candidatos = [
        j for j in jogadores
        if j["position"] == "ST"
    ]

    if not candidatos:
        candidatos = [
            j for j in jogadores
            if j["position"] != "GK"
        ]

    return _escolher_melhor_por_atributos(
        candidatos,
        CONFIG["finalizacao"]
    )


def _escolher_finalizador_com_mc(atacante, finalizador_st):
    """ST é o finalizador padrão; MC 80+ pode aparecer ocasionalmente."""
    mcs_bons = [
        j for j in atacante.jogadores
        if j["position"] == "MC" and float(j.get("overall", 0)) >= 80
    ]

    # Mesmo um MC excelente só recebe uma pequena parte das finalizações.
    if mcs_bons and random.random() < 0.14:
        return _escolher_melhor_por_atributos(
            mcs_bons,
            CONFIG["finalizacao"]
        )

    return finalizador_st


# ============================================================================
# RATINGS DO TIME
# ============================================================================

def _ratings_por_atributos(jogadores):
    # POSIÇÕES ORIGINAIS — NÃO ALTERADAS.
    goleiros = [
        j for j in jogadores
        if j["position"] == "GK"
    ]

    linha = [
        j for j in jogadores
        if j["position"] != "GK"
    ]

    st = [
        j for j in jogadores
        if j["position"] == "ST"
    ]

    mc = [
        j for j in jogadores
        if j["position"] == "MC"
    ]

    # Se faltar uma posição, usa os jogadores disponíveis como fallback.
    st_base = st or linha or jogadores
    mc_base = mc or linha or jogadores
    gk_base = goleiros or jogadores

    ataque = (
        _media_attr(st_base, "SHO") * 0.50
        + _media_attr(st_base, "DRI") * 0.20
        + _media_attr(mc_base, "PAS") * 0.15
        + _media_attr(st_base, "POS") * 0.15
    )

    defesa = (
        _media_attr(linha, "DEF") * 0.55
        + _media_attr(linha, "POS") * 0.20
        + _media_attr(mc_base, "DEF") * 0.10
        + _media_attr(gk_base, "DIV") * 0.15
    )

    posse = (
        _media_attr(mc_base, "PAS") * 0.45
        + _media_attr(mc_base, "VIS") * 0.25
        + _media_attr(jogadores, "POS") * 0.30
    )

    goleiro = (
        _media_attr(gk_base, "REF") * 0.45
        + _media_attr(gk_base, "DIV") * 0.35
        + _media_attr(gk_base, "KIC") * 0.20
    )

    return {
        "ataque": ataque,
        "defesa": defesa,
        "posse": posse,
        "goleiro": goleiro,
    }


def _ratings_por_overall(jogadores):
    """Fallback para jogadores que ainda não possuem atributos detalhados."""
    media_st = _media_por_posicao(jogadores, "ST")
    media_mc = _media_por_posicao(jogadores, "MC")
    media_gk = _media_por_posicao(jogadores, "GK")

    return {
        "ataque": media_st * 0.70 + media_mc * 0.30,
        "defesa": media_gk * 0.55 + media_mc * 0.45,
        "posse": media_mc * 0.60 + media_st * 0.20 + media_gk * 0.20,
        "goleiro": media_gk,
    }


def calcular_ratings_time(jogadores):
    if any(
        _tem_atributos_detalhados(j)
        for j in jogadores
    ):
        return _ratings_por_atributos(jogadores)

    return _ratings_por_overall(jogadores)


def _aplicar_dificuldade(
    ratings,
    jogadores,
    media_alvo,
    fator_dificuldade
):
    if media_alvo is None or fator_dificuldade <= 0:
        return ratings

    media_time = _media([
        j["overall"]
        for j in jogadores
    ])

    if media_time >= media_alvo:
        return ratings

    deficit = media_alvo - media_time
    reducao = min(
        0.70,
        (deficit * fator_dificuldade) / 100.0
    )

    fator = 1.0 - reducao

    return {
        chave: valor * fator
        for chave, valor in ratings.items()
    }


# ============================================================================
# ESTADO DA PARTIDA
# ============================================================================

class _EstadoTime:
    def __init__(self, nome, jogadores, ratings):
        self.nome = nome
        self.jogadores = jogadores
        self.ratings_base = ratings

        # Momento da partida.
        self.controle = 0.0

        self.gols = 0
        self.artilheiros = []
        self.fase_taticas_ativada = False

    def rating_efetivo(
        self,
        chave,
        diferenca_gols,
        minuto
    ):
        base = self.ratings_base[chave]

        fator_controle = (
            1.0
            + self.controle * CONFIG["forca_momento"]
        )

        fator_tatico = _fator_tatico(
            chave,
            diferenca_gols,
            minuto
        )

        return base * fator_controle * fator_tatico

    def ajustar_controle(self, delta):
        self.controle = _clamp(
            self.controle + delta,
            -1.0,
            1.0
        )

    def decair_controle(self):
        self.controle *= 0.90


def _fator_tatico(
    chave,
    diferenca_gols,
    minuto
):
    """
    Mantém a lógica original:
    time perdendo assume mais risco.
    """

    if diferenca_gols <= -3:
        ajuste = {
            "ataque": 1.28,
            "defesa": 0.78
        }

    elif diferenca_gols == -2:
        ajuste = {
            "ataque": 1.16,
            "defesa": 0.88
        }

    elif diferenca_gols == -1 and minuto >= 65:
        ajuste = {
            "ataque": 1.08,
            "defesa": 0.95
        }

    else:
        ajuste = {}

    return ajuste.get(chave, 1.0)


# ============================================================================
# POSSE
# ============================================================================

def _decidir_time_com_posse(
    time_a,
    time_b,
    minuto
):
    diff_a = time_a.gols - time_b.gols
    diff_b = -diff_a

    rating_a = time_a.rating_efetivo(
        "posse",
        diff_a,
        minuto
    )

    rating_b = time_b.rating_efetivo(
        "posse",
        diff_b,
        minuto
    )

    # A posse deve responder aos atributos do time, e não apenas ao OVR.
    # O rating de posse já considera PAS/VIS/POS dos jogadores.
    diferenca_posse = rating_a - rating_b

    fator_a = max(
        0.08,
        rating_a * (1.0 + diferenca_posse / 70.0)
    )

    fator_b = max(
        0.08,
        rating_b * (1.0 - diferenca_posse / 70.0)
    )

    fator_a = fator_a ** 2.2
    fator_b = fator_b ** 2.2

    total = fator_a + fator_b
    prob_a = fator_a / total

    # Times muito diferentes praticamente não perdem a posse
    # para o adversário inferior.
    diferenca_abs = abs(diferenca_posse)

    if diferenca_abs >= 18:
        prob_a = 0.94 if diferenca_posse > 0 else 0.06

    elif diferenca_abs >= 12:
        prob_a = 0.87 if diferenca_posse > 0 else 0.13

    elif diferenca_abs >= 8:
        prob_a = 0.79 if diferenca_posse > 0 else 0.21

    if random.random() < prob_a:
        return time_a, time_b

    return time_b, time_a


# ============================================================================
# CRIAÇÃO DA JOGADA
# ============================================================================

def _qualidade_criacao(
    atacante,
    defensor
):
    criador = _escolher_criador(
        atacante.jogadores
    )

    if criador is None:
        return 30.0, None

    qualidade_criador = _score_ponderado(
        criador,
        CONFIG["criacao"]
    )

    defensores = [
        j for j in defensor.jogadores
        if j["position"] != "GK"
    ]

    defesa_media = _media_attr(
        defensores,
        "DEF",
        50
    )

    vantagem = (
        qualidade_criador
        - defesa_media
    ) * CONFIG["forca_diferenca"]

    qualidade = (
        qualidade_criador
        + vantagem * 0.35
    )

    return _clamp(
        qualidade,
        5,
        100
    ), criador


# ============================================================================
# FINALIZAÇÃO
# ============================================================================

def _qualidade_finalizacao(
    atacante,
    defensor
):
    finalizador = _escolher_finalizador(
        atacante.jogadores
    )

    if finalizador is None:
        return 30.0, None

    qualidade_finalizador = _score_ponderado(
        finalizador,
        CONFIG["finalizacao"]
    )

    goleiro = next(
        (
            j for j in defensor.jogadores
            if j["position"] == "GK"
        ),
        None
    )

    qualidade_goleiro = (
        _score_ponderado(
            goleiro,
            CONFIG["goleiro"]
        )
        if goleiro
        else 50
    )

    vantagem = (
        qualidade_finalizador
        - qualidade_goleiro
    ) * CONFIG["forca_diferenca"]

    qualidade = (
        qualidade_finalizador
        + vantagem * 0.30
    )

    return _clamp(
        qualidade,
        5,
        100
    ), finalizador


# ============================================================================
# UMA FASE DE ATAQUE
# ============================================================================

def _simular_fase(
    atacante,
    defensor,
    minuto
):
    diff_atacante = (
        atacante.gols
        - defensor.gols
    )

    diff_defensor = -diff_atacante

    ataque = atacante.rating_efetivo(
        "ataque",
        diff_atacante,
        minuto
    )

    defesa = defensor.rating_efetivo(
        "defesa",
        diff_defensor,
        minuto
    )

    # ------------------------------------------------------------
    # 1. CRIAÇÃO
    # ------------------------------------------------------------

    criacao, criador = _qualidade_criacao(
        atacante,
        defensor
    )

    diferenca = (
        ataque - defesa
    ) * CONFIG["forca_diferenca"]

    media_ovr_atacante = _media([
        j["overall"] for j in atacante.jogadores
    ])

    media_ovr_defensor = _media([
        j["overall"] for j in defensor.jogadores
    ])

    diferenca_ovr = (
        media_ovr_atacante
        - media_ovr_defensor
    )

    # Diferença de força baseada nos ATRIBUTOS reais.
    # Isso evita que um jogador 92+ seja tratado quase como um 80
    # só porque a média do time mudou pouco.
    rating_ataque = atacante.rating_efetivo("ataque", diff_atacante, minuto)
    rating_defesa = defensor.rating_efetivo("defesa", diff_defensor, minuto)
    diferenca_atributos = rating_ataque - rating_defesa

    # ------------------------------------------------------------
    # DOMÍNIO DE FORÇA
    # ------------------------------------------------------------

    # Quanto maior a diferença de OVR, mais difícil fica para
    # o time inferior sequer criar uma oportunidade.

    # A diferença de atributos é a principal fonte de vantagem.
    # O OVR entra apenas como pequeno desempate, para não substituir
    # os atributos detalhados.
    bonus_forca = _clamp(
        (diferenca_atributos / 55.0)
        + (diferenca_ovr / 500.0),
        -0.34,
        0.34,
    )

    prob_chance = _clamp(
        0.40
        + bonus_forca
        + (criacao - 50) / 500.0,
        0.06,
        0.90
    )

    # A força do time domina a criação.
    # O random só adiciona uma pequena variação.
    decisao = (
        prob_chance * 0.985
        + random.random() * 0.015
    )

    if decisao < 0.42:
        atacante.decair_controle()
        defensor.decair_controle()
        return None

    # ------------------------------------------------------------
    # 2. CHANCE CLARA
    # ------------------------------------------------------------

    prob_clara = _clamp(
        0.20
        + (diferenca_atributos / 110.0)
        + (criacao - 50) / 450.0,
        0.025,
        0.75
    )

    chance_clara = (
        random.random()
        < prob_clara
    )

    # ------------------------------------------------------------
    # 3. FINALIZAÇÃO
    # ------------------------------------------------------------

    finalizacao, finalizador_st = (
        _qualidade_finalizacao(
            atacante,
            defensor
        )
    )

    finalizador = _escolher_finalizador_com_mc(
        atacante,
        finalizador_st
    )

    # MC que entra como finalizador é deliberadamente penalizado:
    # ele pode marcar, mas ST continua tendo vantagem natural.
    if (
        finalizador is not None
        and finalizador["position"] == "MC"
    ):
        finalizacao *= 0.84

    prob_no_alvo = (
        CONFIG["no_alvo_clara"]
        if chance_clara
        else CONFIG["no_alvo_normal"]
    )

    prob_no_alvo += (
        finalizacao - 50
    ) / 220.0

    # MC tem mais dificuldade para transformar a finalização
    # em chute no alvo.
    if (
        finalizador is not None
        and finalizador["position"] == "MC"
    ):
        prob_no_alvo -= 0.10

    prob_no_alvo = _clamp(
        prob_no_alvo,
        0.15,
        0.90
    )

    # ------------------------------------------------------------
    # DINÂMICAS DA JOGADA
    # ------------------------------------------------------------

    dinamica = random.random()

    if dinamica < 0.03:
        jogador_dinamico = criador or finalizador

        atacante.ajustar_controle(0.02)

        return {
            "tipo": "drible",
            "time": atacante.nome,
            "jogador": (
                jogador_dinamico["name"]
                if jogador_dinamico
                else "Jogador"
            )
        }

    if dinamica < 0.055:
        jogador_dinamico = criador or finalizador

        atacante.ajustar_controle(0.02)

        return {
            "tipo": "passe_chave",
            "time": atacante.nome,
            "jogador": (
                jogador_dinamico["name"]
                if jogador_dinamico
                else "Jogador"
            )
        }

    if dinamica < 0.08:
        defensor_j = _escolher_melhor_por_atributos(
            [
                j
                for j in defensor.jogadores
                if j["position"] != "GK"
            ] or defensor.jogadores,
            CONFIG["defesa"]
        )

        defensor.ajustar_controle(0.03)
        atacante.ajustar_controle(-0.02)

        return {
            "tipo": "desarme",
            "time": defensor.nome,
            "jogador": (
                defensor_j["name"]
                if defensor_j
                else "Jogador"
            )
        }

    if dinamica < 0.10:
        jogador_dinamico = finalizador or criador

        atacante.ajustar_controle(0.02)

        return {
            "tipo": "bola_na_trave",
            "time": atacante.nome,
            "jogador": (
                jogador_dinamico["name"]
                if jogador_dinamico
                else "Jogador"
            )
        }

    if dinamica < 0.13:
        jogador_dinamico = criador or finalizador

        atacante.ajustar_controle(0.01)

        return {
            "tipo": "cruzamento_sem_gol",
            "time": atacante.nome,
            "jogador": (
                jogador_dinamico["name"]
                if jogador_dinamico
                else "Jogador"
            )
        }

    if dinamica < 0.16:
        jogador_dinamico = finalizador or criador

        atacante.ajustar_controle(-0.01)
        defensor.ajustar_controle(0.01)

        return {
            "tipo": "cabeceio_fora",
            "time": atacante.nome,
            "jogador": (
                jogador_dinamico["name"]
                if jogador_dinamico
                else "Jogador"
            )
        }

    if dinamica < 0.19:
        jogador_dinamico = finalizador or criador

        atacante.ajustar_controle(-0.02)
        defensor.ajustar_controle(0.02)

        return {
            "tipo": "falta_ou_impedimento",
            "time": atacante.nome,
            "jogador": (
                jogador_dinamico["name"]
                if jogador_dinamico
                else "Jogador"
            )
        }

    # ------------------------------------------------------------
    # CHUTE
    # ------------------------------------------------------------

    if random.random() >= prob_no_alvo:
        atacante.ajustar_controle(-0.04)
        defensor.ajustar_controle(0.02)

        tipo = (
            "chance_perdida"
            if chance_clara
            else "chute_fora"
        )

        jogador = (
            finalizador
            if finalizador
            else criador
        )

        return {
            "tipo": tipo,
            "time": atacante.nome,
            "jogador": (
                jogador["name"]
                if jogador
                else "Jogador"
            )
        }

    # ------------------------------------------------------------
    # 4. GOL
    # ------------------------------------------------------------

    goleiro = next(
        (
            j
            for j in defensor.jogadores
            if j["position"] == "GK"
        ),
        None
    )

    qualidade_goleiro = (
        _score_ponderado(
            goleiro,
            CONFIG["goleiro"]
        )
        if goleiro
        else 50
    )

    vantagem = (
        finalizacao
        - qualidade_goleiro
    ) * CONFIG["forca_diferenca"]

    # A diferença de atributos já está presente em `finalizacao`;
    # O OVR entra só como pequeno ajuste de coerência.
    vantagem += diferenca_ovr * 0.12

    # MC 80+ pode marcar, mas fica abaixo do ST.
    if (
        finalizador is not None
        and finalizador["position"] == "MC"
    ):
        vantagem -= 7.0

    prob_gol = (
        CONFIG["gol_claro_base"]
        if chance_clara
        else CONFIG["gol_normal_base"]
    )

    prob_gol += vantagem / 135.0

    prob_gol = _clamp(
        prob_gol,
        CONFIG["gol_min"],
        CONFIG["gol_max"]
    )

    # ------------------------------------------------------------
    # PROTEÇÃO CONTRA GOLEADA DO TIME MAIS FRACO
    # ------------------------------------------------------------

    media_atacante = _media([
        j["overall"]
        for j in atacante.jogadores
    ])

    media_defensor = _media([
        j["overall"]
        for j in defensor.jogadores
    ])

    goleada_do_mais_fraco_bloqueada = (
        media_atacante < media_defensor
        and (atacante.gols - defensor.gols) >= 2
    )

    if goleada_do_mais_fraco_bloqueada:
        marcou_gol = False
    else:
        marcou_gol = (
            random.random()
            < prob_gol
        )

    if marcou_gol:
        atacante.ajustar_controle(0.20)
        defensor.ajustar_controle(-0.14)

        jogador = (
            finalizador
            if finalizador
            else criador
        )

        assistente = None

        if (
            criador
            and jogador
            and criador["name"] != jogador["name"]
            and random.random() < 0.55
        ):
            assistente = criador["name"]

        return {
            "tipo": "gol",
            "time": atacante.nome,
            "jogador": jogador["name"],
            "assistente": assistente
        }

    # ------------------------------------------------------------
    # 5. DEFESA DO GK
    # ------------------------------------------------------------

    atacante.ajustar_controle(-0.08)
    defensor.ajustar_controle(0.12)

    goleiro_nome = (
        goleiro["name"]
        if goleiro
        else "Goleiro"
    )

    return {
        "tipo": "defesa",
        "time": defensor.nome,
        "jogador": goleiro_nome
    }


# ============================================================================
# PARTIDA COMPLETA
# ============================================================================

def simular_partida(
    nome_time_a,
    time_a,
    nome_time_b,
    time_b,
    media_alvo_a=None,
    fator_dificuldade_a=0.0,
    media_alvo_b=None,
    fator_dificuldade_b=0.0,
):
    ratings_a = calcular_ratings_time(
        time_a
    )

    ratings_b = calcular_ratings_time(
        time_b
    )

    ratings_a = _aplicar_dificuldade(
        ratings_a,
        time_a,
        media_alvo_a,
        fator_dificuldade_a
    )

    ratings_b = _aplicar_dificuldade(
        ratings_b,
        time_b,
        media_alvo_b,
        fator_dificuldade_b
    )

    estado_a = _EstadoTime(
        nome_time_a,
        time_a,
        ratings_a
    )

    estado_b = _EstadoTime(
        nome_time_b,
        time_b,
        ratings_b
    )

    eventos_gol = []
    pool_lances_notaveis = []

    minuto = 0

    while minuto < 90:
        minuto += random.randint(2, 4)

        if minuto > 90:
            minuto = 90

        atacante, defensor = (
            _decidir_time_com_posse(
                estado_a,
                estado_b,
                minuto
            )
        )

        resultado = _simular_fase(
            atacante,
            defensor,
            minuto
        )

        if resultado is None:
            continue

        resultado["minuto"] = minuto

        if resultado["tipo"] == "gol":
            atacante.gols += 1

            atacante.artilheiros.append(
                resultado["jogador"]
            )

            eventos_gol.append(
                resultado
            )

            diferenca_apos_gol = (
                estado_a.gols
                - estado_b.gols
            )

            if abs(diferenca_apos_gol) >= 2:
                time_atras = (
                    estado_b
                    if diferenca_apos_gol > 0
                    else estado_a
                )

                if not time_atras.fase_taticas_ativada:
                    time_atras.fase_taticas_ativada = True

                    pool_lances_notaveis.append({
                        "tipo": "mudanca_tatica",
                        "time": time_atras.nome,
                        "minuto": minuto,
                    })

        else:
            pool_lances_notaveis.append(
                resultado
            )

    eventos_finais = list(
        eventos_gol
    )

    if pool_lances_notaveis:
        quantidade_mostrar = min(
            len(pool_lances_notaveis),
            random.randint(2, 4)
        )

        eventos_finais.extend(
            random.sample(
                pool_lances_notaveis,
                quantidade_mostrar
            )
        )

    eventos_finais.sort(
        key=lambda e: e["minuto"]
    )

    return {
        "eventos": eventos_finais,
        "placar_a": estado_a.gols,
        "placar_b": estado_b.gols,
    }

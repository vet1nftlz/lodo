"""Motor de narração de partidas.

A partida é SIMULADA de verdade (ver simulador_partida.py): força dos times,
momentum interno e mudanças táticas geram os acontecimentos, e o placar é uma
consequência disso — nunca um sorteio prévio. Este módulo aqui cuida só de
transformar os eventos simulados em texto e revelá-los aos poucos no Discord,
pra dar a sensação de partida ao vivo.
"""

import asyncio
import random

import discord

from simulador_partida import simular_partida


TEMPLATES_CHANCE_PERDIDA = [
    "Que chance incrível desperdiçada por {jogador}! Bola por cima do gol vazio!",
    "{jogador} fica cara a cara com o goleiro, mas isola a bola. Chance perdida!",
    "{jogador} recebe livre na área e manda pra fora! Inacreditável!",
    "{jogador} tinha só que empurrar pra dentro, mas erra o alvo!",
    "{jogador} recebe completamente livre e finaliza mal. Era praticamente um gol!",
    "{jogador} dribla o goleiro, mas demora para finalizar e perde a oportunidade!",
    "{jogador} domina dentro da área e chuta por cima! Que desperdício!",
    "{jogador} recebe um passe perfeito, mas pega muito embaixo da bola!",
    "{jogador} tenta colocar no canto, mas manda para fora quando tinha tudo para marcar!",
    "{jogador} aparece sozinho na pequena área e não consegue acertar o gol!",
    "{jogador} ganha da defesa na velocidade, mas finaliza sem direção!",
    "{jogador} recebe na cara do gol e o chute sai completamente torto!",
    "{jogador} tinha espaço de sobra, mas hesita e perde o melhor momento para finalizar!",
    "{jogador} chega livre no segundo pau, mas manda por cima!",
    "{jogador} tenta finalizar de primeira e pega muito mal na bola!",
    "{jogador} invade a área, ajeita para a perna boa e manda para fora!",
]

TEMPLATES_MUDANCA_TATICA = [
    "🔄 O treinador de {time} arrisca tudo: mais um jogador de ataque em campo!",
    "🔄 {time} parte pro tudo ou nada e empurra a linha lá na frente!",
    "🔄 Mudança tática em {time}: time inteiro joga mais adiantado em busca do gol.",
    "🔄 {time} sente a necessidade de reagir e assume mais risco no ataque.",
    "🔄 {time} adianta a marcação e começa a pressionar a saída adversária!",
    "🔄 O treinador de {time} pede mais intensidade e manda o time atacar pelos lados!",
    "🔄 {time} muda a postura e começa a trocar passes mais rapidamente no ataque.",
    "🔄 {time} recua por alguns instantes e passa a apostar nos contra-ataques.",
    "🔄 O treinador de {time} reorganiza o meio-campo para controlar melhor a posse.",
    "🔄 {time} coloca pressão alta e tenta recuperar a bola ainda no campo adversário.",
    "🔄 {time} fecha os espaços no meio e força o adversário a jogar pelas laterais.",
    "🔄 {time} aumenta o número de jogadores próximos da área adversária.",
]

TEMPLATES_GOL_SOZINHO = [
    "{atacante} recebe na entrada da área, ajeita e bate cruzado... GOOOL de {atacante}!",
    "{atacante} arranca em velocidade, driblou um, driblou outro e bate sem chances pro goleiro! Golaço!",
    "Bola alçada na área, {atacante} sobe mais alto que todo mundo e cabeceia pro fundo do gol!",
    "{atacante} pega de primeira, sem deixar a bola cair, e balança a rede! Que categoria!",
    "Contra-ataque fulminante! {atacante} recebe sozinho na cara do gol e não perdoa!",
    "{atacante} bate de bico no canto, o goleiro nem se mexeu. Que finalização!",
    "{atacante} invade a área, ajeita o corpo e bate cruzado no ângulo! Sem chances pro goleiro!",
    "Roubada de bola no campo de ataque, {atacante} avança e chuta forte no canto. GOL!",
    "{atacante} pega de bicicleta e manda pro fundo da rede! Que gol espetacular!",
    "Cobrança de falta e {atacante} acerta o ângulo com categoria! Golaço de placa!",
    "{atacante} arrisca de longe, a bola desvia e engana o goleiro. Gol sem querer, mas vale!",
    "{atacante} aproveita o rebote e não perdoa: bate forte e marca!",
    "{atacante} recebe na entrada da área e coloca a bola no cantinho. GOL!",
    "{atacante} corta para dentro e solta uma bomba de fora da área! GOLAÇO!",
    "{atacante} ganha no corpo, invade a área e finaliza rasteiro no canto!",
    "{atacante} recebe de costas, gira rapidamente e bate antes da defesa reagir!",
    "{atacante} antecipa o zagueiro, fica livre e toca na saída do goleiro!",
    "{atacante} aproveita a bola viva na área e finaliza de primeira para marcar!",
    "{atacante} recebe pela esquerda, corta para o meio e manda no ângulo!",
    "{atacante} dispara pelo corredor central e finaliza com muita força. GOL!",
]

TEMPLATES_GOL_COM_ASSIST = [
    "{assistente} enfia um passe perfeito, {atacante} só empurra pra dentro! GOL!",
    "Jogada bonita: {assistente} cruza rasteiro e {atacante} chega batendo forte. Sem chances!",
    "{assistente} rouba a bola no meio-campo, lança {atacante} na área e ele não desperdiça!",
    "Cobrança de escanteio, {assistente} bate na área, {atacante} sobe e cabeceia com estilo!",
    "{assistente} vê {atacante} livre e toca na medida. Gol fácil!",
    "Triangulação rápida entre {assistente} e {atacante}, que finaliza no cantinho! GOL!",
    "{assistente} arranca pela ponta, cruza na medida e {atacante} testa pro gol!",
    "Contra-ataque relâmpago: {assistente} lança em profundidade e {atacante} bate na saída do goleiro!",
    "{assistente} gira e vê {atacante} nas costas da defesa — passe cirúrgico e GOL!",
    "{assistente} recebe no meio, espera o momento certo e deixa {atacante} na cara do gol!",
    "{assistente} faz uma tabela rápida e encontra {atacante} livre dentro da área!",
    "{assistente} coloca a bola entre dois defensores e {atacante} aparece para finalizar!",
    "{assistente} cruza fechado e {atacante} desvia de primeira para o fundo da rede!",
    "{assistente} recupera a posse e imediatamente aciona {atacante}, que finaliza com precisão!",
    "{assistente} conduz pelo meio e enfia uma bola nas costas da defesa para {atacante}!",
    "{assistente} recebe aberto, levanta a cabeça e encontra {atacante} sozinho no segundo pau!",
    "{assistente} toca de calcanhar e deixa {atacante} em ótima posição para marcar!",
    "{assistente} faz um passe rasteiro perfeito e {atacante} chega batendo de primeira!",
]

TEMPLATES_SEM_GOL = {
    "chute_fora": [
        "{jogador} arrisca de fora da área... a bola sobra pela linha de fundo.",
        "{jogador} bate forte, mas manda a bola pra arquibancada!",
        "{jogador} tenta o chute cruzado, mas a bola passa raspando a trave.",
        "{jogador} finaliza colocado, só um pouco pra fora!",
        "{jogador} bate cruzado, a bola passa perto do ângulo e sai!",
        "{jogador} chuta de primeira, mas isola a jogada!",
        "{jogador} tenta encobrir o goleiro, mas a bola vai longe demais!",
        "{jogador} recebe na entrada da área e manda por cima do gol!",
        "{jogador} arrisca de longe, mas a bola sai sem direção.",
        "{jogador} tenta colocar no canto, mas erra por pouco!",
        "{jogador} bate forte de fora da área, mas a bola passa ao lado da trave!",
        "{jogador} pega de primeira, porém a finalização sai fraca e para fora!",
        "{jogador} ajeita e solta uma bomba, mas a bola sobe demais!",
        "{jogador} tenta o chute rasteiro, mas a bola passa raspando o poste!",
        "{jogador} domina e finaliza rapidamente, mas manda para fora!",
    ],

    "defesa": [
        "Que defesaça! {jogador} espalma a bola e evita o gol certo!",
        "{jogador} sai bem do gol e agarra a bola antes do chute!",
        "{jogador} faz milagre e tira em cima da linha!",
        "{jogador} se estica todo e desvia pra escanteio!",
        "{jogador} lê a jogada e sai pra cortar antes do chute!",
        "{jogador} salta no canto certo e defende com categoria!",
        "{jogador} bloqueia o chute com o corpo, evitando o gol!",
        "{jogador} cai rapidamente no canto e segura a finalização!",
        "{jogador} espalma para longe e salva a equipe!",
        "{jogador} fecha o ângulo e impede a finalização de entrar!",
        "{jogador} voa para fazer uma defesa espetacular!",
        "{jogador} acompanha a trajetória e encaixa a bola com segurança!",
        "{jogador} reage rapidamente e desvia a bola para escanteio!",
        "{jogador} salva com a ponta dos dedos! Defesa importantíssima!",
        "{jogador} fica cara a cara com o atacante e leva a melhor!",
        "{jogador} se posiciona perfeitamente e defende sem dar rebote!",
        "{jogador} espalma a pancada e evita um golaço!",
        "{jogador} sai do gol no momento certo e mata a jogada!",
    ],

    "cruzamento_sem_gol": [
        "{jogador} cruza na área, mas ninguém consegue alcançar a bola.",
        "Bola na área depois do cruzamento de {jogador}, mas a zaga afasta o perigo.",
        "{jogador} tenta o cruzamento, mas a defesa corta antes.",
        "{jogador} levanta a bola na área, mas ela sobra direto pro goleiro.",
        "{jogador} cruza tenso, a bola bate na zaga e sai pela linha de fundo.",
        "{jogador} manda a bola para a área, mas o atacante chega atrasado.",
        "{jogador} cruza rasteiro, porém a defesa consegue interceptar.",
        "{jogador} tenta encontrar alguém na área, mas o cruzamento passa por todo mundo.",
        "{jogador} coloca a bola na área, mas o goleiro sai e fica com ela.",
        "{jogador} faz um cruzamento perigoso, mas ninguém aparece para completar.",
        "{jogador} levanta na segunda trave, mas a bola sai pela linha de fundo.",
        "{jogador} tenta o cruzamento de primeira, mas manda forte demais.",
    ],

    "cabeceio_fora": [
        "{jogador} sobe bem, mas cabeceia por cima do gol!",
        "{jogador} testa a bola, mas ela explode na trave e sai!",
        "{jogador} chega atrasado no cabeceio e a bola passa perto!",
        "{jogador} cabeceia forte, mas sem direção, e a bola vai pra fora!",
        "{jogador} ganha pelo alto, mas manda a bola ao lado do gol!",
        "{jogador} sobe sozinho, porém não consegue direcionar a cabeçada!",
        "{jogador} testa com força, mas a bola passa por cima do travessão!",
        "{jogador} chega primeiro na bola, mas cabeceia para fora!",
        "{jogador} tenta colocar no canto de cabeça, mas erra o alvo!",
        "{jogador} cabeceia no meio da área, mas sem força suficiente!",
    ],

    "falta_ou_impedimento": [
        "🚩 Lance chega a balançar a rede, mas o VAR aponta impedimento de {jogador}!",
        "🟨 Falta dura em {jogador} interrompe o ritmo da partida.",
        "🚩 {jogador} recebe em posição irregular, jogada anulada.",
        "⚠️ Bola na trave depois de um desvio em {jogador} — muito perto!",
        "🚩 {jogador} dispara antes da hora e é flagrado em impedimento.",
        "🟨 {jogador} sofre uma falta no meio-campo e a jogada é interrompida.",
        "🚩 O árbitro marca impedimento de {jogador} no momento da infiltração.",
        "🟨 {jogador} é derrubado e o árbitro paralisa a partida.",
        "⚠️ O ataque de {jogador} é interrompido por uma falta na entrada da área.",
        "🚩 Passe encontra {jogador}, mas a arbitragem marca posição irregular.",
    ],

    "drible": [
        "{jogador} parte pra cima, corta o marcador e ganha espaço no ataque!",
        "{jogador} dá um corte rápido no defensor e acelera pela lateral!",
        "{jogador} recebe pressionado, gira sobre o marcador e mantém a posse!",
        "{jogador} aplica uma caneta no marcador e deixa a torcida em festa!",
        "{jogador} dá dois cortes rápidos e consegue escapar da marcação!",
        "{jogador} finta para um lado, corta para o outro e passa pelo defensor!",
        "{jogador} domina cercado por adversários e consegue sair jogando!",
        "{jogador} muda de direção rapidamente e deixa o marcador para trás!",
        "{jogador} conduz a bola e passa entre dois jogadores adversários!",
        "{jogador} usa o corpo para proteger a bola e escapa da pressão!",
        "{jogador} parte pela ponta e deixa o marcador completamente para trás!",
        "{jogador} recebe no espaço, corta para dentro e cria perigo!",
    ],

    "passe_chave": [
        "{jogador} encontra um passe entre as linhas e deixa o ataque em boa posição!",
        "{jogador} levanta a cabeça e acha um companheiro infiltrando na área!",
        "Passe de muita visão de {jogador}, quebrando a marcação adversária!",
        "{jogador} enfia uma bola perfeita nas costas da defesa!",
        "{jogador} encontra um corredor e coloca o companheiro em ótima posição!",
        "{jogador} faz um lançamento preciso para o ataque!",
        "{jogador} toca rápido e quebra duas linhas de marcação!",
        "{jogador} vê o espaço antes de todo mundo e aciona o companheiro!",
        "{jogador} coloca a bola exatamente onde o atacante precisava!",
        "{jogador} dá um passe vertical e acelera a jogada!",
        "{jogador} encontra o companheiro entre os defensores e cria uma grande oportunidade!",
        "{jogador} faz uma inversão precisa e muda completamente o lado da jogada!",
    ],

    "desarme": [
        "{jogador} chega firme na marcação e recupera a bola no momento exato!",
        "{jogador} lê a jogada e toma a bola antes do adversário finalizar!",
        "Desarme preciso de {jogador}, cortando um ataque que parecia perigoso!",
        "{jogador} aparece por trás e tira a bola com precisão!",
        "{jogador} antecipa o adversário e recupera a posse!",
        "{jogador} trava a finalização no momento certo!",
        "{jogador} fecha o espaço e rouba a bola sem cometer falta!",
        "{jogador} acompanha o atacante e consegue recuperar a bola!",
        "{jogador} intercepta a jogada e impede o contra-ataque!",
        "{jogador} faz um carrinho preciso e salva a defesa!",
        "{jogador} ganha a dividida e mantém a posse para sua equipe!",
        "{jogador} se posiciona bem e corta o passe antes que ele chegue ao atacante!",
    ],

    "bola_na_trave": [
        "{jogador} solta uma pancada e a bola explode na trave! Quase um golaço!",
        "Na trave! {jogador} acerta o poste e a bola volta para a área!",
        "{jogador} bate colocado e carimba a trave — o goleiro estava vendido!",
        "{jogador} recebe na entrada da área e acerta o travessão!",
        "QUE CHANCE! {jogador} finaliza e a bola beija a trave antes de sair!",
        "{jogador} chuta forte no canto e acerta o poste!",
        "A torcida já gritava gol, mas a finalização de {jogador} explode no travessão!",
        "{jogador} cobra a falta com perfeição, mas a bola encontra a trave!",
        "{jogador} bate colocado e vê a bola voltar depois de acertar o poste!",
        "Por muito pouco! {jogador} acerta a trave e perde uma chance incrível!",
    ],

    "torcida": [
        "📣 A torcida grita animada nas arquibancadas!",
        "📣 Início disputado, as duas equipes se estudam em campo.",
        "📣 O ritmo da partida esquenta!",
        "📣 A torcida vaia a arbitragem depois do último lance.",
        "📣 Momento de pressão — o time parece querer o gol com mais intensidade!",
        "📣 A torcida começa a cantar e empurra o time para o ataque!",
        "📣 O estádio aumenta o volume depois de uma grande chance!",
        "📣 A torcida reage a uma sequência de boas jogadas!",
        "📣 Clima de tensão: qualquer erro pode mudar a partida!",
        "📣 A arquibancada explode depois de uma dividida forte!",
        "📣 O jogo fica mais intenso e a torcida percebe!",
        "📣 Silêncio nas arquibancadas durante uma chegada perigosa!",
        "📣 A torcida começa a pressionar depois de vários minutos de domínio!",
        "📣 O estádio vai abaixo com a pressão do time da casa!",
    ],
}

EMOJI_POR_TIPO = {
    "chute_fora": "🎯",
    "defesa": "🧤",
    "cruzamento_sem_gol": "↗️",
    "cabeceio_fora": "🙆",
    "falta_ou_impedimento": "🚩",
    "torcida": "📣",
    "chance_perdida": "😱",
    "drible": "💨",
    "passe_chave": "🪄",
    "desarme": "🛡️",
    "bola_na_trave": "🥅",
    "mudanca_tatica": "🔄",
    "gol": "⚽",
}

_ATRIBUTOS_POSSIVEIS = ("POS", "KIC", "SHO", "PAS", "DRI", "REF", "DEF", "DIV", "VIS")


def normalizar_time(lineup: list) -> list:
    """Aceita jogadores no formato do banco (player_name) ou do catálogo (name)
    e devolve uma lista padronizada de {"name", "position", "overall", ...atributos}.

    Times vindos do banco (escalação de um jogador) não guardam os atributos
    detalhados — só nome/posição/overall/raridade. Por isso aqui a gente busca
    no catálogo pelo nome e completa com os atributos, se existirem lá.
    """
    from players_data import buscar_jogador_catalogo

    padronizado = []
    for j in lineup:
        nome = j.get("player_name") or j.get("name")
        item = {"name": nome, "position": j["position"], "overall": j.get("overall", 0)}

        catalogo = buscar_jogador_catalogo(
            nome,
            j.get("rarity"),
            j.get("overall"),
        )
        if catalogo:
            for chave in _ATRIBUTOS_POSSIVEIS:
                if chave in catalogo:
                    item[chave] = catalogo[chave]

        padronizado.append(item)
    return padronizado


def _escolher_jogador(time: list, posicoes_preferidas=None, excluir_nome: str = None):
    candidatos = time
    if excluir_nome:
        candidatos = [j for j in candidatos if j["name"] != excluir_nome]
    if posicoes_preferidas:
        preferidos = [j for j in candidatos if j["position"] in posicoes_preferidas]
        if preferidos:
            candidatos = preferidos
    if not candidatos:
        candidatos = time
    return random.choice(candidatos)


def _localizar_jogador(time: list, nome: str):
    return next((j for j in time if j["name"] == nome), None)


def _textualizar_evento(evento: dict, nome_time_a: str, time_a: list, nome_time_b: str, time_b: list) -> str:
    """Converte um evento bruto do simulador (tipo/jogador/assistente) numa frase narrada."""
    time_do_evento = time_a if evento["time"] == nome_time_a else time_b

    if evento["tipo"] == "gol":
        if evento.get("assistente"):
            return random.choice(TEMPLATES_GOL_COM_ASSIST).format(
                atacante=evento["jogador"], assistente=evento["assistente"]
            )
        return random.choice(TEMPLATES_GOL_SOZINHO).format(atacante=evento["jogador"])

    if evento["tipo"] == "chance_perdida":
        return random.choice(TEMPLATES_CHANCE_PERDIDA).format(jogador=evento["jogador"])

    if evento["tipo"] == "mudanca_tatica":
        return random.choice(TEMPLATES_MUDANCA_TATICA).format(time=evento["time"])

    if evento["tipo"] in TEMPLATES_SEM_GOL:
        return random.choice(TEMPLATES_SEM_GOL[evento["tipo"]]).format(jogador=evento.get("jogador", ""))

    return ""


async def narrar_partida(
    mensagem: discord.Message,
    embed_base: discord.Embed,
    nome_time_a: str,
    time_a: list,
    nome_time_b: str,
    time_b: list,
    media_alvo_a=None,
    fator_dificuldade_a: float = 0.0,
    media_alvo_b=None,
    fator_dificuldade_b: float = 0.0,
):
    """Simula a partida de verdade (o placar é uma CONSEQUÊNCIA da simulação,
    não um sorteio prévio) e revela os eventos aos poucos, editando `mensagem`.

    Retorna os dados da partida mantendo os quatro primeiros valores compatíveis com o uso antigo:
    (placar_a, placar_b, artilheiros_a, artilheiros_b, assistentes_a, assistentes_b, defesas_a, defesas_b).
    """
    resultado = simular_partida(
        nome_time_a, time_a, nome_time_b, time_b,
        media_alvo_a=media_alvo_a, fator_dificuldade_a=fator_dificuldade_a,
        media_alvo_b=media_alvo_b, fator_dificuldade_b=fator_dificuldade_b,
    )
    eventos = resultado["eventos"]

    linhas = []
    placar_a = placar_b = 0
    artilheiros_a = []
    artilheiros_b = []
    assistentes_a = []
    assistentes_b = []
    defesas_a = []
    defesas_b = []
    intervalo_mostrado = False

    for evento in eventos:
        if not intervalo_mostrado and evento["minuto"] >= 45:
            linhas.append(f"\n🔔 **Intervalo!** Placar parcial: **{placar_a} x {placar_b}**\n")
            intervalo_mostrado = True

        texto = _textualizar_evento(evento, nome_time_a, time_a, nome_time_b, time_b)
        emoji = EMOJI_POR_TIPO.get(evento["tipo"], "▪️")
        linhas.append(f"`{evento['minuto']}'` {emoji} {texto}")

        if evento["tipo"] == "gol":
            if evento["time"] == nome_time_a:
                placar_a += 1
                artilheiros_a.append(evento["jogador"])
                if evento.get("assistente"):
                    assistentes_a.append(evento["assistente"])
            else:
                placar_b += 1
                artilheiros_b.append(evento["jogador"])
                if evento.get("assistente"):
                    assistentes_b.append(evento["assistente"])

        elif evento["tipo"] == "defesa":
            # O time do evento é o time que fez a defesa.
            if evento["time"] == nome_time_a:
                defesas_a.append(evento["jogador"])
            else:
                defesas_b.append(evento["jogador"])

        embed_atual = embed_base.copy()
        embed_atual.description = "\n".join(linhas)
        embed_atual.set_footer(text=f"⏱️ {evento['minuto']}' — {nome_time_a} {placar_a} x {placar_b} {nome_time_b}")

        try:
            await mensagem.edit(embed=embed_atual)
        except discord.HTTPException:
            pass

        await asyncio.sleep(random.uniform(1.3, 2.1))

    # Times sem nenhum evento narrado (raro, só em 0x0 sem lances notáveis sorteados
    # pra exibição) ainda precisam do placar final batendo com o que foi simulado.
    placar_a, placar_b = resultado["placar_a"], resultado["placar_b"]

    return (
        placar_a, placar_b,
        artilheiros_a, artilheiros_b,
        assistentes_a, assistentes_b,
        defesas_a, defesas_b,
    )


def formatar_artilheiros(nomes: list) -> str:
    """Formata a lista de nomes de quem marcou gol, agrupando repetições (ex: 'Aby (x2)')."""
    if not nomes:
        return "Nenhum gol."
    from collections import Counter
    contagem = Counter(nomes)
    vistos = set()
    linhas = []
    for nome in nomes:
        if nome in vistos:
            continue
        vistos.add(nome)
        qtd = contagem[nome]
        linhas.append(f"⚽ {nome}" + (f" (x{qtd})" if qtd > 1 else ""))
    return "\n".join(linhas)


def formatar_estatistica(nomes: list, emoji: str, vazio: str = "Nenhum.") -> str:
    """Agrupa uma estatística individual (assistências ou defesas)."""
    if not nomes:
        return vazio
    from collections import Counter
    contagem = Counter(nomes)
    vistos = set()
    linhas = []
    for nome in nomes:
        if nome in vistos:
            continue
        vistos.add(nome)
        qtd = contagem[nome]
        linhas.append(f"{emoji} {nome}" + (f" (x{qtd})" if qtd > 1 else ""))
    return "\n".join(linhas)


def determinar_mvp(
    nome_time_a: str, artilheiros_a: list, time_a: list,
    nome_time_b: str, artilheiros_b: list, time_b: list,
    assistentes_a: list = None, assistentes_b: list = None,
    defesas_a: list = None, defesas_b: list = None,
):
    """MVP por contribuição ponderada.

    Pesos: gol = 1.0, assistência = 0.6, defesa de GK = 0.3.
    Assim, 2 assistências (1.2) valem pouco mais que 1 gol, e 2 defesas
    (0.6) valem o equivalente a uma assistência.
    """
    from collections import Counter

    assistentes_a = assistentes_a or []
    assistentes_b = assistentes_b or []
    defesas_a = defesas_a or []
    defesas_b = defesas_b or []

    gols = {nome_time_a: Counter(artilheiros_a), nome_time_b: Counter(artilheiros_b)}
    assists = {nome_time_a: Counter(assistentes_a), nome_time_b: Counter(assistentes_b)}
    saves = {nome_time_a: Counter(defesas_a), nome_time_b: Counter(defesas_b)}

    candidatos = []
    for jogador, time in ([(j, nome_time_a) for j in time_a] + [(j, nome_time_b) for j in time_b]):
        nome = jogador["name"]
        g = gols[time][nome]
        a = assists[time][nome]
        s = saves[time][nome] if jogador.get("position") == "GK" else 0
        pontuacao = g * 1.0 + a * 0.6 + s * 0.3
        candidatos.append((pontuacao, g, a, s, jogador.get("overall", 0), nome, time))

    melhor = max(candidatos, key=lambda x: (x[0], x[1], x[2], x[3], x[4]))
    _, g, a, s, _, nome, time = melhor
    return nome, time, g, a, s



def resolver_penaltis(time_a: list, time_b: list):
    """Disputa de pênaltis usada sempre que uma partida termina empatada."""
    def atributo(jogador, chave, padrao=None):
        valor = jogador.get(chave)
        if valor is None:
            return jogador.get("overall", 50) if padrao is None else padrao
        try:
            return float(valor)
        except (TypeError, ValueError):
            return jogador.get("overall", 50) if padrao is None else padrao

    def chutar(time):
        candidatos = [j for j in time if j.get("position") in {"ST", "MC"}]
        if not candidatos:
            candidatos = time
        return random.choice(candidatos)

    def defender(time):
        gks = [j for j in time if j.get("position") == "GK"]
        return gks[0] if gks else max(time, key=lambda j: atributo(j, "overall", 50))

    goleiro_a = defender(time_a)
    goleiro_b = defender(time_b)
    gols_a = gols_b = 0
    sequencia = []

    for rodada in range(1, 6):
        batedor_a = chutar(time_a)
        batedor_b = chutar(time_b)

        chance_a = max(0.45, min(0.90, 0.62 + (atributo(batedor_a, "SHO") - atributo(goleiro_b, "REF")) / 250))
        chance_b = max(0.45, min(0.90, 0.62 + (atributo(batedor_b, "SHO") - atributo(goleiro_a, "REF")) / 250))

        gol_a = random.random() < chance_a
        gol_b = random.random() < chance_b
        if gol_a:
            gols_a += 1
        if gol_b:
            gols_b += 1

        sequencia.append((rodada, batedor_a["name"], gol_a, batedor_b["name"], gol_b))

        if gols_a > gols_b + (5 - rodada):
            break
        if gols_b > gols_a + (5 - rodada):
            break

    rodada = 5
    while gols_a == gols_b and rodada < 15:
        rodada += 1
        batedor_a = chutar(time_a)
        batedor_b = chutar(time_b)
        chance_a = max(0.45, min(0.90, 0.62 + (atributo(batedor_a, "SHO") - atributo(goleiro_b, "REF")) / 250))
        chance_b = max(0.45, min(0.90, 0.62 + (atributo(batedor_b, "SHO") - atributo(goleiro_a, "REF")) / 250))
        gol_a = random.random() < chance_a
        gol_b = random.random() < chance_b
        if gol_a:
            gols_a += 1
        if gol_b:
            gols_b += 1
        sequencia.append((rodada, batedor_a["name"], gol_a, batedor_b["name"], gol_b))

    vencedor = "a" if gols_a > gols_b else "b"
    return {
        "vencedor": vencedor,
        "gols_a": gols_a,
        "gols_b": gols_b,
        "sequencia": sequencia,
    }


def formatar_penaltis(resultado, nome_time_a: str, nome_time_b: str) -> str:
    linhas = []
    for rodada, nome_a, gol_a, nome_b, gol_b in resultado["sequencia"]:
        linhas.append(
            f"**{rodada}ª** {nome_a} {'⚽' if gol_a else '❌'} · "
            f"{nome_b} {'⚽' if gol_b else '❌'}"
        )
    return "\n".join(linhas) + f"\n\n**Placar nos pênaltis: {resultado['gols_a']} x {resultado['gols_b']}**"

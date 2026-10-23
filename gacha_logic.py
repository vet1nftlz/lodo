"""Lógica de sorteio e abertura de pacotes."""

import random

import config
import database as db
from players_data import PLAYERS_CATALOG, jogador_obtivel


def sortear_jogador_por_chance(candidatos):
    if not candidatos:
        return None
    pesos = []
    for jogador in candidatos:
        try:
            peso = float(jogador.get("gacha_chance", 1.0))
        except (TypeError, ValueError):
            peso = 1.0
        pesos.append(max(0.0, peso))
    if not any(pesos):
        pesos = [1.0] * len(candidatos)
    return random.choices(candidatos, weights=pesos, k=1)[0]


def _candidato_disponivel(jogador, chave_pacote):
    """Verifica apenas se a carta está liberada no catálogo.

    O pacote controla as raridades disponíveis via ``pesos``; não há mais
    regras especiais de Pro/Booster ou listas de pacotes por carta.
    """
    return jogador_obtivel(jogador, chave_pacote)


async def abrir_pacote(user_id: int, chave_pacote: str, is_booster: bool = False):
    """Abre UM pacote já pertencente ao inventário de pacotes."""
    pacote = config.PACOTES.get(chave_pacote)
    if pacote is None:
        return False, None, "Pacote não encontrado."

    quantidade = await db.contar_pacotes(user_id, chave_pacote)
    if quantidade < 1:
        return (
            False,
            None,
            f"Você não possui **{pacote['nome']}** no inventário de pacotes. Compre um na `/loja`.",
        )

    # Reserva o pacote. Em qualquer falha abaixo ele é devolvido.
    if not await db.consumir_pacotes(user_id, chave_pacote, 1):
        return False, None, "Não foi possível reservar o pacote. Tente novamente."

    candidatos_validos = []
    for jogador in PLAYERS_CATALOG:
        if not _candidato_disponivel(jogador, chave_pacote):
            continue

        raridade_exclusiva = jogador.get("rarity") in {"Limited", "Special"}
        if config.LIMITAR_SPECIAL_LIMITED and raridade_exclusiva:
            if await db.usuario_tem_carta(user_id, jogador):
                continue
        candidatos_validos.append(jogador)

    pesos_config = pacote.get("pesos_booster") if is_booster else None
    if not isinstance(pesos_config, dict) or not pesos_config:
        pesos_config = pacote.get("pesos", {})

    raridades = list(pesos_config.keys())
    raridades_disponiveis = [
        raridade for raridade in raridades
        if float(pesos_config.get(raridade, 0)) > 0
        and any(j["rarity"] == raridade for j in candidatos_validos)
    ]

    if not raridades_disponiveis:
        await db.adicionar_pacotes(user_id, chave_pacote, 1)
        return False, None, "Nenhuma carta disponível para este pacote no momento."

    pesos = [float(pesos_config[raridade]) for raridade in raridades_disponiveis]
    raridade_sorteada = random.choices(raridades_disponiveis, weights=pesos, k=1)[0]
    candidatos = [j for j in candidatos_validos if j["rarity"] == raridade_sorteada]
    jogador_sorteado = sortear_jogador_por_chance(candidatos)

    if jogador_sorteado is None:
        await db.adicionar_pacotes(user_id, chave_pacote, 1)
        return False, None, f"Nenhum jogador obtível encontrado para a raridade **{raridade_sorteada}**."

    jogador = dict(jogador_sorteado)

    raridade_exclusiva = jogador.get("rarity") in {"Limited", "Special"}
    if config.LIMITAR_SPECIAL_LIMITED and raridade_exclusiva:
        if await db.usuario_tem_carta(user_id, jogador):
            await db.adicionar_pacotes(user_id, chave_pacote, 1)
            return False, None, "Você já possui esta carta Special/Limited."

    resultado = await db.add_player_or_sell_duplicate(user_id, jogador)
    jogador["novo_id"] = resultado.get("novo_id")
    jogador["duplicado"] = resultado.get("duplicado", False)
    jogador["cheio"] = resultado.get("cheio", False)
    jogador["valor_venda"] = resultado.get("valor")


    await db.incrementar_package_opens(user_id)

    return True, jogador, None


async def comprar_pacotes(user_id: int, chave_pacote: str, quantidade: int):
    pacote = config.PACOTES.get(chave_pacote)
    if pacote is None:
        return False, "Pacote não encontrado.", 0

    quantidade = int(quantidade)
    if quantidade <= 0:
        return False, "A quantidade precisa ser maior que zero.", 0

    total = pacote["preco"] * quantidade
    saldo = await db.get_balance(user_id)
    if saldo < total:
        return (
            False,
            f"Saldo insuficiente. Você precisa de {config.MOEDA_EMOJI} **{total} {config.MOEDA_NOME}** e tem {config.MOEDA_EMOJI} **{saldo}**.",
            0,
        )

    await db.update_balance(user_id, -total)
    await db.adicionar_pacotes(user_id, chave_pacote, quantidade)
    return True, None, total


async def abrir_varios_pacotes(user_id: int, chave_pacote: str, quantidade: int, is_booster: bool = False):
    resultados = []
    erros = []

    for _ in range(quantidade):
        sucesso, jogador, erro = await abrir_pacote(user_id, chave_pacote, is_booster=is_booster)
        if not sucesso:
            if erro:
                erros.append(erro)
            break
        resultados.append(jogador)

    return resultados, erros

"""Monta o 'card' visual (embed + arquivo de imagem) de um jogador do catálogo."""

import os

import discord

import config

from players_data import COUNTRY_FLAGS

CARDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cards")


def construir_card(jogador: dict):
    """Retorna (embed, arquivo_ou_None) pronto pra enviar no Discord."""
    cor = config.COR_RARIDADE.get(jogador["rarity"], discord.Color.blue())
    pais = jogador.get("country", "Não informado")
    bandeira = COUNTRY_FLAGS.get(pais, "🌎")
    estrelas = config.formatar_estrelas(
        jogador.get("estrelas", 1.0),
        limited=str(jogador.get("rarity", "")).lower() == "limited",
    )

    embed = discord.Embed(
        title=f"🃏 {jogador['name']}",
        description=(
            f"**País:** {bandeira} {pais}\n"
            f"**Posição:** {jogador['position']}\n"
            f"**Overall:** {jogador['overall']}\n"
            f"{estrelas}\n"
            f"**Raridade:** {jogador['rarity']}\n"
            f"**Preço na loja:** {config.MOEDA_EMOJI} {jogador['price']}"
        ),
        color=cor,
    )

    arquivo = None
    nome_arquivo = jogador.get("image")
    if nome_arquivo:
        caminho = os.path.join(CARDS_DIR, nome_arquivo)
        if os.path.isfile(caminho):
            arquivo = discord.File(caminho, filename=nome_arquivo)
            embed.set_image(url=f"attachment://{nome_arquivo}")

    if arquivo is None:
        embed.set_footer(text="Sem imagem cadastrada para esse jogador ainda.")

    return embed, arquivo

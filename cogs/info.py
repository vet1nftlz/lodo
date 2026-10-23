"""Comando /info: mostra a carta completa de um jogador — só se você já o possui."""

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from cards import construir_card
from players_data import buscar_jogador_catalogo


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="info", description="Veja a carta completa de um jogador que você já possui")
    @app_commands.describe(nome="Nome da carta (a raridade/OVR aparecem nas sugestões)")
    async def info(self, interaction: discord.Interaction, nome: str):
        elenco = await db.get_user_players(interaction.user.id)

        # Autocomplete usa este formato para diferenciar variantes com o mesmo nome:
        # nome||raridade||overall. Também aceita o nome puro para manter compatibilidade.
        partes = nome.split("||")
        nome_base = partes[0].strip()
        raridade = partes[1].strip() if len(partes) > 1 else None
        overall = None
        if len(partes) > 2:
            try:
                overall = int(partes[2])
            except ValueError:
                overall = None

        nome_lower = nome_base.lower()
        if raridade is not None and overall is not None:
            possui = any(
                p["player_name"].lower() == nome_lower
                and p["rarity"].lower() == raridade.lower()
                and p["overall"] == overall
                for p in elenco
            )
        else:
            possui = any(p["player_name"].lower() == nome_lower for p in elenco)

        if not possui:
            await interaction.response.send_message(
                "❌ Você ainda não possui essa carta (ou ela nem existe 👀). "
                "Use `/inventario` pra ver o que você já tem.",
                ephemeral=True,
            )
            return

        jogador = buscar_jogador_catalogo(nome_base, raridade, overall)
        if jogador is None:
            await interaction.response.send_message(
                "❌ Não encontrei essa variante da carta no catálogo.",
                ephemeral=True,
            )
            return

        embed, arquivo = construir_card(jogador)
        if arquivo:
            await interaction.response.send_message(embed=embed, file=arquivo)
        else:
            await interaction.response.send_message(embed=embed)

    @info.autocomplete("nome")
    async def info_autocomplete(self, interaction: discord.Interaction, atual: str):
        elenco = await db.get_user_players(interaction.user.id)
        atual_lower = atual.lower()
        opcoes = []
        vistos = set()

        for p in elenco:
            chave = (p["player_name"].lower(), p["rarity"].lower(), p["overall"])
            if chave in vistos:
                continue
            vistos.add(chave)
            label = f'{p["player_name"]} • {p["rarity"]} • OVR {p["overall"]}'
            if atual_lower in label.lower() or atual_lower in p["player_name"].lower():
                opcoes.append(
                    app_commands.Choice(
                        name=label[:100],
                        value=f'{p["player_name"]}||{p["rarity"]}||{p["overall"]}',
                    )
                )

        return opcoes[:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))

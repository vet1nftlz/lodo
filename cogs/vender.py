"""Comando /vender: venda manual de uma carta do seu elenco pelo preço dela."""

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from players_data import buscar_jogador_catalogo


class Vender(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="vender", description="Venda uma carta do seu elenco pelo preço dela")
    @app_commands.describe(nome="Carta que você quer vender (nome • raridade • OVR)")
    async def vender(self, interaction: discord.Interaction, nome: str):
        elenco = await db.get_user_players(interaction.user.id)
        partes = nome.split("||")
        nome_base = partes[0].strip()
        raridade = partes[1].strip() if len(partes) > 1 else None
        try:
            overall = int(partes[2]) if len(partes) > 2 else None
        except ValueError:
            overall = None
        nome_lower = nome_base.lower()
        carta = next((
            p for p in elenco
            if p["player_name"].lower() == nome_lower
            and (raridade is None or p["rarity"].lower() == raridade.lower())
            and (overall is None or p["overall"] == overall)
        ), None)

        if carta is None:
            await interaction.response.send_message(
                "❌ Você não possui essa carta. Confira com `/inventario`.", ephemeral=True
            )
            return

        jogador_catalogo = buscar_jogador_catalogo(
            carta["player_name"], carta["rarity"], carta["overall"]
        )
        preco = jogador_catalogo["price"] if jogador_catalogo else 0

        await db.remove_one_player_by_name(
            interaction.user.id, carta["player_name"], carta["rarity"], carta["overall"]
        )
        await db.update_balance(interaction.user.id, preco)

        embed = discord.Embed(
            description=f"💰 Você vendeu **{carta['player_name']} • {carta['rarity']} • OVR {carta['overall']}** por {config.MOEDA_EMOJI} **{preco} {config.MOEDA_NOME}**!",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @vender.autocomplete("nome")
    async def vender_autocomplete(self, interaction: discord.Interaction, atual: str):
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
            if atual_lower in label.lower():
                opcoes.append(app_commands.Choice(
                    name=label[:100],
                    value=f'{p["player_name"]}||{p["rarity"]}||{p["overall"]}',
                ))
        return opcoes[:25]



async def setup(bot: commands.Bot):
    await bot.add_cog(Vender(bot))

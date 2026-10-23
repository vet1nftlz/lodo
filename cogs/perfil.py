"""Comando /perfil."""

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db


class Perfil(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="perfil", description="Veja seu perfil ou o perfil de outro jogador")
    @app_commands.describe(jogador="Opcional: perfil de outro usuário")
    async def perfil(self, interaction: discord.Interaction, jogador: discord.Member = None):
        alvo = jogador or interaction.user
        user = await db.get_user(alvo.id)
        identidade = await db.get_identidade_time(alvo.id)
        elenco = await db.get_user_players(alvo.id)
        pacotes = await db.get_user_packages(alvo.id)
        capacidade = await db.get_capacidade_inventario(alvo.id)

        embed = discord.Embed(
            title=f"👤 Perfil de {alvo.display_name}",
            color=discord.Color.blurple(),
        )
        if alvo.display_avatar:
            embed.set_thumbnail(url=alvo.display_avatar.url)

        lineup_4v4 = await db.get_lineup(alvo.id, "4v4")
        lineup_7v7 = await db.get_lineup(alvo.id, "7v7")

        media_4v4 = (sum(p["overall"] for p in lineup_4v4) / len(lineup_4v4)) if lineup_4v4 else 0
        media_7v7 = (sum(p["overall"] for p in lineup_7v7) / len(lineup_7v7)) if lineup_7v7 else 0
        total_pacotes = sum(pacotes.values())

        embed.add_field(name="🏆 Time", value=identidade["time_nome"], inline=True)
        embed.add_field(name="🏟️ Estádio", value=identidade["estadio_nome"], inline=True)
        embed.add_field(
            name="💰 Saldo",
            value=f"{config.MOEDA_EMOJI} **{user['balance']} {config.MOEDA_NOME}**",
            inline=True,
        )
        embed.add_field(
            name="🃏 Jogadores",
            value=f"**{len(elenco)}/{capacidade}**",
            inline=True,
        )
        embed.add_field(
            name="⚽ 4v4",
            value=f"OVR médio: **{media_4v4:.1f}**",
            inline=True,
        )
        embed.add_field(
            name="⚽ 7v7",
            value=f"OVR médio: **{media_7v7:.1f}**",
            inline=True,
        )
        embed.add_field(name="📦 Pacotes", value=f"**{total_pacotes}** armazenados", inline=True)
        embed.add_field(name="🆔 ID", value=str(alvo.id), inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Perfil(bot))

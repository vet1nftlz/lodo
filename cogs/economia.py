"""Comandos de economia: /saldo, /salario, /diario, /pagar."""

import random
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db


def _formatar_tempo_restante(segundos: float) -> str:
    segundos = int(segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    if horas > 0:
        return f"{horas}h {minutos}min"
    if minutos > 0:
        return f"{minutos}min {seg}s"
    return f"{seg}s"


class Economia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="saldo", description="Veja seu saldo ou o de outro jogador")
    @app_commands.describe(jogador="Jogador que você quer ver o saldo (opcional)")
    async def saldo(self, interaction: discord.Interaction, jogador: discord.Member = None):
        alvo = jogador or interaction.user
        saldo_atual = await db.get_balance(alvo.id)

        embed = discord.Embed(
            title=f"💰 Carteira de {alvo.display_name}",
            description=f"{config.MOEDA_EMOJI} **{saldo_atual} {config.MOEDA_NOME}**",
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=alvo.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="salario", description="Receba seu salário em Robux (tem cooldown)")
    async def salario(self, interaction: discord.Interaction):
        user = await db.get_user(interaction.user.id)

        if user["last_work"]:
            ultima_vez = datetime.fromisoformat(user["last_work"])
            cooldown = timedelta(minutes=config.SALARIO_COOLDOWN_MINUTOS)
            if datetime.utcnow() - ultima_vez < cooldown:
                restante = (ultima_vez + cooldown - datetime.utcnow()).total_seconds()
                await interaction.response.send_message(
                    f"⏳ Você já recebeu seu salário recentemente. Tente novamente em "
                    f"**{_formatar_tempo_restante(restante)}**.",
                    ephemeral=True,
                )
                return

        ganho = random.randint(config.SALARIO_MIN, config.SALARIO_MAX)
        await db.update_balance(interaction.user.id, ganho)
        await db.set_last_work(interaction.user.id)

        embed = discord.Embed(
            description=f"💼 Você recebeu seu salário: {config.MOEDA_EMOJI} **{ganho} {config.MOEDA_NOME}**!",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="diario", description="Resgate sua recompensa diária")
    async def diario(self, interaction: discord.Interaction):
        user = await db.get_user(interaction.user.id)

        if user["last_daily"]:
            ultima_vez = datetime.fromisoformat(user["last_daily"])
            cooldown = timedelta(hours=config.DIARIO_COOLDOWN_HORAS)
            if datetime.utcnow() - ultima_vez < cooldown:
                restante = (ultima_vez + cooldown - datetime.utcnow()).total_seconds()
                await interaction.response.send_message(
                    f"⏳ Você já resgatou o diário hoje. Volte em "
                    f"**{_formatar_tempo_restante(restante)}**.",
                    ephemeral=True,
                )
                return

        await db.update_balance(interaction.user.id, config.DIARIO_VALOR)
        await db.set_last_daily(interaction.user.id)

        embed = discord.Embed(
            description=f"🎁 Recompensa diária resgatada: {config.MOEDA_EMOJI} "
                        f"**{config.DIARIO_VALOR} {config.MOEDA_NOME}**!",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pagar", description="Transfira Robux para outro jogador")
    @app_commands.describe(jogador="Quem vai receber", quantidade="Quanto você quer enviar")
    async def pagar(self, interaction: discord.Interaction, jogador: discord.Member, quantidade: int):
        if jogador.id == interaction.user.id:
            await interaction.response.send_message("❌ Você não pode pagar para si mesmo.", ephemeral=True)
            return
        if jogador.bot:
            await interaction.response.send_message("❌ Você não pode pagar para um bot.", ephemeral=True)
            return
        if quantidade <= 0:
            await interaction.response.send_message("❌ Informe uma quantidade válida.", ephemeral=True)
            return

        saldo_atual = await db.get_balance(interaction.user.id)
        if saldo_atual < quantidade:
            await interaction.response.send_message(
                f"❌ Saldo insuficiente. Você tem apenas {config.MOEDA_EMOJI} **{saldo_atual} {config.MOEDA_NOME}**.",
                ephemeral=True,
            )
            return

        await db.update_balance(interaction.user.id, -quantidade)
        await db.update_balance(jogador.id, quantidade)

        embed = discord.Embed(
            description=f"✅ {interaction.user.mention} pagou {config.MOEDA_EMOJI} "
                        f"**{quantidade} {config.MOEDA_NOME}** para {jogador.mention}!",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economia(bot))

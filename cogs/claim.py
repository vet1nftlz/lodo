"""Comando /claim: recompensa gratuita a cada 20 minutos, sorteando entre as 27 cartas."""

import random
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from cards import construir_card
from cogs.loja import descrever_resultado_carta
from players_data import PLAYERS_CATALOG, jogador_obtivel
from gacha_logic import sortear_jogador_por_chance


def _formatar_tempo_restante(segundos: float) -> str:
    segundos = int(segundos)
    minutos, seg = divmod(segundos, 60)
    if minutos > 0:
        return f"{minutos}min {seg}s"
    return f"{seg}s"


class Claim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="claim", description="Resgate uma carta grátis (cooldown de 20 minutos)")
    async def claim(self, interaction: discord.Interaction):
        user = await db.get_user(interaction.user.id)

        if user["last_claim"]:
            ultima_vez = datetime.fromisoformat(user["last_claim"])
            cooldown = timedelta(minutes=config.CLAIM_COOLDOWN_MINUTOS)
            if datetime.utcnow() - ultima_vez < cooldown:
                restante = (ultima_vez + cooldown - datetime.utcnow()).total_seconds()
                await interaction.response.send_message(
                    f"⏳ Você já deu claim recentemente. Tente de novo em "
                    f"**{_formatar_tempo_restante(restante)}**.",
                    ephemeral=True,
                )
                return

        if not await db.tem_espaco_inventario(interaction.user.id, 1):
            await interaction.response.send_message(
                await db.mensagem_sem_espaco(interaction.user.id, 1),
                ephemeral=True,
            )
            return

        raridades = list(config.CLAIM_PESOS_RARIDADE.keys())
        pesos = list(config.CLAIM_PESOS_RARIDADE.values())
        raridade_sorteada = random.choices(raridades, weights=pesos, k=1)[0]
        candidatos = [j for j in PLAYERS_CATALOG if j["rarity"] == raridade_sorteada and jogador_obtivel(j)]
        jogador_sorteado = sortear_jogador_por_chance(candidatos)
        if jogador_sorteado is None:
            await interaction.response.send_message("❌ Não foi possível sortear uma carta para este claim. Tente novamente.", ephemeral=True)
            return
        jogador = dict(jogador_sorteado)

        resultado = await db.add_player_or_sell_duplicate(interaction.user.id, jogador)
        await db.set_last_claim(interaction.user.id)

        embed, arquivo = construir_card(jogador)
        embed.title = f"🎁 Claim resgatado! {embed.title}"
        jogador_com_resultado = {
            **jogador,
            "duplicado": resultado["duplicado"],
            "cheio": resultado["cheio"],
            "valor_venda": resultado["valor"],
        }
        descrever_resultado_carta(embed, jogador_com_resultado)
        embed.set_footer(text=f"Próximo claim disponível em {config.CLAIM_COOLDOWN_MINUTOS} minutos.")

        if arquivo:
            await interaction.response.send_message(embed=embed, file=arquivo)
        else:
            await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Claim(bot))

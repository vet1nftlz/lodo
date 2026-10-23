"""Comando /weekly: pacote semanal (1 carta 70+ garantida + 2 aleatórias), não comprável."""

import asyncio
import random
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from cards import construir_card
from players_data import PLAYERS_CATALOG, jogador_obtivel
from gacha_logic import sortear_jogador_por_chance


def _formatar_tempo_restante(segundos: float) -> str:
    segundos = int(segundos)
    dias, resto = divmod(segundos, 86400)
    horas, resto = divmod(resto, 3600)
    minutos, _ = divmod(resto, 60)
    partes = []
    if dias > 0:
        partes.append(f"{dias}d")
    if horas > 0:
        partes.append(f"{horas}h")
    if not partes:
        partes.append(f"{minutos}min")
    return " ".join(partes)


class Weekly(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="weekly", description="Resgate seu pacote semanal (3 cartas, cooldown de 7 dias)")
    async def weekly(self, interaction: discord.Interaction):
        user = await db.get_user(interaction.user.id)

        if user["last_weekly"]:
            ultima_vez = datetime.fromisoformat(user["last_weekly"])
            cooldown = timedelta(days=config.WEEKLY_COOLDOWN_DIAS)
            if datetime.utcnow() - ultima_vez < cooldown:
                restante = (ultima_vez + cooldown - datetime.utcnow()).total_seconds()
                await interaction.response.send_message(
                    f"⏳ Você já resgatou seu pacote semanal. Volte em "
                    f"**{_formatar_tempo_restante(restante)}**.",
                    ephemeral=True,
                )
                return

        if not await db.tem_espaco_inventario(interaction.user.id, 3):
            await interaction.response.send_message(
                await db.mensagem_sem_espaco(interaction.user.id, 3),
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Sorteia 3 cartas distintas usando as probabilidades de raridade do Weekly
        # e, dentro da raridade sorteada, a chance individual (gacha_chance) da carta.
        # A garantia de 80+ só é aplicada se o sorteio normal das 3 não produzir nenhuma.
        cartas = []
        candidatos = [j for j in PLAYERS_CATALOG if jogador_obtivel(j) and j["rarity"] in config.WEEKLY_PESOS_RARIDADE]

        def sortear_por_raridade(candidatos_disponiveis, pesos_raridade):
            grupos = {}
            for jogador in candidatos_disponiveis:
                grupos.setdefault(jogador["rarity"], []).append(jogador)

            raridades = [r for r, peso in pesos_raridade.items() if float(peso) > 0 and grupos.get(r)]
            pesos = [float(pesos_raridade[r]) for r in raridades]
            if not raridades:
                return None

            raridade = random.choices(raridades, weights=pesos, k=1)[0]
            return sortear_jogador_por_chance(grupos[raridade])

        for _ in range(3):
            disponiveis = [j for j in candidatos if j["name"] not in {c["name"] for c in cartas}]
            escolhida = sortear_por_raridade(disponiveis, config.WEEKLY_PESOS_RARIDADE)
            if escolhida is None:
                break
            cartas.append(dict(escolhida))

        # Garante pelo menos uma carta 80+, mas a carta adicionada pela garantia
        # fica limitada a 80-89 OVR (nunca 90+).
        if cartas and not any(c["overall"] >= config.WEEKLY_OVERALL_MINIMO for c in cartas):
            altas = [
                j for j in candidatos
                if config.WEEKLY_OVERALL_MINIMO <= j["overall"] < 90
                and j["name"] not in {c["name"] for c in cartas}
            ]
            substituicao = sortear_por_raridade(altas, config.WEEKLY_PESOS_RARIDADE)
            if substituicao is not None:
                indice = random.randrange(len(cartas))
                cartas[indice] = dict(substituicao)

        # Salva as 3 no elenco do usuário (ou vende automaticamente se já tiver, ou se estiver cheio)
        for carta in cartas:
            resultado = await db.add_player_or_sell_duplicate(interaction.user.id, carta)
            carta["novo_id"] = resultado["novo_id"]
            carta["duplicado"] = resultado["duplicado"]
            carta["cheio"] = resultado["cheio"]
            carta["valor_venda"] = resultado["valor"]

        await db.set_last_weekly(interaction.user.id)

        # Revela em ordem decrescente de overall, com suspense entre cada uma
        cartas_ordenadas = sorted(cartas, key=lambda j: j["overall"], reverse=True)

        embed_inicial = discord.Embed(
            title="🎁 Pacote Semanal",
            description="Abrindo suas 3 cartas...",
            color=discord.Color.purple(),
        )
        mensagem = await interaction.followup.send(embed=embed_inicial, wait=True)
        await asyncio.sleep(1.5)

        for i, carta in enumerate(cartas_ordenadas, start=1):
            embed, arquivo = construir_card(carta)
            embed.title = f"🎁 Carta {i} de 3 — {embed.title}"
            if carta["duplicado"]:
                embed.description += (
                    f"\n💰 Você já tinha essa carta — convertida automaticamente em "
                    f"{config.MOEDA_EMOJI} **{carta['valor_venda']} {config.MOEDA_NOME}**!"
                )
            elif carta["cheio"]:
                embed.description += (
                    f"\n📦 Inventário cheio — convertida automaticamente em "
                    f"{config.MOEDA_EMOJI} **{carta['valor_venda']} {config.MOEDA_NOME}**!"
                )
            embed.set_footer(text="Pacote Semanal")
            try:
                if arquivo:
                    await mensagem.edit(embed=embed, attachments=[arquivo])
                else:
                    await mensagem.edit(embed=embed)
            except discord.HTTPException:
                pass
            if i < len(cartas_ordenadas):
                await asyncio.sleep(2.5)

        await asyncio.sleep(1.5)

        # Resumo final
        embed_resumo = discord.Embed(title="✅ Pacote Semanal resgatado!", color=discord.Color.gold())
        linhas = []
        for c in cartas_ordenadas:
            base = f"**{c['name']}** ({c['position']}) — OVR {c['overall']} — {c['rarity']}"
            if c["duplicado"]:
                linhas.append(f"{base} — 💰 já possuía, convertida em {config.MOEDA_EMOJI} {c['valor_venda']}")
            elif c["cheio"]:
                linhas.append(f"{base} — 📦 inventário cheio, convertida em {config.MOEDA_EMOJI} {c['valor_venda']}")
            else:
                linhas.append(f"{base} — ✅ adicionada ao elenco")
        embed_resumo.description = "\n".join(linhas)
        embed_resumo.set_footer(text=f"Próximo pacote semanal disponível em {config.WEEKLY_COOLDOWN_DIAS} dias.")
        await mensagem.edit(embed=embed_resumo, attachments=[])


async def setup(bot: commands.Bot):
    await bot.add_cog(Weekly(bot))

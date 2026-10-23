"""Comando de amistoso: /amistoso — enfrenta um time da máquina (overall médio ~75).

Esse era o antigo /campeonato. O nome mudou porque /campeonato agora é o
torneio de mata-mata (quartas -> semis -> final) em cogs/campeonato.py.
A lógica aqui embaixo não mudou.
"""

from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from cogs.time import slots_completos
from maquina import gerar_time_maquina
from motor_partida import determinar_mvp, formatar_artilheiros, formatar_estatistica, narrar_partida, normalizar_time, resolver_penaltis, formatar_penaltis


MODOS = [
    app_commands.Choice(name="4v4", value="4v4"),
    app_commands.Choice(name="7v7", value="7v7"),
]


def _formatar_tempo_restante(segundos: float) -> str:
    segundos = int(segundos)
    minutos, seg = divmod(segundos, 60)
    if minutos > 0:
        return f"{minutos}min {seg}s"
    return f"{seg}s"


class Amistoso(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="amistoso", description="Enfrente um time da máquina (overall médio ~75) e ganhe Robux")
    @app_commands.describe(modo="4v4 ou 7v7")
    @app_commands.choices(modo=MODOS)
    async def amistoso(self, interaction: discord.Interaction, modo: app_commands.Choice[str]):
        modo_valor = modo.value
        user = await db.get_user(interaction.user.id)

        # Cooldown
        if user["last_campeonato"]:
            ultima_vez = datetime.fromisoformat(user["last_campeonato"])
            cooldown = timedelta(minutes=config.AMISTOSO_COOLDOWN_MINUTOS)
            if datetime.utcnow() - ultima_vez < cooldown:
                restante = (ultima_vez + cooldown - datetime.utcnow()).total_seconds()
                await interaction.response.send_message(
                    f"⏳ Você já jogou um amistoso recentemente. Tente de novo em "
                    f"**{_formatar_tempo_restante(restante)}**.",
                    ephemeral=True,
                )
                return

        # Escalação completa?
        lineup = await db.get_lineup(interaction.user.id, modo_valor)
        if not slots_completos(modo_valor, lineup):
            await interaction.response.send_message(
                f"❌ Sua escalação de **{modo_valor}** está incompleta. Use `/time_ver modo:{modo_valor}` para conferir.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Gera o time da máquina (já mirando o overall alvo do amistoso)
        time_maquina = gerar_time_maquina(modo_valor, media_alvo=config.AMISTOSO_MEDIA_ALVO)

        await db.set_last_campeonato(interaction.user.id)

        identidade = await db.get_identidade_time(interaction.user.id)
        nome_jogador = identidade["time_nome"]
        nome_maquina = "Time da Máquina"

        embed_partida = discord.Embed(
            title=f"🏟️ {identidade['estadio_nome']} — {nome_jogador} x {nome_maquina}",
            description="⚽ Bola rolando...",
            color=discord.Color.blue(),
        )
        mensagem = await interaction.followup.send(embed=embed_partida, wait=True)

        placar_jogador, placar_maquina, artilheiros_jogador, artilheiros_maquina, assistentes_jogador, assistentes_maquina, defesas_jogador, defesas_maquina = await narrar_partida(
            mensagem, embed_partida,
            nome_jogador, normalizar_time(lineup),
            nome_maquina, normalizar_time(time_maquina),
            media_alvo_a=config.AMISTOSO_MEDIA_ALVO,
            fator_dificuldade_a=config.AMISTOSO_FATOR_DIFICULDADE,
        )

        penalti = None
        if placar_jogador == placar_maquina:
            penalti = resolver_penaltis(
                normalizar_time(lineup),
                normalizar_time(time_maquina),
            )
            venceu = penalti["vencedor"] == "a"
        else:
            venceu = placar_jogador > placar_maquina

        embed_final = discord.Embed(
            title=f"🏆 Fim de jogo: {nome_jogador} {placar_jogador} x {placar_maquina} {nome_maquina}",
            color=discord.Color.gold(),
        )
        embed_final.add_field(name=f"⚽ Gols — {nome_jogador}", value=formatar_artilheiros(artilheiros_jogador), inline=True)
        embed_final.add_field(name=f"⚽ Gols — {nome_maquina}", value=formatar_artilheiros(artilheiros_maquina), inline=True)
        embed_final.add_field(name=f"👟 Assistências — {nome_jogador}", value=formatar_estatistica(assistentes_jogador, "👟"), inline=True)
        embed_final.add_field(name=f"👟 Assistências — {nome_maquina}", value=formatar_estatistica(assistentes_maquina, "👟"), inline=True)
        embed_final.add_field(name=f"🧤 Defesas — {nome_jogador}", value=formatar_estatistica(defesas_jogador, "🧤"), inline=True)
        embed_final.add_field(name=f"🧤 Defesas — {nome_maquina}", value=formatar_estatistica(defesas_maquina, "🧤"), inline=True)

        if penalti:
            embed_final.add_field(
                name="🥅 Disputa de pênaltis",
                value=formatar_penaltis(penalti, nome_jogador, nome_maquina),
                inline=False,
            )

        nome_mvp, time_mvp, gols_mvp, assist_mvp, defesas_mvp = determinar_mvp(
            nome_jogador, artilheiros_jogador, normalizar_time(lineup),
            nome_maquina, artilheiros_maquina, normalizar_time(time_maquina),
            assistentes_jogador, assistentes_maquina, defesas_jogador, defesas_maquina,
        )
        texto_mvp = f"🏅 **{nome_mvp}** ({time_mvp})"
        partes_mvp = []
        if gols_mvp > 0:
            partes_mvp.append(f"⚽ {gols_mvp} gol{'s' if gols_mvp > 1 else ''}")
        if assist_mvp > 0:
            partes_mvp.append(f"👟 {assist_mvp} assistência{'s' if assist_mvp > 1 else ''}")
        if defesas_mvp > 0:
            partes_mvp.append(f"🧤 {defesas_mvp} defesa{'s' if defesas_mvp > 1 else ''}")
        if partes_mvp:
            texto_mvp += " — " + " · ".join(partes_mvp)
        embed_final.add_field(name="MVP da partida", value=texto_mvp, inline=False)

        if venceu:
            await db.update_balance(interaction.user.id, config.AMISTOSO_RECOMPENSA)
            embed_final.description = (
                f"🎉 **Vitória!** Você ganhou {config.MOEDA_EMOJI} "
                f"**{config.AMISTOSO_RECOMPENSA} {config.MOEDA_NOME}**!"
            )
            embed_final.color = discord.Color.green()
        elif penalti:
            embed_final.description = (
                f"🥅 **Pênaltis!** {nome_jogador if venceu else nome_maquina} venceu a disputa e levou a partida."
            )
            embed_final.color = discord.Color.green() if venceu else discord.Color.red()
        else:
            embed_final.description = "💀 **Derrota.** A máquina levou essa. Tente novamente mais tarde!"
            embed_final.color = discord.Color.red()

        embed_final.set_footer(text=f"Próximo amistoso disponível em {config.AMISTOSO_COOLDOWN_MINUTOS} minutos.")

        await mensagem.edit(embed=embed_final)


async def setup(bot: commands.Bot):
    await bot.add_cog(Amistoso(bot))

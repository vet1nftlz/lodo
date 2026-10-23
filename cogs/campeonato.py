"""Comando de campeonato: /campeonato — torneio de mata-mata contra a máquina.

Fases: Quartas de Final (máquina 70+) -> Semifinal (75+) -> Final (80+).
Usa exatamente o mesmo modelo de partida do resto do bot (overall + sorte,
penalidade se o time estiver abaixo da média alvo, narração ao vivo, MVP e
artilheiros no final) — só muda o overall alvo da máquina a cada fase e
encadeia as partidas com um botão de "continuar" entre elas.
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


def _formatar_tempo_restante(segundos: float) -> str:
    segundos = int(segundos)
    minutos, seg = divmod(segundos, 60)
    if minutos > 0:
        return f"{minutos}min {seg}s"
    return f"{seg}s"


MODOS = [
    app_commands.Choice(name="4v4", value="4v4"),
    app_commands.Choice(name="7v7", value="7v7"),
]


class FaseView(discord.ui.View):
    """Botão único: 'Iniciar' na primeira fase, 'Continuar' nas seguintes."""

    def __init__(self, autor_id: int, modo: str, fase_index: int, label: str):
        super().__init__(timeout=300)
        self.autor_id = autor_id
        self.modo = modo
        self.fase_index = fase_index

        botao = discord.ui.Button(label=label, style=discord.ButtonStyle.success, emoji="▶️")
        botao.callback = self._callback
        self.add_item(botao)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "❌ Esse campeonato não é seu — use `/campeonato` pra começar o seu!",
                ephemeral=True,
            )
            return False
        return True

    async def _callback(self, interaction: discord.Interaction):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await jogar_fase(interaction, self.autor_id, self.modo, self.fase_index)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


async def jogar_fase(interaction: discord.Interaction, autor_id: int, modo: str, fase_index: int):
    fase = config.CAMPEONATO_FASES[fase_index]
    media_alvo = fase["media_alvo"]

    lineup = await db.get_lineup(autor_id, modo)
    if not slots_completos(modo, lineup):
        await interaction.followup.send(
            f"❌ Sua escalação de **{modo}** ficou incompleta. Ajuste com `/time_montar` e tente de novo com `/campeonato`.",
        )
        return

    time_maquina = gerar_time_maquina(modo, media_alvo=media_alvo)

    identidade = await db.get_identidade_time(interaction.user.id)
    nome_jogador = identidade["time_nome"]
    nome_maquina = f"Máquina ({fase['nome']})"

    embed_partida = discord.Embed(
        title=f"🏟️ {identidade['estadio_nome']} — {fase['nome']}: {nome_jogador} x {nome_maquina}",
        description="⚽ Bola rolando...",
        color=discord.Color.blue(),
    )
    mensagem = await interaction.followup.send(embed=embed_partida, wait=True)

    placar_jogador, placar_maquina, artilheiros_jogador, artilheiros_maquina, assistentes_jogador, assistentes_maquina, defesas_jogador, defesas_maquina = await narrar_partida(
        mensagem, embed_partida,
        nome_jogador, normalizar_time(lineup),
        nome_maquina, normalizar_time(time_maquina),
        media_alvo_a=media_alvo,
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
        title=f"🏆 {fase['nome']} — Fim de jogo: {nome_jogador} {placar_jogador} x {placar_maquina} {nome_maquina}",
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

    eh_final = fase_index == len(config.CAMPEONATO_FASES) - 1

    if venceu and eh_final:
        await db.update_balance(autor_id, config.CAMPEONATO_RECOMPENSA_FINAL)
        embed_final.description = (
            f"🏆🎉 **CAMPEÃO!** Você venceu a Final e ganhou {config.MOEDA_EMOJI} "
            f"**{config.CAMPEONATO_RECOMPENSA_FINAL} {config.MOEDA_NOME}**!"
        )
        embed_final.color = discord.Color.gold()
        await mensagem.edit(embed=embed_final)

    elif venceu:
        proxima_fase = config.CAMPEONATO_FASES[fase_index + 1]
        embed_final.description = f"✅ **Classificado!** Você avança para a **{proxima_fase['nome']}**."
        embed_final.color = discord.Color.green()
        await mensagem.edit(embed=embed_final)

        view = FaseView(autor_id, modo, fase_index + 1, label=f"Continuar para a {proxima_fase['nome']}")
        await interaction.followup.send(
            f"Quando estiver pronto pra {proxima_fase['nome']} (máquina {proxima_fase['media_alvo']}+ de overall), clique abaixo:",
            view=view,
        )

    else:
        embed_final.description = "💀 **Derrota.** Você foi eliminado do campeonato nesta fase."
        embed_final.color = discord.Color.red()
        await mensagem.edit(embed=embed_final)


class Campeonato(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="campeonato", description="Torneio contra a máquina: quartas, semis e final")
    @app_commands.describe(modo="4v4 ou 7v7")
    @app_commands.choices(modo=MODOS)
    async def campeonato(self, interaction: discord.Interaction, modo: app_commands.Choice[str]):
        modo_valor = modo.value

        user = await db.get_user(interaction.user.id)
        if user["last_torneio"]:
            ultima_vez = datetime.fromisoformat(user["last_torneio"])
            cooldown = timedelta(minutes=config.CAMPEONATO_COOLDOWN_MINUTOS)
            if datetime.utcnow() - ultima_vez < cooldown:
                restante = (ultima_vez + cooldown - datetime.utcnow()).total_seconds()
                await interaction.response.send_message(
                    f"⏳ Você já disputou um campeonato recentemente. Tente de novo em "
                    f"**{_formatar_tempo_restante(restante)}**.",
                    ephemeral=True,
                )
                return

        lineup = await db.get_lineup(interaction.user.id, modo_valor)
        if not slots_completos(modo_valor, lineup):
            await interaction.response.send_message(
                f"❌ Sua escalação de **{modo_valor}** está incompleta. Use `/time_ver modo:{modo_valor}` para conferir.",
                ephemeral=True,
            )
            return

        await db.set_last_torneio(interaction.user.id)

        primeira_fase = config.CAMPEONATO_FASES[0]
        embed = discord.Embed(
            title="🏆 Campeonato",
            description=(
                f"Você vai disputar um torneio de 3 fases contra a máquina:\n\n"
                + "\n".join(f"**{f['nome']}** — overall {f['media_alvo']}+" for f in config.CAMPEONATO_FASES)
                + f"\n\nVenceu a Final? Ganha {config.MOEDA_EMOJI} **{config.CAMPEONATO_RECOMPENSA_FINAL} {config.MOEDA_NOME}**!\n"
                f"Empate ou derrota em qualquer fase = eliminado.\n\n"
                f"Pronto pra começar as **{primeira_fase['nome']}**?"
            ),
            color=discord.Color.blue(),
        )
        view = FaseView(interaction.user.id, modo_valor, 0, label=f"Iniciar {primeira_fase['nome']}")
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Campeonato(bot))

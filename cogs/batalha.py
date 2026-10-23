"""Comando de batalha: /batalha — desafia outro jogador com aposta em Robux."""

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from cogs.time import slots_completos
from motor_partida import determinar_mvp, formatar_artilheiros, formatar_estatistica, narrar_partida, normalizar_time, resolver_penaltis, formatar_penaltis


MODOS = [
    app_commands.Choice(name="4v4", value="4v4"),
    app_commands.Choice(name="7v7", value="7v7"),
]


class ConfirmarBatalhaView(discord.ui.View):
    """View com botões Aceitar/Recusar, exibida para o oponente desafiado."""

    def __init__(self, desafiante: discord.Member, oponente: discord.Member, modo: str, aposta: int):
        super().__init__(timeout=config.BATALHA_TIMEOUT_CONFIRMACAO)
        self.desafiante = desafiante
        self.oponente = oponente
        self.modo = modo
        self.aposta = aposta
        self.resultado: bool | None = None  # True=aceitou, False=recusou, None=expirou
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.oponente.id:
            await interaction.response.send_message(
                "❌ Só o jogador desafiado pode responder a esse desafio.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Aceitar", style=discord.ButtonStyle.success, emoji="⚔️")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.resultado = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="🚫")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.resultado = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self):
        if self.message is not None:
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(
                    content="⏳ O desafio expirou (o oponente não respondeu a tempo).",
                    view=self,
                )
            except discord.HTTPException:
                pass


class Batalha(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="batalha", description="Desafie outro jogador para uma batalha com aposta")
    @app_commands.describe(
        oponente="Quem você quer desafiar",
        modo="4v4 ou 7v7",
        aposta="Quantidade de Robux apostada (0 para batalha sem aposta)",
    )
    @app_commands.choices(modo=MODOS)
    async def batalha(
        self,
        interaction: discord.Interaction,
        oponente: discord.Member,
        modo: app_commands.Choice[str],
        aposta: int = 0,
    ):
        modo_valor = modo.value

        if oponente.id == interaction.user.id:
            await interaction.response.send_message("❌ Você não pode batalhar contra si mesmo.", ephemeral=True)
            return
        if oponente.bot:
            await interaction.response.send_message("❌ Você não pode batalhar contra um bot.", ephemeral=True)
            return
        if aposta < 0:
            await interaction.response.send_message("❌ A aposta não pode ser negativa.", ephemeral=True)
            return

        # Verifica escalações completas
        lineup_desafiante = await db.get_lineup(interaction.user.id, modo_valor)
        lineup_oponente = await db.get_lineup(oponente.id, modo_valor)

        if not slots_completos(modo_valor, lineup_desafiante):
            await interaction.response.send_message(
                f"❌ Sua escalação de **{modo_valor}** está incompleta. Use `/time_ver modo:{modo_valor}` para conferir.",
                ephemeral=True,
            )
            return
        if not slots_completos(modo_valor, lineup_oponente):
            await interaction.response.send_message(
                f"❌ A escalação de **{modo_valor}** de {oponente.display_name} está incompleta. "
                f"Ele(a) precisa completar o time antes de batalhar.",
                ephemeral=True,
            )
            return

        # Verifica saldo, se houver aposta
        if aposta > 0:
            saldo_desafiante = await db.get_balance(interaction.user.id)
            saldo_oponente = await db.get_balance(oponente.id)
            if saldo_desafiante < aposta:
                await interaction.response.send_message(
                    f"❌ Você não tem {config.MOEDA_EMOJI} **{aposta}** para apostar.", ephemeral=True
                )
                return
            if saldo_oponente < aposta:
                await interaction.response.send_message(
                    f"❌ {oponente.display_name} não tem saldo suficiente para cobrir essa aposta.",
                    ephemeral=True,
                )
                return

        # Envia o desafio com botões para o oponente confirmar
        view = ConfirmarBatalhaView(interaction.user, oponente, modo_valor, aposta)
        aposta_texto = f"{config.MOEDA_EMOJI} **{aposta} {config.MOEDA_NOME}**" if aposta > 0 else "sem aposta"
        embed_desafio = discord.Embed(
            title="⚔️ Desafio de batalha!",
            description=(
                f"{interaction.user.mention} desafiou {oponente.mention} para uma batalha **{modo_valor}**!\n"
                f"Aposta: {aposta_texto}\n\n"
                f"{oponente.mention}, você tem {config.BATALHA_TIMEOUT_CONFIRMACAO}s para aceitar ou recusar."
            ),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed_desafio, view=view)
        view.message = await interaction.original_response()
        await view.wait()

        if view.resultado is not True:
            return  # recusou ou expirou; a própria view já atualizou a mensagem

        # Recalcula saldos e escalações no momento da aceitação (podem ter mudado)
        if aposta > 0:
            saldo_desafiante = await db.get_balance(interaction.user.id)
            saldo_oponente = await db.get_balance(oponente.id)
            if saldo_desafiante < aposta or saldo_oponente < aposta:
                await interaction.followup.send(
                    "❌ Um dos jogadores não tem mais saldo suficiente para essa aposta. Batalha cancelada."
                )
                return

        lineup_desafiante = await db.get_lineup(interaction.user.id, modo_valor)
        lineup_oponente = await db.get_lineup(oponente.id, modo_valor)

        identidade_desafiante = await db.get_identidade_time(interaction.user.id)
        identidade_oponente = await db.get_identidade_time(oponente.id)
        nome_desafiante = identidade_desafiante["time_nome"]
        nome_oponente_time = identidade_oponente["time_nome"]

        embed_partida = discord.Embed(
            title=f"🏟️ {identidade_desafiante['estadio_nome']} — {nome_desafiante} x {nome_oponente_time}",
            description="⚽ Bola rolando...",
            color=discord.Color.blue(),
        )
        mensagem = await interaction.followup.send(embed=embed_partida, wait=True)

        placar_desafiante, placar_oponente, artilheiros_desafiante, artilheiros_oponente, assistentes_desafiante, assistentes_oponente, defesas_desafiante, defesas_oponente = await narrar_partida(
            mensagem, embed_partida,
            nome_desafiante, normalizar_time(lineup_desafiante),
            nome_oponente_time, normalizar_time(lineup_oponente),
        )

        embed_resultado = discord.Embed(
            title=f"🏆 Fim de jogo: {nome_desafiante} {placar_desafiante} x {placar_oponente} {nome_oponente_time}",
            color=discord.Color.blurple(),
        )
        embed_resultado.add_field(name=f"⚽ Gols — {nome_desafiante}", value=formatar_artilheiros(artilheiros_desafiante), inline=True)
        embed_resultado.add_field(name=f"⚽ Gols — {nome_oponente_time}", value=formatar_artilheiros(artilheiros_oponente), inline=True)
        embed_resultado.add_field(name=f"👟 Assistências — {nome_desafiante}", value=formatar_estatistica(assistentes_desafiante, "👟"), inline=True)
        embed_resultado.add_field(name=f"👟 Assistências — {nome_oponente_time}", value=formatar_estatistica(assistentes_oponente, "👟"), inline=True)
        embed_resultado.add_field(name=f"🧤 Defesas — {nome_desafiante}", value=formatar_estatistica(defesas_desafiante, "🧤"), inline=True)
        embed_resultado.add_field(name=f"🧤 Defesas — {nome_oponente_time}", value=formatar_estatistica(defesas_oponente, "🧤"), inline=True)

        penalti = None
        if placar_desafiante == placar_oponente:
            penalti = resolver_penaltis(
                normalizar_time(lineup_desafiante),
                normalizar_time(lineup_oponente),
            )
            embed_resultado.add_field(
                name="🥅 Disputa de pênaltis",
                value=formatar_penaltis(penalti, nome_desafiante, nome_oponente_time),
                inline=False,
            )

        nome_mvp, time_mvp, gols_mvp, assist_mvp, defesas_mvp = determinar_mvp(
            nome_desafiante, artilheiros_desafiante, normalizar_time(lineup_desafiante),
            nome_oponente_time, artilheiros_oponente, normalizar_time(lineup_oponente),
            assistentes_desafiante, assistentes_oponente, defesas_desafiante, defesas_oponente,
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
        embed_resultado.add_field(name="MVP da partida", value=texto_mvp, inline=False)

        if placar_desafiante == placar_oponente:
            if penalti["vencedor"] == "a":
                vencedor, perdedor = interaction.user, oponente
            else:
                vencedor, perdedor = oponente, interaction.user
            embed_resultado.description = (
                f"🥅 **Pênaltis!** {vencedor.display_name} venceu a disputa."
            )
        else:
            if placar_desafiante > placar_oponente:
                vencedor, perdedor = interaction.user, oponente
            else:
                vencedor, perdedor = oponente, interaction.user

            if aposta > 0:
                await db.update_balance(vencedor.id, aposta)
                await db.update_balance(perdedor.id, -aposta)
                embed_resultado.description = (
                    f"🎉 **{vencedor.display_name}** venceu e ganhou {config.MOEDA_EMOJI} "
                    f"**{aposta} {config.MOEDA_NOME}** de {perdedor.display_name}!"
                )
            else:
                embed_resultado.description = f"🎉 **{vencedor.display_name}** venceu a batalha!"

        await mensagem.edit(embed=embed_resultado)


async def setup(bot: commands.Bot):
    await bot.add_cog(Batalha(bot))

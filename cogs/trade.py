"""Comando /trade: troca cartas suas por cartas de outro jogador (com confirmação)."""

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from players_data import buscar_jogador_catalogo, jogador_obtivel


class ConfirmarTradeView(discord.ui.View):
    """Botões Aceitar/Recusar mostrados pra quem recebeu a proposta de troca."""

    def __init__(self, proponente: discord.Member, oponente: discord.Member, minha_carta: str, carta_dele: str, amount: int, minha_carta_id: int, carta_dele_id: int):
        super().__init__(timeout=60)
        self.proponente = proponente
        self.oponente = oponente
        self.minha_carta = minha_carta
        self.carta_dele = carta_dele
        self.amount = amount
        self.minha_carta_id = minha_carta_id
        self.carta_dele_id = carta_dele_id
        self.resultado = None
        self.message: discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.oponente.id:
            await interaction.response.send_message(
                "❌ Só quem recebeu a proposta pode responder a ela.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Aceitar", style=discord.ButtonStyle.success, emoji="🤝")
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
                await self.message.edit(content="⏳ A proposta de troca expirou.", view=self)
            except discord.HTTPException:
                pass


class Trade(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="trade", description="Proponha trocar cartas suas por cartas de outro jogador")
    @app_commands.describe(
        oponente="Com quem você quer trocar",
        minha_carta="Carta sua que você vai dar",
        carta_dele="Carta que você quer receber (confira com /inventario jogador:<ele>)",
        amount="Quantidade de Robux adicionada à oferta (opcional; padrão 0)",
    )
    async def trade(
        self,
        interaction: discord.Interaction,
        oponente: discord.Member,
        minha_carta: str,
        carta_dele: str,
        amount: int = 0,
    ):
        if oponente.id == interaction.user.id:
            await interaction.response.send_message("❌ Você não pode trocar consigo mesmo.", ephemeral=True)
            return
        if oponente.bot:
            await interaction.response.send_message("❌ Você não pode trocar com um bot.", ephemeral=True)
            return

        if amount < 0:
            await interaction.response.send_message("❌ O `amount` não pode ser negativo.", ephemeral=True)
            return

        saldo_proponente = await db.get_balance(interaction.user.id)
        if saldo_proponente < amount:
            await interaction.response.send_message(
                f"❌ Você não possui Robux suficientes para oferecer **{amount} {config.MOEDA_NOME}**. "
                f"Seu saldo: **{saldo_proponente} {config.MOEDA_NOME}**.", ephemeral=True
            )
            return

        elenco_proponente = await db.get_user_players(interaction.user.id)
        elenco_oponente = await db.get_user_players(oponente.id)

        def _identidade(valor):
            partes = valor.split("||")
            nome = partes[0].strip()
            raridade = partes[1].strip() if len(partes) > 1 else None
            try:
                overall = int(partes[2]) if len(partes) > 2 else None
            except ValueError:
                overall = None
            return nome, raridade, overall

        nome_minha_oficial, raridade_minha, overall_minha = _identidade(minha_carta)
        nome_dele_oficial, raridade_dele, overall_dele = _identidade(carta_dele)

        carta_minha = next((p for p in elenco_proponente if
            p["player_name"].lower() == nome_minha_oficial.lower() and
            (raridade_minha is None or p["rarity"].lower() == raridade_minha.lower()) and
            (overall_minha is None or p["overall"] == overall_minha)), None)
        carta_dele_db = next((p for p in elenco_oponente if
            p["player_name"].lower() == nome_dele_oficial.lower() and
            (raridade_dele is None or p["rarity"].lower() == raridade_dele.lower()) and
            (overall_dele is None or p["overall"] == overall_dele)), None)

        if carta_minha is None:
            await interaction.response.send_message(f"❌ Você não possui **{minha_carta}**.", ephemeral=True)
            return
        if carta_dele_db is None:
            await interaction.response.send_message(
                f"❌ {oponente.display_name} não possui **{carta_dele}**. "
                f"Confira com `/inventario jogador:{oponente.mention}`.",
                ephemeral=True,
            )
            return


        # Cartas marcadas como obtainable=False não podem entrar em trocas.
        jogador_dele_catalogo = buscar_jogador_catalogo(nome_dele_oficial, raridade_dele, overall_dele)
        jogador_minha_catalogo = buscar_jogador_catalogo(nome_minha_oficial, raridade_minha, overall_minha)

        if jogador_dele_catalogo and not jogador_obtivel(jogador_dele_catalogo):
            await interaction.response.send_message(
                f"❌ **{nome_dele_oficial}** é uma carta exclusiva e não pode ser obtida por troca.",
                ephemeral=True,
            )
            return

        if jogador_minha_catalogo and not jogador_obtivel(jogador_minha_catalogo):
            await interaction.response.send_message(
                f"❌ **{nome_minha_oficial}** é uma carta exclusiva e não pode ser colocada em troca.",
                ephemeral=True,
            )
            return

        oferta_dinheiro = (
            f" + {config.MOEDA_EMOJI} **{amount} {config.MOEDA_NOME}**"
            if amount > 0 else ""
        )
        embed = discord.Embed(
            title="🔄 Proposta de troca",
            description=(
                f"{interaction.user.mention} oferece **{nome_minha_oficial}**{oferta_dinheiro}\n"
                f"em troca de **{nome_dele_oficial}** de {oponente.mention}\n\n"
                f"{oponente.mention}, você aceita?"
            ),
            color=discord.Color.orange(),
        )
        view = ConfirmarTradeView(
            interaction.user, oponente, nome_minha_oficial, nome_dele_oficial, amount,
            carta_minha["id"], carta_dele_db["id"]
        )
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        await view.wait()

        if view.resultado is not True:
            return  # recusou ou expirou; a própria view já atualizou a mensagem

        # Revalida e executa a troca de forma atômica usando os IDs exatos das cartas.
        # Isso evita que a própria remoção da carta faça a trade parecer inválida.
        resultado_trade = await db.execute_trade(
            proponente_id=interaction.user.id,
            oponente_id=oponente.id,
            minha_carta_id=view.minha_carta_id,
            carta_dele_id=view.carta_dele_id,
            amount=amount,
        )

        if not resultado_trade["ok"]:
            mensagens = {
                "indisponivel": "❌ A troca não pôde ser concluída — uma das cartas não está mais disponível.",
                "limite_proponente": f"❌ A troca foi cancelada — você já possui **2x {nome_dele_oficial}**, que é o máximo permitido.",
                "limite_oponente": f"❌ A troca foi cancelada — {oponente.mention} já possui **2x {nome_minha_oficial}**, que é o máximo permitido.",
                "saldo": f"❌ A troca foi cancelada — você não possui mais **{amount} {config.MOEDA_NOME}** disponíveis.",
            }
            await interaction.followup.send(mensagens.get(resultado_trade["motivo"], "❌ A troca não pôde ser concluída."))
            return

        resultados_proponente = [{"duplicado": False, "cheio": False, "valor": None}]
        resultados_oponente = [{"duplicado": False, "cheio": False, "valor": None}]

        linhas = [f"✅ **Troca concluída!** — troca de 1x cada carta"]
        if amount > 0:
            linhas.append(f"💰 {interaction.user.mention} transferiu **{amount} {config.MOEDA_NOME}** para {oponente.mention}.")

        def resumo_resultados(usuario_mention, nome, resultados):
            recebidas = sum(1 for r in resultados if not r["duplicado"] and not r["cheio"])
            vendidas = sum(r["valor"] or 0 for r in resultados if r["duplicado"] or r["cheio"])
            if recebidas and vendidas:
                return f"{usuario_mention} recebeu **{recebidas}x {nome}** e converteu o restante em {config.MOEDA_EMOJI} **{vendidas} {config.MOEDA_NOME}**."
            if recebidas:
                return f"{usuario_mention} recebeu **{recebidas}x {nome}**."
            return f"{usuario_mention} recebeu {config.MOEDA_EMOJI} **{vendidas} {config.MOEDA_NOME}** no lugar das cartas duplicadas/indisponíveis."

        linhas.append(resumo_resultados(interaction.user.mention, nome_dele_oficial, resultados_proponente))
        linhas.append(resumo_resultados(oponente.mention, nome_minha_oficial, resultados_oponente))

        embed_final = discord.Embed(description="\n".join(linhas), color=discord.Color.green())
        await interaction.followup.send(embed=embed_final)

    @trade.autocomplete("minha_carta")
    async def minha_carta_autocomplete(self, interaction: discord.Interaction, atual: str):
        elenco = await db.get_user_players(interaction.user.id)
        return self._cartas_autocomplete(elenco, atual)

    @trade.autocomplete("carta_dele")
    async def carta_dele_autocomplete(self, interaction: discord.Interaction, atual: str):
        oponente = getattr(interaction.namespace, "oponente", None)
        if not isinstance(oponente, discord.Member):
            return []
        elenco = await db.get_user_players(oponente.id)
        return self._cartas_autocomplete(elenco, atual)

    @staticmethod
    def _cartas_autocomplete(elenco, atual):
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
    await bot.add_cog(Trade(bot))

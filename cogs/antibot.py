"""Verificação anti-autoclick para abertura de pacotes."""

import random

import discord

import config
import database as db


class VerificacaoAntiBotView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=config.ANTIBOT_TIMEOUT_SEGUNDOS)
        self.user_id = user_id
        self.codigo = random.choice(config.ANTIBOT_SIMBOLOS)
        simbolos = list(config.ANTIBOT_SIMBOLOS)
        random.shuffle(simbolos)

        for simbolo in simbolos:
            self.add_item(BotaoVerificacao(simbolo, simbolo == self.codigo, user_id))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class BotaoVerificacao(discord.ui.Button):
    def __init__(self, simbolo: str, correto: bool, user_id: int):
        super().__init__(
            label=simbolo,
            style=discord.ButtonStyle.secondary,
        )
        self.correto = correto
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Essa verificação pertence a outro usuário.",
                ephemeral=True,
            )
            return

        if self.correto:
            await db.reset_package_opens_since_verification(self.user_id)

            for item in self.view.children:
                item.disabled = True

            await interaction.response.edit_message(
                content="✅ Verificação concluída! Você pode continuar abrindo pacotes.",
                view=self.view,
            )
            self.view.stop()
            return

        await interaction.response.send_message(
            "❌ Resposta incorreta. Tente abrir o pacote novamente para fazer uma nova verificação.",
            ephemeral=True,
        )
        self.view.stop()


async def verificar_se_necessario(interaction: discord.Interaction) -> bool:
    """Retorna True se a abertura deve ser bloqueada para verificação."""
    contador = await db.get_package_opens_since_verification(interaction.user.id)

    if contador < config.ANTIBOT_ABERTURAS:
        return False

    view = VerificacaoAntiBotView(interaction.user.id)
    await interaction.response.send_message(
        "🤖 **Verificação anti-bot**\n\n"
        "Você abriu vários pacotes rapidamente. "
        f"Para continuar, clique no símbolo **{view.codigo}** abaixo.\n"
        "A posição dos botões muda a cada verificação.",
        view=view,
        ephemeral=True,
    )
    return True

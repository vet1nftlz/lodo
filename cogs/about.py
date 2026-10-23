"""Comando /about: informações configuráveis sobre raridades e jogadores Limited."""

import discord
from discord import app_commands
from discord.ext import commands

import config
from cards import construir_card
from players_data import PLAYERS_CATALOG


class AboutView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id

        raridades = [
            discord.SelectOption(
                label=raridade,
                value=f"raridade:{raridade}",
                emoji=config.EMOJI_RARIDADE.get(raridade, "🔹"),
            )
            for raridade in config.ORDEM_RARIDADE
            if raridade in config.ABOUT_RARIDADES
        ]
        self.rarity_select = discord.ui.Select(
            placeholder="🏆 Escolha uma raridade",
            options=raridades[:25] or [
                discord.SelectOption(label="Nenhuma configurada", value="none")
            ],
            row=0,
        )
        self.rarity_select.callback = self._raridade_callback
        self.add_item(self.rarity_select)

        limited_names = [
            p["name"] for p in PLAYERS_CATALOG
            if str(p.get("rarity", "")).lower() == "limited"
        ]
        limited_names = list(dict.fromkeys(limited_names))
        self.limited_select = discord.ui.Select(
            placeholder="⌛ Escolha um Limited",
            options=[
                discord.SelectOption(
                    label=nome[:100],
                    value=f"limited:{nome}",
                    emoji="⌛",
                )
                for nome in limited_names[:25]
            ] or [
                discord.SelectOption(label="Nenhum Limited cadastrado", value="none")
            ],
            row=1,
        )
        self.limited_select.callback = self._limited_callback
        self.add_item(self.limited_select)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Esse painel pertence a outra pessoa.",
                ephemeral=True,
            )
            return False
        return True

    async def _raridade_callback(self, interaction: discord.Interaction):
        valor = self.rarity_select.values[0]
        if valor == "none":
            await interaction.response.send_message("❌ Nenhuma raridade configurada.", ephemeral=True)
            return
        raridade = valor.split(":", 1)[1]
        descricao = config.ABOUT_RARIDADES.get(
            raridade,
            "Você ainda não colocou a descrição dessa raridade em config.py.",
        )
        embed = discord.Embed(
            title=f"{config.EMOJI_RARIDADE.get(raridade, '🔹')} {raridade}",
            description=descricao,
            color=config.COR_RARIDADE.get(raridade, discord.Color.blurple()),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _limited_callback(self, interaction: discord.Interaction):
        valor = self.limited_select.values[0]
        if valor == "none":
            await interaction.response.send_message("❌ Nenhum Limited cadastrado.", ephemeral=True)
            return

        nome = valor.split(":", 1)[1]
        jogador = next(
            (
                p for p in PLAYERS_CATALOG
                if p.get("name") == nome and str(p.get("rarity", "")).lower() == "limited"
            ),
            None,
        )
        if jogador is None:
            await interaction.response.send_message("❌ Não encontrei esse Limited no catálogo.", ephemeral=True)
            return

        descricao = config.ABOUT_LIMITED.get(
            nome,
            "Você ainda não colocou a descrição desse Limited em config.py.",
        )
        embed = discord.Embed(
            title=f"⌛ {nome}",
            description=descricao,
            color=config.COR_RARIDADE.get("Limited", discord.Color.gold()),
        )
        embed.add_field(
            name="Carta",
            value=f"**{jogador.get('position', '?')}** · **{jogador.get('overall', '?')} OVR**",
            inline=False,
        )

        arquivo = None
        imagem = jogador.get("image")
        if imagem:
            import os
            caminho = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets", "cards", imagem,
            )
            if os.path.isfile(caminho):
                arquivo = discord.File(caminho, filename=imagem)
                embed.set_thumbnail(url=f"attachment://{imagem}")

        if arquivo:
            await interaction.response.edit_message(embed=embed, attachments=[arquivo], view=self)
        else:
            embed.set_footer(text="Sem imagem cadastrada para este Limited.")
            await interaction.response.edit_message(embed=embed, view=self)


class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="about", description="Veja informações sobre raridades e jogadores Limited")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="ℹ️ About",
            description=(
                "Escolha abaixo se quer consultar uma **raridade** ou um **jogador Limited**.\n"
                "As informações são configuradas no `config.py`."
            ),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(
            embed=embed,
            view=AboutView(interaction.user.id),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))

"""Comandos de loja e elenco: /loja (pacotes + expandir inventário) e /inventario."""

import asyncio
import os
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from cards import construir_card
from gacha_logic import abrir_pacote, abrir_varios_pacotes, comprar_pacotes
from players_data import PLAYERS_CATALOG, buscar_jogador_catalogo, COUNTRY_FLAGS
from cogs.antibot import verificar_se_necessario
from cogs.pro import sincronizar_pro


def construir_embed_icon() -> discord.Embed:
    """Embed da aba exclusiva do Pacote Icon."""
    pacote = config.PACOTES.get("icon", {})

    raridades = pacote.get(
        "raridades",
        [
            "Ouro",
            "Elite",
            "Dominante",
            "Immortal",
            "Lendário",
            "Mítico",
            "Icon",
        ],
    )

    raridades_texto = "\n".join(
        f"• {raridade}" for raridade in raridades
    )

    embed = discord.Embed(
        title="<:icon:1553554131484938340> Pacote Icon",
        description=(
            f"💰 Preço: **{config.MOEDA_EMOJI} "
            f"{pacote.get('preco', 0)} {config.MOEDA_NOME}**\n\n"
            "Este pacote contém:\n"
            f"{raridades_texto}\n\n"
        ),
        color=discord.Color.from_rgb(255, 255, 255),
    )

    imagem = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "assets",
        "icon_loja.png",
    )

    if os.path.exists(imagem):
        embed.set_image(url="attachment://icon_loja.png")
    else:
        embed.add_field(
            name="🖼️ Imagem do pacote",
            value=(
                "Adicione `icon_loja.png` dentro da pasta "
                "`assets` para exibir o banner."
            ),
            inline=False,
        )

    embed.set_footer(
        text="Clique em Comprar 1x para adquirir o Pacote Icon."
    )

    return embed


async def _comprar_icon(interaction: discord.Interaction):
    """Compra exatamente 1 Icon usando a transação atômica do banco."""

    resultado = await db.comprar_icon_pacote(
        interaction.user.id
    )

    if not resultado.get("ok"):
        motivo = resultado.get("motivo")

        if motivo == "cooldown":
            restante = float(
                resultado.get("restante", 0)
            )

            minutos = int(restante) // 60
            segundos = int(restante) % 60

            tempo = (
                f"{minutos}min {segundos}s"
                if minutos
                else f"{segundos}s"
            )

            await interaction.response.send_message(
                f"⏳ Aguarde **{tempo}** para comprar outro **Pacote Icon**.",
                ephemeral=True,
            )
            return

        if motivo == "saldo":
            preco = resultado.get(
                "preco",
                config.PACOTES["icon"].get("preco", 0),
            )

            saldo = resultado.get(
                "saldo",
                0,
            )

            await interaction.response.send_message(
                f"❌ Saldo insuficiente. Você precisa de "
                f"{config.MOEDA_EMOJI} **{preco} {config.MOEDA_NOME}** "
                f"e tem {config.MOEDA_EMOJI} **{saldo}**.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "❌ Não foi possível comprar o Pacote Icon.",
            ephemeral=True,
        )
        return

    quantidade_total = await db.contar_pacotes(
        interaction.user.id,
        "icon",
    )

    total = resultado.get(
        "total",
        config.PACOTES["icon"].get("preco", 0),
    )

    await interaction.response.send_message(
        embed=discord.Embed(
            title="💠 Compra de Pacote Icon 1x concluída!",
            description=(
                f"Você comprou **1x {config.PACOTES['icon']['nome']}**.\n"
                f"Valor pago: {config.MOEDA_EMOJI} **{total} {config.MOEDA_NOME}**\n"
                f"Agora você possui **{quantidade_total}x** desse pacote no inventário.\n\n"
                f"⏳ Próxima compra disponível em **"
                f"{getattr(config, 'ICON_COOLDOWN_MINUTOS', 30)} minutos**."
            ),
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )


def usuario_e_booster(member: discord.Member) -> bool:
    """Verifica cargo Server Booster ou usuário liberado manualmente."""

    if member.id in config.BOOSTER_USER_IDS:
        return True

    if config.BOOSTER_ROLE_ID:
        return any(
            role.id == config.BOOSTER_ROLE_ID
            for role in member.roles
        )

    return any(
        role.name == config.BOOSTER_ROLE_NOME
        for role in member.roles
    )


def construir_embed_pacotes(
    member: discord.Member = None,
) -> discord.Embed:

    embed = discord.Embed(
        title="🎁 Loja",
        description=(
            "Ninguém sabe o que vem no pacote até abrir!\n"
            "Use os botões abaixo para comprar pacotes e guardar eles no inventário."
        ),
        color=discord.Color.purple(),
    )

    # O Pacote Icon continua existindo no sistema,
    # mas não aparece na loja.
    for chave, pacote in config.PACOTES.items():

        # Só exibe pacotes marcados explicitamente como disponíveis na loja.
        # Para liberar um pacote, basta mudar "na_loja": False para True
        # dentro do próprio pacote em config.py.
        if not pacote.get("na_loja", False):
            continue


        linhas = [
            f"{config.EMOJI_RARIDADE.get(raridade, '')} **{raridade}**"
            for raridade, peso in pacote["pesos"].items()
        ]

        embed.add_field(
            name=(
                f"{pacote.get('emoji', '')} "
                f"{pacote['nome']} — "
                f"{config.MOEDA_EMOJI} "
                f"{pacote['preco']}"
            ),
            value="\n".join(linhas),
            inline=True,
        )

    embed.add_field(
        name=(
            f"📦 Expandir Inventário — "
            f"{config.MOEDA_EMOJI} "
            f"{config.EXPANSAO_INVENTARIO_PRECO}"
        ),
        value=(
            f"Adiciona +{config.EXPANSAO_INVENTARIO_SLOTS} "
            "espaços permanentes no seu elenco."
        ),
        inline=False,
    )

    return embed


def descrever_resultado_carta(
    embed: discord.Embed,
    jogador: dict,
):
    """Adiciona ao embed a linha certa dependendo do resultado."""

    if jogador.get("duplicado", False):
        embed.description += (
            f"\n💰 Você já tinha essa carta — convertida automaticamente em "
            f"{config.MOEDA_EMOJI} **{jogador.get('valor_venda', 0)} "
            f"{config.MOEDA_NOME}**!"
        )

    elif jogador.get("cheio", False):
        embed.description += (
            f"\n📦 Seu inventário está cheio — convertida automaticamente em "
            f"{config.MOEDA_EMOJI} **{jogador.get('valor_venda', 0)} "
            f"{config.MOEDA_NOME}**! "
            f"Use `/loja` pra expandir o espaço."
        )

    else:
        embed.description += "\n✅ Adicionada ao seu elenco!"


def e_limited(jogador: dict) -> bool:
    """Indica se a carta usa a animação de revelação Special/Limited."""
    return str(jogador.get("rarity", "")).strip().lower() in {
        "limited",
        "special",
    }


def e_big_time(jogador: dict) -> bool:
    """Indica se a carta usa a animação exclusiva do Big Time."""
    return str(jogador.get("rarity", "")).strip().lower() == "big time"


async def enviar_resultado_carta(
    interaction: discord.Interaction,
    jogador: dict,
):
    """Envia a carta aberta com a animação correspondente à raridade."""

    # Big Time: animação exclusiva
    if e_big_time(jogador):
        pais = jogador.get("country", "Não informado")
        bandeira = COUNTRY_FLAGS.get(pais, "🌎")
        posicao = jogador.get("position", "?")
        overall = jogador.get("overall", "?")

        # Cada frame avança o relógio e reinicia os pontos após "...":
        # 🕛. -> 🕑.. -> 🕒... -> 🕓. -> 🕔.. -> 🕕...
        frames = [
            ("🕛", "."),
            ("🕑", ".."),
            ("🕒", "..."),
            ("🕓", "."),
            ("🕔", ".."),
            ("🕕", "..."),
        ]

        drama = discord.Embed(
            title=f"{frames[0][0]}{frames[0][1]}",
            description="",
            color=discord.Color.from_rgb(255, 215, 0),
        )

        mensagem = await interaction.followup.send(
            embed=drama,
            wait=True,
        )

        for emoji, pontos in frames[1:]:
            await asyncio.sleep(0.75)
            drama.title = f"{emoji}{pontos}"
            await mensagem.edit(embed=drama)

        await asyncio.sleep(0.75)

        drama.title = "🕰️ Big Time"
        drama.description = f"**POSIÇÃO**\n# {posicao}"
        await mensagem.edit(embed=drama)

        await asyncio.sleep(1.2)
        drama.description = (
            f"**POSIÇÃO**\n# {posicao}\n\n"
            f"**PAÍS**\n# {bandeira}"
        )
        await mensagem.edit(embed=drama)

        await asyncio.sleep(1.2)
        drama.description = (
            f"**POSIÇÃO**\n# {posicao}\n\n"
            f"**PAÍS**\n# {bandeira}\n\n"
            f"**OVERALL**\n# {overall}"
        )
        await mensagem.edit(embed=drama)

        await asyncio.sleep(1.5)

        embed, arquivo = construir_card(jogador)
        embed.title = "🕰️ Você abriu um Big Time!"
        descrever_resultado_carta(embed, jogador)

        if arquivo:
            await mensagem.edit(
                embed=embed,
                attachments=[arquivo],
            )
        else:
            await mensagem.edit(
                embed=embed,
                attachments=[],
            )
        return

    # Limited / Special
    if e_limited(jogador):
        pais = jogador.get("country", "Não informado")
        bandeira = COUNTRY_FLAGS.get(pais, "🌎")
        posicao = jogador.get("position", "?")
        overall = jogador.get("overall", "?")

        drama = discord.Embed(
            title="❕❕❕",
            description=f"**POSIÇÃO**\n# {posicao}",
            color=discord.Color.from_rgb(255, 215, 0),
        )

        mensagem = await interaction.followup.send(
            embed=drama,
            wait=True,
        )

        await asyncio.sleep(1.2)
        drama.description = (
            f"**POSIÇÃO**\n# {posicao}\n\n"
            f"**PAÍS**\n# {bandeira}"
        )
        await mensagem.edit(embed=drama)

        await asyncio.sleep(1.2)
        drama.description = (
            f"**POSIÇÃO**\n# {posicao}\n\n"
            f"**PAÍS**\n# {bandeira}\n\n"
            f"**OVERALL**\n# {overall}"
        )
        await mensagem.edit(embed=drama)

        await asyncio.sleep(1.5)

        embed, arquivo = construir_card(jogador)
        embed.title = f"🎁 Pacote aberto! {embed.title}"
        descrever_resultado_carta(embed, jogador)

        if arquivo:
            await mensagem.edit(embed=embed, attachments=[arquivo])
        else:
            await mensagem.edit(embed=embed, attachments=[])
        return

    # Cartas normais
    embed, arquivo = construir_card(jogador)
    embed.title = f"🎁 Pacote aberto! {embed.title}"
    descrever_resultado_carta(embed, jogador)

    if arquivo:
        await interaction.followup.send(embed=embed, file=arquivo)
    else:
        await interaction.followup.send(embed=embed)


class CompraPacoteModal(discord.ui.Modal):

    def __init__(
        self,
        chave_pacote: str,
    ):
        self.chave_pacote = chave_pacote

        pacote = config.PACOTES[
            chave_pacote
        ]

        super().__init__(
            title=f"Comprar {pacote['nome']}"
        )

        self.quantidade = discord.ui.TextInput(
            label="Quantidade",
            placeholder="Ex.: 10",
            required=True,
            min_length=1,
            max_length=10,
        )

        self.add_item(
            self.quantidade
        )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        try:
            quantidade = int(
                self.quantidade.value.strip()
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Coloque uma quantidade inteira válida.",
                ephemeral=True,
            )
            return

        if quantidade <= 0:
            await interaction.response.send_message(
                "❌ A quantidade precisa ser maior que zero.",
                ephemeral=True,
            )
            return


        ok, erro, total = await comprar_pacotes(
            interaction.user.id,
            self.chave_pacote,
            quantidade,
        )

        if not ok:
            await interaction.response.send_message(
                f"❌ {erro}",
                ephemeral=True,
            )
            return

        pacote = config.PACOTES[
            self.chave_pacote
        ]

        quantidade_total = await db.contar_pacotes(
            interaction.user.id,
            self.chave_pacote,
        )

        embed = discord.Embed(
            title="📦 Compra concluída!",
            description=(
                f"Você comprou **{quantidade}x {pacote['nome']}**.\n"
                f"Valor pago: {config.MOEDA_EMOJI} "
                f"**{total} {config.MOEDA_NOME}**\n"
                f"Agora você possui **{quantidade_total}x** "
                f"desse pacote no inventário."
            ),
            color=discord.Color.green(),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


class BotaoAbrirPacote(discord.ui.Button):

    def __init__(
        self,
        chave_pacote: str,
    ):
        pacote = config.PACOTES[
            chave_pacote
        ]

        emoji = None
        estilo = discord.ButtonStyle.primary

        # Emoji customizado
        if pacote.get("emoji_id"):
            emoji = discord.PartialEmoji(
                name=pacote.get("emoji_name"),
                id=int(
                    pacote.get("emoji_id")
                ),
            )

        # Emoji Unicode
        elif pacote.get("emoji"):
            emoji = pacote.get("emoji")

        super().__init__(
            label=pacote["nome"],
            style=estilo,
            emoji=emoji,
        )

        self.chave_pacote = chave_pacote

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        view = self.view

        if (
            isinstance(view, LojaView)
            and interaction.user.id != view.user_id
        ):
            await interaction.response.send_message(
                "❌ Essa loja pertence a outra pessoa.",
                ephemeral=True,
            )
            return


        await interaction.response.send_modal(
            CompraPacoteModal(
                self.chave_pacote
            )
        )


class BotaoComprarIcon(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Comprar 1x",
            style=discord.ButtonStyle.success,
            emoji="💰",
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        view = self.view

        if (
            isinstance(view, IconLojaView)
            and interaction.user.id != view.user_id
        ):
            await interaction.response.send_message(
                "❌ Essa loja pertence a outra pessoa.",
                ephemeral=True,
            )
            return

        await _comprar_icon(
            interaction
        )


class BotaoVoltarLoja(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Voltar à Loja",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        view = self.view

        if (
            isinstance(view, IconLojaView)
            and interaction.user.id != view.user_id
        ):
            await interaction.response.send_message(
                "❌ Essa loja pertence a outra pessoa.",
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(
            embed=construir_embed_pacotes(
                interaction.user
            ),
            view=LojaView(
                interaction.user
            ),
            attachments=[],
        )


class IconLojaView(discord.ui.View):
    """Aba exclusiva do Pacote Icon."""

    def __init__(
        self,
        interaction_user: discord.Member,
    ):
        super().__init__(
            timeout=180
        )

        self.user_id = interaction_user.id

        self.add_item(
            BotaoComprarIcon()
        )

        self.add_item(
            BotaoVoltarLoja()
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Essa loja pertence a outra pessoa.",
                ephemeral=True,
            )
            return False

        return True


class BotaoExpandirInventario(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label=(
                f"Expandir Inventário "
                f"(+{config.EXPANSAO_INVENTARIO_SLOTS}, "
                f"{config.EXPANSAO_INVENTARIO_PRECO} "
                f"{config.MOEDA_NOME})"
            ),
            style=discord.ButtonStyle.secondary,
            emoji="📦",
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        saldo_atual = await db.get_balance(
            interaction.user.id
        )

        if (
            saldo_atual
            < config.EXPANSAO_INVENTARIO_PRECO
        ):
            await interaction.response.send_message(
                f"❌ Você precisa de "
                f"{config.MOEDA_EMOJI} "
                f"**{config.EXPANSAO_INVENTARIO_PRECO} "
                f"{config.MOEDA_NOME}** pra expandir. "
                f"Você tem "
                f"{config.MOEDA_EMOJI} "
                f"**{saldo_atual}**.",
                ephemeral=True,
            )
            return

        await db.update_balance(
            interaction.user.id,
            -config.EXPANSAO_INVENTARIO_PRECO,
        )

        await db.expandir_inventario(
            interaction.user.id,
            config.EXPANSAO_INVENTARIO_SLOTS,
        )

        nova_capacidade = (
            await db.get_capacidade_inventario(
                interaction.user.id
            )
        )

        embed = discord.Embed(
            description=(
                f"📦 Inventário expandido! "
                f"Novo limite: **{nova_capacidade}** espaços."
            ),
            color=discord.Color.green(),
        )

        await interaction.response.send_message(
            embed=embed
        )


class LojaView(discord.ui.View):

    def __init__(
        self,
        interaction_user: discord.Member,
    ):
        super().__init__(
            timeout=180
        )

        self.user_id = interaction_user.id

        # Adiciona somente os pacotes normais.
        # O Icon continua existindo no sistema,
        # mas não aparece na /loja.
        for chave, pacote in config.PACOTES.items():

            # Só cria botão para pacotes marcados como disponíveis na loja.
            if not pacote.get("na_loja", False):
                continue


            self.add_item(
                BotaoAbrirPacote(
                    chave
                )
            )

        # Apenas UM botão de expandir inventário.
        self.add_item(
            BotaoExpandirInventario()
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Essa loja pertence a outra pessoa.",
                ephemeral=True,
            )
            return False

        return True




def _emoji_pacote(cfg: dict):
    """Converte a configuração do pacote em emoji compatível com Discord UI."""
    if cfg.get("emoji_id"):
        try:
            return discord.PartialEmoji(
                name=cfg.get("emoji_name"),
                id=int(cfg["emoji_id"]),
            )
        except (TypeError, ValueError):
            pass
    return cfg.get("emoji") or "📦"


def _arquivo_imagem_pacote(chave_pacote: str):
    """Retorna o PNG do pacote em assets/pacotes/<chave>.png, quando existir."""
    caminho = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "assets",
        "pacotes",
        f"{chave_pacote}.png",
    )
    if not os.path.exists(caminho):
        return None
    return discord.File(caminho, filename=f"{chave_pacote}.png")


def construir_embed_pacote_inventario(view: "InventarioView"):
    """Embed da aba de pacotes, mostrando um pacote selecionado por vez."""
    pacotes = view.pacotes or {}
    chave = view.pacote_selecionado

    embed = discord.Embed(
        title="📦 Pacotes no inventário",
        color=discord.Color.dark_teal(),
    )

    if not pacotes:
        embed.description = "📦 Você não possui pacotes armazenados."
        return embed, None

    if not chave or chave not in pacotes:
        linhas = []
        for chave_item, quantidade in pacotes.items():
            cfg = config.PACOTES.get(chave_item)
            if not cfg:
                continue
            linhas.append(
                f"{_emoji_pacote(cfg)} **{cfg['nome']}** ×{quantidade}"
            )
        embed.description = (
            "Selecione um pacote abaixo para ver sua imagem e as opções de abertura.\n\n"
            + ("\n".join(linhas) if linhas else "Nenhum pacote válido encontrado.")
        )
        embed.set_footer(text="📦 Selecione um pacote para continuar.")
        return embed, None

    cfg = config.PACOTES.get(chave)
    if not cfg:
        embed.description = "❌ Esse pacote não existe mais na configuração."
        return embed, None

    quantidade = int(pacotes.get(chave, 0))
    embed.title = f"{_emoji_pacote(cfg)} {cfg['nome']}"
    embed.description = (
        f"Você possui **{quantidade}x** deste pacote.\n\n"
        f"Preço de referência: {config.MOEDA_EMOJI} **{cfg.get('preco', 0)} {config.MOEDA_NOME}**\n\n"
        "Clique em **Abrir pacotes** e informe a quantidade exata."
    )
    arquivo = _arquivo_imagem_pacote(chave)
    if arquivo:
        embed.set_image(url=f"attachment://{chave}.png")
    else:
        embed.add_field(
            name="🖼️ Imagem do pacote",
            value=(
                f"Adicione o arquivo `assets/pacotes/{chave}.png`\n"
                "para exibir a imagem do pacote aqui."
            ),
            inline=False,
        )
    embed.set_footer(text=f"No inventário: ×{quantidade}")
    return embed, arquivo


class SeletorPacoteInventario(discord.ui.Select):
    def __init__(self, view: "InventarioView"):
        self.inv_view = view
        opcoes = []
        for chave, quantidade in list((view.pacotes or {}).items())[:25]:
            cfg = config.PACOTES.get(chave)
            if not cfg:
                continue
            opcoes.append(
                discord.SelectOption(
                    label=cfg["nome"][:100],
                    value=chave,
                    description=f"Você possui ×{quantidade}"[:100],
                    emoji=_emoji_pacote(cfg),
                    default=(view.pacote_selecionado == chave),
                )
            )

        super().__init__(
            placeholder="📦 Escolha um pacote do seu inventário",
            options=opcoes or [
                discord.SelectOption(
                    label="Nenhum pacote disponível",
                    value="__none__",
                    default=True,
                )
            ],
            disabled=not opcoes,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        valor = self.values[0]
        if valor == "__none__":
            await interaction.response.send_message(
                "❌ Você não possui nenhum pacote disponível.",
                ephemeral=True,
            )
            return
        self.inv_view.pacote_selecionado = valor
        self.inv_view._montar_controles()
        embed, arquivo = construir_embed_pacote_inventario(self.inv_view)
        kwargs = {"embed": embed, "view": self.inv_view, "attachments": [arquivo] if arquivo else []}
        await interaction.response.edit_message(**kwargs)


class AbrirPacotesModal(discord.ui.Modal):
    def __init__(self, view: "InventarioView", chave_pacote: str, limite: int):
        self.inv_view = view
        self.chave_pacote = chave_pacote
        self.limite = limite
        pacote = config.PACOTES[chave_pacote]
        super().__init__(title=f"Abrir {pacote['nome']}")

        self.quantidade = discord.ui.TextInput(
            label=f"Quantidade exata (Max: {limite})",
            placeholder=f"Digite de 1 a {limite}",
            required=True,
            min_length=1,
            max_length=3,
        )
        self.add_item(self.quantidade)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantidade = int(self.quantidade.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "❌ Digite apenas um número inteiro.",
                ephemeral=True,
            )
            return

        if quantidade < 1 or quantidade > self.limite:
            await interaction.response.send_message(
                f"❌ A quantidade deve estar entre **1** e **{self.limite}**.",
                ephemeral=True,
            )
            return

        disponiveis = await db.contar_pacotes(interaction.user.id, self.chave_pacote)
        if disponiveis < quantidade:
            await interaction.response.send_message(
                f"❌ Você possui apenas **{disponiveis}x** desse pacote.",
                ephemeral=True,
            )
            return

        if not await db.tem_espaco_inventario(interaction.user.id, quantidade):
            await interaction.response.send_message(
                await db.mensagem_sem_espaco(interaction.user.id, quantidade),
                ephemeral=True,
            )
            return

        if quantidade > 1:
            restante = await db.get_multi_open_cooldown(interaction.user.id)
            if restante > 0:
                minutos, segundos = divmod(int(restante), 60)
                tempo = f"{minutos}min {segundos}s" if minutos else f"{segundos}s"
                await interaction.response.send_message(
                    f"⏳ Aguarde **{tempo}** para abrir vários pacotes novamente. "
                    "Você ainda pode abrir 1 pacote por vez.",
                    ephemeral=True,
                )
                return

        if await verificar_se_necessario(interaction):
            return

        await interaction.response.defer()
        is_booster = usuario_e_booster(interaction.user)

        try:
            if quantidade == 1:
                sucesso, jogador, erro = await abrir_pacote(
                    interaction.user.id,
                    self.chave_pacote,
                    is_booster=is_booster,
                )
                if not sucesso:
                    await interaction.followup.send(f"❌ {erro}", ephemeral=True)
                    return
                await enviar_resultado_carta(interaction, jogador)
                return

            resultados, erros = await abrir_varios_pacotes(
                interaction.user.id,
                self.chave_pacote,
                quantidade,
                is_booster=is_booster,
            )
            await db.set_multi_open_cooldown(interaction.user.id)

            if not resultados:
                await interaction.followup.send(
                    f"❌ Nenhum pacote pôde ser aberto. {erros[0] if erros else ''}",
                    ephemeral=True,
                )
                return

            melhores = sorted(
                resultados,
                key=lambda j: (j.get("overall", 0), j.get("estrelas", 0)),
                reverse=True,
            )[:3]
            embed = discord.Embed(
                title=f"📦 {len(resultados)} pacote(s) aberto(s)!",
                description=(
                    "Os **3 melhores jogadores sorteados** nesta abertura foram:\n\n"
                    + "\n".join(
                        f"**{i}. {j['name']}** — {j['rarity']} · **{j['overall']} OVR**"
                        for i, j in enumerate(melhores, 1)
                    )
                ),
                color=discord.Color.gold(),
            )
            adicionados = sum(1 for j in resultados if j.get("novo_id") is not None)
            convertidos = sum(1 for j in resultados if j.get("duplicado") or j.get("cheio"))
            footer = f"📥 {adicionados} jogador(es) adicionado(s) ao inventário"
            if convertidos:
                footer += f" · 💰 {convertidos} convertido(s) em {config.MOEDA_NOME}"
            if erros:
                footer += " · ⚠️ A abertura foi interrompida antes de completar a quantidade."
            embed.set_footer(text=footer)
            await interaction.followup.send(embed=embed)
        except Exception as erro:
            print(f"[INVENTARIO-PACOTES] Erro ao abrir pacote: {erro}")
            await interaction.followup.send(
                "❌ Ocorreu um erro durante a abertura. Verifique o inventário antes de tentar novamente.",
                ephemeral=True,
            )


class BotaoAbrirPacotesInventario(discord.ui.Button):
    def __init__(self, view: "InventarioView"):
        self.inv_view = view
        limite = config.ABRIR_QUANTIDADE_MAX_BOOSTER if usuario_e_booster(view.alvo) else config.ABRIR_QUANTIDADE_MAX
        super().__init__(
            label=f"Abrir pacotes · Max: {limite}",
            style=discord.ButtonStyle.success,
            emoji="📦",
            row=1,
            disabled=(
                not view.pacote_selecionado
                or view.alvo.id != view.user_id
            ),
        )

    async def callback(self, interaction: discord.Interaction):
        if self.inv_view.alvo.id != interaction.user.id:
            await interaction.response.send_message(
                "❌ Você só pode abrir pacotes do seu próprio inventário.",
                ephemeral=True,
            )
            return

        chave = self.inv_view.pacote_selecionado
        if not chave or chave not in self.inv_view.pacotes:
            await interaction.response.send_message(
                "❌ Selecione um pacote primeiro.",
                ephemeral=True,
            )
            return

        limite = config.ABRIR_QUANTIDADE_MAX_BOOSTER if usuario_e_booster(interaction.user) else config.ABRIR_QUANTIDADE_MAX
        await interaction.response.send_modal(
            AbrirPacotesModal(self.inv_view, chave, limite)
        )

class InventarioView(discord.ui.View):
    """Coleção paginada com filtros de posição/raridade e ordenação."""

    def __init__(
        self,
        user_id: int,
        alvo: discord.Member,
        elenco: list,
        capacidade: int,
    ):
        super().__init__(
            timeout=180
        )

        self.user_id = user_id
        self.alvo = alvo
        self.elenco = elenco
        self.capacidade = capacidade
        self.posicao = "Todos"
        self.raridade = "Todas"
        self.ordenacao = "OVR ↓"
        self.pagina = 0
        self.por_pagina = 7
        self.exibicao = "jogadores"
        self.pacotes = {}
        self.pacote_selecionado = None

        self._montar_controles()

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Esse inventário pertence a outra pessoa.",
                ephemeral=True,
            )
            return False

        return True

    def _filtrados(self):

        unicos = {}

        for p in self.elenco:
            chave = (
                p["player_name"],
                p["rarity"],
                p["overall"],
            )

            unicos.setdefault(
                chave,
                p,
            )

        itens = list(
            unicos.values()
        )

        if self.posicao != "Todos":
            itens = [
                p
                for p in itens
                if p["position"] == self.posicao
            ]

        if self.raridade != "Todas":
            itens = [
                p
                for p in itens
                if p["rarity"] == self.raridade
            ]

        if self.ordenacao == "OVR ↓":
            itens.sort(
                key=lambda p: (
                    -int(
                        p.get(
                            "overall",
                            0,
                        )
                        or 0
                    ),
                    str(
                        p.get(
                            "player_name",
                            "",
                        )
                    ).lower(),
                )
            )

        elif self.ordenacao == "OVR ↑":
            itens.sort(
                key=lambda p: (
                    int(
                        p.get(
                            "overall",
                            0,
                        )
                        or 0
                    ),
                    str(
                        p.get(
                            "player_name",
                            "",
                        )
                    ).lower(),
                )
            )

        elif self.ordenacao == "Nome A-Z":
            itens.sort(
                key=lambda p: str(
                    p.get(
                        "player_name",
                        "",
                    )
                ).lower()
            )

        elif self.ordenacao == "Raridade":
            itens.sort(
                key=lambda p: (
                    -config.ORDEM_RARIDADE.index(
                        p["rarity"]
                    )
                    if p["rarity"]
                    in config.ORDEM_RARIDADE
                    else 99,
                    p["player_name"].lower(),
                )
            )

        elif self.ordenacao == "Preço ↓":
            itens.sort(
                key=lambda p: (
                    -self._preco(p),
                    p["player_name"].lower(),
                )
            )

        return itens

    @staticmethod
    def _preco(p):

        c = next(
            (
                j
                for j in PLAYERS_CATALOG
                if j.get("name")
                == p["player_name"]
                and j.get("rarity")
                == p["rarity"]
                and j.get("overall")
                == p["overall"]
            ),
            None,
        )

        return (
            c.get("price", 0)
            if c
            else 0
        )

    def _montar_controles(self):

        self.clear_items()

        if self.exibicao == "jogadores":
            self.add_item(FiltroPosicao(self))
            self.add_item(FiltroRaridade(self))
            self.add_item(FiltroOrdenacao(self))
            self.add_item(BotaoAlternarInventario(self))
            self.add_item(BotaoPagina(self, -1))
            self.add_item(BotaoPagina(self, 1))
        else:
            if self.pacotes:
                self.add_item(SeletorPacoteInventario(self))
                self.add_item(BotaoAbrirPacotesInventario(self))
            self.add_item(BotaoAlternarInventario(self))

    def embed(self):

        itens = self._filtrados()

        total_paginas = max(
            1,
            (
                len(itens)
                + self.por_pagina
                - 1
            )
            // self.por_pagina,
        )

        self.pagina = max(
            0,
            min(
                self.pagina,
                total_paginas - 1,
            ),
        )

        inicio = (
            self.pagina
            * self.por_pagina
        )

        pagina = itens[
            inicio:
            inicio + self.por_pagina
        ]

        embed = discord.Embed(
            title=(
                f"🎒 Coleção de "
                f"{self.alvo.display_name}"
            ),
            color=discord.Color.dark_teal(),
        )

        if self.exibicao == "pacotes":
            embed, _ = construir_embed_pacote_inventario(self)
            return embed

        if not pagina:

            embed.description = (
                "Nenhuma carta encontrada "
                "com esses filtros."
            )

        else:

            vistos = []

            for p in pagina:

                chave = (
                    p["player_name"],
                    p["rarity"],
                    p["overall"],
                )

                if chave in vistos:
                    continue

                vistos.append(
                    chave
                )

                qtd = sum(
                    1
                    for x in self.elenco
                    if (
                        x["player_name"],
                        x["rarity"],
                        x["overall"],
                    )
                    == chave
                )

                cat = (
                    buscar_jogador_catalogo(
                        p["player_name"],
                        p["rarity"],
                        p["overall"],
                    )
                    or {}
                )

                pais = cat.get(
                    "country",
                    "Não informado",
                )

                emoji_raridade = (
                    config.EMOJI_RARIDADE.get(
                        p["rarity"],
                        "🃏",
                    )
                )

                estoque = (
                    f" **×{qtd}**"
                    if qtd > 1
                    else ""
                )

                embed.add_field(
                    name=(
                        f"{emoji_raridade} "
                        f"{p['player_name']}"
                        f"{estoque}"
                    ),
                    value=(
                        f"{pais} · "
                        f"{p['position']} · "
                        f"**{p['overall']} OVR** · "
                        f"{p['rarity']}"
                    ),
                    inline=False,
                )

        embed.set_footer(
            text=(
                f"Página {self.pagina + 1}/"
                f"{total_paginas} · "
                f"{len(self.elenco)}/"
                f"{self.capacidade} espaços · "
                f"Filtro: {self.posicao} / "
                f"{self.raridade} · "
                f"Ordenação: {self.ordenacao}"
            )
        )

        return embed

    async def atualizar(
        self,
        interaction: discord.Interaction,
    ):
        """Atualiza o inventário e edita a mensagem da interação."""

        try:

            self.elenco = await db.get_user_players(
                self.alvo.id
            )

            self.capacidade = (
                await db.get_capacidade_inventario(
                    self.alvo.id
                )
            )

            if self.exibicao == "pacotes":
                self.pacotes = (
                    await db.get_user_packages(
                        self.alvo.id
                    )
                )

            self._montar_controles()

            await interaction.response.edit_message(
                embed=self.embed(),
                view=self,
            )

        except Exception:

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "❌ Não foi possível atualizar o inventário agora.",
                    ephemeral=True,
                )

            else:

                try:
                    await interaction.followup.send(
                        "❌ Não foi possível atualizar o inventário agora.",
                        ephemeral=True,
                    )
                except Exception:
                    pass

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ):
        try:

            mensagem = (
                "❌ Ocorreu um erro ao atualizar o inventário. "
                "Tente usar `/inventario` novamente."
            )

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    mensagem,
                    ephemeral=True,
                )

            else:

                await interaction.followup.send(
                    mensagem,
                    ephemeral=True,
                )

        except Exception:
            pass


class BotaoAlternarInventario(
    discord.ui.Button
):

    def __init__(
        self,
        view,
    ):
        self.inv_view = view

        super().__init__(
            label=(
                "Ver pacotes"
                if view.exibicao == "jogadores"
                else "Ver jogadores"
            ),
            emoji=(
                "📦"
                if view.exibicao == "jogadores"
                else "🃏"
            ),
            style=discord.ButtonStyle.primary,
            row=3,
        )

    async def callback(
        self,
        interaction,
    ):

        self.inv_view.exibicao = (
            "pacotes"
            if self.inv_view.exibicao == "jogadores"
            else "jogadores"
        )

        if self.inv_view.exibicao == "pacotes":
            self.inv_view.pacotes = (
                await db.get_user_packages(
                    self.inv_view.user_id
                )
            )
            self.inv_view.pacote_selecionado = None
        else:
            self.inv_view.pacote_selecionado = None

        self.inv_view.pagina = 0

        await self.inv_view.atualizar(
            interaction
        )


class FiltroPosicao(
    discord.ui.Select
):

    def __init__(
        self,
        view,
    ):
        self.inv_view = view

        options = [
            discord.SelectOption(
                label="Todos",
                value="Todos",
                default=(
                    view.posicao
                    == "Todos"
                ),
            )
        ]

        for pos in config.ORDEM_POSICOES:

            options.append(
                discord.SelectOption(
                    label=pos,
                    value=pos,
                    default=(
                        view.posicao
                        == pos
                    ),
                )
            )

        super().__init__(
            placeholder="⚽ Posição",
            options=options,
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        self.inv_view.posicao = (
            self.values[0]
        )

        self.inv_view.pagina = 0

        await self.inv_view.atualizar(
            interaction
        )


class FiltroRaridade(
    discord.ui.Select
):

    def __init__(
        self,
        view,
    ):
        self.inv_view = view

        options = [
            discord.SelectOption(
                label="Todas",
                value="Todas",
                default=(
                    view.raridade
                    == "Todas"
                ),
            )
        ]

        for rar in config.ORDEM_RARIDADE:

            options.append(
                discord.SelectOption(
                    label=rar,
                    value=rar,
                    default=(
                        view.raridade
                        == rar
                    ),
                )
            )

        super().__init__(
            placeholder="🏆 Raridade",
            options=options,
            row=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        self.inv_view.raridade = (
            self.values[0]
        )

        self.inv_view.pagina = 0

        await self.inv_view.atualizar(
            interaction
        )


class FiltroOrdenacao(
    discord.ui.Select
):

    def __init__(
        self,
        view,
    ):
        self.inv_view = view

        opcoes = [
            "OVR ↓",
            "OVR ↑",
            "Raridade",
            "Nome A-Z",
            "Preço ↓",
        ]

        options = [
            discord.SelectOption(
                label=x,
                value=x,
                default=(
                    view.ordenacao
                    == x
                ),
            )
            for x in opcoes
        ]

        super().__init__(
            placeholder="📊 Ordenar",
            options=options,
            row=2,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        self.inv_view.ordenacao = (
            self.values[0]
        )

        self.inv_view.pagina = 0

        await self.inv_view.atualizar(
            interaction
        )


class BotaoPagina(
    discord.ui.Button
):

    def __init__(
        self,
        view,
        delta,
    ):
        self.inv_view = view
        self.delta = delta

        super().__init__(
            label=(
                "Anterior"
                if delta < 0
                else "Próxima"
            ),
            emoji=(
                "◀️"
                if delta < 0
                else "▶️"
            ),
            style=discord.ButtonStyle.secondary,
            row=4,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        self.inv_view.pagina += (
            self.delta
        )

        await self.inv_view.atualizar(
            interaction
        )


class MultisellModal(
    discord.ui.Modal,
    title="💰 Multisell",
):
    filtro = discord.ui.TextInput(
        label="Tipo de filtro",
        placeholder="Raridade ou OVR",
        required=True,
        max_length=10,
    )

    valor = discord.ui.TextInput(
        label="Valor",
        placeholder="Ex.: Ouro ou 80",
        required=True,
        max_length=20,
    )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        # Modal submissions have only ~3 seconds to be acknowledged.
        # The database operations below can exceed that time, especially
        # when many cards are being sold at once.
        await interaction.response.defer(ephemeral=True)

        try:
            tipo = self.filtro.value.strip().lower()
            valor = self.valor.value.strip()

            elenco = await db.get_user_players(interaction.user.id)

            if not elenco:
                await interaction.followup.send(
                    "❌ Seu inventário está vazio.",
                    ephemeral=True,
                )
                return

            if tipo in {"raridade", "raridade(s)", "rarity"}:
                candidatos = [
                    p for p in elenco
                    if p["rarity"].lower() == valor.lower()
                ]

                if not candidatos:
                    await interaction.followup.send(
                        "❌ Nenhuma carta encontrada com essa raridade.",
                        ephemeral=True,
                    )
                    return

            elif tipo in {"ovr", "overall"}:
                try:
                    limite = int(valor)
                except ValueError:
                    await interaction.followup.send(
                        "❌ Para OVR, coloque um número. Ex.: `80`.",
                        ephemeral=True,
                    )
                    return

                candidatos = [
                    p for p in elenco
                    if p["overall"] <= limite
                ]

                if not candidatos:
                    await interaction.followup.send(
                        "❌ Nenhuma carta encontrada até esse OVR.",
                        ephemeral=True,
                    )
                    return

            else:
                await interaction.followup.send(
                    "❌ Tipo inválido. Use `Raridade` ou `OVR`.",
                    ephemeral=True,
                )
                return

            total = 0
            cartas = 0
            nomes = []

            for p in list(candidatos):
                cat = buscar_jogador_catalogo(
                    p["player_name"],
                    p["rarity"],
                    p["overall"],
                )

                preco = cat.get("price", 0) if cat else 0

                if await db.remove_player_by_id(p["id"]):
                    total += preco
                    cartas += 1

                    if p["player_name"] not in nomes:
                        nomes.append(p["player_name"])

            await db.update_balance(
                interaction.user.id,
                total,
            )

            resumo = ", ".join(nomes[:8])
            if len(nomes) > 8:
                resumo += "..."

            await interaction.followup.send(
                f"💰 **Multisell concluído!**\n"
                f"Vendidas: **{cartas} carta(s)**\n"
                f"Jogadores: {resumo}\n"
                f"Recebido: {config.MOEDA_EMOJI} "
                f"**{total} {config.MOEDA_NOME}**",
                ephemeral=False,
            )

        except Exception as erro:
            print(f"[MULTISELL] Erro ao processar modal: {erro}")
            try:
                await interaction.followup.send(
                    "❌ Ocorreu um erro ao processar o Multisell. "
                    "Sua venda não deve ser repetida sem conferir o inventário.",
                    ephemeral=True,
                )
            except Exception as envio_erro:
                print(f"[MULTISELL] Falha ao enviar erro: {envio_erro}")


class Loja(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="loja",
        description=(
            "Abra a loja: pacotes misteriosos "
            "e expansão de inventário"
        ),
    )
    async def loja(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.send_message(
            embed=construir_embed_pacotes(
                interaction.user
            ),
            view=LojaView(
                interaction.user
            ),
        )

    @app_commands.command(
        name="inventario",
        description="Veja sua coleção de jogadores",
    )
    @app_commands.describe(
        jogador=(
            "Ver a coleção de outro jogador "
            "(opcional)"
        )
    )
    async def inventario(
        self,
        interaction: discord.Interaction,
        jogador: discord.Member = None,
    ):

        alvo = (
            jogador
            or interaction.user
        )

        await interaction.response.defer()

        elenco = await db.get_user_players(
            alvo.id
        )

        capacidade = (
            await db.get_capacidade_inventario(
                alvo.id
            )
        )

        view = InventarioView(
            interaction.user.id,
            alvo,
            elenco,
            capacidade,
        )

        view.pacotes = (
            await db.get_user_packages(
                alvo.id
            )
        )
        view._montar_controles()

        await interaction.followup.send(
            embed=view.embed(),
            view=view,
        )

    @app_commands.command(
        name="multisell",
        description=(
            "Venda várias cartas por raridade ou OVR"
        ),
    )
    async def multisell(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.send_modal(
            MultisellModal()
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Loja(bot)
    )

"""Transfer Market: anúncios, compra e cancelamento."""

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db


class TransferMarket(commands.GroupCog, group_name="transfermarket", group_description="Mercado de transferências"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="listar", description="Veja os jogadores anunciados no Transfer Market")
    async def listar(self, interaction: discord.Interaction):
        anuncios = await db.get_anuncios_mercado(config.TRANSFER_MARKET_MAX_ANUNCIOS)
        embed = discord.Embed(
            title="💰 Transfer Market",
            description="Use `/transfermarket comprar anuncio:<ID>` para comprar uma carta.",
            color=discord.Color.green(),
        )
        if not anuncios:
            embed.description = "O mercado está vazio."
        else:
            for a in anuncios:
                embed.add_field(
                    name=f"#{a['id']} · {a['player_name']} — {a['overall']} OVR",
                    value=(
                        f"**{a['rarity']}** · {a['position']}\n"
                        f"Preço: {config.MOEDA_EMOJI} **{a['price']} {config.MOEDA_NOME}**\n"
                        f"Vendedor: <@{a['seller_id']}>"
                    ),
                    inline=True,
                )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="vender", description="Anuncie uma carta do seu inventário")
    @app_commands.describe(nome="Carta que você quer anunciar (nome • raridade • OVR)", preco="Preço da venda")
    async def vender(self, interaction: discord.Interaction, nome: str, preco: int):
        if preco <= 0:
            await interaction.response.send_message(
                "❌ O preço precisa ser maior que zero.",
                ephemeral=True,
            )
            return

        # O jogador escolhe a carta pelo nome/raridade/OVR.
        # O ID interno do banco fica totalmente oculto.
        partes = nome.split("||")
        nome_base = partes[0].strip()
        raridade = partes[1].strip() if len(partes) > 1 else None
        try:
            overall = int(partes[2]) if len(partes) > 2 else None
        except ValueError:
            overall = None

        elenco = await db.get_user_players(interaction.user.id)
        nome_lower = nome_base.lower()
        player = next(
            (
                p for p in elenco
                if p["player_name"].lower() == nome_lower
                and (raridade is None or p["rarity"].lower() == raridade.lower())
                and (overall is None or int(p["overall"]) == overall)
            ),
            None,
        )

        if player is None:
            await interaction.response.send_message(
                "❌ Você não possui essa carta. Confira com `/inventario`.",
                ephemeral=True,
            )
            return

        # O ID interno só é usado internamente para criar o anúncio.
        ok, motivo = await db.criar_anuncio_mercado(
            interaction.user.id,
            int(player["id"]),
            preco,
        )
        if not ok:
            mensagens = {
                "ja_anunciada": "Essa carta já está anunciada.",
                "carta_indisponivel": "Essa carta não está disponível para anúncio.",
                "preco_invalido": "O preço precisa ser maior que zero.",
                "mercado_cheio": "O Transfer Market já está cheio.",
            }
            await interaction.response.send_message(
                f"❌ {mensagens.get(motivo, 'Não foi possível criar o anúncio.')}",
                ephemeral=True,
            )
            return

        # Mostra somente o ID do ANÚNCIO, que é o identificador que o jogador usa
        # para comprar/cancelar. Nunca mostramos o ID interno da carta.
        anuncios = await db.get_anuncios_mercado(config.TRANSFER_MARKET_MAX_ANUNCIOS)
        anuncio_criado = next(
            (
                a for a in anuncios
                if int(a["seller_id"]) == int(interaction.user.id)
                and int(a["player_id"]) == int(player["id"])
            ),
            None,
        )

        if anuncio_criado:
            referencia = f"#{anuncio_criado['id']}"
        else:
            referencia = "seu anúncio"

        await interaction.response.send_message(
            f"✅ **{player['player_name']}** ({player['rarity']} · {player['overall']} OVR) "
            f"foi anunciado por {config.MOEDA_EMOJI} **{preco} {config.MOEDA_NOME}**.\n"
            f"ID do anúncio: **{referencia}**",
        )

    @vender.autocomplete("nome")
    async def vender_autocomplete(self, interaction: discord.Interaction, atual: str):
        elenco = await db.get_user_players(interaction.user.id)
        atual_lower = atual.lower()
        opcoes = []
        vistos = set()

        for p in elenco:
            chave = (
                p["player_name"].lower(),
                p["rarity"].lower(),
                int(p["overall"]),
            )
            if chave in vistos:
                continue
            vistos.add(chave)

            label = f'{p["player_name"]} • {p["rarity"]} • OVR {p["overall"]}'
            if atual_lower in label.lower():
                opcoes.append(
                    app_commands.Choice(
                        name=label[:100],
                        value=f'{p["player_name"]}||{p["rarity"]}||{p["overall"]}',
                    )
                )

        return opcoes[:25]

    @app_commands.command(name="comprar", description="Compre um anúncio do Transfer Market")
    @app_commands.describe(anuncio="ID do anúncio")
    async def comprar(self, interaction: discord.Interaction, anuncio: int):
        resultado = await db.comprar_anuncio_mercado(interaction.user.id, anuncio)
        if not resultado["ok"]:
            mensagens = {
                "nao_encontrado": "Esse anúncio não existe mais.",
                "proprio": "Você não pode comprar seu próprio anúncio.",
                "saldo": "Você não tem saldo suficiente.",
                "limite_copias": "Você já possui 2 cópias dessa carta.",
                "inventario": "Seu inventário está cheio.",
                "carta_indisponivel": "Essa carta não está mais disponível para compra.",
            }
            await interaction.response.send_message(
                f"❌ {mensagens.get(resultado['motivo'], 'Não foi possível concluir a compra.')}",
                ephemeral=True,
            )
            return

        a = resultado["anuncio"]
        await interaction.response.send_message(
            f"✅ Você comprou **{a['player_name']}** ({a['rarity']} · {a['overall']} OVR) "
            f"por {config.MOEDA_EMOJI} **{a['price']} {config.MOEDA_NOME}**."
        )

    @app_commands.command(name="cancelar", description="Cancele um anúncio seu")
    @app_commands.describe(anuncio="ID do anúncio")
    async def cancelar(self, interaction: discord.Interaction, anuncio: int):
        ok = await db.cancelar_anuncio_mercado(interaction.user.id, anuncio)
        if not ok:
            await interaction.response.send_message(
                "❌ Anúncio não encontrado ou ele não pertence a você.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(f"✅ Anúncio **#{anuncio}** cancelado.")


async def setup(bot: commands.Bot):
    await bot.add_cog(TransferMarket(bot))

"""Comandos de escalação: /escalar, /escalacao, /time_remover."""

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db


MODOS = [
    app_commands.Choice(name="4v4", value="4v4"),
    app_commands.Choice(name="7v7", value="7v7"),
]

POSICOES = [
    app_commands.Choice(name="Goleiro (GK)", value="GK"),
    app_commands.Choice(name="Meio-campo (MC)", value="MC"),
    app_commands.Choice(name="Atacante (ST)", value="ST"),
]


def overall_total(lineup: list) -> int:
    return sum(p["overall"] for p in lineup)


def slots_completos(modo: str, lineup: list) -> bool:
    """Confere se a escalação atende às regras do modo.

    No 4v4, GK é fixo e as 3 vagas de linha podem ser 1 MC + 2 ST
    ou 2 MC + 1 ST. Nos demais modos, a formação configurada permanece rígida.
    """
    contagem = {}
    for p in lineup:
        contagem[p["posicao"]] = contagem.get(p["posicao"], 0) + 1

    if modo == "4v4":
        return (
            contagem.get("GK", 0) == 1
            and contagem.get("MC", 0) + contagem.get("ST", 0) == 3
            and 0 <= contagem.get("MC", 0) <= 2
            and 0 <= contagem.get("ST", 0) <= 2
        )

    formacao = config.FORMACOES[modo]
    return all(contagem.get(pos, 0) == qtd for pos, qtd in formacao.items())


def _max_slots_para_posicao(modo: str, posicao: str) -> int:
    """Quantos slots existem pra essa posição nesse modo (usado na escolha manual)."""
    if modo == "4v4" and posicao in {"MC", "ST"}:
        return 2  # vaga flexível: até 2 MC ou até 2 ST, respeitando o total de 3 na linha
    return config.FORMACOES[modo].get(posicao, 0)


class Time(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="nomeartime", description="Defina o nome do seu time")
    @app_commands.describe(nome="Nome que aparecerá no seu perfil e nas partidas")
    async def nomeartime(self, interaction: discord.Interaction, nome: str):
        nome = nome.strip()
        if not 2 <= len(nome) <= 32:
            await interaction.response.send_message(
                "❌ O nome do time precisa ter entre **2 e 32 caracteres**.",
                ephemeral=True,
            )
            return
        await db.definir_nome_time(interaction.user.id, nome)
        await interaction.response.send_message(f"✅ Seu time agora se chama **{nome}**.")

    @app_commands.command(name="nomearestadio", description="Defina o nome do seu estádio")
    @app_commands.describe(nome="Nome que aparecerá no seu perfil e nas partidas")
    async def nomearestadio(self, interaction: discord.Interaction, nome: str):
        nome = nome.strip()
        if not 2 <= len(nome) <= 40:
            await interaction.response.send_message(
                "❌ O nome do estádio precisa ter entre **2 e 40 caracteres**.",
                ephemeral=True,
            )
            return
        await db.definir_nome_estadio(interaction.user.id, nome)
        await interaction.response.send_message(f"✅ Seu estádio agora se chama **{nome}**.")

    @app_commands.command(name="escalar", description="Coloque um jogador do seu elenco na escalação")
    @app_commands.describe(
        modo="4v4 ou 7v7",
        jogador="Nome do jogador do seu elenco (veja /inventario)",
        posicao="Opcional: escolha a posição do slot manualmente (em vez do bot escolher sozinho)",
        slot="Opcional: número do slot dessa posição (precisa vir junto com 'posicao')",
    )
    @app_commands.choices(modo=MODOS, posicao=POSICOES)
    async def time_montar(
        self,
        interaction: discord.Interaction,
        modo: app_commands.Choice[str],
        jogador: str,
        posicao: app_commands.Choice[str] = None,
        slot: int = None,
    ):
        modo_valor = modo.value
        elenco = await db.get_user_players(interaction.user.id)
        partes = jogador.split("||")
        nome_base = partes[0].strip()
        raridade = partes[1].strip() if len(partes) > 1 else None
        try:
            overall = int(partes[2]) if len(partes) > 2 else None
        except ValueError:
            overall = None
        nome_lower = nome_base.lower()
        carta = next((
            p for p in elenco
            if p["player_name"].lower() == nome_lower
            and (raridade is None or p["rarity"].lower() == raridade.lower())
            and (overall is None or p["overall"] == overall)
        ), None)

        if carta is None:
            await interaction.response.send_message(
                f"❌ Você não possui **{jogador}**. Veja `/inventario`.",
                ephemeral=True,
            )
            return

        # posicao e slot são opcionais, mas precisam vir os dois juntos (ou nenhum)
        if (posicao is None) != (slot is None):
            await interaction.response.send_message(
                "❌ Pra escolher o slot manualmente, informe **posicao** e **slot** juntos. "
                "Se quiser que o bot escolha sozinho, deixe os dois em branco.",
                ephemeral=True,
            )
            return

        escolha_manual = posicao is not None and slot is not None

        lineup_atual = await db.get_lineup(interaction.user.id, modo_valor)
        if any(p["id"] == carta["id"] for p in lineup_atual):
            atual = next(p for p in lineup_atual if p["id"] == carta["id"])
            await interaction.response.send_message(
                f"❌ **{carta['player_name']}** já está no time ({atual['posicao']} #{atual['slot']}).",
                ephemeral=True,
            )
            return

        formacao = config.FORMACOES[modo_valor]
        contagem = {pos: sum(1 for p in lineup_atual if p["posicao"] == pos) for pos in formacao}
        posicao_do_jogador = carta["position"]

        if posicao_do_jogador not in formacao:
            await interaction.response.send_message(
                f"❌ **{carta['player_name']}** não pode ser usado no modo **{modo_valor}**.",
                ephemeral=True,
            )
            return

        if escolha_manual:
            # --- Escolha manual do slot (sistema antigo, agora opcional) ---
            posicao_valor = posicao.value

            if posicao_valor != posicao_do_jogador:
                await interaction.response.send_message(
                    f"❌ **{carta['player_name']}** joga de **{posicao_do_jogador}**, "
                    f"não pode ser escalado como **{posicao_valor}**.",
                    ephemeral=True,
                )
                return

            # Nunca permita que uma escalação 4v4 ultrapasse 4 jogadores.
            # A formação pode ser 1 GK + 1 MC + 2 ST ou 1 GK + 2 MC + 1 ST.
            if modo_valor == "4v4" and len(lineup_atual) >= 4:
                await interaction.response.send_message(
                    "❌ A escalação **4v4 já tem 4 jogadores**. Remova alguém antes de adicionar outro.",
                    ephemeral=True,
                )
                return

            max_slots = _max_slots_para_posicao(modo_valor, posicao_valor)
            if max_slots == 0:
                await interaction.response.send_message(
                    f"❌ O modo **{modo_valor}** não tem slots de **{posicao_valor}**.",
                    ephemeral=True,
                )
                return
            if slot < 1 or slot > max_slots:
                await interaction.response.send_message(
                    f"❌ No modo **{modo_valor}**, a posição **{posicao_valor}** tem slots de 1 até {max_slots}.",
                    ephemeral=True,
                )
                return

            await db.set_lineup_slot(interaction.user.id, modo_valor, posicao_valor, slot, carta["id"])

            embed = discord.Embed(
                description=(
                    f"✅ **{carta['player_name']}** ({carta['position']}, OVR {carta['overall']}) "
                    f"escalado no **{modo_valor}**, posição **{posicao_valor}** slot **{slot}**."
                ),
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
            return

        # --- Escolha automática (comportamento padrão) ---
        posicao_alvo = posicao_do_jogador

        # No 4v4, GK ocupa uma vaga fixa. MC/ST dividem as 3 vagas restantes:
        # 1 MC + 2 ST ou 2 MC + 1 ST. Assim, nunca é necessário escolher slot.
        if modo_valor == "4v4" and posicao_alvo in {"MC", "ST"}:
            max_pos = 2
            if contagem[posicao_alvo] >= max_pos:
                await interaction.response.send_message(
                    f"❌ Não há espaço para outro **{posicao_alvo}** no 4v4. "
                    f"A escalação permite no máximo 2 {posicao_alvo} e precisa manter 3 jogadores entre MC/ST.",
                    ephemeral=True,
                )
                return
            if contagem["MC"] + contagem["ST"] >= 3:
                await interaction.response.send_message(
                    "❌ Os 3 espaços de linha já estão ocupados. Remova alguém antes de adicionar outro jogador.",
                    ephemeral=True,
                )
                return
        elif contagem.get(posicao_alvo, 0) >= formacao.get(posicao_alvo, 0):
            await interaction.response.send_message(
                f"❌ Não há mais espaço para **{posicao_alvo}** no modo **{modo_valor}**.",
                ephemeral=True,
            )
            return

        # Não use quantidade + 1: se o slot 1 tiver sido removido, o próximo
        # jogador deve ocupar o primeiro slot realmente livre (1, depois 2...).
        slots_ocupados = {p["slot"] for p in lineup_atual if p["posicao"] == posicao_alvo}
        max_slots = _max_slots_para_posicao(modo_valor, posicao_alvo)
        slot_automatico = next(
            (numero for numero in range(1, max_slots + 1) if numero not in slots_ocupados),
            None,
        )

        if slot_automatico is None:
            await interaction.response.send_message(
                f"❌ Não há slot livre para **{posicao_alvo}** no modo **{modo_valor}**.",
                ephemeral=True,
            )
            return

        await db.set_lineup_slot(interaction.user.id, modo_valor, posicao_alvo, slot_automatico, carta["id"])

        embed = discord.Embed(
            description=(
                f"✅ **{carta['player_name']}** ({carta['position']}, OVR {carta['overall']}) "
                f"foi colocado automaticamente no **{modo_valor}** em **{posicao_alvo} #{slot_automatico}**."
            ),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @time_montar.autocomplete("jogador")
    async def time_montar_autocomplete(self, interaction: discord.Interaction, atual: str):
        elenco = await db.get_user_players(interaction.user.id)
        opcoes = []
        atual_lower = atual.lower()
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

    @app_commands.command(name="time_remover", description="Remova um jogador de um slot da escalação")
    @app_commands.describe(modo="4v4 ou 7v7", posicao="Posição do slot", slot="Número do slot")
    @app_commands.choices(modo=MODOS, posicao=POSICOES)
    async def time_remover(
        self,
        interaction: discord.Interaction,
        modo: app_commands.Choice[str],
        posicao: app_commands.Choice[str],
        slot: int,
    ):
        if slot < 1:
            await interaction.response.send_message(
                f"❌ O slot **{posicao.value} #{slot}** não existe no modo **{modo.value}**.",
                ephemeral=True,
            )
            return

        max_slots = _max_slots_para_posicao(modo.value, posicao.value)
        if slot > max_slots:
            await interaction.response.send_message(
                f"❌ O slot **{posicao.value} #{slot}** não existe no modo **{modo.value}**.",
                ephemeral=True,
            )
            return

        lineup = await db.get_lineup(interaction.user.id, modo.value)
        ocupado = any(
            p["posicao"] == posicao.value and int(p["slot"]) == int(slot)
            for p in lineup
        )
        if not ocupado:
            await interaction.response.send_message(
                f"❌ O slot **{posicao.value} #{slot}** está vazio no modo **{modo.value}**.",
                ephemeral=True,
            )
            return

        await db.clear_lineup_slot(interaction.user.id, modo.value, posicao.value, slot)
        await interaction.response.send_message(
            f"🗑️ Slot **{posicao.value} #{slot}** do modo **{modo.value}** foi esvaziado."
        )

    @app_commands.command(name="escalacao", description="Veja sua escalação atual em um modo")
    @app_commands.describe(modo="4v4 ou 7v7", jogador="Ver o time de outro jogador (opcional)")
    @app_commands.choices(modo=MODOS)
    async def time_ver(
        self,
        interaction: discord.Interaction,
        modo: app_commands.Choice[str],
        jogador: discord.Member = None,
    ):
        alvo = jogador or interaction.user
        lineup = await db.get_lineup(alvo.id, modo.value)
        formacao = config.FORMACOES[modo.value]

        embed = discord.Embed(
            title=f"⚽ Escalação {modo.value} — {alvo.display_name}",
            color=discord.Color.dark_gold(),
        )

        for pos in config.ORDEM_POSICOES:
            qtd_slots = formacao.get(pos, 0)
            if modo.value == "4v4" and pos in {"MC", "ST"}:
                # As três vagas de linha são flexíveis: 1+2 ou 2+1.
                qtd_slots = 2
            if qtd_slots == 0:
                continue
            jogadores_pos = {p["slot"]: p for p in lineup if p["posicao"] == pos}
            linhas = []
            for slot_num in range(1, qtd_slots + 1):
                p = jogadores_pos.get(slot_num)
                if p:
                    linhas.append(f"`{slot_num}.` {p['player_name']}")
                else:
                    linhas.append(f"`{slot_num}.` *(vazio)*")
            embed.add_field(name=pos, value="\n".join(linhas), inline=True)

        completo = slots_completos(modo.value, lineup)
        total = overall_total(lineup)
        embed.add_field(
            name="Resumo",
            value=(
                f"Overall total: **{total}**\n"
                f"Status: {'✅ Completo' if completo else '⚠️ Incompleto'}"
            ),
            inline=False,
        )
        embed.set_footer(text="Use /info nome:<jogador> pra ver a carta completa de alguém do time.")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Time(bot))

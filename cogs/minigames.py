"""Minigames /adivinhe e /draft.

Os minigames reutilizam o PLAYERS_CATALOG e a camada de banco existentes.
Nenhuma posição nova é criada: o catálogo atual só possui GK, MC e ST.
"""

import asyncio
import random
import re
import unicodedata
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from players_data import PLAYERS_CATALOG, jogador_obtivel
from maquina import gerar_time_maquina
from motor_partida import determinar_mvp, formatar_artilheiros, formatar_estatistica, narrar_partida, normalizar_time, resolver_penaltis, formatar_penaltis


# Estado transitório das partidas ativas. O banco continua sendo a fonte dos
# jogadores e das recompensas; estes dicionários apenas impedem duas partidas
# simultâneas do mesmo usuário durante a vida do processo.
_ADIVINHE_ATIVOS: set[int] = set()
_DRAFT_ATIVOS: set[int] = set()


def _normalizar(texto: str) -> str:
    """Normaliza nome para aceitar caixa, acentos e pontuação simples."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.casefold()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def _pais(jogador: dict) -> str:
    """Usa país se o catálogo tiver o campo; não inventa país ausente."""
    valor = jogador.get("country") or jogador.get("pais") or jogador.get("country_name")
    return str(valor).strip() if valor else "Não informado"


def _cor_raridade(jogador: dict) -> discord.Color:
    return discord.Color(config.COR_RARIDADE.get(jogador.get("rarity"), 0x5865F2))


def _jogadores_disponiveis() -> list[dict]:
    # Limited/não obtíveis continuam existindo no catálogo, mas não entram no
    # minigame para não criar uma forma indireta de obter cartas bloqueadas.
    return [p for p in PLAYERS_CATALOG if jogador_obtivel(p)]


def _melhor_atributo(jogador: dict) -> tuple[str, int]:
    pos = jogador["position"]
    atributos = ["POS", "KIC", "PAS", "REF", "DIV", "VIS"] if pos == "GK" else [
        "POS", "SHO", "PAS", "DRI", "DEF", "VIS"
    ]
    presentes = [(a, jogador[a]) for a in atributos if isinstance(jogador.get(a), (int, float))]
    return max(presentes, key=lambda item: item[1]) if presentes else ("—", 0)


def _embed_adivinhe(jogador: dict, pistas: list[str], tentativas: int) -> discord.Embed:
    max_t = config.ADIVINHE_MAX_TENTATIVAS
    embed = discord.Embed(
        title="🕵️ Adivinhe o Jogador",
        description=(
            "Descubra qual jogador está escondido.\n"
            "Envie **somente o nome** no chat para tentar.\n\n"
            f"🎯 Tentativas restantes: **{max_t - tentativas}/{max_t}**"
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(name="🇧🇷 País", value=_pais(jogador), inline=True)
    embed.add_field(name="📍 Posição", value=jogador["position"], inline=True)
    embed.add_field(name="⭐ Overall", value=str(jogador["overall"]), inline=True)

    if pistas:
        embed.add_field(
            name="🔎 Pistas liberadas",
            value="\n".join(f"• {p}" for p in pistas),
            inline=False,
        )
    else:
        embed.add_field(name="🔎 Pistas liberadas", value="Nenhuma ainda.", inline=False)

    embed.set_footer(text="Somente quem iniciou a partida pode responder.")
    return embed


def _pista(jogador: dict, numero: int) -> str:
    # Todas as pistas são derivadas de campos que já existem no catálogo.
    if numero == 1:
        return f"Raridade: **{jogador.get('rarity', 'Não informada')}**"
    if numero == 2:
        return f"Preço de catálogo: **{jogador.get('price', 'Não informado')}**"
    if numero == 3:
        nome, valor = _melhor_atributo(jogador)
        return f"Melhor atributo: **{nome} ({valor})**"
    # Última pista: estatística POS/visão/etc. sem revelar o nome.
    if jogador["position"] == "GK":
        return f"REF: **{jogador.get('REF', '—')}** • DIV: **{jogador.get('DIV', '—')}**"
    return f"SHO: **{jogador.get('SHO', '—')}** • DRI: **{jogador.get('DRI', '—')}**"


def _embed_adivinhe_final(
    jogador: dict,
    acertou: bool,
    tentativas: int,
    recompensa: int = 0,
) -> discord.Embed:
    if acertou:
        titulo = "✅ Acertou!"
        descricao = (
            f"O jogador era **{jogador['name']}**!\n"
            f"Você acertou em **{tentativas}** tentativa(s).\n\n"
            f"💰 Recompensa: **{config.MOEDA_EMOJI} {recompensa} {config.MOEDA_NOME}**"
        )
        cor = discord.Color.green()
    else:
        titulo = "❌ Fim de jogo"
        descricao = (
            f"As tentativas acabaram.\n"
            f"O jogador era **{jogador['name']}**.\n"
            "Nenhuma recompensa foi concedida."
        )
        cor = discord.Color.red()

    embed = discord.Embed(title=titulo, description=descricao, color=cor)
    embed.add_field(name="🇧🇷 País", value=_pais(jogador), inline=True)
    embed.add_field(name="📍 Posição", value=jogador["position"], inline=True)
    embed.add_field(name="⭐ Overall", value=str(jogador["overall"]), inline=True)
    embed.add_field(name="💎 Raridade", value=jogador.get("rarity", "—"), inline=True)
    return embed


class _DraftSelect(discord.ui.Select):
    def __init__(self, cog: "Minigames", user_id: int, options: list[dict]):
        self.cog = cog
        self.user_id = user_id
        self.options_players = options
        select_options = [
            discord.SelectOption(
                label=f"{p['name']} • OVR {p['overall']}",
                value=str(i),
                description=f"{p['rarity']} • {p['position']}",
            )
            for i, p in enumerate(options)
        ]
        super().__init__(
            placeholder="Escolha um jogador...",
            min_values=1,
            max_values=1,
            options=select_options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Esse draft pertence a outra pessoa.", ephemeral=True
            )
            return
        view: _DraftView = self.view
        if view is None or view.finished:
            await interaction.response.send_message(
                "❌ Esta rodada já terminou.", ephemeral=True
            )
            return
        await self.cog._draft_escolher(interaction, view, int(self.values[0]))


class _DraftView(discord.ui.View):
    def __init__(self, cog: "Minigames", user_id: int, options: list[dict]):
        super().__init__(timeout=config.DRAFT_TIMEOUT_SEGUNDOS)
        self.cog = cog
        self.user_id = user_id
        self.finished = False
        self.select = _DraftSelect(cog, user_id, options)
        self.add_item(self.select)

    def disable_all(self):
        self.finished = True
        for item in self.children:
            item.disabled = True
        self.stop()

    async def on_timeout(self):
        self.disable_all()
        self.cog._draft_limpar(self.user_id)
        if self.message:
            try:
                await self.message.edit(
                    content="⏰ O draft expirou por inatividade.",
                    view=self,
                )
            except (discord.NotFound, discord.HTTPException):
                pass


class Minigames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._draft_data: dict[int, dict] = {}

    @app_commands.command(name="adivinhe", description="Adivinhe qual jogador está escondido")
    async def adivinhe(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        cooldown = await db.get_adivinhe_cooldown(user_id)
        if cooldown > 0:
            minutos = int(cooldown // 60)
            segundos = int(cooldown % 60)
            await interaction.response.send_message(
                f"⏳ Você perdeu sua sequência. Tente novamente em **{minutos}m {segundos:02d}s**.",
                ephemeral=True,
            )
            return

        if user_id in _ADIVINHE_ATIVOS:
            await interaction.response.send_message(
                "❌ Você já tem um `/adivinhe` ativo. Continue tentando na rodada atual.",
                ephemeral=True,
            )
            return

        jogadores = _jogadores_disponiveis()
        if not jogadores:
            await interaction.response.send_message(
                "❌ Não há jogadores disponíveis para iniciar o minigame.",
                ephemeral=True,
            )
            return

        _ADIVINHE_ATIVOS.add(user_id)
        sequencia = (await db.get_adivinhe_stats(user_id))["sequencia"]
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🕵️ Adivinhe o Jogador",
                description=(
                    f"🔥 Sequência atual: **{sequencia}**\n"
                    "Acerte para continuar. Se errar ou o tempo acabar, sua sequência zera e entra em cooldown de 30 minutos."
                ),
                color=discord.Color.blurple(),
            )
        )
        mensagem_rodada = await interaction.original_response()

        try:
            while True:
                jogadores = _jogadores_disponiveis()
                jogador = random.choice(jogadores)
                tentativas = 0
                pistas: list[str] = []

                if sequencia >= 10:
                    limite_tempo = config.ADIVINHE_TIMEOUT_POS_10
                    recompensa = config.ADIVINHE_RECOMPENSA_POS_10
                elif sequencia >= 5:
                    limite_tempo = config.ADIVINHE_TIMEOUT_5_ATE_10
                    recompensa = config.ADIVINHE_RECOMPENSA_POS_5
                else:
                    limite_tempo = config.ADIVINHE_TIMEOUT_ATE_5
                    recompensa = config.ADIVINHE_RECOMPENSA_BASE

                embed = _embed_adivinhe(jogador, pistas, tentativas)
                embed.description = (
                    f"Descubra qual jogador está escondido.\n"
                    "Envie **somente o nome** no chat para tentar.\n\n"
                    f"🔥 Sequência: **{sequencia}**\n"
                    f"⏱️ Tempo: **{limite_tempo}s** • 💰 Recompensa: **{recompensa} {config.MOEDA_NOME}**"
                )
                if mensagem_rodada is None:
                    mensagem_rodada = await interaction.followup.send(embed=embed, wait=True)
                else:
                    await mensagem_rodada.edit(embed=embed)

                perdeu = False
                while tentativas < config.ADIVINHE_MAX_TENTATIVAS:
                    try:
                        mensagem = await self.bot.wait_for(
                            "message",
                            timeout=limite_tempo,
                            check=lambda m: (
                                m.author.id == user_id
                                and m.channel.id == interaction.channel_id
                                and not m.author.bot
                            ),
                        )
                    except asyncio.TimeoutError:
                        perdeu = True
                        break

                    tentativas += 1
                    if _normalizar(mensagem.content) == _normalizar(jogador["name"]):
                        sequencia += 1
                        await db.update_balance(user_id, recompensa)
                        await db.registrar_adivinhe_resultado(user_id, True, tentativas)
                        final = _embed_adivinhe_final(jogador, True, tentativas, recompensa)
                        final.set_footer(text=f"🔥 Sequência: {sequencia} • Próxima rodada: {('5s' if sequencia >= 10 else '15s' if sequencia >= 5 else '30s')}")
                        await interaction.followup.send(embed=final)
                        mensagem_rodada = None
                        break

                    if tentativas >= config.ADIVINHE_MAX_TENTATIVAS:
                        perdeu = True
                        break

                    pistas.append(_pista(jogador, len(pistas) + 1))
                    await mensagem_rodada.edit(
                        embed=_embed_adivinhe(jogador, pistas, tentativas)
                    )

                if perdeu:
                    await db.registrar_adivinhe_resultado(user_id, False, max(1, tentativas))
                    await db.definir_adivinhe_cooldown(user_id, config.ADIVINHE_COOLDOWN_MINUTOS)
                    final = _embed_adivinhe_final(jogador, False, tentativas)
                    final.description += (
                        f"\n\n🔥 Sua sequência era **{sequencia}**.\n"
                        f"⏳ Você entrou em cooldown por **{config.ADIVINHE_COOLDOWN_MINUTOS} minutos**."
                    )
                    await mensagem_rodada.edit(embed=final)
                    return

                # Se acertou, a sequência continua automaticamente com outro jogador.
        finally:
            _ADIVINHE_ATIVOS.discard(user_id)

    @app_commands.command(name="draft", description="Monte um elenco de 4 jogadores através de um Draft")
    async def draft(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        cooldown = await db.get_draft_cooldown(user_id)
        if cooldown > 0:
            minutos = int(cooldown // 60)
            segundos = int(cooldown % 60)
            await interaction.response.send_message(
                f"⏳ Você venceu seu último Draft. Tente novamente em **{minutos}m {segundos:02d}s**.",
                ephemeral=True,
            )
            return
        if user_id in _DRAFT_ATIVOS:
            await interaction.response.send_message(
                "❌ Você já tem um `/draft` ativo. Termine esse draft antes de iniciar outro.",
                ephemeral=True,
            )
            return

        jogadores = _jogadores_disponiveis()
        if len(jogadores) < config.DRAFT_OPCOES_POR_RODADA:
            await interaction.response.send_message(
                "❌ Não há jogadores suficientes para iniciar o Draft.", ephemeral=True
            )
            return

        _DRAFT_ATIVOS.add(user_id)
        self._draft_data[user_id] = {
            "indice": 0,
            "total": config.DRAFT_RODADAS,
            "selecionados": [],
            "usados": set(),
            "opcoes": [],
            "posicoes": [],
            "processing": False,
            "mensagem": None,
            "view": None,
        }

        try:
            await self._draft_mostrar_rodada(interaction, primeira=True)
        except Exception:
            self._draft_limpar(user_id)
            raise

    def _draft_proxima_posicao(self, selecionados: list[dict]) -> str:
        """Escolhe automaticamente a posição necessária, sem pedir slot ao usuário."""
        contagem = {"GK": 0, "MC": 0, "ST": 0}
        for p in selecionados:
            contagem[p["position"]] = contagem.get(p["position"], 0) + 1

        if contagem["GK"] == 0:
            return "GK"
        # As 3 vagas restantes aceitam 1 MC + 2 ST ou 2 MC + 1 ST.
        if contagem["MC"] >= 2:
            return "ST"
        if contagem["ST"] >= 2:
            return "MC"
        if contagem["MC"] == 0 and contagem["ST"] == 0:
            return random.choice(["MC", "ST"])
        if contagem["MC"] == 0:
            return "MC"
        if contagem["ST"] == 0:
            return "ST"
        return random.choice(["MC", "ST"])

    def _draft_embed(self, data: dict, opcoes: list[dict], posicao: str, escolhido: dict | None = None) -> discord.Embed:
        rodada = data["indice"] + 1
        embed = discord.Embed(
            title=f"🃏 Draft — Rodada {rodada}/{data['total']}",
            description=(
                f"O bot está procurando uma vaga de **{posicao}** para você.\n"
                "Escolha **1 jogador**. A posição/slot será administrada automaticamente."
            ),
            color=discord.Color.blurple(),
        )
        for p in opcoes:
            embed.add_field(
                name=f"⭐ {p['name']} — OVR {p['overall']}",
                value=f"{p['rarity']} • {p['position']} • 🇧🇷 {p.get('country', 'Não informado')}",
                inline=True,
            )
        if escolhido:
            embed.add_field(
                name="✅ Escolhido",
                value=f"**{escolhido['name']}** — {escolhido['position']} • OVR **{escolhido['overall']}**",
                inline=False,
            )
        if data["selecionados"]:
            resumo = " • ".join(
                f"{p['position']} {p['name']} ({p['overall']})"
                for p in data["selecionados"]
            )
            embed.add_field(name="📋 Seu time até agora", value=resumo, inline=False)
        return embed

    async def _draft_mostrar_rodada(self, interaction: discord.Interaction, primeira: bool = False):
        data = self._draft_data[interaction.user.id]
        posicao = self._draft_proxima_posicao(data["selecionados"])
        disponiveis = [
            p for p in _jogadores_disponiveis()
            if p["position"] == posicao and p["name"] not in data["usados"]
        ]
        if len(disponiveis) < config.DRAFT_OPCOES_POR_RODADA:
            raise RuntimeError(f"Não há opções suficientes para {posicao} sem repetir jogadores.")

        opcoes = random.sample(disponiveis, config.DRAFT_OPCOES_POR_RODADA)
        data["opcoes"] = opcoes
        data["posicoes"].append(posicao)
        view = _DraftView(self, interaction.user.id, opcoes)
        data["view"] = view
        embed = self._draft_embed(data, opcoes, posicao)

        if primeira:
            await interaction.response.send_message(embed=embed, view=view)
            data["mensagem"] = await interaction.original_response()
            view.message = data["mensagem"]
        else:
            await interaction.response.edit_message(embed=embed, view=view)
            view.message = data.get("mensagem")

    async def _draft_escolher(self, interaction: discord.Interaction, view: _DraftView, indice: int):
        user_id = interaction.user.id
        data = self._draft_data.get(user_id)
        if not data or data.get("view") is not view:
            await interaction.response.send_message("❌ Este draft não está mais ativo.", ephemeral=True)
            return
        if data.get("processing"):
            await interaction.response.send_message("⏳ Essa escolha já está sendo processada.", ephemeral=True)
            return
        if indice < 0 or indice >= len(data["opcoes"]):
            await interaction.response.send_message("❌ Opção inválida.", ephemeral=True)
            return

        data["processing"] = True
        jogador = data["opcoes"][indice]
        if jogador["name"] in data["usados"]:
            data["processing"] = False
            await interaction.response.send_message("❌ Esse jogador já foi escolhido.", ephemeral=True)
            return

        view.disable_all()
        data["usados"].add(jogador["name"])
        data["selecionados"].append(jogador)
        data["indice"] += 1

        if data["indice"] >= data["total"]:
            await interaction.response.edit_message(
                embed=self._draft_embed(data, [], jogador["position"], jogador),
                view=view,
            )
            await self._draft_finalizar(interaction, data)
            return

        data["processing"] = False
        # A mesma mensagem é atualizada; nenhuma nova mensagem é criada para as rodadas 2–4.
        await self._draft_mostrar_rodada(interaction)

    async def _draft_finalizar(self, interaction: discord.Interaction, data: dict):
        selecionados = data["selecionados"]
        media = sum(p["overall"] for p in selecionados) / len(selecionados)
        maior = max(selecionados, key=lambda p: p["overall"])

        embed = discord.Embed(
            title="🏆 Draft concluído!",
            description=(
                f"**Média do Draft:** `{media:.1f}`\n"
                f"**Maior carta:** ⭐ **{maior['name']} — {maior['overall']} OVR**\n\n"
                "🤖 Agora seu Draft vai enfrentar uma máquina com **80–85 OVR**."
            ),
            color=discord.Color.gold(),
        )
        linhas = [
            f"`{pos}` **{p['name']}** — OVR **{p['overall']}** • {p['rarity']}"
            for pos, p in zip(data["posicoes"], selecionados)
        ]
        embed.add_field(name="📋 Elenco", value="\n".join(linhas), inline=False)

        current_view: Optional[_DraftView] = data.get("view")
        if current_view:
            current_view.disable_all()
        try:
            await interaction.edit_original_response(embed=embed, view=current_view)
        except (discord.NotFound, discord.HTTPException):
            pass

        await self._draft_partida_maquina(interaction, selecionados, data)
        self._draft_limpar(interaction.user.id)

    async def _draft_partida_maquina(self, interaction: discord.Interaction, selecionados: list[dict], data: dict):
        """Joga a partida do Draft usando o motor de partidas já existente."""
        alvo = random.randint(config.DRAFT_MAQUINA_MEDIA_MIN, config.DRAFT_MAQUINA_MEDIA_MAX)
        time_maquina = None
        melhor = None
        melhor_dist = float("inf")
        # O gerador existente monta o 4v4; repetimos algumas tentativas para garantir
        # que a média final fique realmente dentro de 80–85 quando possível.
        for _ in range(20):
            alvo_tentativa = random.randint(config.DRAFT_MAQUINA_MEDIA_MIN, config.DRAFT_MAQUINA_MEDIA_MAX)
            candidato = gerar_time_maquina("4v4", media_alvo=alvo_tentativa, tolerancia=0.5)
            if not candidato or len(candidato) != 4:
                continue
            media_candidato = sum(j["overall"] for j in candidato) / len(candidato)
            distancia = 0 if config.DRAFT_MAQUINA_MEDIA_MIN <= media_candidato <= config.DRAFT_MAQUINA_MEDIA_MAX else min(
                abs(media_candidato - config.DRAFT_MAQUINA_MEDIA_MIN),
                abs(media_candidato - config.DRAFT_MAQUINA_MEDIA_MAX),
            )
            if distancia < melhor_dist:
                melhor, melhor_dist = candidato, distancia
            if distancia == 0:
                time_maquina = candidato
                break
        if time_maquina is None:
            time_maquina = melhor or gerar_time_maquina(
                "4v4",
                media_alvo=(config.DRAFT_MAQUINA_MEDIA_MIN + config.DRAFT_MAQUINA_MEDIA_MAX) / 2,
                tolerancia=2.0,
            )

        nome_jogador = f"Draft de {interaction.user.display_name}"
        nome_maquina = "Máquina"
        embed_partida = discord.Embed(
            title=f"🤖 Partida do Draft — {nome_jogador} x {nome_maquina}",
            description=f"A máquina está com média próxima de **{sum(j['overall'] for j in time_maquina) / len(time_maquina):.1f} OVR**.",
            color=discord.Color.blue(),
        )
        mensagem = await interaction.followup.send(embed=embed_partida, wait=True)

        placar_jogador, placar_maquina, artilheiros_jogador, artilheiros_maquina, assistentes_jogador, assistentes_maquina, defesas_jogador, defesas_maquina = await narrar_partida(
            mensagem,
            embed_partida,
            nome_jogador,
            normalizar_time(selecionados),
            nome_maquina,
            normalizar_time(time_maquina),
            media_alvo_a=alvo,
            fator_dificuldade_a=1.0,
        )

        penalti = None
        if placar_jogador == placar_maquina:
            penalti = resolver_penaltis(
                normalizar_time(selecionados),
                normalizar_time(time_maquina),
            )
            venceu = penalti["vencedor"] == "a"
        else:
            venceu = placar_jogador > placar_maquina

        embed_final = discord.Embed(
            title=f"🏁 Fim da partida — {placar_jogador} x {placar_maquina}",
            color=discord.Color.green() if venceu else (discord.Color.greyple() if placar_jogador == placar_maquina else discord.Color.red()),
        )
        embed_final.add_field(
            name=f"⚽ Gols — {nome_jogador}",
            value=formatar_artilheiros(artilheiros_jogador),
            inline=True,
        )
        embed_final.add_field(
            name=f"⚽ Gols — {nome_maquina}",
            value=formatar_artilheiros(artilheiros_maquina),
            inline=True,
        )
        embed_final.add_field(
            name=f"👟 Assistências — {nome_jogador}",
            value=formatar_estatistica(assistentes_jogador, "👟"),
            inline=True,
        )
        embed_final.add_field(
            name=f"👟 Assistências — {nome_maquina}",
            value=formatar_estatistica(assistentes_maquina, "👟"),
            inline=True,
        )
        embed_final.add_field(
            name=f"🧤 Defesas — {nome_jogador}",
            value=formatar_estatistica(defesas_jogador, "🧤"),
            inline=True,
        )
        embed_final.add_field(
            name=f"🧤 Defesas — {nome_maquina}",
            value=formatar_estatistica(defesas_maquina, "🧤"),
            inline=True,
        )
        if penalti:
            embed_final.add_field(
                name="🥅 Disputa de pênaltis",
                value=formatar_penaltis(penalti, nome_jogador, nome_maquina),
                inline=False,
            )
        nome_mvp, time_mvp, gols_mvp, assist_mvp, defesas_mvp = determinar_mvp(
            nome_jogador, artilheiros_jogador, normalizar_time(selecionados),
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
        embed_final.add_field(name="MVP", value=texto_mvp, inline=False)

        if venceu:
            await db.update_balance(interaction.user.id, config.DRAFT_RECOMPENSA_VITORIA)
            await db.set_last_draft(interaction.user.id)
            embed_final.description = (
                f"🎉 **Vitória!** Você ganhou 🪙 **{config.DRAFT_RECOMPENSA_VITORIA} Robux**!\n"
                f"⏳ Próximo Draft disponível em **{config.DRAFT_COOLDOWN_MINUTOS} minutos**."
            )
        elif placar_jogador == placar_maquina:
            embed_final.description = "🤝 **Empate!** Você não recebe a recompensa de vitória."
        else:
            embed_final.description = "💀 **Derrota.** A máquina venceu o seu Draft."

        await mensagem.edit(embed=embed_final)

    def _draft_limpar(self, user_id: int):
        _DRAFT_ATIVOS.discard(user_id)
        self._draft_data.pop(user_id, None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Minigames(bot))

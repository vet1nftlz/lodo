"""Comando /view: mostra a escalação diretamente sobre o campo fornecido."""

import io
import os

import discord
from PIL import ImageDraw, ImageFont
from discord import app_commands
from discord.ext import commands
from PIL import Image

import config
import database as db
from players_data import buscar_jogador_catalogo


MODOS = [
    app_commands.Choice(name="4v4", value="4v4"),
    app_commands.Choice(name="7v7", value="7v7"),
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_DIR = os.path.join(BASE_DIR, "assets", "cards")
BACKGROUND_PATH = os.path.join(BASE_DIR, "assets", "lineup_background.png")
FONT_REGULAR = os.path.join(BASE_DIR, "assets", "LiberationSans.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "assets", "LiberationSans-Bold.ttf")

# Todas as posições abaixo foram desenhadas no sistema original de 440x275.
# O /view converte automaticamente essas coordenadas para o tamanho REAL do
# fundo. Assim, se você trocar o fundo por uma versão maior, as cartas não
# ficam presas no canto nem minúsculas.
BASE_W = 440
BASE_H = 275

SLOTS = {
    "4v4": {
        "GK": [(38, 138)],
        # 1-1-2 ou 1-2-1
        "MC": [(185, 108), (185, 168)],
        "ST": [(320, 108), (320, 168)],
    },
    "7v7": {
        "GK": [(38, 138)],
        "MC": [(157, 62), (157, 138), (157, 214)],
        "ST": [(315, 62), (315, 138), (315, 214)],
    },
}

CARD_SIZES = {
    "4v4": (62, 87),
    "7v7": (50, 70),
}


def _load_card(player: dict):
    # A escalação vem do banco com apenas os dados da carta possuída
    # (nome, posição, overall e raridade). A imagem da card fica no
    # PLAYERS_CATALOG, então precisamos localizar a carta no catálogo
    # antes de tentar abrir o PNG.
    catalogo = buscar_jogador_catalogo(
        player.get("player_name"),
        player.get("rarity"),
        player.get("overall"),
    )

    if catalogo is None:
        # Fallback para caso exista algum jogador antigo/fora do catálogo.
        filename = player.get("image")
    else:
        filename = catalogo.get("image")

    if not filename:
        return None

    path = os.path.join(CARDS_DIR, os.path.basename(filename))
    if not os.path.isfile(path):
        return None

    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def _scale_xy(x: float, y: float, canvas: Image.Image) -> tuple[int, int]:
    """Converte uma coordenada do campo-base 440x275 para o fundo atual."""
    sx = canvas.width / BASE_W
    sy = canvas.height / BASE_H
    return round(x * sx), round(y * sy)


def _scale_size(size: tuple[int, int], canvas: Image.Image) -> tuple[int, int]:
    """Escala o tamanho da card junto com a resolução do fundo."""
    sx = canvas.width / BASE_W
    sy = canvas.height / BASE_H
    return max(1, round(size[0] * sx)), max(1, round(size[1] * sy))


def _paste_card(
    canvas: Image.Image,
    player: dict,
    center: tuple[int, int],
    size: tuple[int, int],
):
    card = _load_card(player)
    if card is None:
        return

    # Mantém a proporção original da card.
    card.thumbnail(size, Image.Resampling.LANCZOS)
    x = round(center[0] - card.width / 2)
    y = round(center[1] - card.height / 2)
    canvas.alpha_composite(card, (x, y))


def gerar_view_imagem(lineup: list, modo: str, nome_time: str, nome_jogador: str) -> io.BytesIO:
    # A imagem enviada pelo usuário é mantida como fundo, sem cabeçalho,
    # texto, moldura ou qualquer outro elemento desenhado pelo comando.
    background = Image.open(BACKGROUND_PATH).convert("RGBA")
    canvas = background.copy()

    # Primeiro definimos mentalmente todos os slots pela posição/slot do banco.
    # Depois, e somente depois, as cartas são colocadas nesses pontos.
    jogadores_por_posicao = {
        "GK": {p.get("slot"): p for p in lineup if p.get("posicao") == "GK"},
        "MC": {p.get("slot"): p for p in lineup if p.get("posicao") == "MC"},
        "ST": {p.get("slot"): p for p in lineup if p.get("posicao") == "ST"},
    }

    tamanho = _scale_size(CARD_SIZES[modo], canvas)
    for posicao in ("GK", "MC", "ST"):
        jogadores_posicao = jogadores_por_posicao[posicao]

        # A posição é determinada pela escalação salva no banco.
        # Isso é importante no 4v4, onde a linha pode ser 1 MC + 2 ST
        # OU 2 MC + 1 ST. Não usamos a formação padrão do config para
        # decidir quais cards desenhar.
        jogadores_ordenados = [
            jogadores_posicao[slot]
            for slot in sorted(jogadores_posicao)
            if jogadores_posicao.get(slot) is not None
        ]

        for indice, jogador in enumerate(jogadores_ordenados):
            if indice >= len(SLOTS[modo][posicao]):
                break
            centro = _scale_xy(*SLOTS[modo][posicao][indice], canvas)
            _paste_card(canvas, jogador, centro, tamanho)

    # Faixa de identificação no canto inferior esquerdo.
    # Usa os dados do dono da escalação, e não de quem executou /view.
    draw = ImageDraw.Draw(canvas)
    # A faixa também escala junto com o fundo. Antes ela continuava com
    # 205x32 px mesmo depois que o fundo foi aumentado para alta resolução.
    escala_fonte = min(canvas.width / BASE_W, canvas.height / BASE_H)
    fonte_time_tam = max(18, round(12 * escala_fonte))
    fonte_jogador_tam = max(14, round(9 * escala_fonte))

    try:
        fonte_time = ImageFont.truetype(FONT_BOLD, fonte_time_tam)
        fonte_jogador = ImageFont.truetype(FONT_REGULAR, fonte_jogador_tam)
    except Exception:
        fonte_time = ImageFont.load_default()
        fonte_jogador = ImageFont.load_default()

    nome_time = str(nome_time or "Time Sem Nome").strip()
    nome_jogador = str(nome_jogador or "Usuário").strip()

    def limitar_texto(texto, fonte, largura_max):
        if draw.textbbox((0, 0), texto, font=fonte)[2] <= largura_max:
            return texto
        while texto and draw.textbbox((0, 0), texto + "...", font=fonte)[2] > largura_max:
            texto = texto[:-1]
        return (texto.rstrip() + "...") if texto else "..."

    margem = max(20, round(10 * escala_fonte))
    faixa_x = margem
    faixa_y = canvas.height - max(75, round(42 * escala_fonte))
    faixa_w = min(round(205 * escala_fonte), canvas.width - (margem * 2))
    faixa_h = max(58, round(32 * escala_fonte))
    padding_x = max(14, round(9 * escala_fonte))
    largura_texto = faixa_w - (padding_x * 2)

    nome_time = limitar_texto(nome_time, fonte_time, largura_texto)
    nome_jogador = limitar_texto(nome_jogador, fonte_jogador, largura_texto)

    # Pequena faixa arredondada e discreta, sem alterar o restante do campo.
    draw.rounded_rectangle(
        (faixa_x, faixa_y, faixa_x + faixa_w, faixa_y + faixa_h),
        radius=max(10, round(8 * escala_fonte)),
        fill=(12, 18, 14, 215),
        outline=(255, 255, 255, 150),
        width=max(1, round(1 * escala_fonte)),
    )
    draw.text(
        (faixa_x + padding_x, faixa_y + max(5, round(4 * escala_fonte))),
        nome_time,
        font=fonte_time,
        fill=(255, 255, 255, 255),
    )
    draw.text(
        (faixa_x + padding_x, faixa_y + max(5, round(19 * escala_fonte))),
        nome_jogador,
        font=fonte_jogador,
        fill=(215, 225, 215, 255),
    )

    output = io.BytesIO()
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    output.seek(0)
    return output


class View(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="view", description="Veja sua escalação em uma imagem")
    @app_commands.describe(
        modo="Modo da escalação",
        jogador="Opcional: veja a escalação de outro jogador",
    )
    @app_commands.choices(modo=MODOS)
    async def view(
        self,
        interaction: discord.Interaction,
        modo: app_commands.Choice[str],
        jogador: discord.Member = None,
    ):
        alvo = jogador or interaction.user
        lineup = await db.get_lineup(alvo.id, modo.value)

        if not lineup:
            await interaction.response.send_message(
                f"❌ **{alvo.display_name}** ainda não possui jogadores na escalação **{modo.value}**.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            identidade = await db.get_identidade_time(alvo.id)
            imagem = gerar_view_imagem(
                lineup,
                modo.value,
                identidade["time_nome"],
                alvo.name,
            )
            arquivo = discord.File(
                imagem,
                filename=f"escalacao_{modo.value.lower()}.png",
            )
            await interaction.followup.send(file=arquivo)
        except Exception:
            await interaction.followup.send(
                "❌ Não consegui gerar a imagem da escalação. Verifique os logs do bot.",
                ephemeral=True,
            )
            raise


async def setup(bot: commands.Bot):
    await bot.add_cog(View(bot))

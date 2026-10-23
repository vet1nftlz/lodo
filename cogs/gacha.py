"""Comando /abrirpacote."""

import discord
from discord import app_commands
from discord.ext import commands

import config
import database as db
from cogs.antibot import verificar_se_necessario
from cogs.loja import enviar_resultado_carta
from gacha_logic import abrir_pacote, abrir_varios_pacotes


PACOTES_CHOICES = [
    app_commands.Choice(name=pacote["nome"], value=chave)
    for chave, pacote in config.PACOTES.items()
]


def _formatar_tempo(segundos: float) -> str:
    segundos = int(segundos)
    minutos, seg = divmod(segundos, 60)
    if minutos:
        return f"{minutos}min {seg}s"
    return f"{seg}s"


class Gacha(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="abrirpacote",
        description="Abra pacote(s) que você possui no inventário"
    )
    @app_commands.describe(
        pacote="Qual pacote você quer abrir",
        quantidade="Quantidade de pacotes para abrir (máximo 10)",
    )
    @app_commands.choices(pacote=PACOTES_CHOICES)
    async def abrirpacote(
        self,
        interaction: discord.Interaction,
        pacote: app_commands.Choice[str],
        quantidade: int = 1,
    ):
        chave = pacote.value

        if quantidade < 1 or quantidade > config.ABRIR_QUANTIDADE_MAX:
            await interaction.response.send_message(
                f"❌ A quantidade deve estar entre **1 e "
                f"{config.ABRIR_QUANTIDADE_MAX}**.",
                ephemeral=True,
            )
            return

        # Pacote Icon só pode ser aberto individualmente.
        if chave == "icon" and quantidade > 1:
            await interaction.response.send_message(
                "❌ O **Pacote Icon** só pode ser aberto **1 por vez**.",
                ephemeral=True,
            )
            return

        disponiveis = await db.contar_pacotes(
            interaction.user.id,
            chave,
        )

        if disponiveis < quantidade:
            await interaction.response.send_message(
                f"❌ Você possui apenas **{disponiveis}** pacote(s) de "
                f"**{config.PACOTES[chave]['nome']}**.",
                ephemeral=True,
            )
            return

        # Só abre se o inventário comportar todas as cartas da abertura.
        if not await db.tem_espaco_inventario(interaction.user.id, quantidade):
            await interaction.response.send_message(
                await db.mensagem_sem_espaco(interaction.user.id, quantidade),
                ephemeral=True,
            )
            return

        # Cooldown para abertura de vários pacotes.
        if quantidade > 1:
            restante = await db.get_multi_open_cooldown(
                interaction.user.id
            )

            if restante > 0:
                await interaction.response.send_message(
                    f"⏳ Aguarde **{_formatar_tempo(restante)}** "
                    "para usar `quantidade` novamente. "
                    "Você ainda pode abrir 1 pacote por vez.",
                    ephemeral=True,
                )
                return

        if await verificar_se_necessario(interaction):
            return

        await interaction.response.defer()

        try:
            if quantidade == 1:
                sucesso, jogador, erro = await abrir_pacote(
                    interaction.user.id,
                    chave,
                )

                if not sucesso:
                    await interaction.followup.send(
                        f"❌ {erro}",
                        ephemeral=True,
                    )
                    return

                # O pacote já foi consumido e a carta já foi processada no banco.
                # A exibição nunca deve transformar uma abertura concluída em mensagem de erro.
                try:
                    await enviar_resultado_carta(
                        interaction,
                        jogador,
                    )
                except Exception as erro_exibicao:
                    print(f"[GACHA] Carta aberta, mas houve falha ao montar a exibição: {erro_exibicao}")
                    fallback = discord.Embed(
                        title="🎁 Pacote aberto!",
                        description=(
                            f"**{jogador.get('name', 'Jogador')}**\n"
                            f"{jogador.get('rarity', 'Raridade desconhecida')} · "
                            f"**{jogador.get('overall', '?')} OVR**"
                        ),
                        color=discord.Color.gold(),
                    )
                    try:
                        await interaction.followup.send(embed=fallback)
                    except Exception as envio_erro:
                        print(f"[GACHA] Falha também no fallback da exibição: {envio_erro}")
                return

            resultados, erros = await abrir_varios_pacotes(
                interaction.user.id,
                chave,
                quantidade,
            )

            await db.set_multi_open_cooldown(
                interaction.user.id
            )

            if not resultados:
                await interaction.followup.send(
                    f"❌ Nenhum pacote pôde ser aberto. "
                    f"{erros[0] if erros else ''}",
                    ephemeral=True,
                )
                return

            melhores = sorted(
                resultados,
                key=lambda j: (
                    j.get("overall", 0),
                    j.get("estrelas", 0),
                ),
                reverse=True,
            )[:3]

            embed = discord.Embed(
                title=f"📦 {len(resultados)} pacote(s) aberto(s)!",
                description=(
                    "Os **3 melhores jogadores sorteados** "
                    "nesta abertura foram:\n\n"
                    + "\n".join(
                        f"**{i}. {j['name']}** — "
                        f"{j['rarity']} · **{j['overall']} OVR**"
                        for i, j in enumerate(melhores, 1)
                    )
                ),
                color=discord.Color.gold(),
            )

            adicionados = sum(
                1
                for j in resultados
                if j.get("novo_id") is not None
            )

            convertidos = sum(
                1
                for j in resultados
                if j.get("duplicado", False)
                or j.get("cheio", False)
            )

            footer = (
                f"📥 {adicionados} jogador(es) "
                "adicionado(s) ao inventário"
            )

            if convertidos:
                footer += (
                    f" · 💰 {convertidos} convertido(s) "
                    f"em {config.MOEDA_NOME}"
                )

            if erros:
                footer += (
                    " · ⚠️ A abertura foi interrompida antes "
                    "de completar a quantidade."
                )

            embed.set_footer(text=footer)

            await interaction.followup.send(
                embed=embed
            )

        except Exception as erro:
            print(f"[GACHA] Erro durante /abrirpacote: {erro}")

            # Se alguma carta já foi aberta nesta operação, ela permanece aberta.
            # Nesse caso, não exibimos uma mensagem dizendo que a abertura falhou.
            if 'resultados' in locals() and resultados:
                try:
                    await interaction.followup.send(
                        f"🎁 **{len(resultados)} pacote(s) foram abertos.** "
                        "A exibição completa do resultado teve um problema.",
                        ephemeral=False,
                    )
                except Exception as envio_erro:
                    print(f"[GACHA] Falha ao enviar confirmação: {envio_erro}")
            else:
                try:
                    await interaction.followup.send(
                        "❌ Não foi possível concluir a abertura do pacote.",
                        ephemeral=True,
                    )
                except Exception as envio_erro:
                    print(f"[GACHA] Falha ao enviar erro: {envio_erro}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Gacha(bot))

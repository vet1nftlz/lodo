"""Comandos de administração: só quem tem permissão de Administrador no servidor pode usar.

- /admin_zerar_weekly
- /admin_zerar_inventario
- /admin_zerar_saldo
- /admin_zerar_claim
"""

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from players_data import PLAYERS_CATALOG, buscar_jogador_catalogo


def _eh_admin(interaction: discord.Interaction) -> bool:
    return isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_zerar_weekly", description="[ADMIN] Zera o cooldown do /weekly de um usuário")
    @app_commands.describe(usuario="Usuário que vai ter o cooldown do weekly zerado")
    @app_commands.default_permissions(administrator=True)
    async def admin_zerar_weekly(self, interaction: discord.Interaction, usuario: discord.Member):
        if not _eh_admin(interaction):
            await interaction.response.send_message("❌ Só administradores do servidor podem usar esse comando.", ephemeral=True)
            return

        await db.resetar_last_weekly(usuario.id)
        await interaction.response.send_message(
            f"✅ Cooldown do `/weekly` de {usuario.mention} foi zerado. Ele(a) já pode usar de novo.",
        )

    @app_commands.command(name="admin_zerar_inventario", description="[ADMIN] Apaga todas as cartas de um usuário")
    @app_commands.describe(usuario="Usuário que vai ter o inventário apagado")
    @app_commands.default_permissions(administrator=True)
    async def admin_zerar_inventario(self, interaction: discord.Interaction, usuario: discord.Member):
        if not _eh_admin(interaction):
            await interaction.response.send_message("❌ Só administradores do servidor podem usar esse comando.", ephemeral=True)
            return

        quantidade = await db.zerar_inventario(usuario.id)
        await interaction.response.send_message(
            f"✅ Inventário de {usuario.mention} foi zerado — **{quantidade}** carta(s) removida(s) "
            f"(e as escalações dele(a) foram limpas também).",
        )

    @app_commands.command(name="admin_adicionar_dinheiro", description="[ADMIN] Adiciona Robux ao saldo de um usuário")
    @app_commands.describe(
        usuario="Usuário que vai receber os Robux",
        quantidade="Quantidade de Robux para adicionar",
    )
    @app_commands.default_permissions(administrator=True)
    async def admin_adicionar_dinheiro(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        quantidade: app_commands.Range[int, 1, 2_147_483_647],
    ):
        if not _eh_admin(interaction):
            await interaction.response.send_message(
                "❌ Só administradores do servidor podem usar esse comando.",
                ephemeral=True,
            )
            return

        await db.update_balance(usuario.id, quantidade)
        saldo_novo = await db.get_balance(usuario.id)

        await interaction.response.send_message(
            f"✅ Foram adicionados **{quantidade:,} Robux** para {usuario.mention}."
            f"💰 Novo saldo: **{saldo_novo:,} Robux**."
        )

    @app_commands.command(name="admin_adicionar_jogador", description="[ADMIN] Adiciona uma carta específica ao usuário")
    @app_commands.describe(
        usuario="Usuário que vai receber o jogador",
        jogador="Nome exato do jogador do catálogo",
        raridade="Raridade da carta que será adicionada",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(raridade=[
        app_commands.Choice(name="Ouro", value="Ouro"),
        app_commands.Choice(name="Elite", value="Elite"),
        app_commands.Choice(name="Dominante", value="Dominante"),
        app_commands.Choice(name="Immortal", value="Immortal"),
        app_commands.Choice(name="Lendário", value="Lendário"),
        app_commands.Choice(name="Mítico", value="Mítico"),
        app_commands.Choice(name="Limited", value="Limited"),
        app_commands.Choice(name="Special", value="Special"),
        app_commands.Choice(name="Icon", value="Icon"),
    ])
    async def admin_adicionar_jogador(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        jogador: str,
        raridade: str,
    ):
        if not _eh_admin(interaction):
            await interaction.response.send_message(
                "❌ Só administradores do servidor podem usar esse comando.",
                ephemeral=True,
            )
            return

        carta = buscar_jogador_catalogo(jogador, raridade=raridade)
        if carta is None:
            await interaction.response.send_message(
                f"❌ Não existe **{jogador}** com a raridade **{raridade}** no catálogo.",
                ephemeral=True,
            )
            return

        if await db.usuario_possui_jogador(
            usuario.id,
            carta["name"],
            carta.get("rarity"),
            carta.get("overall"),
        ):
            await interaction.response.send_message(
                f"❌ {usuario.mention} já possui **{carta['name']}** • **{carta['rarity']}** • OVR **{carta['overall']}**.",
                ephemeral=True,
            )
            return

        await db.add_player_to_user(usuario.id, carta)
        await interaction.response.send_message(
            f"✅ **{carta['name']}** ({carta['rarity']} • {carta['position']} • OVR {carta['overall']}) "
            f"foi adicionado ao inventário de {usuario.mention}."
        )

    @app_commands.command(name="admin_remover_jogador", description="[ADMIN] Remove uma carta específica do usuário")
    @app_commands.describe(
        usuario="Usuário que vai perder o jogador",
        jogador="Nome exato do jogador",
        raridade="Raridade da carta que será removida",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(raridade=[
        app_commands.Choice(name="Ouro", value="Ouro"),
        app_commands.Choice(name="Elite", value="Elite"),
        app_commands.Choice(name="Dominante", value="Dominante"),
        app_commands.Choice(name="Immortal", value="Immortal"),
        app_commands.Choice(name="Lendário", value="Lendário"),
        app_commands.Choice(name="Mítico", value="Mítico"),
        app_commands.Choice(name="Limited", value="Limited"),
        app_commands.Choice(name="Special", value="Special"),
        app_commands.Choice(name="Icon", value="Icon"),
    ])
    async def admin_remover_jogador(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        jogador: str,
        raridade: str,
    ):
        if not _eh_admin(interaction):
            await interaction.response.send_message(
                "❌ Só administradores do servidor podem usar esse comando.",
                ephemeral=True,
            )
            return

        carta = buscar_jogador_catalogo(jogador, raridade=raridade)
        if carta is None:
            await interaction.response.send_message(
                f"❌ Não existe **{jogador}** com a raridade **{raridade}** no catálogo.",
                ephemeral=True,
            )
            return

        removido = await db.remove_one_player_by_name(
            usuario.id,
            carta["name"],
            carta.get("rarity"),
            carta.get("overall"),
        )
        if removido is None:
            await interaction.response.send_message(
                f"❌ {usuario.mention} não possui **{carta['name']} • {carta['rarity']} • OVR {carta['overall']}**.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ **{carta['name']}** ({carta['rarity']} • OVR {carta['overall']}) foi removido do inventário de {usuario.mention}. "
            f"Se estava escalado, o slot também foi liberado."
        )

    @app_commands.command(name="admin_zerar_saldo", description="[ADMIN] Zera o saldo de Robux de um usuário")
    @app_commands.describe(usuario="Usuário que vai ter o saldo zerado")
    @app_commands.default_permissions(administrator=True)
    async def admin_zerar_saldo(self, interaction: discord.Interaction, usuario: discord.Member):
        if not _eh_admin(interaction):
            await interaction.response.send_message("❌ Só administradores do servidor podem usar esse comando.", ephemeral=True)
            return

        await db.zerar_saldo(usuario.id)
        await interaction.response.send_message(f"✅ Saldo de {usuario.mention} foi zerado (0 Robux).")

    @app_commands.command(name="admin_zerar_claim", description="[ADMIN] Zera o cooldown do /claim de um usuário")
    @app_commands.describe(usuario="Usuário que vai ter o cooldown do claim zerado")
    @app_commands.default_permissions(administrator=True)
    async def admin_zerar_claim(self, interaction: discord.Interaction, usuario: discord.Member):
        if not _eh_admin(interaction):
            await interaction.response.send_message("❌ Só administradores do servidor podem usar esse comando.", ephemeral=True)
            return

        await db.resetar_last_claim(usuario.id)
        await interaction.response.send_message(
            f"✅ Cooldown do `/claim` de {usuario.mention} foi zerado. Ele(a) já pode usar de novo.",
        )

    @app_commands.command(
        name="admin_limpar_cartas_invalidas",
        description="[ADMIN] Remove do SQLite cartas que não existem mais no catálogo",
    )
    @app_commands.default_permissions(administrator=True)
    async def admin_limpar_cartas_invalidas(self, interaction: discord.Interaction):
        if not _eh_admin(interaction):
            await interaction.response.send_message(
                "❌ Só administradores do servidor podem usar esse comando.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        removidas = await db.limpar_cartas_fora_do_catalogo(PLAYERS_CATALOG)

        if not removidas:
            await interaction.followup.send(
                "✅ Nenhuma carta inválida foi encontrada no SQLite.",
                ephemeral=True,
            )
            return

        linhas = [
            f"• ID `{carta['id']}` — **{carta['player_name']}** "
            f"({carta['position']} • OVR {carta['overall']} • {carta['rarity']})"
            for carta in removidas[:20]
        ]

        if len(removidas) > 20:
            linhas.append(f"• ... e mais **{len(removidas) - 20}** carta(s).")

        await interaction.followup.send(
            "🧹 **Limpeza concluída!**\n\n"
            f"Foram removidas **{len(removidas)}** carta(s) que não existem mais no `PLAYERS_CATALOG`.\n"
            "As referências dessas cartas na escalação e no mercado também foram removidas.\n\n"
            + "\n".join(linhas),
            ephemeral=True,
        )

    @app_commands.command(name="admin_vacuum", description="[ADMIN] Limpa o espaço livre do banco (reduz o tamanho do arquivo .db)")
    @app_commands.default_permissions(administrator=True)
    async def admin_vacuum(self, interaction: discord.Interaction):
        if not _eh_admin(interaction):
            await interaction.response.send_message("❌ Só administradores do servidor podem usar esse comando.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        tamanho_antes, tamanho_depois = await db.vacuum_manual()

        antes_kb = tamanho_antes / 1024
        depois_kb = tamanho_depois / 1024
        reducao_kb = antes_kb - depois_kb
        reducao_pct = (reducao_kb / antes_kb * 100) if antes_kb > 0 else 0

        await interaction.followup.send(
            f"🧹 **Banco limpo!**\n"
            f"Antes: `{antes_kb:.1f} KB`\n"
            f"Depois: `{depois_kb:.1f} KB`\n"
            f"Redução: `{reducao_kb:.1f} KB` ({reducao_pct:.1f}%)",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))

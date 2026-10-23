"""Compra e controle do Pacote Pro."""

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import database as db


PRO_CHOICES = [app_commands.Choice(name="Pro", value="pro")]


async def obter_role_pro(guild: discord.Guild) -> discord.Role | None:
    role = discord.utils.get(guild.roles, name=config.PRO_ROLE_NOME)
    if role is not None:
        return role
    try:
        return await guild.create_role(
            name=config.PRO_ROLE_NOME,
            reason="Cargo usado pelo Pacote Pro",
        )
    except discord.Forbidden:
        return None


async def sincronizar_pro(member: discord.Member) -> bool:
    """Sincroniza cargo Pro com a assinatura persistida no banco."""
    expirou = await db.expirar_pro_se_necessario(member.id)
    role = discord.utils.get(member.guild.roles, name=config.PRO_ROLE_NOME)

    if expirou:
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="Pacote Pro expirado")
            except discord.HTTPException:
                pass
        return False

    expiracao = await db.get_pro_expiracao(member.id)
    if not expiracao:
        return False

    try:
        ativo = datetime.fromisoformat(expiracao) > datetime.utcnow()
    except (TypeError, ValueError):
        ativo = False

    if not ativo:
        return False

    if role is None:
        role = await obter_role_pro(member.guild)
    if role is None:
        return False

    if role not in member.roles:
        try:
            await member.add_roles(role, reason="Pacote Pro ativo")
        except discord.HTTPException:
            return False
    return True


class Pro(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.expirador_pro.start()

    def cog_unload(self):
        self.expirador_pro.cancel()

    @tasks.loop(minutes=10)
    async def expirador_pro(self):
        # Remove cargos de assinaturas expiradas sem depender de o usuário executar um comando.
        pro_ids = await db.get_pro_user_ids()
        if not pro_ids:
            return
        for guild in self.bot.guilds:
            role = discord.utils.get(guild.roles, name=config.PRO_ROLE_NOME)
            if role is None:
                continue
            for user_id in pro_ids:
                member = guild.get_member(user_id)
                if member is None:
                    continue
                expirou = await db.expirar_pro_se_necessario(user_id)
                if expirou and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Pacote Pro expirado")
                    except discord.HTTPException:
                        pass

    @expirador_pro.before_loop
    async def antes_expirador_pro(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="comprar", description="Compre um pacote Pro por 7 dias")
    @app_commands.describe(produto="Escolha o produto")
    @app_commands.choices(produto=PRO_CHOICES)
    async def comprar(self, interaction: discord.Interaction, produto: app_commands.Choice[str]):
        from cogs.loja import usuario_e_booster
        
        if produto.value != "pro":
            await interaction.response.send_message("❌ Produto inválido.", ephemeral=True)
            return

        if usuario_e_booster(interaction.user):
            await interaction.response.send_message(
                "❌ Você já possui o **Booster** e não pode comprar o **Pro**.",
                ephemeral=True,
            )
            return

        # Remove eventual Pro vencido antes de avaliar uma nova compra.
        await sincronizar_pro(interaction.user)

        # Garante o cargo antes de debitar o saldo.
        role = await obter_role_pro(interaction.guild)
        if role is None:
            await interaction.response.send_message(
                "❌ Não consegui criar/encontrar o cargo **Pro**. Dê ao bot a permissão "
                "**Gerenciar Cargos** e coloque o cargo do bot acima do cargo Pro.",
                ephemeral=True,
            )
            return

        sucesso, motivo, expiracao = await db.ativar_pro_se_disponivel(
            interaction.user.id,
            config.PRO_PRECO,
            config.PRO_DURACAO_DIAS,
        )

        if not sucesso:
            if motivo == "ativo":
                restante = max(0, int((expiracao - datetime.utcnow()).total_seconds()))
                dias, resto = divmod(restante, 86400)
                horas, _ = divmod(resto, 3600)
                await interaction.response.send_message(
                    f"❌ Você já possui o **Pro** ativo. Ele expira em **{dias}d {horas}h**. "
                    "Você só poderá comprar novamente depois que expirar.",
                    ephemeral=True,
                )
                return

            await interaction.response.send_message(
                f"❌ Saldo insuficiente. O **Pacote Pro** custa {config.MOEDA_EMOJI} "
                f"**{config.PRO_PRECO} {config.MOEDA_NOME}**.",
                ephemeral=True,
            )
            return

        try:
            await interaction.user.add_roles(role, reason="Compra do Pacote Pro")
        except discord.HTTPException:
            await interaction.response.send_message(
                "⚠️ O Pro foi comprado, mas não consegui atribuir o cargo. Verifique a hierarquia/permissão de cargos do bot.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"💎 **Pro ativado!** Você pagou {config.MOEDA_EMOJI} **{config.PRO_PRECO} {config.MOEDA_NOME}**.\n"
            f"Acesso válido por **{config.PRO_DURACAO_DIAS} dias**.\n"
            f"O cargo **{config.PRO_ROLE_NOME}** foi atribuído e o **Pacote Pro** já está disponível na loja.",
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Pro(bot))

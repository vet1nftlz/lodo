"""Ponto de entrada do bot DreamTeam."""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes de importar database, para DB_PATH ser lido corretamente

import discord
from discord.ext import commands

import database as db

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # não é obrigatório pra slash commands, mas útil pra debug

bot = commands.Bot(command_prefix="!", intents=intents)

COGS_INICIAIS = [
    "cogs.economia",
    "cogs.loja",
    "cogs.pro",
    "cogs.claim",
    "cogs.weekly",
    "cogs.vender",
    "cogs.trade",
    "cogs.info",
    "cogs.perfil",
    "cogs.about",
    "cogs.transfermarket",
    "cogs.time",
    "cogs.view",
    "cogs.batalha",
    "cogs.amistoso",
    "cogs.campeonato",
    "cogs.admin",
    "cogs.minigames",
]


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")
    try:
        guild_id = os.getenv("GUILD_ID")

        # Este bot usa slash commands SOMENTE de forma local.
        # Nunca sincroniza os comandos globalmente.
        if not guild_id:
            print("⚠️ GUILD_ID não definido. Slash commands NÃO serão sincronizados globalmente.")
            return

        guild = discord.Object(id=int(guild_id))

        # Copia os comandos carregados para a árvore específica deste servidor
        # e sincroniza somente nele (aparece praticamente na hora).
        bot.tree.copy_global_to(guild=guild)
        sincronizados = await bot.tree.sync(guild=guild)
        print(f"🔄 {len(sincronizados)} slash commands sincronizados localmente no servidor {guild_id}.")

        # Remove comandos globais antigos que possam ter ficado registrados
        # por versões anteriores do bot.
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        print("🧹 Comandos globais antigos removidos.")

    except Exception as e:
        print(f"⚠️ Erro ao sincronizar slash commands locais: {e}")


async def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN não encontrado. Crie um arquivo .env com DISCORD_TOKEN=seu_token_aqui "
            "(veja .env.example)."
        )

    await db.init_db()

    async with bot:
        for cog in COGS_INICIAIS:
            await bot.load_extension(cog)
            print(f"📦 Cog carregado: {cog}")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

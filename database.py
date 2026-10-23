"""Camada de banco de dados (SQLite assíncrono) do bot DreamTeam."""

import os
import aiosqlite
from datetime import datetime, timedelta

import config

DB_PATH = os.getenv("DB_PATH", "dreamteam.db")


async def init_db():
    """Cria as tabelas do banco caso ainda não existam."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                last_work TEXT,
                last_daily TEXT
            )
        """)
        # Migração segura: adiciona a coluna se o banco já existir de uma versão anterior
        for coluna, tipo in (
            ("last_campeonato", "TEXT"),
            ("last_claim", "TEXT"),
            ("last_weekly", "TEXT"),
            ("last_torneio", "TEXT"),
            ("inventory_extra_slots", "INTEGER DEFAULT 0"),
            ("package_opens_since_verification", "INTEGER DEFAULT 0"),
            ("adivinhe_jogos", "INTEGER DEFAULT 0"),
            ("adivinhe_acertos", "INTEGER DEFAULT 0"),
            ("adivinhe_erros", "INTEGER DEFAULT 0"),
            ("adivinhe_sequencia", "INTEGER DEFAULT 0"),
            ("adivinhe_melhor_sequencia", "INTEGER DEFAULT 0"),
            ("adivinhe_cooldown_ate", "TEXT"),
            ("pro_ate", "TEXT"),
            ("last_draft", "TEXT"),
            ("time_nome", "TEXT"),
            ("estadio_nome", "TEXT"),
            ("last_multi_open", "TEXT"),
            ("last_icon_open", "TEXT"),
            ("last_icon_purchase", "TEXT"),
        ):
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {coluna} {tipo}")
            except Exception:
                pass  # coluna já existe, ignora
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                position TEXT NOT NULL,
                overall INTEGER NOT NULL,
                rarity TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS booster_unique_claims (
                user_id INTEGER NOT NULL,
                group_key TEXT NOT NULL,
                player_name TEXT NOT NULL,
                claimed_at TEXT NOT NULL,
                PRIMARY KEY (user_id, group_key)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_packages (
                user_id INTEGER NOT NULL,
                package_key TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, package_key)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transfer_market (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL UNIQUE,
                price INTEGER NOT NULL,
                listed_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lineup (
                user_id INTEGER NOT NULL,
                modo TEXT NOT NULL,
                posicao TEXT NOT NULL,
                slot INTEGER NOT NULL,
                user_player_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, modo, posicao, slot)
            )
        """)
        await db.commit()

    # Corrige escalações 4v4 antigas que ficaram com 5 jogadores.
    # Isso NÃO remove jogadores do inventário: apenas limpa a escalação.
    await _limpar_escalacoes_4v4_invalidas()

    # Mantém no máximo 2 cópias de cada jogador e converte apenas o excesso.
    await _resgatar_duplicatas_existentes()


async def _limpar_escalacoes_4v4_invalidas():
    """Limpa apenas escalações 4v4 que atualmente possuem mais de 4 jogadores."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT user_id, COUNT(*) AS total
               FROM lineup
               WHERE modo = '4v4'
               GROUP BY user_id
               HAVING COUNT(*) > 4"""
        )
        usuarios = await cur.fetchall()

        if usuarios:
            ids = [row[0] for row in usuarios]
            await db.execute("DELETE FROM lineup WHERE modo = '4v4' AND user_id IN (%s)" % ",".join("?" * len(ids)), ids)
            await db.commit()
            print(f"🧹 Migração: {len(ids)} escalação(ões) 4v4 inválida(s) com 5+ jogadores foram esvaziadas; jogadores preservados no inventário.")


async def _resgatar_duplicatas_existentes():
    from players_data import PLAYERS_CATALOG, buscar_jogador_catalogo

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id, user_id, player_name, overall, rarity FROM user_players ORDER BY user_id, player_name, rarity, overall, id"
        )
        linhas = await cur.fetchall()

        contagens = {}
        convertidas = 0
        for linha in linhas:
            chave = (linha["user_id"], linha["player_name"], linha["rarity"], linha["overall"])
            contagens[chave] = contagens.get(chave, 0) + 1
            if contagens[chave] > 2:
                jogador = next(
                    (j for j in PLAYERS_CATALOG if
                     j.get("name") == linha["player_name"] and
                     j.get("rarity") == linha["rarity"] and
                     j.get("overall") == linha["overall"]),
                    None,
                )
                preco = jogador["price"] if jogador else 0
                await db.execute("DELETE FROM user_players WHERE id = ?", (linha["id"],))
                await db.execute("DELETE FROM lineup WHERE user_player_id = ?", (linha["id"],))
                await db.execute(
                    "INSERT INTO users (user_id, balance) VALUES (?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET balance = balance + excluded.balance",
                    (linha["user_id"], preco),
                )
                convertidas += 1

        await db.commit()
        if convertidas:
            print(f"💰 Migração: {convertidas} carta(s) duplicada(s) convertida(s) em Robux.")


async def usuario_tem_carta(user_id: int, jogador: dict) -> bool:
    """Verifica se o usuário já possui esta variante exata da carta."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT 1 FROM user_players
               WHERE user_id = ? AND lower(player_name) = lower(?)
                 AND overall = ? AND rarity = ?
               LIMIT 1""",
            (
                user_id,
                jogador.get("name", ""),
                int(jogador.get("overall", 0)),
                jogador.get("rarity", ""),
            ),
        )
        return await cur.fetchone() is not None


# ---------- Usuário / saldo ----------

async def get_user(user_id: int) -> dict:
    """Retorna os dados do usuário, criando um registro novo se não existir."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, balance) VALUES (?, ?)",
                (user_id, config.SALDO_INICIAL),
            )
            await db.commit()
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
        return dict(row)


async def get_balance(user_id: int) -> int:
    user = await get_user(user_id)
    return user["balance"]


async def update_balance(user_id: int, amount: int):
    """Soma (ou subtrai, se negativo) um valor ao saldo do usuário."""
    await get_user(user_id)  # garante que o usuário existe
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()


async def set_last_work(user_id: int):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_work = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def set_last_daily(user_id: int):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_daily = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def set_last_campeonato(user_id: int):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_campeonato = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def set_last_claim(user_id: int):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_claim = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def set_last_weekly(user_id: int):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_weekly = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def resetar_last_weekly(user_id: int):
    """Zera o cooldown do /weekly (admin)."""
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_weekly = NULL WHERE user_id = ?", (user_id,))
        await db.commit()


async def resetar_last_claim(user_id: int):
    """Zera o cooldown do /claim (admin)."""
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_claim = NULL WHERE user_id = ?", (user_id,))
        await db.commit()


async def zerar_saldo(user_id: int):
    """Zera o saldo de Robux do usuário (admin)."""
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def zerar_inventario(user_id: int) -> int:
    """Apaga todas as cartas do usuário e limpa as escalações dele (admin).
    Retorna quantas cartas foram removidas.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM user_players WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        quantidade = row[0] if row else 0

        await db.execute("DELETE FROM user_players WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM lineup WHERE user_id = ?", (user_id,))
        await db.commit()
        return quantidade


async def vacuum_manual():
    """Roda VACUUM no banco pra reciclar o espaço livre deixado por deleções
    (cartas vendidas, duplicatas convertidas, etc.) e encolher o arquivo no disco.
    Só roda quando chamado explicitamente (comando de admin) — não é automático.
    Retorna (tamanho_antes_bytes, tamanho_depois_bytes).
    """
    tamanho_antes = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("VACUUM")
        await db.commit()
    tamanho_depois = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    return tamanho_antes, tamanho_depois


async def set_last_torneio(user_id: int):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_torneio = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def get_package_opens_since_verification(user_id: int) -> int:
    """Retorna quantos pacotes o usuário abriu desde a última verificação anti-bot."""
    user = await get_user(user_id)
    return int(user.get("package_opens_since_verification") or 0)


async def incrementar_package_opens(user_id: int) -> int:
    """Incrementa o contador de aberturas e retorna o novo valor."""
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET package_opens_since_verification = COALESCE(package_opens_since_verification, 0) + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
    return await get_package_opens_since_verification(user_id)


async def reset_package_opens_since_verification(user_id: int):
    """Zera o contador depois que o usuário passa pela verificação."""
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET package_opens_since_verification = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()



# ---------- Inventário / cartas ----------

async def get_user_players(user_id: int) -> list:
    """Retorna todas as cartas do inventário do usuário."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM user_players WHERE user_id = ? ORDER BY position, overall DESC, id",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_capacidade_inventario(user_id: int) -> int:
    """Retorna a capacidade atual do inventário."""
    user = await get_user(user_id)
    extra = int(user.get("inventory_extra_slots") or 0)
    return int(config.INVENTARIO_LIMITE_BASE) + extra


async def expandir_inventario(user_id: int, quantidade: int) -> int:
    """Adiciona espaços ao inventário e retorna a nova capacidade."""
    quantidade = max(0, int(quantidade))
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET inventory_extra_slots = COALESCE(inventory_extra_slots, 0) + ? WHERE user_id = ?",
            (quantidade, user_id),
        )
        await db.commit()
    return await get_capacidade_inventario(user_id)


async def _capacidade_em_transacao(db, user_id: int) -> int:
    """Capacidade do inventário lida dentro de uma transação já aberta."""
    cur = await db.execute(
        "SELECT inventory_extra_slots FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    extra = int((row[0] if row else 0) or 0)
    return int(config.INVENTARIO_LIMITE_BASE) + extra


async def get_espaco_inventario(user_id: int) -> dict:
    """Retorna total de cartas, capacidade e espaços livres do usuário."""
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM user_players WHERE user_id = ?",
            (user_id,),
        )
        total = int((await cur.fetchone())[0] or 0)
        capacidade = await _capacidade_em_transacao(db, user_id)
    return {
        "total": total,
        "capacidade": capacidade,
        "livres": max(0, capacidade - total),
    }


async def tem_espaco_inventario(user_id: int, quantidade: int = 1) -> bool:
    """True se o inventário comporta `quantidade` cartas novas."""
    espaco = await get_espaco_inventario(user_id)
    return espaco["livres"] >= int(quantidade)


async def mensagem_sem_espaco(user_id: int, quantidade: int) -> str:
    """Mensagem padrão quando o usuário não tem espaço para as cartas."""
    espaco = await get_espaco_inventario(user_id)
    return (
        f"📦 Você não tem espaço suficiente no inventário. "
        f"Essa ação precisa de **{int(quantidade)}** espaço(s) livre(s), "
        f"mas você tem apenas **{espaco['livres']}** "
        f"({espaco['total']}/{espaco['capacidade']} em uso). "
        f"Venda cartas com `/multisell` ou expanda o inventário na `/loja`."
    )


async def _contar_carta(db, user_id: int, player_name: str, rarity: str, overall: int) -> int:
    cur = await db.execute(
        """SELECT COUNT(*) FROM user_players
           WHERE user_id = ? AND player_name = ? AND rarity = ? AND overall = ?""",
        (user_id, player_name, rarity, overall),
    )
    row = await cur.fetchone()
    return int(row[0] or 0)


async def add_player_or_sell_duplicate(user_id: int, jogador: dict) -> dict:
    """Adiciona a carta; acima de 2 cópias converte automaticamente em Robux."""
    nome = jogador["name"]
    position = jogador["position"]
    overall = int(jogador["overall"])
    rarity = jogador["rarity"]
    valor = int(jogador.get("price", 0) or 0)

    await get_user(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        try:
            qtd = await _contar_carta(db, user_id, nome, rarity, overall)

            if qtd >= 2:
                await db.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (valor, user_id),
                )
                await db.commit()
                return {
                    "novo_id": None,
                    "duplicado": True,
                    "cheio": False,
                    "valor": valor,
                }

            cur = await db.execute(
                "SELECT COUNT(*) FROM user_players WHERE user_id = ?",
                (user_id,),
            )
            total = int((await cur.fetchone())[0] or 0)

            cur = await db.execute(
                "SELECT inventory_extra_slots FROM users WHERE user_id = ?",
                (user_id,),
            )
            extra = int((await cur.fetchone())[0] or 0)
            capacidade = int(config.INVENTARIO_LIMITE_BASE) + extra

            if total >= capacidade:
                await db.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (valor, user_id),
                )
                await db.commit()
                return {
                    "novo_id": None,
                    "duplicado": False,
                    "cheio": True,
                    "valor": valor,
                }

            cur = await db.execute(
                """INSERT INTO user_players
                   (user_id, player_name, position, overall, rarity)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, nome, position, overall, rarity),
            )
            novo_id = cur.lastrowid
            await db.commit()
            return {
                "novo_id": novo_id,
                "duplicado": False,
                "cheio": False,
                "valor": None,
            }
        except Exception:
            await db.rollback()
            raise


async def add_player_to_user(user_id: int, jogador: dict):
    """Adiciona uma carta administrativamente sem ultrapassar o limite de 2 cópias."""
    resultado = await add_player_or_sell_duplicate(user_id, jogador)
    if resultado.get("novo_id") is None:
        raise ValueError("O usuário já possui 2 cópias ou o inventário está cheio.")
    return resultado["novo_id"]


async def usuario_possui_jogador(user_id: int, player_name: str, rarity=None, overall=None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        query = "SELECT 1 FROM user_players WHERE user_id = ? AND lower(player_name) = lower(?)"
        args = [user_id, player_name]
        if rarity is not None:
            query += " AND rarity = ?"
            args.append(rarity)
        if overall is not None:
            query += " AND overall = ?"
            args.append(int(overall))
        query += " LIMIT 1"
        cur = await db.execute(query, args)
        return await cur.fetchone() is not None


async def limpar_cartas_fora_do_catalogo(catalogo: list[dict]) -> list[dict]:
    """Remove cartas do SQLite cuja identidade não existe mais no catálogo.

    A identidade usa nome + posição + overall + raridade, sem usar apenas o nome,
    para não confundir cartas diferentes do mesmo jogador. Também remove referências
    dessas instâncias na escalação e no mercado de transferências.
    """
    identidades_catalogo = {
        (
            str(jogador.get("name", "")).strip().casefold(),
            str(jogador.get("position", "")).strip().upper(),
            int(jogador.get("overall", 0)),
            str(jogador.get("rarity", "")).strip().casefold(),
        )
        for jogador in catalogo
    }

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        try:
            cur = await db.execute(
                """SELECT id, user_id, player_name, position, overall, rarity
                   FROM user_players
                   ORDER BY id"""
            )
            cartas = await cur.fetchall()

            invalidas = []
            for carta in cartas:
                identidade = (
                    str(carta["player_name"]).strip().casefold(),
                    str(carta["position"]).strip().upper(),
                    int(carta["overall"]),
                    str(carta["rarity"]).strip().casefold(),
                )
                if identidade not in identidades_catalogo:
                    invalidas.append(dict(carta))

            if not invalidas:
                await db.commit()
                return []

            ids = [carta["id"] for carta in invalidas]
            placeholders = ",".join("?" for _ in ids)

            # Primeiro remove referências para não deixar IDs órfãos.
            await db.execute(
                f"DELETE FROM lineup WHERE user_player_id IN ({placeholders})",
                ids,
            )
            await db.execute(
                f"DELETE FROM transfer_market WHERE player_id IN ({placeholders})",
                ids,
            )
            await db.execute(
                f"DELETE FROM user_players WHERE id IN ({placeholders})",
                ids,
            )

            await db.commit()
            return invalidas
        except Exception:
            await db.rollback()
            raise


async def remove_player_by_id(user_id: int, player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute(
            "SELECT id FROM user_players WHERE id = ? AND user_id = ?",
            (int(player_id), user_id),
        )
        row = await cur.fetchone()
        if not row:
            await db.rollback()
            return False
        await db.execute("DELETE FROM lineup WHERE user_player_id = ?", (int(player_id),))
        await db.execute(
            "DELETE FROM user_players WHERE id = ? AND user_id = ?",
            (int(player_id), user_id),
        )
        await db.commit()
        return True


async def remove_one_player_by_name(user_id: int, player_name: str, rarity=None, overall=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """SELECT * FROM user_players
                   WHERE user_id = ? AND lower(player_name) = lower(?)"""
        args = [user_id, player_name]
        if rarity is not None:
            query += " AND rarity = ?"
            args.append(rarity)
        if overall is not None:
            query += " AND overall = ?"
            args.append(int(overall))
        query += " ORDER BY id LIMIT 1"
        cur = await db.execute(query, args)
        row = await cur.fetchone()
        if not row:
            return None
        pid = row["id"]
        await db.execute("DELETE FROM lineup WHERE user_player_id = ?", (pid,))
        await db.execute("DELETE FROM user_players WHERE id = ? AND user_id = ?", (pid, user_id))
        await db.commit()
        return dict(row)


# ---------- Escalações ----------

async def get_lineup(user_id: int, modo: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT up.*, l.modo, l.posicao, l.slot
               FROM lineup l
               JOIN user_players up ON up.id = l.user_player_id
               WHERE l.user_id = ? AND l.modo = ?
               ORDER BY l.posicao, l.slot""",
            (user_id, modo),
        )
        return [dict(r) for r in await cur.fetchall()]


async def clear_lineup_slot(user_id: int, modo: str, posicao: str, slot: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM lineup WHERE user_id = ? AND modo = ? AND posicao = ? AND slot = ?",
            (user_id, modo, posicao, int(slot)),
        )
        await db.commit()


async def set_lineup_slot(user_id: int, modo: str, posicao: str, slot: int, user_player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        try:
            cur = await db.execute(
                "SELECT 1 FROM user_players WHERE id = ? AND user_id = ?",
                (int(user_player_id), user_id),
            )
            if not await cur.fetchone():
                raise ValueError("Carta não pertence ao usuário.")
            await db.execute(
                "DELETE FROM lineup WHERE user_id = ? AND modo = ? AND posicao = ? AND slot = ?",
                (user_id, modo, posicao, int(slot)),
            )
            await db.execute(
                """INSERT INTO lineup (user_id, modo, posicao, slot, user_player_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, modo, posicao, int(slot), int(user_player_id)),
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise


# ---------- Trocas ----------

async def execute_trade(proponente_id: int, oponente_id: int, minha_carta_id: int, carta_dele_id: int, amount: int = 0) -> dict:
    amount = max(0, int(amount))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")
        try:
            cur = await db.execute(
                "SELECT * FROM user_players WHERE id = ? AND user_id = ?",
                (int(minha_carta_id), proponente_id),
            )
            minha = await cur.fetchone()
            cur = await db.execute(
                "SELECT * FROM user_players WHERE id = ? AND user_id = ?",
                (int(carta_dele_id), oponente_id),
            )
            dele = await cur.fetchone()

            if not minha or not dele:
                await db.rollback()
                return {"ok": False, "motivo": "indisponivel"}

            cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (proponente_id,))
            saldo = await cur.fetchone()
            if amount > 0 and (not saldo or int(saldo[0]) < amount):
                await db.rollback()
                return {"ok": False, "motivo": "saldo"}

            # O limite de 2 cópias é aplicado para cada carta recebida.
            for receiver, row, motivo in (
                (proponente_id, dele, "limite_proponente"),
                (oponente_id, minha, "limite_oponente"),
            ):
                cur = await db.execute(
                    """SELECT COUNT(*) FROM user_players
                       WHERE user_id = ? AND player_name = ? AND rarity = ? AND overall = ?""",
                    (receiver, row[2], row[5], row[4]),
                )
                if int((await cur.fetchone())[0]) >= 2:
                    await db.rollback()
                    return {"ok": False, "motivo": motivo}

            # Uma carta trocada não pode permanecer presa à escalação antiga.
            await db.execute("DELETE FROM lineup WHERE user_player_id IN (?, ?)", (int(minha_carta_id), int(carta_dele_id)))

            await db.execute(
                "UPDATE user_players SET user_id = ? WHERE id = ? AND user_id = ?",
                (oponente_id, int(minha_carta_id), proponente_id),
            )
            await db.execute(
                "UPDATE user_players SET user_id = ? WHERE id = ? AND user_id = ?",
                (proponente_id, int(carta_dele_id), oponente_id),
            )
            if amount:
                await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, proponente_id))
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, oponente_id))

            await db.commit()
            return {"ok": True}
        except Exception:
            await db.rollback()
            raise

# ---------- Pacote Pro ----------

async def get_pro_expiracao(user_id: int):
    user = await get_user(user_id)
    return user.get("pro_ate")


async def ativar_pro_se_disponivel(user_id: int, preco: int, duracao_dias: int):
    """Compra o Pro de forma atômica. Retorna (ok, motivo, expiracao)."""
    await get_user(user_id)
    agora = datetime.utcnow()
    expiracao = agora + timedelta(days=int(duracao_dias))
    valor_expiracao = expiracao.isoformat()
    agora_iso = agora.isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """UPDATE users
               SET balance = balance - ?, pro_ate = ?
               WHERE user_id = ?
                 AND balance >= ?
                 AND (pro_ate IS NULL OR pro_ate <= ?)""",
            (int(preco), valor_expiracao, user_id, int(preco), agora_iso),
        )
        await db.commit()
        if cur.rowcount != 1:
            user = await get_user(user_id)
            if user.get("pro_ate"):
                try:
                    expira = datetime.fromisoformat(user["pro_ate"])
                    if expira > agora:
                        return False, "ativo", expira
                except (TypeError, ValueError):
                    pass
            return False, "saldo", None

    return True, "ok", expiracao


async def get_pro_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE pro_ate IS NOT NULL")
        rows = await cur.fetchall()
        return [int(row[0]) for row in rows]


async def expirar_pro_se_necessario(user_id: int):
    """Retorna True se havia um Pro expirado e limpa o registro."""
    user = await get_user(user_id)
    valor = user.get("pro_ate")
    if not valor:
        return False
    try:
        expiracao = datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        expiracao = datetime.utcnow()
    if expiracao <= datetime.utcnow():
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET pro_ate = NULL WHERE user_id = ?", (user_id,))
            await db.commit()
        return True
    return False


# ---------- Estatísticas do /adivinhe ----------

async def registrar_adivinhe_resultado(user_id: int, acertou: bool, tentativas: int = 0):
    """Atualiza estatísticas persistentes do minigame /adivinhe."""
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        if acertou:
            await db.execute(
                """UPDATE users
                   SET adivinhe_jogos = COALESCE(adivinhe_jogos, 0) + 1,
                       adivinhe_acertos = COALESCE(adivinhe_acertos, 0) + 1,
                       adivinhe_erros = COALESCE(adivinhe_erros, 0) + MAX(0, ? - 1),
                       adivinhe_sequencia = COALESCE(adivinhe_sequencia, 0) + 1,
                       adivinhe_melhor_sequencia = MAX(
                           COALESCE(adivinhe_melhor_sequencia, 0),
                           COALESCE(adivinhe_sequencia, 0) + 1
                       )
                   WHERE user_id = ?""",
                (tentativas, user_id),
            )
        else:
            await db.execute(
                """UPDATE users
                   SET adivinhe_jogos = COALESCE(adivinhe_jogos, 0) + 1,
                       adivinhe_erros = COALESCE(adivinhe_erros, 0) + ?,
                       adivinhe_sequencia = 0
                   WHERE user_id = ?""",
                (max(0, int(tentativas)), user_id),
            )
        await db.commit()


async def definir_adivinhe_cooldown(user_id: int, minutos: int):
    """Aplica cooldown persistente ao /adivinhe após perder a sequência."""
    await get_user(user_id)
    ate = datetime.utcnow().timestamp() + (int(minutos) * 60)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET adivinhe_cooldown_ate = ? WHERE user_id = ?",
            (datetime.utcfromtimestamp(ate).isoformat(), user_id),
        )
        await db.commit()


async def set_last_draft(user_id: int):
    agora = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_draft = ? WHERE user_id = ?",
            (agora, user_id),
        )
        await db.commit()


async def get_draft_cooldown(user_id: int) -> float:
    user = await get_user(user_id)
    valor = user.get("last_draft")
    if not valor:
        return 0.0
    try:
        ultima_vez = datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        return 0.0
    restante = timedelta(minutes=config.DRAFT_COOLDOWN_MINUTOS) - (datetime.utcnow() - ultima_vez)
    return max(0.0, restante.total_seconds())


async def get_adivinhe_cooldown(user_id: int) -> float:
    """Retorna os segundos restantes do cooldown persistente."""
    user = await get_user(user_id)
    valor = user.get("adivinhe_cooldown_ate")
    if not valor:
        return 0.0
    try:
        restante = datetime.fromisoformat(valor).timestamp() - datetime.utcnow().timestamp()
        return max(0.0, restante)
    except (TypeError, ValueError, OSError):
        return 0.0


async def get_adivinhe_stats(user_id: int) -> dict:
    user = await get_user(user_id)
    return {
        "jogos": int(user.get("adivinhe_jogos") or 0),
        "acertos": int(user.get("adivinhe_acertos") or 0),
        "erros": int(user.get("adivinhe_erros") or 0),
        "sequencia": int(user.get("adivinhe_sequencia") or 0),
        "melhor_sequencia": int(user.get("adivinhe_melhor_sequencia") or 0),
    }


# ---------- Exclusividades de pacotes ----------

async def usuario_tem_grupo_booster(user_id: int, group_key: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM booster_unique_claims WHERE user_id = ? AND group_key = ? LIMIT 1",
            (user_id, group_key),
        )
        return await cur.fetchone() is not None


async def registrar_grupo_booster(user_id: int, group_key: str, player_name: str) -> bool:
    """Registra uma exclusividade de pacote de forma atômica.

    Retorna True se o grupo foi registrado agora e False se o usuário
    já possuía esse grupo. A tabela é compartilhada por Booster e Pro;
    o nome histórico da função/tabela é mantido para não quebrar dados
    existentes.
    """
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO booster_unique_claims (user_id, group_key, player_name, claimed_at) VALUES (?, ?, ?, ?)",
            (user_id, group_key, player_name, datetime.utcnow().isoformat()),
        )
        await db.commit()
        return cur.rowcount == 1




# ---------- Perfil / identidade ----------

async def definir_nome_time(user_id: int, nome: str):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET time_nome = ? WHERE user_id = ?", (nome, user_id))
        await db.commit()


async def definir_nome_estadio(user_id: int, nome: str):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET estadio_nome = ? WHERE user_id = ?", (nome, user_id))
        await db.commit()


async def get_identidade_time(user_id: int) -> dict:
    user = await get_user(user_id)
    return {
        "time_nome": user.get("time_nome") or config.NOME_TIME_PADRAO,
        "estadio_nome": user.get("estadio_nome") or config.NOME_ESTADIO_PADRAO,
    }


# ---------- Pacotes armazenados ----------

async def adicionar_pacotes(user_id: int, chave_pacote: str, quantidade: int):
    if quantidade <= 0:
        return
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO user_packages (user_id, package_key, quantity)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, package_key)
               DO UPDATE SET quantity = quantity + excluded.quantity""",
            (user_id, chave_pacote, int(quantidade)),
        )
        await db.commit()


async def contar_pacotes(user_id: int, chave_pacote: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT quantity FROM user_packages WHERE user_id = ? AND package_key = ?",
            (user_id, chave_pacote),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def get_user_packages(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT package_key, quantity FROM user_packages WHERE user_id = ? AND quantity > 0 ORDER BY package_key",
            (user_id,),
        )
        rows = await cur.fetchall()
        return {row[0]: int(row[1]) for row in rows}


async def consumir_pacotes(user_id: int, chave_pacote: str, quantidade: int) -> bool:
    if quantidade <= 0:
        return False
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """UPDATE user_packages
               SET quantity = quantity - ?
               WHERE user_id = ? AND package_key = ? AND quantity >= ?""",
            (int(quantidade), user_id, chave_pacote, int(quantidade)),
        )
        await db.commit()
        return cur.rowcount == 1


async def get_multi_open_cooldown(user_id: int) -> float:
    user = await get_user(user_id)
    valor = user.get("last_multi_open")
    if not valor:
        return 0.0
    try:
        restante = timedelta(minutes=config.ABRIR_QUANTIDADE_COOLDOWN_MINUTOS) - (
            datetime.utcnow() - datetime.fromisoformat(valor)
        )
        return max(0.0, restante.total_seconds())
    except (TypeError, ValueError):
        return 0.0


async def set_multi_open_cooldown(user_id: int):
    await get_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_multi_open = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()

async def get_icon_open_cooldown(user_id: int) -> float:
    user = await get_user(user_id)
    valor = user.get("last_icon_open")

    if not valor:
        return 0.0

    try:
        restante = timedelta(minutes=config.ICON_COOLDOWN_MINUTOS) - (
            datetime.utcnow() - datetime.fromisoformat(valor)
        )
        return max(0.0, restante.total_seconds())
    except (TypeError, ValueError):
        return 0.0


async def set_icon_open_cooldown(user_id: int):
    await get_user(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_icon_open = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def comprar_icon_pacote(user_id: int):
    """Compra exatamente 1 Pacote Icon com saldo e cooldown atômicos."""
    pacote = config.PACOTES.get("icon")
    if pacote is None:
        return {"ok": False, "motivo": "pacote"}

    await get_user(user_id)
    agora = datetime.utcnow()
    cooldown = timedelta(minutes=getattr(config, "ICON_COOLDOWN_MINUTOS", 30))
    preco = int(pacote.get("preco", 0))

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("BEGIN IMMEDIATE")
            cur = await db.execute(
                "SELECT balance, last_icon_purchase FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = await cur.fetchone()
            if row is None:
                await db.rollback()
                return {"ok": False, "motivo": "usuario"}

            saldo = int(row[0] or 0)
            ultima = row[1]
            if ultima:
                try:
                    restante = cooldown - (agora - datetime.fromisoformat(ultima))
                    if restante.total_seconds() > 0:
                        await db.rollback()
                        return {
                            "ok": False,
                            "motivo": "cooldown",
                            "restante": restante.total_seconds(),
                        }
                except (TypeError, ValueError):
                    pass

            if saldo < preco:
                await db.rollback()
                return {"ok": False, "motivo": "saldo", "saldo": saldo, "preco": preco}

            await db.execute(
                "UPDATE users SET balance = balance - ?, last_icon_purchase = ? WHERE user_id = ?",
                (preco, agora.isoformat(), user_id),
            )
            await db.execute(
                "INSERT INTO user_packages (user_id, package_key, quantity) VALUES (?, 'icon', 1) "
                "ON CONFLICT(user_id, package_key) DO UPDATE SET quantity = quantity + 1",
                (user_id,),
            )
            await db.commit()
            return {"ok": True, "total": preco}
        except Exception:
            await db.rollback()
            raise


# ---------- Transfer Market ----------

async def criar_anuncio_mercado(seller_id: int, player_id: int, price: int):
    if price <= 0:
        return False, "preco_invalido"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            await db.execute("BEGIN IMMEDIATE")

            cur = await db.execute(
                "SELECT COUNT(*) FROM transfer_market"
            )
            if int((await cur.fetchone())[0]) >= int(config.TRANSFER_MARKET_MAX_ANUNCIOS):
                await db.rollback()
                return False, "mercado_cheio"

            cur = await db.execute(
                "SELECT id, user_id FROM user_players WHERE id = ?",
                (player_id,),
            )
            player = await cur.fetchone()
            if player is None or int(player["user_id"]) != int(seller_id):
                await db.rollback()
                return False, "carta_indisponivel"

            cur = await db.execute(
                "SELECT 1 FROM transfer_market WHERE player_id = ?",
                (player_id,),
            )
            if await cur.fetchone():
                await db.rollback()
                return False, "ja_anunciada"

            await db.execute(
                "INSERT INTO transfer_market (seller_id, player_id, price, listed_at) VALUES (?, ?, ?, ?)",
                (seller_id, player_id, int(price), datetime.utcnow().isoformat()),
            )
            await db.commit()
            return True, "ok"
        except Exception:
            await db.rollback()
            raise


async def _reindexar_transfer_market(db):
    """Renumera os anúncios de forma contígua, preservando a ordem atual."""
    cur = await db.execute("SELECT id FROM transfer_market ORDER BY id ASC")
    ids = [int(row[0]) for row in await cur.fetchall()]
    if not ids:
        await db.execute("DELETE FROM sqlite_sequence WHERE name = 'transfer_market'")
        return

    # IDs temporários negativos evitam colisões durante a renumeração.
    await db.execute("UPDATE transfer_market SET id = -id")
    for novo_id, antigo_id in enumerate(ids, start=1):
        await db.execute(
            "UPDATE transfer_market SET id = ? WHERE id = ?",
            (novo_id, -antigo_id),
        )

    await db.execute(
        "UPDATE sqlite_sequence SET seq = ? WHERE name = 'transfer_market'",
        (len(ids),),
    )


async def cancelar_anuncio_mercado(seller_id: int, listing_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM transfer_market WHERE id = ? AND seller_id = ?",
            (listing_id, seller_id),
        )
        if cur.rowcount == 1:
            await _reindexar_transfer_market(db)
        await db.commit()
        return cur.rowcount == 1


async def get_anuncios_mercado(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT m.id, m.seller_id, m.player_id, m.price, m.listed_at,
                      p.player_name, p.position, p.overall, p.rarity
               FROM transfer_market m
               JOIN user_players p ON p.id = m.player_id
               ORDER BY m.id DESC LIMIT ?""",
            (int(limit),),
        )
        return [dict(row) for row in await cur.fetchall()]


async def comprar_anuncio_mercado(buyer_id: int, listing_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            await db.execute("BEGIN IMMEDIATE")
            cur = await db.execute(
                """SELECT m.*, p.player_name, p.position, p.overall, p.rarity
                   FROM transfer_market m
                   JOIN user_players p ON p.id = m.player_id
                  WHERE m.id = ?""",
                (listing_id,),
            )
            anuncio = await cur.fetchone()
            if anuncio is None:
                await db.rollback()
                return {"ok": False, "motivo": "nao_encontrado"}

            if int(anuncio["seller_id"]) == int(buyer_id):
                await db.rollback()
                return {"ok": False, "motivo": "proprio"}

            cur = await db.execute(
                "SELECT balance FROM users WHERE user_id = ?",
                (buyer_id,),
            )
            row = await cur.fetchone()
            saldo = int(row[0] or 0) if row else 0
            if saldo < int(anuncio["price"]):
                await db.rollback()
                return {"ok": False, "motivo": "saldo"}

            cur = await db.execute(
                """SELECT COUNT(*) FROM user_players
                   WHERE user_id = ? AND player_name = ? AND rarity = ? AND overall = ?""",
                (buyer_id, anuncio["player_name"], anuncio["rarity"], anuncio["overall"]),
            )
            if int((await cur.fetchone())[0]) >= 2:
                await db.rollback()
                return {"ok": False, "motivo": "limite_copias"}

            cur = await db.execute(
                "SELECT COUNT(*) FROM user_players WHERE user_id = ?",
                (buyer_id,),
            )
            if int((await cur.fetchone())[0]) >= await _capacidade_em_transacao(db, buyer_id):
                await db.rollback()
                return {"ok": False, "motivo": "inventario"}

            # A carta precisa continuar pertencendo ao vendedor no momento da compra.
            cur = await db.execute(
                "UPDATE user_players SET user_id = ? WHERE id = ? AND user_id = ?",
                (buyer_id, int(anuncio["player_id"]), int(anuncio["seller_id"])),
            )
            if cur.rowcount != 1:
                await db.rollback()
                return {"ok": False, "motivo": "carta_indisponivel"}

            await db.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (int(anuncio["price"]), buyer_id),
            )
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (int(anuncio["price"]), int(anuncio["seller_id"])),
            )
            await db.execute(
                "DELETE FROM lineup WHERE user_player_id = ?",
                (int(anuncio["player_id"]),),
            )
            await db.execute(
                "DELETE FROM transfer_market WHERE id = ?",
                (listing_id,),
            )
            await _reindexar_transfer_market(db)
            await db.commit()
            return {"ok": True, "anuncio": dict(anuncio)}

        except Exception:
            await db.rollback()
            raise

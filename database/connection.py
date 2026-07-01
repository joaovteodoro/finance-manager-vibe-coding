"""
Gerenciamento da conexão e inicialização do banco de dados SQLite.

O banco é criado automaticamente na primeira execução em financeiro.db.
Migrações são aplicadas automaticamente em bancos de versões anteriores,
preservando os dados já existentes.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "financeiro.db"

COLUNAS_ESPERADAS = {
    "saldo_atual": "REAL",
    "vinculo_id": "INTEGER",
    "forma_pagamento": "TEXT",
}


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão com o banco de dados.

    Returns:
        Conexão SQLite configurada com row_factory para acesso por nome.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_banco() -> None:
    """Cria as tabelas do banco se ainda não existirem e aplica migrações.

    Executado automaticamente no startup da aplicação.
    """
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                tipo TEXT NOT NULL
                    CHECK(tipo IN ('receita', 'despesa', 'ativo', 'passivo')),
                categoria TEXT NOT NULL,
                saldo_atual REAL,
                vinculo_id INTEGER,
                forma_pagamento TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()
        _migrar_check_tipo(conn)
        _migrar_colunas_novas(conn)
        _preencher_saldo_atual_legado(conn)


def _migrar_check_tipo(conn: sqlite3.Connection) -> None:
    """Atualiza bancos com o CHECK antigo (apenas receita/despesa).

    Recria a tabela com o CHECK expandido, preservando os dados.
    Idempotente: não faz nada se o schema já estiver atualizado.

    Args:
        conn: Conexão ativa com o banco.
    """
    sql_tabela = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='transacoes'"
    ).fetchone()
    if sql_tabela and "'ativo'" in sql_tabela["sql"]:
        return

    conn.execute("ALTER TABLE transacoes RENAME TO transacoes_old")
    conn.execute("""
        CREATE TABLE transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL
                CHECK(tipo IN ('receita', 'despesa', 'ativo', 'passivo')),
            categoria TEXT NOT NULL,
            criado_em TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    colunas_old = [
        r["name"] for r in conn.execute("PRAGMA table_info(transacoes_old)")
    ]
    colunas_comuns = [
        c for c in ("id", "data", "descricao", "valor", "tipo",
                     "categoria", "criado_em") if c in colunas_old
    ]
    cols_sql = ", ".join(colunas_comuns)
    conn.execute(f"""
        INSERT INTO transacoes ({cols_sql})
        SELECT {cols_sql} FROM transacoes_old
    """)
    conn.execute("DROP TABLE transacoes_old")
    conn.commit()


def _migrar_colunas_novas(conn: sqlite3.Connection) -> None:
    """Adiciona colunas novas (saldo_atual, vinculo_id, forma_pagamento).

    Usa ALTER TABLE ADD COLUMN, seguro para bancos já em uso.
    Idempotente: verifica quais colunas já existem antes de adicionar.

    Args:
        conn: Conexão ativa com o banco.
    """
    colunas_existentes = {
        r["name"] for r in conn.execute("PRAGMA table_info(transacoes)")
    }
    for coluna, tipo_sql in COLUNAS_ESPERADAS.items():
        if coluna not in colunas_existentes:
            conn.execute(f"ALTER TABLE transacoes ADD COLUMN {coluna} {tipo_sql}")
    conn.commit()


def _preencher_saldo_atual_legado(conn: sqlite3.Connection) -> None:
    """Preenche saldo_atual = valor para lançamentos antigos sem saldo.

    Necessário para ativos/passivos criados antes da introdução do
    conceito de saldo vigente, garantindo que a tela de Ativos e
    Passivos sempre tenha um saldo_atual válido para exibir.

    Args:
        conn: Conexão ativa com o banco.
    """
    conn.execute("""
        UPDATE transacoes SET saldo_atual = valor
        WHERE saldo_atual IS NULL AND tipo IN ('ativo', 'passivo')
    """)
    conn.commit()

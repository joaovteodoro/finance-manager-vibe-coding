"""Repositório de transações — toda comunicação com o banco passa aqui."""

from database.connection import get_connection
from models.transacao import Transacao

COLUNAS_ORDENAVEIS = {
    "data": "data",
    "descricao": "descricao",
    "tipo": "tipo",
    "categoria": "categoria",
    "valor": "valor",
    "saldo_atual": "saldo_atual",
}


def inserir(transacao: Transacao) -> int:
    """Insere uma nova transação no banco de dados.

    Args:
        transacao: Objeto Transacao a ser persistido.

    Returns:
        ID gerado para a transação inserida.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO transacoes
                (data, descricao, valor, tipo, categoria,
                 saldo_atual, vinculo_id, forma_pagamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transacao.data,
                transacao.descricao,
                transacao.valor,
                transacao.tipo,
                transacao.categoria,
                transacao.saldo_atual,
                transacao.vinculo_id,
                transacao.forma_pagamento,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def vincular(id_origem: int, id_destino: int) -> None:
    """Vincula duas transações como contrapartida uma da outra (partida dobrada).

    Args:
        id_origem: ID da primeira transação.
        id_destino: ID da segunda transação (contrapartida).
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE transacoes SET vinculo_id = ? WHERE id = ?",
            (id_destino, id_origem),
        )
        conn.execute(
            "UPDATE transacoes SET vinculo_id = ? WHERE id = ?",
            (id_origem, id_destino),
        )
        conn.commit()


def atualizar_saldo(id_transacao: int, novo_saldo: float) -> None:
    """Atualiza o saldo atual de um lançamento de Ativo ou Passivo.

    Args:
        id_transacao: ID da transação a atualizar.
        novo_saldo: Novo saldo vigente.
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE transacoes SET saldo_atual = ? WHERE id = ?",
            (novo_saldo, id_transacao),
        )
        conn.commit()


def buscar_por_id(id_transacao: int) -> Transacao | None:
    """Busca uma transação pelo ID.

    Args:
        id_transacao: ID da transação.

    Returns:
        Objeto Transacao ou None se não encontrado.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM transacoes WHERE id = ?", (id_transacao,)
        ).fetchone()
    return _row_para_transacao(row) if row else None


def listar_por_mes(
    ano: int, mes: int,
    ordenar_por: str = "data", decrescente: bool = True,
    filtro_tipo: str = None, filtro_categoria: str = None,
) -> list[Transacao]:
    """Retorna transações de Receita/Despesa de um mês específico.

    Args:
        ano: Ano de referência (ex: 2024).
        mes: Mês de referência (1-12).
        ordenar_por: Nome da coluna para ordenação.
        decrescente: Se True, ordena do maior para o menor.
        filtro_tipo: 'receita', 'despesa' ou None (sem filtro).
        filtro_categoria: Nome do item ou None (sem filtro).

    Returns:
        Lista de Transacao ordenada conforme parâmetros.
    """
    periodo = f"{ano}-{mes:02d}"
    coluna = COLUNAS_ORDENAVEIS.get(ordenar_por, "data")
    direcao = "DESC" if decrescente else "ASC"

    condicoes = ["strftime('%Y-%m', data) = ?", "tipo IN ('receita', 'despesa')"]
    params = [periodo]
    if filtro_tipo:
        condicoes.append("tipo = ?")
        params.append(filtro_tipo)
    if filtro_categoria:
        condicoes.append("categoria = ?")
        params.append(filtro_categoria)

    where_sql = " AND ".join(condicoes)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM transacoes
            WHERE {where_sql}
            ORDER BY {coluna} {direcao}, id DESC
            """,
            params,
        ).fetchall()
    return [_row_para_transacao(r) for r in rows]


def listar_ativos_passivos(
    ordenar_por: str = "data", decrescente: bool = True,
    filtro_tipo: str = None, filtro_categoria: str = None,
) -> list[Transacao]:
    """Retorna todos os lançamentos de Ativo/Passivo (posição atual).

    Não é filtrado por mês: representa a posição patrimonial vigente.

    Args:
        ordenar_por: Nome da coluna para ordenação.
        decrescente: Se True, ordena do maior para o menor.
        filtro_tipo: 'ativo', 'passivo' ou None (sem filtro).
        filtro_categoria: Nome do item ou None (sem filtro).

    Returns:
        Lista de Transacao ordenada conforme parâmetros.
    """
    coluna = COLUNAS_ORDENAVEIS.get(ordenar_por, "data")
    direcao = "DESC" if decrescente else "ASC"

    condicoes = ["tipo IN ('ativo', 'passivo')"]
    params = []
    if filtro_tipo:
        condicoes.append("tipo = ?")
        params.append(filtro_tipo)
    if filtro_categoria:
        condicoes.append("categoria = ?")
        params.append(filtro_categoria)

    where_sql = " AND ".join(condicoes)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM transacoes
            WHERE {where_sql}
            ORDER BY {coluna} {direcao}, id DESC
            """,
            params,
        ).fetchall()
    return [_row_para_transacao(r) for r in rows]


def listar_por_periodo(data_inicio: str, data_fim: str) -> list[Transacao]:
    """Retorna transações dentro de um intervalo de datas.

    Args:
        data_inicio: Data inicial no formato YYYY-MM-DD.
        data_fim: Data final no formato YYYY-MM-DD.

    Returns:
        Lista de Transacao ordenada por data.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM transacoes
            WHERE data BETWEEN ? AND ?
            ORDER BY data ASC
            """,
            (data_inicio, data_fim),
        ).fetchall()
    return [_row_para_transacao(r) for r in rows]


def listar_meses_disponiveis() -> list[tuple[int, int]]:
    """Retorna todos os meses/anos que possuem transações de DRE registradas.

    Returns:
        Lista de tuplas (ano, mes) ordenada cronologicamente.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT
                CAST(strftime('%Y', data) AS INTEGER) AS ano,
                CAST(strftime('%m', data) AS INTEGER) AS mes
            FROM transacoes
            WHERE tipo IN ('receita', 'despesa')
            ORDER BY ano ASC, mes ASC
            """
        ).fetchall()
    return [(r["ano"], r["mes"]) for r in rows]


def _row_para_transacao(row: object) -> Transacao:
    """Converte uma linha do banco em objeto Transacao.

    Args:
        row: Linha retornada pelo sqlite3 com row_factory.

    Returns:
        Objeto Transacao populado.
    """
    chaves = row.keys()
    return Transacao(
        id=row["id"],
        data=row["data"],
        descricao=row["descricao"],
        valor=row["valor"],
        tipo=row["tipo"],
        categoria=row["categoria"],
        saldo_atual=row["saldo_atual"] if "saldo_atual" in chaves else None,
        vinculo_id=row["vinculo_id"] if "vinculo_id" in chaves else None,
        forma_pagamento=row["forma_pagamento"] if "forma_pagamento" in chaves else None,
    )

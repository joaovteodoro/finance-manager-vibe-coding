"""
Serviço de cálculo do DRE e seus índices financeiros.

Toda lógica de negócio do DRE está centralizada aqui.
A UI apenas consome os dicionários retornados por este módulo.

Lógica de classificação automática:
    Resultado Operacional = Receita - Despesas Operacionais (dia a dia)
    Resultado Líquido = Resultado Operacional - Despesas Não Operacionais
    (eventos extraordinários: multas, impostos extras, perdas)

O usuário nunca escolhe "operacional ou não operacional" — isso é
inferido automaticamente a partir do item escolhido em Categoria
(ver models/categoria.py).
"""

from models import categoria as cat
from models.transacao import Transacao
from repositories import transacao_repo


def calcular_dre(ano: int, mes: int) -> dict:
    """Calcula o DRE completo para um mês/ano específico.

    Args:
        ano: Ano de referência.
        mes: Mês de referência (1-12).

    Returns:
        Dicionário com receitas, despesas por categoria (separadas em
        operacionais e não operacionais), resultados e índices.
    """
    transacoes = transacao_repo.listar_por_mes(ano, mes)
    receita_bruta = _somar_por_tipo(transacoes, "receita")

    despesas_oper = _agrupar_despesas(transacoes, operacional=True)
    despesas_nao_oper = _agrupar_despesas(transacoes, operacional=False)
    total_oper = sum(despesas_oper.values())
    total_nao_oper = sum(despesas_nao_oper.values())
    total_despesas = total_oper + total_nao_oper

    resultado_operacional = receita_bruta - total_oper
    resultado_liquido = resultado_operacional - total_nao_oper

    indices = _calcular_indices_dre(
        receita_bruta, despesas_oper, total_oper, total_despesas, ano, mes
    )

    return {
        "receita_bruta": receita_bruta,
        "despesas_operacionais": despesas_oper,
        "despesas_nao_operacionais": despesas_nao_oper,
        "despesas": {**despesas_oper, **despesas_nao_oper},  # compat. p/ Excel
        "total_operacional": total_oper,
        "total_nao_operacional": total_nao_oper,
        "total_despesas": total_despesas,
        "resultado_operacional": resultado_operacional,
        "resultado_liquido": resultado_liquido,
        "indices": indices,
        "ano": ano,
        "mes": mes,
    }


def _somar_por_tipo(transacoes: list[Transacao], tipo: str) -> float:
    """Soma os valores das transações de um tipo específico.

    Args:
        transacoes: Lista de transações.
        tipo: 'receita', 'despesa', 'ativo' ou 'passivo'.

    Returns:
        Soma dos valores.
    """
    return sum(t.valor for t in transacoes if t.tipo == tipo)


def _agrupar_despesas(
    transacoes: list[Transacao], operacional: bool
) -> dict[str, float]:
    """Agrupa o total de despesas por categoria, filtrando por tipo.

    Args:
        transacoes: Lista de transações.
        operacional: Se True, retorna apenas despesas operacionais;
            se False, retorna apenas despesas não operacionais.

    Returns:
        Dicionário {categoria: total}.
    """
    agrupado: dict[str, float] = {}
    for t in transacoes:
        if t.tipo != "despesa":
            continue
        if cat.eh_operacional(t.categoria) != operacional:
            continue
        agrupado[t.categoria] = agrupado.get(t.categoria, 0.0) + t.valor
    return agrupado


def _calcular_indices_dre(
    receita_bruta: float,
    despesas_oper: dict,
    total_oper: float,
    total_despesas: float,
    ano: int,
    mes: int,
) -> list[dict]:
    """Calcula os índices financeiros do DRE com interpretação automática.

    Args:
        receita_bruta: Total de receitas do período.
        despesas_oper: Dicionário de despesas operacionais por categoria.
        total_oper: Total de despesas operacionais.
        total_despesas: Total geral de despesas (oper. + não oper.).
        ano: Ano de referência.
        mes: Mês de referência.

    Returns:
        Lista de dicionários com nome, valor, status e interpretação.
    """
    indices = []

    margem_liq = (
        ((receita_bruta - total_despesas) / receita_bruta * 100)
        if receita_bruta > 0 else 0.0
    )
    indices.append({
        "nome": "Margem Líquida",
        "valor": margem_liq,
        "unidade": "%",
        "benchmark": "Ideal > 20%",
        **_status_margem_liquida(margem_liq),
    })

    taxa_poupanca = (
        ((receita_bruta - total_oper) / receita_bruta * 100)
        if receita_bruta > 0 else 0.0
    )
    indices.append({
        "nome": "Taxa de Poupança",
        "valor": taxa_poupanca,
        "unidade": "%",
        "benchmark": "Ideal > 20%",
        **_status_taxa_poupanca(taxa_poupanca),
    })

    despesas_fixas_total = sum(
        despesas_oper.get(c, 0.0) for c in cat.despesas_fixas()
    )
    comprometimento = (
        (despesas_fixas_total / receita_bruta * 100) if receita_bruta > 0 else 0.0
    )
    indices.append({
        "nome": "Comprometimento de Renda",
        "valor": comprometimento,
        "unidade": "%",
        "benchmark": "Ideal < 50%",
        **_status_comprometimento(comprometimento),
    })

    despesas_var_total = sum(
        despesas_oper.get(c, 0.0) for c in cat.despesas_variaveis()
    )
    idx_var = (
        (despesas_var_total / receita_bruta * 100) if receita_bruta > 0 else 0.0
    )
    indices.append({
        "nome": "Despesas Variáveis",
        "valor": idx_var,
        "unidade": "%",
        "benchmark": "Ideal < 30%",
        **_status_despesas_variaveis(idx_var),
    })

    caixa_atual = _calcular_caixa_acumulado(ano, mes)
    media_despesas = _calcular_media_despesas_mensais(ano, mes)
    cobertura = (
        (caixa_atual / media_despesas) if media_despesas > 0 else 0.0
    )
    indices.append({
        "nome": "Cobertura de Emergência",
        "valor": cobertura,
        "unidade": " meses",
        "benchmark": "Ideal ≥ 6 meses",
        **_status_cobertura(cobertura),
    })

    return indices


def _calcular_caixa_acumulado(ano: int, mes: int) -> float:
    """Calcula o saldo de caixa (Ativo Circulante) acumulado até o mês.

    Receitas aumentam o caixa; despesas reduzem; lançamentos de Ativo
    Não Circulante e Passivo não afetam o caixa diretamente.

    Args:
        ano: Ano de referência.
        mes: Mês de referência.

    Returns:
        Saldo acumulado em reais (mínimo zero).
    """
    data_fim = f"{ano}-{mes:02d}-31"
    transacoes = transacao_repo.listar_por_periodo("2000-01-01", data_fim)
    caixa = 0.0
    for t in transacoes:
        if t.tipo == "receita":
            caixa += t.valor
        elif t.tipo == "despesa":
            caixa -= t.valor
    return max(caixa, 0.0)


def _calcular_media_despesas_mensais(ano: int, mes: int) -> float:
    """Calcula a média mensal de despesas operacionais dos últimos 3 meses.

    Args:
        ano: Ano de referência.
        mes: Mês de referência.

    Returns:
        Média de despesas mensais.
    """
    totais = []
    for i in range(1, 4):
        m = mes - i
        a = ano
        if m <= 0:
            m += 12
            a -= 1
        transacoes = transacao_repo.listar_por_mes(a, m)
        total = sum(
            t.valor for t in transacoes
            if t.tipo == "despesa" and cat.eh_operacional(t.categoria)
        )
        if total > 0:
            totais.append(total)
    return sum(totais) / len(totais) if totais else 0.0


def _status_margem_liquida(valor: float) -> dict:
    if valor >= 20:
        return {"status": "ok", "icone": "✅", "interpretacao": f"Margem de {valor:.1f}% — excelente! Você está guardando mais do que gasta."}
    if valor >= 5:
        return {"status": "atencao", "icone": "⚠️", "interpretacao": f"Margem de {valor:.1f}% — atenção. Revise despesas para alcançar 20%."}
    return {"status": "critico", "icone": "🔴", "interpretacao": f"Margem de {valor:.1f}% — crítico. Suas despesas estão consumindo quase toda a renda."}


def _status_taxa_poupanca(valor: float) -> dict:
    if valor >= 20:
        return {"status": "ok", "icone": "✅", "interpretacao": f"Você está poupando {valor:.1f}% da renda — acima do recomendado de 20%."}
    if valor >= 10:
        return {"status": "atencao", "icone": "⚠️", "interpretacao": f"Taxa de poupança de {valor:.1f}% — abaixo do ideal. Tente reduzir despesas variáveis."}
    return {"status": "critico", "icone": "🔴", "interpretacao": f"Taxa de poupança de {valor:.1f}% — muito baixa. Revise seus gastos urgentemente."}


def _status_comprometimento(valor: float) -> dict:
    if valor <= 50:
        return {"status": "ok", "icone": "✅", "interpretacao": f"{valor:.1f}% da renda comprometida com fixos — dentro do limite saudável de 50%."}
    if valor <= 70:
        return {"status": "atencao", "icone": "⚠️", "interpretacao": f"{valor:.1f}% comprometida — pouca margem para imprevistos. Reduza custos fixos."}
    return {"status": "critico", "icone": "🔴", "interpretacao": f"{valor:.1f}% comprometida — risco alto. Seus custos fixos excedem a capacidade financeira."}


def _status_despesas_variaveis(valor: float) -> dict:
    if valor <= 30:
        return {"status": "ok", "icone": "✅", "interpretacao": f"Despesas variáveis em {valor:.1f}% — boa flexibilidade orçamentária."}
    if valor <= 50:
        return {"status": "atencao", "icone": "⚠️", "interpretacao": f"Despesas variáveis em {valor:.1f}% — revise lazer e alimentação."}
    return {"status": "critico", "icone": "🔴", "interpretacao": f"Despesas variáveis em {valor:.1f}% — consumo excessivo de renda variável."}


def _status_cobertura(valor: float) -> dict:
    if valor >= 6:
        return {"status": "ok", "icone": "✅", "interpretacao": f"Reserva para {valor:.1f} meses — excelente! Você tem uma boa reserva de emergência."}
    if valor >= 3:
        return {"status": "atencao", "icone": "⚠️", "interpretacao": f"Reserva para {valor:.1f} meses — tente chegar a 6 meses de despesas guardados."}
    return {"status": "critico", "icone": "🔴", "interpretacao": f"Reserva para {valor:.1f} meses — insuficiente. Priorize construir sua reserva de emergência."}

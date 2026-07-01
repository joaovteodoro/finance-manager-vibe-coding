"""
Serviço de cálculo e movimentação do Balanço Patrimonial.

Toda lógica contábil do Balanço está centralizada aqui, isolada do DRE.
Lançamentos de Ativo/Passivo nunca afetam o DRE, e vice-versa.

Regras de partida dobrada (a única automação de contrapartida do app):
    1. Novo Ativo Não Circulante pago À VISTA
       -> Ativo +X  /  Caixa -X (contrapartida: lançamento de despesa
          tipo 'ativo' interno que reduz o caixa, sem entrar no DRE)
    2. Novo Ativo Não Circulante FINANCIADO
       -> Ativo +X  /  Passivo +X (novo passivo vinculado, mesmo valor)
    3. Atualização do saldo devedor de um Passivo (saldo digitado
       manualmente pelo usuário)
       -> Passivo = novo valor  /  Patrimônio Líquido ajustado pela
          diferença (reduzir uma dívida sem mexer no caixa aumenta o PL)

O usuário não lança a contrapartida manualmente — o sistema cuida disso.
"""

import calendar as cal_module

from models import categoria as cat
from models.transacao import Transacao
from repositories import transacao_repo

# Item interno usado para representar a saída de caixa quando um
# Ativo Não Circulante é comprado à vista. Não aparece nos dropdowns
# de Lançamentos — é gerado automaticamente pelo sistema.
ITEM_SAIDA_CAIXA = "Saída de Caixa (compra de bem à vista)"


def lancar_ativo_nao_circulante(
    data: str, descricao: str, valor: float, categoria: str,
    forma_pagamento: str, nome_passivo_vinculado: str = None,
) -> dict:
    """Registra um novo Ativo Não Circulante com sua contrapartida automática.

    Args:
        data: Data do lançamento (YYYY-MM-DD).
        descricao: Descrição do bem/investimento.
        valor: Valor do ativo.
        categoria: Item do ativo (ex: "Imóvel", "Veículo").
        forma_pagamento: 'a_vista' ou 'financiado'.
        nome_passivo_vinculado: Descrição da dívida gerada, usada
            apenas quando forma_pagamento == 'financiado'.

    Returns:
        Dicionário com os IDs das transações criadas.

    Raises:
        ValueError: Se forma_pagamento for inválida ou faltar o nome
            do passivo vinculado quando financiado.
    """
    if forma_pagamento not in ("a_vista", "financiado"):
        raise ValueError("forma_pagamento deve ser 'a_vista' ou 'financiado'.")
    if forma_pagamento == "financiado" and not nome_passivo_vinculado:
        raise ValueError("Informe o nome do passivo vinculado ao financiamento.")

    id_ativo = transacao_repo.inserir(Transacao(
        data=data, descricao=descricao, valor=valor,
        tipo="ativo", categoria=categoria,
        saldo_atual=valor, forma_pagamento=forma_pagamento,
    ))

    if forma_pagamento == "a_vista":
        id_contrapartida = transacao_repo.inserir(Transacao(
            data=data, descricao=f"Saída de caixa — {descricao}",
            valor=valor, tipo="ativo", categoria=ITEM_SAIDA_CAIXA,
            saldo_atual=-valor,
        ))
    else:
        id_contrapartida = transacao_repo.inserir(Transacao(
            data=data, descricao=nome_passivo_vinculado, valor=valor,
            tipo="passivo", categoria="Financiamento (Imóvel/Veículo)",
            saldo_atual=valor,
        ))

    transacao_repo.vincular(id_ativo, id_contrapartida)
    return {"id_ativo": id_ativo, "id_contrapartida": id_contrapartida}


def lancar_ativo_circulante_ou_passivo_simples(
    data: str, descricao: str, valor: float, categoria: str,
) -> int:
    """Registra um lançamento simples de Passivo (sem contrapartida automática).

    Usado quando o usuário lança uma dívida diretamente (ex: "peguei
    um empréstimo"), sem estar atrelada à compra de um Ativo Não
    Circulante específico no mesmo momento.

    Args:
        data: Data do lançamento (YYYY-MM-DD).
        descricao: Descrição da dívida.
        valor: Valor da dívida.
        categoria: Item do passivo (ex: "Empréstimo").

    Returns:
        ID da transação criada.
    """
    return transacao_repo.inserir(Transacao(
        data=data, descricao=descricao, valor=valor,
        tipo="passivo", categoria=categoria, saldo_atual=valor,
    ))


def atualizar_saldo_devedor(id_passivo: int, novo_saldo: float) -> dict:
    """Atualiza o saldo devedor de um Passivo, ajustando o PL como contrapartida.

    Reduzir uma dívida sem reduzir o caixa aumenta o Patrimônio Líquido
    (Ativo = Passivo + PL precisa continuar batendo). Como o PL não é
    um lançamento e sim um valor calculado (Ativo - Passivo), a
    "contrapartida" aqui é puramente o efeito do novo saldo no cálculo
    — não é necessário criar uma transação nova.

    Args:
        id_passivo: ID do lançamento de Passivo a atualizar.
        novo_saldo: Novo saldo devedor total (digitado pelo usuário).

    Returns:
        Dicionário com saldo anterior, novo saldo e a diferença.

    Raises:
        ValueError: Se a transação não existir, não for um Passivo,
            ou o novo saldo for negativo.
    """
    transacao = transacao_repo.buscar_por_id(id_passivo)
    if transacao is None or transacao.tipo != "passivo":
        raise ValueError("Transação informada não é um Passivo válido.")
    if novo_saldo < 0:
        raise ValueError("O saldo devedor não pode ser negativo.")

    saldo_anterior = transacao.saldo_atual
    transacao_repo.atualizar_saldo(id_passivo, novo_saldo)
    return {
        "saldo_anterior": saldo_anterior,
        "saldo_novo": novo_saldo,
        "diferenca": novo_saldo - saldo_anterior,
    }


def calcular_balanco(ano: int, mes: int) -> dict:
    """Calcula o Balanço Patrimonial completo até o mês de referência.

    Args:
        ano: Ano de referência.
        mes: Mês de referência (1-12).

    Returns:
        Dicionário com ativo circulante/não circulante, passivo,
        patrimônio líquido, detalhamento por item e índices.
    """
    data_fim = f"{ano}-{mes:02d}-31"
    transacoes = transacao_repo.listar_por_periodo("2000-01-01", data_fim)

    caixa = _calcular_caixa(transacoes)
    ativo_nao_circulante, itens_anc = _calcular_ativo_nao_circulante(transacoes)
    ativo_total = caixa + ativo_nao_circulante

    passivo_total, itens_passivo = _calcular_passivo(transacoes)
    pl = ativo_total - passivo_total

    indices = _calcular_indices_balanco(
        caixa, ativo_nao_circulante, ativo_total, passivo_total, pl, ano, mes
    )
    evolucao = _calcular_evolucao_pl(ano, mes)

    return {
        "caixa": caixa,
        "investimentos": ativo_nao_circulante,
        "itens_ativo_nao_circulante": itens_anc,
        "ativo_total": ativo_total,
        "dividas": passivo_total,
        "itens_passivo": itens_passivo,
        "patrimonio_liquido": pl,
        "passivo_total": passivo_total + pl,
        "indices": indices,
        "evolucao_pl": evolucao,
        "ano": ano,
        "mes": mes,
    }


def _calcular_caixa(transacoes: list) -> float:
    """Calcula o saldo de caixa (Ativo Circulante) a partir das transações.

    Receitas/despesas (DRE) movem o caixa normalmente. Lançamentos de
    Ativo com categoria ITEM_SAIDA_CAIXA também reduzem o caixa
    (contrapartida de compra à vista).

    Args:
        transacoes: Lista de todas as transações até o período.

    Returns:
        Saldo de caixa em reais (mínimo zero).
    """
    caixa = 0.0
    for t in transacoes:
        if t.tipo == "receita":
            caixa += t.valor
        elif t.tipo == "despesa":
            caixa -= t.valor
        elif t.tipo == "ativo" and t.categoria == ITEM_SAIDA_CAIXA:
            caixa += t.saldo_atual  # já é negativo
    return max(caixa, 0.0)


def _calcular_ativo_nao_circulante(transacoes: list) -> tuple[float, dict]:
    """Soma os lançamentos de Ativo Não Circulante (saldo atual), por item.

    Exclui o item interno de saída de caixa, que é só contrapartida.

    Args:
        transacoes: Lista de transações.

    Returns:
        Tupla (total, {item: total}).
    """
    itens: dict[str, float] = {}
    for t in transacoes:
        if t.tipo == "ativo" and t.categoria != ITEM_SAIDA_CAIXA:
            itens[t.categoria] = itens.get(t.categoria, 0.0) + t.saldo_atual
    return sum(itens.values()), itens


def _calcular_passivo(transacoes: list) -> tuple[float, dict]:
    """Soma os lançamentos de Passivo (saldo atual), agrupados por item.

    Args:
        transacoes: Lista de transações.

    Returns:
        Tupla (total, {item: total}).
    """
    itens: dict[str, float] = {}
    for t in transacoes:
        if t.tipo == "passivo":
            itens[t.categoria] = itens.get(t.categoria, 0.0) + t.saldo_atual
    return sum(itens.values()), itens


def _calcular_pl_em(ano: int, mes: int) -> float:
    """Calcula o Patrimônio Líquido acumulado até um mês específico.

    Args:
        ano: Ano de referência.
        mes: Mês de referência.

    Returns:
        Patrimônio Líquido (Ativo Total - Passivo Total).
    """
    data_fim = f"{ano}-{mes:02d}-31"
    transacoes = transacao_repo.listar_por_periodo("2000-01-01", data_fim)
    caixa = _calcular_caixa(transacoes)
    anc, _ = _calcular_ativo_nao_circulante(transacoes)
    passivo, _ = _calcular_passivo(transacoes)
    return (caixa + anc) - passivo


def _calcular_evolucao_pl(ano: int, mes: int) -> list[dict]:
    """Calcula a evolução do PL nos últimos 12 meses.

    Args:
        ano: Ano de referência.
        mes: Mês de referência.

    Returns:
        Lista de dicionários {label, pl} para o gráfico de linha.
    """
    evolucao = []
    for i in range(11, -1, -1):
        m = mes - i
        a = ano
        while m <= 0:
            m += 12
            a -= 1
        pl = _calcular_pl_em(a, m)
        label = f"{cal_module.month_abbr[m]}/{str(a)[2:]}"
        evolucao.append({"label": label, "pl": pl})
    return evolucao


def _calcular_indices_balanco(
    caixa: float,
    ativo_nao_circulante: float,
    ativo_total: float,
    passivo_total: float,
    pl: float,
    ano: int,
    mes: int,
) -> list[dict]:
    """Calcula os índices financeiros do Balanço com interpretação automática.

    Args:
        caixa: Saldo de caixa atual (Ativo Circulante).
        ativo_nao_circulante: Total em bens e investimentos (saldo atual).
        ativo_total: Soma de caixa + ativo não circulante.
        passivo_total: Total de dívidas (saldo atual).
        pl: Patrimônio Líquido acumulado.
        ano: Ano de referência.
        mes: Mês de referência.

    Returns:
        Lista de dicionários com nome, valor, status e interpretação.
    """
    indices = []

    liq = (caixa / passivo_total) if passivo_total > 0 else None
    indices.append(_indice_liquidez(liq))

    endiv = (passivo_total / pl * 100) if pl > 0 else None
    indices.append(_indice_endividamento(endiv))

    inv_pl = (ativo_nao_circulante / pl * 100) if pl > 0 else None
    indices.append(_indice_investimento_pl(inv_pl))

    pl_anterior = _calcular_pl_em_mes_anterior(ano, mes)
    evolucao_pct = (
        ((pl - pl_anterior) / abs(pl_anterior) * 100)
        if pl_anterior != 0 else None
    )
    indices.append(_indice_evolucao_pl(evolucao_pct))

    ativo_prod = (
        (ativo_nao_circulante / ativo_total * 100) if ativo_total > 0 else None
    )
    indices.append(_indice_ativo_produtivo(ativo_prod))

    return indices


def _calcular_pl_em_mes_anterior(ano: int, mes: int) -> float:
    """Calcula o PL acumulado até o mês anterior ao de referência.

    Args:
        ano: Ano de referência.
        mes: Mês de referência.

    Returns:
        PL do mês anterior.
    """
    m = mes - 1
    a = ano
    if m <= 0:
        m = 12
        a -= 1
    return _calcular_pl_em(a, m)


def _indice_liquidez(valor) -> dict:
    if valor is None:
        return {"nome": "Liquidez Imediata", "valor": None, "unidade": "x", "benchmark": "Ideal > 1,0", "status": "na", "icone": "➖", "interpretacao": "Sem dívidas lançadas — índice não aplicável."}
    if valor >= 1:
        return {"nome": "Liquidez Imediata", "valor": valor, "unidade": "x", "benchmark": "Ideal > 1,0", "status": "ok", "icone": "✅", "interpretacao": f"Liquidez de {valor:.2f}x — você tem caixa suficiente para quitar todas as dívidas."}
    return {"nome": "Liquidez Imediata", "valor": valor, "unidade": "x", "benchmark": "Ideal > 1,0", "status": "critico", "icone": "🔴", "interpretacao": f"Liquidez de {valor:.2f}x — seu caixa não cobre as dívidas atuais."}


def _indice_endividamento(valor) -> dict:
    if valor is None:
        return {"nome": "Índice de Endividamento", "valor": None, "unidade": "%", "benchmark": "Ideal < 30%", "status": "na", "icone": "➖", "interpretacao": "Patrimônio Líquido zerado ou negativo — registre mais movimentações."}
    if valor <= 30:
        return {"nome": "Índice de Endividamento", "valor": valor, "unidade": "%", "benchmark": "Ideal < 30%", "status": "ok", "icone": "✅", "interpretacao": f"{valor:.1f}% do patrimônio comprometido com dívidas — nível saudável."}
    if valor <= 60:
        return {"nome": "Índice de Endividamento", "valor": valor, "unidade": "%", "benchmark": "Ideal < 30%", "status": "atencao", "icone": "⚠️", "interpretacao": f"{valor:.1f}% comprometido — atenção. Priorize a quitação das dívidas."}
    return {"nome": "Índice de Endividamento", "valor": valor, "unidade": "%", "benchmark": "Ideal < 30%", "status": "critico", "icone": "🔴", "interpretacao": f"{valor:.1f}% comprometido — endividamento crítico. Busque renegociação."}


def _indice_investimento_pl(valor) -> dict:
    if valor is None:
        return {"nome": "Investimento / Patrimônio", "valor": None, "unidade": "%", "benchmark": "Ideal > 20%", "status": "na", "icone": "➖", "interpretacao": "Sem dados suficientes para calcular."}
    if valor >= 20:
        return {"nome": "Investimento / Patrimônio", "valor": valor, "unidade": "%", "benchmark": "Ideal > 20%", "status": "ok", "icone": "✅", "interpretacao": f"{valor:.1f}% do patrimônio está em bens/investimentos — seu dinheiro está trabalhando."}
    if valor >= 5:
        return {"nome": "Investimento / Patrimônio", "valor": valor, "unidade": "%", "benchmark": "Ideal > 20%", "status": "atencao", "icone": "⚠️", "interpretacao": f"Apenas {valor:.1f}% investido. Tente aumentar aportes mensais."}
    return {"nome": "Investimento / Patrimônio", "valor": valor, "unidade": "%", "benchmark": "Ideal > 20%", "status": "critico", "icone": "🔴", "interpretacao": f"Somente {valor:.1f}% do patrimônio está investido — priorize investir."}


def _indice_evolucao_pl(valor) -> dict:
    if valor is None:
        return {"nome": "Evolução do Patrimônio", "valor": None, "unidade": "%", "benchmark": "Ideal > 0%", "status": "na", "icone": "➖", "interpretacao": "Sem histórico anterior para comparar."}
    if valor > 0:
        return {"nome": "Evolução do Patrimônio", "valor": valor, "unidade": "%", "benchmark": "Ideal > 0%", "status": "ok", "icone": "✅", "interpretacao": f"Patrimônio cresceu {valor:.1f}% em relação ao mês anterior — trajetória positiva."}
    return {"nome": "Evolução do Patrimônio", "valor": valor, "unidade": "%", "benchmark": "Ideal > 0%", "status": "critico", "icone": "🔴", "interpretacao": f"Patrimônio reduziu {abs(valor):.1f}% — revise suas finanças este mês."}


def _indice_ativo_produtivo(valor) -> dict:
    if valor is None:
        return {"nome": "Ativo Produtivo / Total", "valor": None, "unidade": "%", "benchmark": "Ideal > 30%", "status": "na", "icone": "➖", "interpretacao": "Sem ativo registrado para calcular."}
    if valor >= 30:
        return {"nome": "Ativo Produtivo / Total", "valor": valor, "unidade": "%", "benchmark": "Ideal > 30%", "status": "ok", "icone": "✅", "interpretacao": f"{valor:.1f}% do ativo está em bens/investimentos — boa alocação produtiva."}
    if valor >= 10:
        return {"nome": "Ativo Produtivo / Total", "valor": valor, "unidade": "%", "benchmark": "Ideal > 30%", "status": "atencao", "icone": "⚠️", "interpretacao": f"{valor:.1f}% produtivo — maior parte do dinheiro ainda está parada no caixa."}
    return {"nome": "Ativo Produtivo / Total", "valor": valor, "unidade": "%", "benchmark": "Ideal > 30%", "status": "critico", "icone": "🔴", "interpretacao": f"Apenas {valor:.1f}% do ativo é produtivo — seu dinheiro não está rendendo."}

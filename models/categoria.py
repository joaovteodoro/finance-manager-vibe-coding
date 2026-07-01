"""
Mapa de itens de lançamento e sua classificação contábil interna.

O usuário NUNCA escolhe um "grupo contábil" — ele só escolhe um Item
(ex: "Imóvel", "Salário", "Empréstimo"). O sistema infere sozinho,
a partir deste mapa, se o item pertence ao DRE (receita/despesa) ou
ao Balanço Patrimonial (ativo/passivo), e sua subclassificação.

Há dois dropdowns de Item na aplicação, cada um filtrado por domínio:
    - Subaba "Receitas e Despesas": apenas itens de DRE
    - Subaba "Ativos e Passivos": apenas itens de Balanço
"""

from enum import Enum


class Grupo(str, Enum):
    """Grupos contábeis usados internamente para classificar lançamentos."""

    RECEITA_OPERACIONAL = "Receita Operacional"
    DESPESA_OPERACIONAL = "Despesa Operacional"
    DESPESA_NAO_OPERACIONAL = "Despesa Não Operacional"
    ATIVO_NAO_CIRCULANTE = "Ativo Não Circulante"
    PASSIVO = "Passivo"


# Mapa de cada item visível ao usuário -> grupo contábil correspondente.
MAPA_CATEGORIAS: dict[str, Grupo] = {
    # Receita Operacional
    "Salário": Grupo.RECEITA_OPERACIONAL,
    "Freelance / Renda Extra": Grupo.RECEITA_OPERACIONAL,
    "Rendimento de Investimento": Grupo.RECEITA_OPERACIONAL,

    # Despesa Operacional — gastos do dia a dia (entram no Resultado Operacional)
    "Alimentação": Grupo.DESPESA_OPERACIONAL,
    "Moradia": Grupo.DESPESA_OPERACIONAL,
    "Transporte": Grupo.DESPESA_OPERACIONAL,
    "Saúde": Grupo.DESPESA_OPERACIONAL,
    "Lazer": Grupo.DESPESA_OPERACIONAL,
    "Parcela de Empréstimo/Financiamento": Grupo.DESPESA_OPERACIONAL,
    "Outros Gastos do Dia a Dia": Grupo.DESPESA_OPERACIONAL,

    # Despesa Não Operacional — gastos eventuais (só afetam o Resultado Líquido)
    "Multas e Juros": Grupo.DESPESA_NAO_OPERACIONAL,
    "Imposto / Taxa Extraordinária": Grupo.DESPESA_NAO_OPERACIONAL,
    "Perda ou Prejuízo Eventual": Grupo.DESPESA_NAO_OPERACIONAL,

    # Ativo Não Circulante — bens e investimentos de longo prazo
    "Imóvel": Grupo.ATIVO_NAO_CIRCULANTE,
    "Veículo": Grupo.ATIVO_NAO_CIRCULANTE,
    "Investimento (Ações, Fundos, Tesouro)": Grupo.ATIVO_NAO_CIRCULANTE,
    "Outros Bens": Grupo.ATIVO_NAO_CIRCULANTE,

    # Passivo — dívidas e obrigações
    "Empréstimo": Grupo.PASSIVO,
    "Financiamento (Imóvel/Veículo)": Grupo.PASSIVO,
    "Cartão de Crédito (Fatura)": Grupo.PASSIVO,
    "Outras Dívidas": Grupo.PASSIVO,
}


def itens_dre() -> list[str]:
    """Retorna os itens de Receita/Despesa, para o dropdown da subaba DRE.

    Returns:
        Lista de nomes de itens (Receita Operacional + Despesas).
    """
    grupos_dre = (
        Grupo.RECEITA_OPERACIONAL,
        Grupo.DESPESA_OPERACIONAL,
        Grupo.DESPESA_NAO_OPERACIONAL,
    )
    return [item for item, g in MAPA_CATEGORIAS.items() if g in grupos_dre]


def itens_balanco() -> list[str]:
    """Retorna os itens de Ativo/Passivo, para o dropdown da subaba Balanço.

    Returns:
        Lista de nomes de itens (Ativo Não Circulante + Passivo).
    """
    grupos_bp = (Grupo.ATIVO_NAO_CIRCULANTE, Grupo.PASSIVO)
    return [item for item, g in MAPA_CATEGORIAS.items() if g in grupos_bp]


def grupo_da_categoria(categoria: str) -> Grupo:
    """Retorna o grupo contábil de um item.

    Args:
        categoria: Nome do item conforme escolhido pelo usuário.

    Returns:
        Grupo contábil correspondente. Fallback seguro:
        DESPESA_OPERACIONAL para itens não reconhecidos (dados legados).
    """
    return MAPA_CATEGORIAS.get(categoria, Grupo.DESPESA_OPERACIONAL)


def tipo_da_categoria(categoria: str) -> str:
    """Infere o tipo de lançamento (receita/despesa/ativo/passivo).

    Args:
        categoria: Nome do item conforme escolhido pelo usuário.

    Returns:
        'receita', 'despesa', 'ativo' ou 'passivo'.
    """
    grupo = grupo_da_categoria(categoria)
    if grupo == Grupo.RECEITA_OPERACIONAL:
        return "receita"
    if grupo in (Grupo.DESPESA_OPERACIONAL, Grupo.DESPESA_NAO_OPERACIONAL):
        return "despesa"
    if grupo == Grupo.ATIVO_NAO_CIRCULANTE:
        return "ativo"
    return "passivo"


def eh_operacional(categoria: str) -> bool:
    """Indica se uma despesa é operacional (afeta Resultado Operacional).

    Args:
        categoria: Nome do item conforme escolhido pelo usuário.

    Returns:
        True se for Despesa Operacional.
    """
    return grupo_da_categoria(categoria) == Grupo.DESPESA_OPERACIONAL


def despesas_fixas() -> list[str]:
    """Itens operacionais considerados despesas fixas (recorrência alta).

    Returns:
        Lista de nomes de itens.
    """
    return ["Moradia", "Saúde", "Transporte"]


def despesas_variaveis() -> list[str]:
    """Itens operacionais considerados despesas variáveis (discricionárias).

    Returns:
        Lista de nomes de itens.
    """
    return ["Alimentação", "Lazer", "Outros Gastos do Dia a Dia"]

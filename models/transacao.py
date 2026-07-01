"""Dataclass representando uma transação financeira."""

from dataclasses import dataclass, field


@dataclass
class Transacao:
    """Representa uma movimentação financeira ou um item patrimonial.

    Para tipo 'receita'/'despesa' (DRE): apenas `valor` é usado.
    Para tipo 'ativo'/'passivo' (Balanço): `valor` é o valor original
    do lançamento e `saldo_atual` é o saldo vigente (igual a `valor`
    na criação; pode ser atualizado depois, ex: ao abater uma dívida).

    Attributes:
        data: Data da transação no formato YYYY-MM-DD.
        descricao: Descrição textual da movimentação.
        valor: Valor original em reais (sempre positivo).
        tipo: 'receita', 'despesa', 'ativo' ou 'passivo'.
        categoria: Item específico do lançamento (ex: "Imóvel", "Salário").
        id: Identificador único gerado pelo banco (opcional).
        saldo_atual: Saldo vigente (apenas ativo/passivo). Igual a
            `valor` por padrão; é atualizado manualmente pelo usuário
            ao registrar pagamentos/abatimentos.
        vinculo_id: ID da transação de contrapartida automática
            (partida dobrada), quando aplicável. None caso não exista.
        forma_pagamento: 'a_vista' ou 'financiado' (apenas Ativo Não
            Circulante). None para os demais tipos.
    """

    data: str
    descricao: str
    valor: float
    tipo: str
    categoria: str
    id: int = field(default=0)
    saldo_atual: float = field(default=None)
    vinculo_id: int = field(default=None)
    forma_pagamento: str = field(default=None)

    def __post_init__(self) -> None:
        """Garante que saldo_atual comece igual a valor, se não informado."""
        if self.saldo_atual is None:
            self.saldo_atual = self.valor

    def valor_formatado(self) -> str:
        """Retorna o valor original formatado como moeda brasileira.

        Returns:
            String no formato 'R$ 1.234,56'.
        """
        return _formatar_moeda(self.valor)

    def saldo_formatado(self) -> str:
        """Retorna o saldo atual formatado como moeda brasileira.

        Returns:
            String no formato 'R$ 1.234,56'.
        """
        return _formatar_moeda(self.saldo_atual)

    def data_formatada(self) -> str:
        """Retorna a data no formato brasileiro DD/MM/YYYY.

        Returns:
            String no formato 'DD/MM/YYYY'.
        """
        partes = self.data.split("-")
        return f"{partes[2]}/{partes[1]}/{partes[0]}"


def _formatar_moeda(valor: float) -> str:
    """Formata um valor numérico como moeda brasileira.

    Args:
        valor: Valor a formatar.

    Returns:
        String no formato 'R$ 1.234,56'.
    """
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

"""
Aba de Lançamentos — layout de duas colunas.

Coluna esquerda (≈30%): formulário fixo e sempre visível.
    O formulário adapta seus campos dinamicamente conforme a subaba
    ativa na coluna direita (Receitas/Despesas ou Ativos/Passivos).

Coluna direita (≈70%): visualização com toggle entre as duas subabas.
    Cada subaba tem sua própria tabela, filtros e resumo.
    Não contém formulário próprio — delega ao formulário da esquerda.
"""

import customtkinter as ctk
from datetime import date, datetime

from models import categoria as cat
from models.transacao import Transacao
from repositories import transacao_repo
from services import balanco_service
from ui.sub_lancamentos_dre import SubAbaDRE
from ui.sub_lancamentos_bp import SubAbaBP


class TabLancamentos(ctk.CTkFrame):
    """Aba principal de Lançamentos com duas colunas."""

    def __init__(self, parent, cores: dict) -> None:
        """Inicializa o layout de duas colunas.

        Args:
            parent: Frame pai.
            cores: Paleta de cores da aplicação.
        """
        super().__init__(parent, fg_color=cores["fundo"])
        self.cores = cores
        self._subaba_ativa = "dre"

        self._construir_layout()

    def _construir_layout(self) -> None:
        """Divide a tela em coluna esquerda (formulário) e direita (visualização)."""
        # Coluna esquerda — formulário fixo
        self.col_esquerda = ctk.CTkFrame(
            self, fg_color=self.cores["card"], corner_radius=0, width=300
        )
        self.col_esquerda.pack(side="left", fill="y", padx=(0, 1))
        self.col_esquerda.pack_propagate(False)

        # Coluna direita — visualização com subabas
        self.col_direita = ctk.CTkFrame(
            self, fg_color=self.cores["fundo"], corner_radius=0
        )
        self.col_direita.pack(side="left", fill="both", expand=True)

        self._construir_formulario()
        self._construir_toggle_subabas()
        self._construir_subabas()
        self._alternar_subaba("dre")

    def _construir_formulario(self) -> None:
        """Constrói o formulário fixo na coluna esquerda."""
        pad = {"padx": 16}

        ctk.CTkLabel(
            self.col_esquerda, text="Novo Lançamento",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.cores["texto"]
        ).pack(anchor="w", pady=(20, 12), **pad)

        # Data
        ctk.CTkLabel(self.col_esquerda, text="Data",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w", **pad)
        self.campo_data = ctk.CTkEntry(
            self.col_esquerda, placeholder_text="DD/MM/AAAA"
        )
        self.campo_data.insert(0, date.today().strftime("%d/%m/%Y"))
        self.campo_data.pack(fill="x", pady=(0, 10), **pad)

        # Descrição
        ctk.CTkLabel(self.col_esquerda, text="Descrição",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w", **pad)
        self.campo_descricao = ctk.CTkEntry(
            self.col_esquerda, placeholder_text="Ex: Supermercado"
        )
        self.campo_descricao.pack(fill="x", pady=(0, 10), **pad)

        # Valor
        ctk.CTkLabel(self.col_esquerda, text="Valor (R$)",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w", **pad)
        self.campo_valor = ctk.CTkEntry(
            self.col_esquerda, placeholder_text="0,00"
        )
        self.campo_valor.pack(fill="x", pady=(0, 10), **pad)

        # Item — muda conforme subaba ativa
        ctk.CTkLabel(self.col_esquerda, text="Item",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w", **pad)
        self.campo_item = ctk.CTkComboBox(
            self.col_esquerda,
            values=cat.itens_dre(),
            fg_color=self.cores["fundo"],
            button_color=self.cores["azul"],
            dropdown_fg_color=self.cores["card"],
            command=lambda _: self._ao_mudar_item(),
        )
        self.campo_item.set(cat.itens_dre()[0])
        self.campo_item.pack(fill="x", pady=(0, 6), **pad)

        # Badge de feedback
        self.label_badge = ctk.CTkLabel(
            self.col_esquerda, text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.cores["texto_secundario"],
            wraplength=260, justify="left"
        )
        self.label_badge.pack(anchor="w", pady=(0, 8), **pad)

        # Frame condicional — "Como foi pago?" (só para Ativo NC)
        self.frame_pagamento = ctk.CTkFrame(
            self.col_esquerda, fg_color="transparent"
        )
        ctk.CTkLabel(self.frame_pagamento, text="Como foi pago?",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.var_pagamento = ctk.StringVar(value="a_vista")
        ctk.CTkRadioButton(
            self.frame_pagamento, text="À vista (sai do caixa)",
            variable=self.var_pagamento, value="a_vista",
            text_color=self.cores["texto"], fg_color=self.cores["azul"],
            command=self._ao_mudar_pagamento,
        ).pack(anchor="w", pady=(2, 2))
        ctk.CTkRadioButton(
            self.frame_pagamento, text="Financiado (vira dívida)",
            variable=self.var_pagamento, value="financiado",
            text_color=self.cores["texto"], fg_color=self.cores["azul"],
            command=self._ao_mudar_pagamento,
        ).pack(anchor="w")

        # Frame condicional — nome do passivo (só se financiado)
        self.frame_nome_passivo = ctk.CTkFrame(
            self.col_esquerda, fg_color="transparent"
        )
        ctk.CTkLabel(self.frame_nome_passivo, text="Nome da dívida gerada:",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.campo_nome_passivo = ctk.CTkEntry(
            self.frame_nome_passivo,
            placeholder_text="Ex: Financiamento do Apê"
        )
        self.campo_nome_passivo.pack(fill="x", pady=(4, 0))

        # Erro e botão salvar
        self.label_erro = ctk.CTkLabel(
            self.col_esquerda, text="",
            text_color=self.cores["despesa"], font=ctk.CTkFont(size=11),
            wraplength=260, justify="left"
        )
        self.label_erro.pack(anchor="w", **pad)

        self.btn_salvar = ctk.CTkButton(
            self.col_esquerda,
            text="💾  Salvar",
            fg_color=self.cores["azul"], hover_color="#4a8aee",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40, command=self._salvar
        )
        self.btn_salvar.pack(fill="x", pady=(8, 0), **pad)

        self.campo_descricao.bind("<Return>", lambda e: self._salvar())
        self.campo_valor.bind("<Return>", lambda e: self._salvar())
        self.campo_data.bind("<Return>", lambda e: self._salvar())
        self._ao_mudar_item()

    def _construir_toggle_subabas(self) -> None:
        """Constrói os botões de toggle no topo da coluna direita."""
        self.barra_toggle = ctk.CTkFrame(
            self.col_direita, fg_color=self.cores["card"],
            height=44, corner_radius=0
        )
        self.barra_toggle.pack(fill="x", side="top")
        self.barra_toggle.pack_propagate(False)

        self._btn_toggle: dict[str, ctk.CTkButton] = {}
        self._ind_toggle: dict[str, ctk.CTkFrame] = {}

        for label, chave in [
            ("💰  Receitas e Despesas", "dre"),
            ("🏛  Ativos e Passivos", "bp"),
        ]:
            wrap = ctk.CTkFrame(self.barra_toggle, fg_color="transparent")
            wrap.pack(side="left", fill="y", padx=2)

            btn = ctk.CTkButton(
                wrap, text=label, font=ctk.CTkFont(size=12),
                fg_color="transparent", hover_color=self.cores["fundo"],
                text_color=self.cores["texto_secundario"],
                height=38, corner_radius=0,
                command=lambda c=chave: self._alternar_subaba(c),
            )
            btn.pack(side="top", fill="x")

            ind = ctk.CTkFrame(wrap, fg_color=self.cores["receita"], height=3, corner_radius=0)
            ind.pack(side="bottom", fill="x")
            ind.pack_forget()

            self._btn_toggle[chave] = btn
            self._ind_toggle[chave] = ind

    def _construir_subabas(self) -> None:
        """Instancia as duas subabas de visualização na coluna direita."""
        self.area_subaba = ctk.CTkFrame(
            self.col_direita, fg_color=self.cores["fundo"], corner_radius=0
        )
        self.area_subaba.pack(fill="both", expand=True)

        self.subaba_dre = SubAbaDRE(self.area_subaba, self.cores)
        self.subaba_bp = SubAbaBP(self.area_subaba, self.cores)

    def _alternar_subaba(self, chave: str) -> None:
        """Troca a subaba visível e atualiza o formulário.

        Args:
            chave: 'dre' ou 'bp'.
        """
        self._subaba_ativa = chave

        self.subaba_dre.pack_forget()
        self.subaba_bp.pack_forget()

        for c, btn in self._btn_toggle.items():
            btn.configure(text_color=self.cores["texto_secundario"])
            self._ind_toggle[c].pack_forget()

        if chave == "dre":
            self.subaba_dre.pack(fill="both", expand=True)
        else:
            self.subaba_bp.pack(fill="both", expand=True)

        self._btn_toggle[chave].configure(text_color=self.cores["texto"])
        self._ind_toggle[chave].pack(side="bottom", fill="x")

        # Atualiza dropdown de Item conforme contexto
        if chave == "dre":
            itens = cat.itens_dre()
        else:
            itens = cat.itens_balanco()

        self.campo_item.configure(values=itens)
        self.campo_item.set(itens[0])
        self._ao_mudar_item()

    def _ao_mudar_item(self) -> None:
        """Atualiza badge e campos condicionais conforme o item selecionado."""
        item = self.campo_item.get()
        grupo = cat.grupo_da_categoria(item)

        # Badge
        if grupo == cat.Grupo.RECEITA_OPERACIONAL:
            txt, cor = "🟢 Vai entrar como Receita", self.cores["receita"]
        elif grupo == cat.Grupo.DESPESA_NAO_OPERACIONAL:
            txt, cor = "🟠 Despesa Extraordinária (eventual)", "#f59e0b"
        elif grupo == cat.Grupo.DESPESA_OPERACIONAL:
            txt, cor = "🔴 Despesa do dia a dia", self.cores["despesa"]
        elif grupo == cat.Grupo.ATIVO_NAO_CIRCULANTE:
            txt, cor = "🔵 Será adicionado como Bem/Investimento", self.cores["azul"]
        else:
            txt, cor = "🟣 Será adicionada como Dívida", "#a78bfa"

        self.label_badge.configure(text=txt, text_color=cor)

        # Campos condicionais
        eh_anc = grupo == cat.Grupo.ATIVO_NAO_CIRCULANTE
        if eh_anc:
            self.frame_pagamento.pack(anchor="w", padx=16, pady=(0, 6), fill="x")
            self._ao_mudar_pagamento()
        else:
            self.frame_pagamento.pack_forget()
            self.frame_nome_passivo.pack_forget()

    def _ao_mudar_pagamento(self) -> None:
        """Exibe ou oculta o campo de nome do passivo."""
        if self.var_pagamento.get() == "financiado":
            self.frame_nome_passivo.pack(anchor="w", padx=16, pady=(0, 6), fill="x")
        else:
            self.frame_nome_passivo.pack_forget()

    def _salvar(self) -> None:
        """Valida e persiste o lançamento, delegando ao service correto."""
        data_str = self.campo_data.get().strip()
        descricao = self.campo_descricao.get().strip()
        valor_str = self.campo_valor.get().strip().replace(",", ".")
        item = self.campo_item.get()
        grupo = cat.grupo_da_categoria(item)

        if not descricao:
            self._erro("Descrição é obrigatória.")
            return
        try:
            valor = float(valor_str)
            if valor <= 0:
                raise ValueError
        except ValueError:
            self._erro("Valor inválido (ex: 150,00).")
            return
        try:
            data_iso = datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            self._erro("Data inválida. Use DD/MM/AAAA.")
            return

        if grupo == cat.Grupo.ATIVO_NAO_CIRCULANTE:
            forma = self.var_pagamento.get()
            nome_passivo = self.campo_nome_passivo.get().strip()
            if forma == "financiado" and not nome_passivo:
                self._erro("Informe o nome da dívida gerada.")
                return
            try:
                balanco_service.lancar_ativo_nao_circulante(
                    data=data_iso, descricao=descricao, valor=valor,
                    categoria=item, forma_pagamento=forma,
                    nome_passivo_vinculado=nome_passivo if forma == "financiado" else None,
                )
            except ValueError as e:
                self._erro(str(e))
                return
        elif grupo == cat.Grupo.PASSIVO:
            balanco_service.lancar_ativo_circulante_ou_passivo_simples(
                data=data_iso, descricao=descricao, valor=valor, categoria=item
            )
        else:
            tipo = cat.tipo_da_categoria(item)
            transacao_repo.inserir(Transacao(
                data=data_iso, descricao=descricao,
                valor=valor, tipo=tipo, categoria=item
            ))

        # Reset do formulário
        self.campo_descricao.delete(0, "end")
        self.campo_valor.delete(0, "end")
        self.campo_nome_passivo.delete(0, "end")
        self.label_erro.configure(text="")
        self.campo_descricao.focus()

        # Atualiza a subaba visível
        if self._subaba_ativa == "dre":
            self.subaba_dre._atualizar_tudo()
        else:
            self.subaba_bp._atualizar_tudo()

    def _erro(self, msg: str) -> None:
        """Exibe mensagem de erro no formulário.

        Args:
            msg: Texto do erro.
        """
        self.label_erro.configure(text=f"⚠ {msg}")

"""
Subaba "Receitas e Despesas" — apenas visualização.

O formulário de lançamento vive na coluna esquerda de TabLancamentos.
Esta subaba é responsável apenas por exibir a tabela de transações
do mês, com resumo, filtros e ordenação por coluna.
"""

import calendar
import customtkinter as ctk
from tkinter import ttk

from repositories import transacao_repo
from models import categoria as cat


class SubAbaDRE(ctk.CTkFrame):
    """Subaba de visualização de Receitas e Despesas."""

    def __init__(self, parent, cores: dict) -> None:
        """Inicializa a subaba de visualização.

        Args:
            parent: Frame pai.
            cores: Paleta de cores da aplicação.
        """
        super().__init__(parent, fg_color=cores["fundo"])
        self.cores = cores
        from datetime import date
        hoje = date.today()
        self.mes_atual = hoje.month
        self.ano_atual = hoje.year
        self.ordenar_por = "data"
        self.ordem_decrescente = True
        self.filtro_tipo = "Todos"
        self.filtro_categoria = "Todas"

        self._construir_resumo()
        self._construir_filtros()
        self._construir_tabela()
        self._atualizar_tudo()

    def _construir_resumo(self) -> None:
        """Constrói a navegação de mês e os cards de resumo."""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=(12, 6))

        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(side="left")
        ctk.CTkButton(nav, text="◀", width=32, fg_color=self.cores["card"],
                      command=self._mes_anterior).pack(side="left", padx=(0, 4))
        self.label_mes = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.cores["texto"], width=130
        )
        self.label_mes.pack(side="left")
        ctk.CTkButton(nav, text="▶", width=32, fg_color=self.cores["card"],
                      command=self._mes_proximo).pack(side="left", padx=(4, 16))

        for attr, label, cor in [
            ("card_receitas", "Receitas", self.cores["receita"]),
            ("card_despesas", "Despesas", self.cores["despesa"]),
            ("card_saldo", "Saldo", self.cores["azul"]),
        ]:
            c = ctk.CTkFrame(frame, fg_color=self.cores["card"], corner_radius=8)
            c.pack(side="left", padx=6, ipady=6, ipadx=10)
            ctk.CTkLabel(c, text=label, font=ctk.CTkFont(size=11),
                         text_color=self.cores["texto_secundario"]).pack()
            lbl = ctk.CTkLabel(c, text="R$ 0,00",
                               font=ctk.CTkFont(size=14, weight="bold"),
                               text_color=cor)
            lbl.pack()
            setattr(self, attr, lbl)

    def _construir_filtros(self) -> None:
        """Constrói os dropdowns de filtro por Tipo e Categoria."""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(frame, text="Filtrar:",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 6))

        self.combo_tipo = ctk.CTkComboBox(
            frame, values=["Todos", "Receita", "Despesa"], width=120,
            fg_color=self.cores["card"], button_color=self.cores["azul"],
            command=self._ao_filtrar
        )
        self.combo_tipo.set("Todos")
        self.combo_tipo.pack(side="left", padx=(0, 8))

        self.combo_cat = ctk.CTkComboBox(
            frame, values=["Todas"] + cat.itens_dre(), width=220,
            fg_color=self.cores["card"], button_color=self.cores["azul"],
            command=self._ao_filtrar
        )
        self.combo_cat.set("Todas")
        self.combo_cat.pack(side="left")

    def _ao_filtrar(self, _=None) -> None:
        """Callback dos filtros."""
        self.filtro_tipo = self.combo_tipo.get()
        self.filtro_categoria = self.combo_cat.get()
        self._atualizar_tudo()

    def _construir_tabela(self) -> None:
        """Constrói a tabela com cabeçalhos clicáveis para ordenação."""
        frame = ctk.CTkFrame(self, fg_color=self.cores["card"], corner_radius=10)
        frame.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("DRE.Treeview",
                        background=self.cores["card"],
                        fieldbackground=self.cores["card"],
                        foreground=self.cores["texto"],
                        rowheight=32, font=("Arial", 11))
        style.configure("DRE.Treeview.Heading",
                        background=self.cores["fundo"],
                        foreground=self.cores["texto"],
                        font=("Arial", 11, "bold"), relief="flat")
        style.map("DRE.Treeview", background=[("selected", "#3a3a6e")])

        self.colunas = [
            ("data", "Data ↕", 95),
            ("descricao", "Descrição ↕", 250),
            ("tipo", "Tipo ↕", 100),
            ("categoria", "Categoria ↕", 210),
            ("valor", "Valor ↕", 130),
        ]
        self.tree = ttk.Treeview(
            frame, columns=[c[0] for c in self.colunas],
            show="headings", style="DRE.Treeview", selectmode="browse",
        )
        for col, label, w in self.colunas:
            self.tree.heading(col, text=label,
                              command=lambda c=col: self._ordenar_por(c))
            self.tree.column(col, width=w, anchor="w")

        self.tree.tag_configure("receita", foreground=self.cores["receita"])
        self.tree.tag_configure("despesa", foreground=self.cores["despesa"])

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

    def _ordenar_por(self, coluna: str) -> None:
        """Alterna ordenação pela coluna clicada.

        Args:
            coluna: Nome da coluna.
        """
        if self.ordenar_por == coluna:
            self.ordem_decrescente = not self.ordem_decrescente
        else:
            self.ordenar_por = coluna
            self.ordem_decrescente = True
        self._atualizar_tudo()

    def _atualizar_tudo(self) -> None:
        """Recarrega resumo e tabela com os filtros e ordenação atuais."""
        self.label_mes.configure(
            text=f"{calendar.month_name[self.mes_atual]} {self.ano_atual}"
        )
        tipo_sql = {"Receita": "receita", "Despesa": "despesa"}.get(self.filtro_tipo)
        cat_sql = None if self.filtro_categoria == "Todas" else self.filtro_categoria

        transacoes = transacao_repo.listar_por_mes(
            self.ano_atual, self.mes_atual,
            ordenar_por=self.ordenar_por, decrescente=self.ordem_decrescente,
            filtro_tipo=tipo_sql, filtro_categoria=cat_sql,
        )
        todas = transacao_repo.listar_por_mes(self.ano_atual, self.mes_atual)
        receitas = sum(t.valor for t in todas if t.tipo == "receita")
        despesas = sum(t.valor for t in todas if t.tipo == "despesa")

        def fmt(v):
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        self.card_receitas.configure(text=fmt(receitas))
        self.card_despesas.configure(text=fmt(despesas))
        self.card_saldo.configure(text=fmt(receitas - despesas))

        for row in self.tree.get_children():
            self.tree.delete(row)
        for t in transacoes:
            sinal = "+" if t.tipo == "receita" else "-"
            rotulo = "🟢 Receita" if t.tipo == "receita" else "🔴 Despesa"
            self.tree.insert("", "end", tags=(t.tipo,), values=(
                t.data_formatada(), t.descricao, rotulo,
                t.categoria, f"{sinal} {t.valor_formatado()}"
            ))

    def _mes_anterior(self) -> None:
        """Navega para o mês anterior."""
        if self.mes_atual == 1:
            self.mes_atual, self.ano_atual = 12, self.ano_atual - 1
        else:
            self.mes_atual -= 1
        self._atualizar_tudo()

    def _mes_proximo(self) -> None:
        """Navega para o próximo mês."""
        if self.mes_atual == 12:
            self.mes_atual, self.ano_atual = 1, self.ano_atual + 1
        else:
            self.mes_atual += 1
        self._atualizar_tudo()

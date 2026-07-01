"""
Subaba "Ativos e Passivos" — apenas visualização e gestão de saldo.

O formulário de lançamento vive na coluna esquerda de TabLancamentos.
Esta subaba exibe a posição patrimonial atual (todos os ativos e
passivos registrados), com filtros, ordenação por coluna e duplo
clique para atualizar o saldo devedor de um Passivo.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox

from repositories import transacao_repo
from services import balanco_service
from models import categoria as cat


class SubAbaBP(ctk.CTkFrame):
    """Subaba de visualização de Ativos e Passivos."""

    def __init__(self, parent, cores: dict) -> None:
        """Inicializa a subaba de visualização patrimonial.

        Args:
            parent: Frame pai.
            cores: Paleta de cores da aplicação.
        """
        super().__init__(parent, fg_color=cores["fundo"])
        self.cores = cores
        self.ordenar_por = "data"
        self.ordem_decrescente = True
        self.filtro_tipo = "Todos"
        self.filtro_categoria = "Todas"

        self._construir_resumo()
        self._construir_filtros()
        self._construir_tabela()
        self._atualizar_tudo()

    def _construir_resumo(self) -> None:
        """Constrói os cards de resumo: Total Ativo, Passivo e PL."""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            frame, text="Posição Patrimonial Atual",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.cores["texto"]
        ).pack(side="left", padx=(0, 20))

        for attr, label, cor in [
            ("card_ativo", "Total em Ativos", self.cores["azul"]),
            ("card_passivo", "Total em Dívidas", self.cores["despesa"]),
            ("card_pl", "Patrimônio Líquido", self.cores["receita"]),
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
        """Constrói dropdowns de filtro por Tipo e Categoria."""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(frame, text="Filtrar:",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 6))

        self.combo_tipo = ctk.CTkComboBox(
            frame, values=["Todos", "Ativo", "Passivo"], width=120,
            fg_color=self.cores["card"], button_color=self.cores["azul"],
            command=self._ao_filtrar
        )
        self.combo_tipo.set("Todos")
        self.combo_tipo.pack(side="left", padx=(0, 8))

        self.combo_cat = ctk.CTkComboBox(
            frame, values=["Todas"] + cat.itens_balanco(), width=220,
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
        """Constrói a tabela patrimonial com cabeçalhos clicáveis."""
        frame = ctk.CTkFrame(self, fg_color=self.cores["card"], corner_radius=10)
        frame.pack(fill="both", expand=True, padx=16, pady=(4, 4))

        style = ttk.Style()
        style.configure("BP.Treeview",
                        background=self.cores["card"],
                        fieldbackground=self.cores["card"],
                        foreground=self.cores["texto"],
                        rowheight=32, font=("Arial", 11))
        style.configure("BP.Treeview.Heading",
                        background=self.cores["fundo"],
                        foreground=self.cores["texto"],
                        font=("Arial", 11, "bold"), relief="flat")
        style.map("BP.Treeview", background=[("selected", "#3a3a6e")])

        self.colunas_bp = [
            ("data", "Data ↕", 95),
            ("descricao", "Descrição ↕", 200),
            ("tipo", "Tipo ↕", 85),
            ("categoria", "Categoria ↕", 185),
            ("valor", "Valor Original ↕", 130),
            ("saldo_atual", "Saldo Atual ↕", 130),
        ]
        self.tree = ttk.Treeview(
            frame, columns=[c[0] for c in self.colunas_bp],
            show="headings", style="BP.Treeview", selectmode="browse",
        )
        for col, label, w in self.colunas_bp:
            self.tree.heading(col, text=label,
                              command=lambda c=col: self._ordenar_por(c))
            self.tree.column(col, width=w, anchor="w")

        self.tree.tag_configure("ativo", foreground=self.cores["azul"])
        self.tree.tag_configure("passivo", foreground="#a78bfa")

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        self.tree.bind("<Double-Button-1>", self._ao_duplo_clique)

        ctk.CTkLabel(
            self, text="💡 Duplo clique em uma linha de Passivo para atualizar o saldo devedor",
            font=ctk.CTkFont(size=10),
            text_color=self.cores["texto_secundario"]
        ).pack(anchor="w", padx=16, pady=(2, 8))

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

    def _ao_duplo_clique(self, event) -> None:
        """Abre diálogo de atualização de saldo para linha de Passivo.

        Args:
            event: Evento de duplo clique do tkinter.
        """
        sel = self.tree.selection()
        if not sel:
            return
        tags = self.tree.item(sel[0], "tags")
        if "passivo" not in tags:
            messagebox.showinfo(
                "Ativo selecionado",
                "A atualização de saldo está disponível apenas para Passivos.\n\n"
                "Para atualizar um Ativo, registre uma nova movimentação."
            )
            return
        id_t = int(self.tree.item(sel[0], "text"))
        valores = self.tree.item(sel[0], "values")
        self._abrir_dialogo_saldo(id_t, valores[1], valores[5])

    def _abrir_dialogo_saldo(self, id_t: int, descricao: str, saldo_fmt: str) -> None:
        """Abre janela modal para digitar o novo saldo devedor.

        Args:
            id_t: ID da transação Passivo.
            descricao: Descrição para exibir.
            saldo_fmt: Saldo atual formatado.
        """
        janela = ctk.CTkToplevel(self)
        janela.title("Atualizar Saldo Devedor")
        janela.geometry("420x230")
        janela.configure(fg_color=self.cores["fundo"])
        janela.grab_set()

        ctk.CTkLabel(janela, text="Atualizar Saldo Devedor",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=self.cores["texto"]).pack(pady=(16, 4))
        ctk.CTkLabel(janela, text=descricao,
                     font=ctk.CTkFont(size=12),
                     text_color=self.cores["texto_secundario"]).pack()
        ctk.CTkLabel(janela, text=f"Saldo atual: {saldo_fmt}",
                     font=ctk.CTkFont(size=12),
                     text_color="#a78bfa").pack(pady=(4, 12))

        row = ctk.CTkFrame(janela, fg_color="transparent")
        row.pack()
        ctk.CTkLabel(row, text="Novo saldo total (R$):",
                     text_color=self.cores["texto"],
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        campo = ctk.CTkEntry(row, width=140, placeholder_text="0,00")
        campo.pack(side="left")
        campo.focus()

        label_msg = ctk.CTkLabel(janela, text="",
                                 text_color=self.cores["despesa"],
                                 font=ctk.CTkFont(size=11))
        label_msg.pack(pady=4)

        def confirmar():
            try:
                novo = float(campo.get().strip().replace(",", "."))
                if novo < 0:
                    raise ValueError
            except ValueError:
                label_msg.configure(text="⚠ Informe um valor válido (ex: 9.500,00).")
                return
            res = balanco_service.atualizar_saldo_devedor(id_t, novo)
            diff = res["diferenca"]
            sinal = "↓" if diff < 0 else "↑"
            messagebox.showinfo(
                "Saldo atualizado",
                f"Atualizado com sucesso!\n\n"
                f"Anterior: R$ {res['saldo_anterior']:,.2f}\n"
                f"Novo:     R$ {res['saldo_novo']:,.2f}\n"
                f"Variação: {sinal} R$ {abs(diff):,.2f}"
            )
            janela.destroy()
            self._atualizar_tudo()

        campo.bind("<Return>", lambda e: confirmar())
        ctk.CTkButton(janela, text="✅  Confirmar",
                      fg_color=self.cores["receita"], hover_color="#00a87e",
                      command=confirmar).pack(pady=4)

    def _atualizar_tudo(self) -> None:
        """Recarrega resumo e tabela de Ativos/Passivos."""
        tipo_sql = {"Ativo": "ativo", "Passivo": "passivo"}.get(self.filtro_tipo)
        cat_sql = None if self.filtro_categoria == "Todas" else self.filtro_categoria

        transacoes = transacao_repo.listar_ativos_passivos(
            ordenar_por=self.ordenar_por, decrescente=self.ordem_decrescente,
            filtro_tipo=tipo_sql, filtro_categoria=cat_sql,
        )
        todos = transacao_repo.listar_ativos_passivos()
        ISC = balanco_service.ITEM_SAIDA_CAIXA
        total_ativo = sum(
            t.saldo_atual for t in todos
            if t.tipo == "ativo" and t.categoria != ISC and t.saldo_atual > 0
        )
        total_passivo = sum(t.saldo_atual for t in todos if t.tipo == "passivo")

        def fmt(v):
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        self.card_ativo.configure(text=fmt(total_ativo))
        self.card_passivo.configure(text=fmt(total_passivo))
        self.card_pl.configure(text=fmt(total_ativo - total_passivo))

        for row in self.tree.get_children():
            self.tree.delete(row)
        for t in transacoes:
            if t.categoria == ISC:
                continue
            rotulo = "🔵 Ativo" if t.tipo == "ativo" else "🟣 Passivo"
            self.tree.insert(
                "", "end", text=str(t.id), tags=(t.tipo,),
                values=(
                    t.data_formatada(), t.descricao, rotulo,
                    t.categoria, t.valor_formatado(), t.saldo_formatado(),
                )
            )

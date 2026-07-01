"""
Aba Balanço Patrimonial — visão do patrimônio com gráficos e índices embutidos.

Dois gráficos: barras horizontais (Ativo vs Passivo) e linha temporal do PL.
Nenhuma lógica de negócio aqui — apenas exibição dos dados do balanco_service.
"""

import calendar
import customtkinter as ctk
from tkinter import filedialog, messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from services import balanco_service
from reports import excel_exporter


class TabBalanco(ctk.CTkFrame):
    """Aba de Balanço Patrimonial com cards de índices, gráficos e exportação."""

    def __init__(self, parent, cores: dict) -> None:
        """Inicializa a aba de Balanço Patrimonial.

        Args:
            parent: Frame pai.
            cores: Paleta de cores da aplicação.
        """
        super().__init__(parent, fg_color=cores["fundo"])
        self.cores = cores
        from datetime import date
        hoje = date.today()
        self.mes = hoje.month
        self.ano = hoje.year
        self.dados = None
        self.cards_widgets = []

        self._construir_controles()
        self._construir_cards()
        self._construir_graficos()
        self._construir_tabela_colapsavel()
        self._atualizar()

    def _construir_controles(self) -> None:
        """Constrói a barra de navegação de período e botão de exportação."""
        barra = ctk.CTkFrame(self, fg_color=self.cores["card"], corner_radius=8)
        barra.pack(fill="x", padx=16, pady=(12, 4))

        nav = ctk.CTkFrame(barra, fg_color="transparent")
        nav.pack(side="left", padx=12, pady=8)
        ctk.CTkButton(nav, text="◀", width=32, fg_color=self.cores["fundo"],
                      command=self._mes_anterior).pack(side="left", padx=(0, 4))
        self.label_periodo = ctk.CTkLabel(
            nav, text="", width=150,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.cores["texto"]
        )
        self.label_periodo.pack(side="left")
        ctk.CTkButton(nav, text="▶", width=32, fg_color=self.cores["fundo"],
                      command=self._mes_proximo).pack(side="left", padx=(4, 0))

        ctk.CTkButton(
            barra, text="📥  Exportar Excel", width=160,
            fg_color=self.cores["fundo"], hover_color=self.cores["card"],
            border_width=1, border_color=self.cores["azul"],
            text_color=self.cores["azul"],
            command=self._exportar_excel
        ).pack(side="right", padx=12, pady=8)

    def _construir_cards(self) -> None:
        """Reserva o frame para os cards de índices."""
        self.frame_cards = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_cards.pack(fill="x", padx=16, pady=4)

    def _construir_graficos(self) -> None:
        """Reserva o frame para os gráficos matplotlib."""
        self.frame_graficos = ctk.CTkFrame(self, fg_color=self.cores["card"], corner_radius=10)
        self.frame_graficos.pack(fill="both", expand=True, padx=16, pady=4)

    def _construir_tabela_colapsavel(self) -> None:
        """Constrói a tabela de detalhes do Balanço, colapsável com filtros."""
        self.frame_tabela_outer = ctk.CTkFrame(self, fg_color=self.cores["card"], corner_radius=10)
        self.frame_tabela_outer.pack(fill="x", padx=16, pady=(4, 12))

        cabecalho = ctk.CTkFrame(self.frame_tabela_outer, fg_color="transparent")
        cabecalho.pack(fill="x", padx=12, pady=(4, 0))

        self.btn_colapso = ctk.CTkButton(
            cabecalho, text="▼  Ver detalhes do Balanço",
            fg_color="transparent", hover_color=self.cores["fundo"],
            text_color=self.cores["texto_secundario"],
            font=ctk.CTkFont(size=12), anchor="w", command=self._toggle_tabela
        )
        self.btn_colapso.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(cabecalho, text="Filtrar:",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 4))
        self.combo_filtro_bp_tipo = ctk.CTkComboBox(
            cabecalho, values=["Todos", "Ativo", "Passivo"], width=110,
            fg_color=self.cores["card"], button_color=self.cores["azul"],
            command=lambda _: self._atualizar()
        )
        self.combo_filtro_bp_tipo.set("Todos")
        self.combo_filtro_bp_tipo.pack(side="left", padx=(0, 6))

        from models import categoria as cat_mod
        self.combo_filtro_bp_cat = ctk.CTkComboBox(
            cabecalho, values=["Todas"] + cat_mod.itens_balanco(), width=200,
            fg_color=self.cores["card"], button_color=self.cores["azul"],
            command=lambda _: self._atualizar()
        )
        self.combo_filtro_bp_cat.set("Todas")
        self.combo_filtro_bp_cat.pack(side="left")

        self.frame_tabela_inner = None
        self.tabela_visivel = False

    def _toggle_tabela(self) -> None:
        """Alterna a visibilidade da tabela de detalhes."""
        if self.tabela_visivel:
            if self.frame_tabela_inner:
                self.frame_tabela_inner.destroy()
            self.btn_colapso.configure(text="▼  Ver detalhes do Balanço")
            self.tabela_visivel = False
        else:
            self._renderizar_tabela_detalhes()
            self.btn_colapso.configure(text="▲  Ocultar detalhes")
            self.tabela_visivel = True

    def _renderizar_tabela_detalhes(self) -> None:
        """Preenche a tabela com os dados do Balanço atual, respeitando filtros."""
        if not self.dados:
            return
        self.frame_tabela_inner = ctk.CTkFrame(
            self.frame_tabela_outer, fg_color="transparent"
        )
        self.frame_tabela_inner.pack(fill="x", padx=12, pady=(0, 8))
        d = self.dados
        filtro_tipo = getattr(self, "combo_filtro_bp_tipo", None)
        filtro_cat = getattr(self, "combo_filtro_bp_cat", None)
        tipo_sel = filtro_tipo.get() if filtro_tipo else "Todos"
        cat_sel = filtro_cat.get() if filtro_cat else "Todas"

        frame_cols = ctk.CTkFrame(self.frame_tabela_inner, fg_color="transparent")
        frame_cols.pack(fill="x")

        def mostrar_secao(parent, titulo, itens_dict, total, cor_total, tipo_tag):
            if tipo_sel not in ("Todos", titulo):
                return
            self._linha_detalhe(parent, titulo.upper(), None, negrito=True)
            for nome_item, val in itens_dict.items():
                if cat_sel == "Todas" or cat_sel == nome_item:
                    self._linha_detalhe(parent, f"   {nome_item}", val)
            self._linha_detalhe(parent, f"Total — {titulo}", total, negrito=True, cor=cor_total)

        col_ativo = ctk.CTkFrame(frame_cols, fg_color="transparent")
        col_ativo.pack(side="left", expand=True, fill="x", padx=(0, 16))
        mostrar_secao(col_ativo, "Ativo",
                      {"Caixa (Ativo Circulante)": d["caixa"],
                       **d["itens_ativo_nao_circulante"]},
                      d["ativo_total"], self.cores["receita"], "ativo")

        col_passivo = ctk.CTkFrame(frame_cols, fg_color="transparent")
        col_passivo.pack(side="left", expand=True, fill="x")
        passivo_itens = d["itens_passivo"] if d["itens_passivo"] else {"Dívidas": 0.0}
        mostrar_secao(col_passivo, "Passivo",
                      {**passivo_itens, "Patrimônio Líquido": d["patrimonio_liquido"]},
                      d["dividas"] + d["patrimonio_liquido"],
                      self.cores["receita"], "passivo")

    def _linha_detalhe(self, parent, nome: str, valor, negrito: bool = False, cor: str = None) -> None:
        """Renderiza uma linha de detalhe com nome e valor.

        Args:
            parent: Frame pai.
            nome: Label da linha.
            valor: Valor numérico ou None para linhas de título.
            negrito: Se True, aplica negrito.
            cor: Cor opcional para o valor.
        """
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=1)
        font = ctk.CTkFont(size=11, weight="bold" if negrito else "normal")
        ctk.CTkLabel(row, text=nome, text_color=self.cores["texto"],
                     font=font, anchor="w").pack(side="left", expand=True, fill="x")
        if valor is not None:
            ctk.CTkLabel(row, text=self._fmt(valor),
                         text_color=cor or self.cores["texto"],
                         font=font).pack(side="right")

    def _atualizar(self) -> None:
        """Recalcula e redesenha todos os elementos da aba."""
        self.label_periodo.configure(
            text=f"{calendar.month_name[self.mes]} {self.ano}"
        )
        self.dados = balanco_service.calcular_balanco(self.ano, self.mes)
        self._renderizar_cards()
        self._renderizar_graficos()
        if self.tabela_visivel and self.frame_tabela_inner:
            self.frame_tabela_inner.destroy()
            self._renderizar_tabela_detalhes()

    def _renderizar_cards(self) -> None:
        """Atualiza os cards de índices do Balanço."""
        for w in self.cards_widgets:
            w.destroy()
        self.cards_widgets.clear()

        for idx in self.dados["indices"]:
            card = ctk.CTkFrame(self.frame_cards, fg_color=self.cores["card"], corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=5, pady=4)

            valor_txt = (
                f"{idx['valor']:.2f}{idx['unidade']}"
                if idx["valor"] is not None else "N/A"
            )
            cor = {"ok": self.cores["receita"], "atencao": "#f59e0b",
                   "critico": self.cores["despesa"], "na": self.cores["texto_secundario"]
                   }.get(idx["status"], self.cores["texto"])

            ctk.CTkLabel(card, text=idx["nome"], font=ctk.CTkFont(size=10),
                         text_color=self.cores["texto_secundario"]).pack(pady=(8, 0), padx=10)
            ctk.CTkLabel(card, text=f"{idx['icone']} {valor_txt}",
                         font=ctk.CTkFont(size=15, weight="bold"),
                         text_color=cor).pack(padx=10)
            ctk.CTkLabel(card, text=idx["interpretacao"], font=ctk.CTkFont(size=9),
                         text_color=self.cores["texto_secundario"],
                         wraplength=190).pack(padx=10, pady=(2, 8))
            self.cards_widgets.append(card)

    def _renderizar_graficos(self) -> None:
        """Renderiza os dois gráficos do Balanço embutidos na janela."""
        for widget in self.frame_graficos.winfo_children():
            widget.destroy()

        d = self.dados
        bg = self.cores["fundo"]
        evolucao = d["evolucao_pl"]
        tem_dados = d["ativo_total"] > 0 or any(e["pl"] != 0 for e in evolucao)

        if not tem_dados:
            ctk.CTkLabel(
                self.frame_graficos,
                text="📊 Dados insuficientes — registre movimentações para visualizar o Balanço",
                font=ctk.CTkFont(size=13),
                text_color=self.cores["texto_secundario"]
            ).pack(expand=True)
            return

        fig = Figure(figsize=(10, 3.2), facecolor=bg)
        fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.15, wspace=0.35)

        # Gráfico 1 — Barras verticais empilhadas: Ativo vs Passivo + PL
        ax1 = fig.add_subplot(1, 2, 1)
        ax1.set_facecolor(bg)
        ax1.set_title("Estrutura Patrimonial", color=self.cores["texto"], fontsize=10)

        x = [0, 1]
        labels_x = ["Ativo", "Passivo + PL"]
        base_baixo = [d["caixa"], d["dividas"]]
        topo = [d["investimentos"], d["patrimonio_liquido"]]
        rotulo_base = ["Caixa", "Dívidas"]
        rotulo_topo = ["Bens/Invest.", "Patrimônio Líq."]

        barras_base = ax1.bar(x, base_baixo, width=0.5, color=self.cores["receita"])
        barras_topo = ax1.bar(x, topo, width=0.5, bottom=base_baixo, color=self.cores["azul"])

        for i in range(2):
            if base_baixo[i] > 0:
                ax1.text(x[i], base_baixo[i] / 2, f"{rotulo_base[i]}\n{self._fmt(base_baixo[i])}",
                         ha="center", va="center", fontsize=7, color="white")
            if topo[i] > 0:
                ax1.text(x[i], base_baixo[i] + topo[i] / 2, f"{rotulo_topo[i]}\n{self._fmt(topo[i])}",
                         ha="center", va="center", fontsize=7, color="white")
            total = base_baixo[i] + topo[i]
            ax1.text(x[i], total, self._fmt(total), ha="center", va="bottom",
                     fontsize=9, color=self.cores["texto"], fontweight="bold")

        ax1.set_xticks(x)
        ax1.set_xticklabels(labels_x, color=self.cores["texto"], fontsize=10)
        ax1.tick_params(colors=self.cores["texto"])
        ax1.spines[:].set_color("#444466")
        ax1.yaxis.set_tick_params(labelcolor=self.cores["texto"])
        ax1.set_ylim(0, max(sum(base_baixo) , sum(topo) , max(base_baixo[0]+topo[0], base_baixo[1]+topo[1])) * 1.2 or 1)

        # Gráfico 2 — Linha temporal PL
        ax2 = fig.add_subplot(1, 2, 2)
        ax2.set_facecolor(bg)
        ax2.set_title("Evolução do Patrimônio Líquido (12 meses)", color=self.cores["texto"], fontsize=10)

        labels = [e["label"] for e in evolucao]
        pls = [e["pl"] for e in evolucao]

        meses_com_dados = sum(1 for p in pls if p != 0)
        if meses_com_dados < 2:
            ax2.text(0.5, 0.5, "Registre pelo menos\n2 meses para ver a evolução",
                     ha="center", va="center", color=self.cores["texto_secundario"],
                     fontsize=9, transform=ax2.transAxes)
        else:
            ax2.plot(range(len(labels)), pls, color=self.cores["azul"], linewidth=2, marker="o",
                     markersize=4)
            ax2.fill_between(range(len(labels)), pls, alpha=0.2, color=self.cores["azul"])
            ax2.set_xticks(range(len(labels)))
            ax2.set_xticklabels(labels, rotation=35, ha="right", fontsize=7,
                                 color=self.cores["texto"])
            ax2.tick_params(colors=self.cores["texto"])
            ax2.spines[:].set_color("#444466")
            ax2.yaxis.set_tick_params(labelcolor=self.cores["texto"])
            ax2.axhline(0, color="#444466", linewidth=0.8, linestyle="--")

        canvas = FigureCanvasTkAgg(fig, master=self.frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def _exportar_excel(self) -> None:
        """Abre diálogo para escolher destino e exporta o Balanço em Excel."""
        if not self.dados:
            return
        pasta = filedialog.askdirectory(title="Escolha a pasta de destino")
        if not pasta:
            return
        caminho = excel_exporter.exportar_balanco(self.dados, pasta)
        messagebox.showinfo("Exportado!", f"Arquivo salvo em:\n{caminho}")

    def _mes_anterior(self) -> None:
        """Navega para o mês anterior e atualiza."""
        if self.mes == 1:
            self.mes = 12
            self.ano -= 1
        else:
            self.mes -= 1
        self._atualizar()

    def _mes_proximo(self) -> None:
        """Navega para o próximo mês e atualiza."""
        if self.mes == 12:
            self.mes = 1
            self.ano += 1
        else:
            self.mes += 1
        self._atualizar()

    def _fmt(self, valor: float) -> str:
        """Formata valor como moeda brasileira.

        Args:
            valor: Valor numérico a formatar.

        Returns:
            String no formato 'R$ X.XXX,XX'.
        """
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

"""
Aba DRE — visualização de resultado com gráficos e índices embutidos.

Gráficos renderizados via matplotlib + FigureCanvasTkAgg direto na janela.
Nenhuma lógica de negócio aqui — apenas exibição dos dados do dre_service.
"""

import calendar
import customtkinter as ctk
from tkinter import filedialog, messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as mpatches

from services import dre_service
from reports import excel_exporter


class TabDRE(ctk.CTkFrame):
    """Aba de DRE com cards de índices, gráficos e exportação Excel."""

    def __init__(self, parent, cores: dict) -> None:
        """Inicializa a aba DRE.

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
        self.canvas_fig = None

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
        """Constrói a linha de cards de índices financeiros."""
        self.frame_cards = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_cards.pack(fill="x", padx=16, pady=4)
        self.cards_widgets = []

    def _construir_graficos(self) -> None:
        """Reserva o frame onde os gráficos matplotlib serão embutidos."""
        self.frame_graficos = ctk.CTkFrame(self, fg_color=self.cores["card"], corner_radius=10)
        self.frame_graficos.pack(fill="both", expand=True, padx=16, pady=4)

    def _construir_tabela_colapsavel(self) -> None:
        """Constrói a tabela de detalhes do DRE, colapsável com filtro por categoria."""
        self.frame_tabela_outer = ctk.CTkFrame(self, fg_color=self.cores["card"], corner_radius=10)
        self.frame_tabela_outer.pack(fill="x", padx=16, pady=(4, 12))

        cabecalho = ctk.CTkFrame(self.frame_tabela_outer, fg_color="transparent")
        cabecalho.pack(fill="x", padx=12, pady=(4, 0))

        self.btn_colapso = ctk.CTkButton(
            cabecalho, text="▼  Ver detalhes do DRE",
            fg_color="transparent", hover_color=self.cores["fundo"],
            text_color=self.cores["texto_secundario"],
            font=ctk.CTkFont(size=12), anchor="w", command=self._toggle_tabela
        )
        self.btn_colapso.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(cabecalho, text="Filtrar categoria:",
                     text_color=self.cores["texto_secundario"],
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 4))
        from models import categoria as cat_mod
        self.combo_filtro_dre = ctk.CTkComboBox(
            cabecalho, values=["Todas"] + cat_mod.itens_dre(), width=200,
            fg_color=self.cores["card"], button_color=self.cores["azul"],
            command=lambda _: self._atualizar()
        )
        self.combo_filtro_dre.set("Todas")
        self.combo_filtro_dre.pack(side="left")

        self.frame_tabela_inner = None
        self.tabela_visivel = False

    def _toggle_tabela(self) -> None:
        """Alterna a visibilidade da tabela de detalhes."""
        if self.tabela_visivel:
            if self.frame_tabela_inner:
                self.frame_tabela_inner.destroy()
            self.btn_colapso.configure(text="▼  Ver detalhes do DRE")
            self.tabela_visivel = False
        else:
            self._renderizar_tabela_detalhes()
            self.btn_colapso.configure(text="▲  Ocultar detalhes")
            self.tabela_visivel = True

    def _renderizar_tabela_detalhes(self) -> None:
        """Preenche a tabela de detalhes com os dados do DRE atual."""
        if not self.dados:
            return
        self.frame_tabela_inner = ctk.CTkFrame(
            self.frame_tabela_outer, fg_color="transparent"
        )
        self.frame_tabela_inner.pack(fill="x", padx=12, pady=(0, 8))
        d = self.dados
        filtro = self.combo_filtro_dre.get() if hasattr(self, "combo_filtro_dre") else "Todas"

        linhas = [("Receita Bruta", d["receita_bruta"], self.cores["receita"], False)]

        for nome_cat, val in d["despesas_operacionais"].items():
            if filtro == "Todas" or filtro == nome_cat:
                linhas.append((f"  {nome_cat}", -val, self.cores["despesa"], False))
        linhas.append((
            "Resultado Operacional", d["resultado_operacional"],
            self.cores["receita"] if d["resultado_operacional"] >= 0 else self.cores["despesa"],
            True
        ))
        for nome_cat, val in d["despesas_nao_operacionais"].items():
            if filtro == "Todas" or filtro == nome_cat:
                linhas.append((f"  {nome_cat} (extraordinário)", -val, "#f59e0b", False))
        linhas.append((
            "Resultado Líquido", d["resultado_liquido"],
            self.cores["receita"] if d["resultado_liquido"] >= 0 else self.cores["despesa"],
            True
        ))

        for nome, val, cor, destaque in linhas:
            row = ctk.CTkFrame(self.frame_tabela_inner,
                               fg_color=self.cores["fundo"] if destaque else "transparent")
            row.pack(fill="x", pady=2 if destaque else 1)
            peso = "bold" if destaque else "normal"
            ctk.CTkLabel(row, text=nome, text_color=self.cores["texto"],
                         font=ctk.CTkFont(size=11, weight=peso),
                         anchor="w").pack(side="left", expand=True, fill="x", padx=6)
            ctk.CTkLabel(row, text=self._fmt(val), text_color=cor,
                         font=ctk.CTkFont(size=11, weight="bold")).pack(side="right", padx=6)

    def _atualizar(self) -> None:
        """Recalcula e redesenha todos os elementos da aba."""
        self.label_periodo.configure(
            text=f"{calendar.month_name[self.mes]} {self.ano}"
        )
        self.dados = dre_service.calcular_dre(self.ano, self.mes)
        self._renderizar_cards()
        self._renderizar_graficos()
        if self.tabela_visivel and self.frame_tabela_inner:
            self.frame_tabela_inner.destroy()
            self._renderizar_tabela_detalhes()

    def _renderizar_cards(self) -> None:
        """Atualiza os cards de índices com os dados calculados."""
        for w in self.cards_widgets:
            w.destroy()
        self.cards_widgets.clear()

        for idx in self.dados["indices"]:
            card = ctk.CTkFrame(self.frame_cards, fg_color=self.cores["card"],
                                corner_radius=10)
            card.pack(side="left", expand=True, fill="x", padx=5, pady=4)

            valor_txt = (
                f"{idx['valor']:.1f}{idx['unidade']}"
                if idx["valor"] is not None else "N/A"
            )
            cor = {"ok": self.cores["receita"], "atencao": "#f59e0b",
                   "critico": self.cores["despesa"], "na": self.cores["texto_secundario"]
                   }.get(idx["status"], self.cores["texto"])

            ctk.CTkLabel(card, text=idx["nome"], font=ctk.CTkFont(size=10),
                         text_color=self.cores["texto_secundario"]).pack(pady=(8, 0), padx=10)
            ctk.CTkLabel(card, text=f"{idx['icone']} {valor_txt}",
                         font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=cor).pack(padx=10)
            ctk.CTkLabel(card, text=idx["interpretacao"], font=ctk.CTkFont(size=9),
                         text_color=self.cores["texto_secundario"],
                         wraplength=190).pack(padx=10, pady=(2, 8))

            self.cards_widgets.append(card)

    def _renderizar_graficos(self) -> None:
        """Renderiza os dois gráficos matplotlib embutidos na janela."""
        for widget in self.frame_graficos.winfo_children():
            widget.destroy()

        d = self.dados
        bg = self.cores["fundo"]

        if not d["despesas"] and d["receita_bruta"] == 0:
            ctk.CTkLabel(
                self.frame_graficos,
                text="📊 Dados insuficientes — registre movimentações neste período",
                font=ctk.CTkFont(size=13),
                text_color=self.cores["texto_secundario"]
            ).pack(expand=True)
            return

        fig = Figure(figsize=(10, 3.2), facecolor=bg)
        fig.subplots_adjust(left=0.06, right=0.97, top=0.88, bottom=0.12, wspace=0.35)

        # Gráfico 1 — Waterfall
        ax1 = fig.add_subplot(1, 2, 1)
        ax1.set_facecolor(bg)
        ax1.set_title("Composição do Resultado", color=self.cores["texto"], fontsize=10)
        categorias = ["Receita"] + list(d["despesas"].keys()) + ["Resultado"]
        valores = [d["receita_bruta"]] + [-v for v in d["despesas"].values()] + [d["resultado_liquido"]]
        cores_bar = (
            [self.cores["receita"]]
            + [self.cores["despesa"]] * len(d["despesas"])
            + [self.cores["receita"] if d["resultado_liquido"] >= 0 else self.cores["despesa"]]
        )
        bars = ax1.bar(range(len(categorias)), [abs(v) for v in valores], color=cores_bar, width=0.6)
        ax1.set_xticks(range(len(categorias)))
        ax1.set_xticklabels(categorias, rotation=25, ha="right", fontsize=8, color=self.cores["texto"])
        ax1.tick_params(colors=self.cores["texto"])
        ax1.spines[:].set_color("#444466")
        for spine in ax1.spines.values():
            spine.set_color("#444466")
        ax1.yaxis.set_tick_params(labelcolor=self.cores["texto"])

        # Gráfico 2 — Donut
        ax2 = fig.add_subplot(1, 2, 2)
        ax2.set_facecolor(bg)
        ax2.set_title("Distribuição de Despesas", color=self.cores["texto"], fontsize=10)
        if d["despesas"]:
            cats = list(d["despesas"].keys())
            vals = list(d["despesas"].values())
            palette = ["#ff4f6d", "#f59e0b", "#5c9eff", "#a78bfa", "#34d399", "#fb923c", "#60a5fa", "#e879f9"]
            cores_donut = [palette[i % len(palette)] for i in range(len(cats))]
            wedges, texts, autotexts = ax2.pie(
                vals, labels=None, autopct="%1.0f%%",
                colors=cores_donut, startangle=90,
                wedgeprops={"width": 0.55, "edgecolor": bg},
                pctdistance=0.75
            )
            for t in autotexts:
                t.set_color("white")
                t.set_fontsize(8)
            patches = [mpatches.Patch(color=cores_donut[i], label=f"{cats[i]}: {self._fmt(vals[i])}") for i in range(len(cats))]
            ax2.legend(handles=patches, loc="center left", bbox_to_anchor=(1, 0.5),
                       fontsize=7, frameon=False, labelcolor=self.cores["texto"],
                       facecolor=bg)
        else:
            ax2.text(0.5, 0.5, "Sem despesas", ha="center", va="center",
                     color=self.cores["texto_secundario"], transform=ax2.transAxes)

        canvas = FigureCanvasTkAgg(fig, master=self.frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        self.canvas_fig = canvas

    def _exportar_excel(self) -> None:
        """Abre diálogo para escolher destino e exporta o DRE em Excel."""
        if not self.dados:
            return
        pasta = filedialog.askdirectory(title="Escolha a pasta de destino")
        if not pasta:
            return
        caminho = excel_exporter.exportar_dre(self.dados, pasta)
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

    @property
    def texto_secundario(self):
        return self.cores["texto_secundario"]

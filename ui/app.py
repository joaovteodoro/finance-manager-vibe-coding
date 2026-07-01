"""
Janela principal da aplicação.

Navegação customizada integrada ao header — título e botões de aba
formam uma única barra horizontal contínua, eliminando o aspecto de
CTkTabview flutuante no meio da tela.
"""

import customtkinter as ctk
from ui.tab_lancamentos import TabLancamentos
from ui.tab_dre import TabDRE
from ui.tab_balanco import TabBalanco

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CORES = {
    "fundo": "#1e1e2e",
    "card": "#2a2a3e",
    "receita": "#00c896",
    "despesa": "#ff4f6d",
    "azul": "#5c9eff",
    "texto": "#e0e0e0",
    "texto_secundario": "#888888",
}

ABAS = [
    ("📋  Lançamentos", "lancamentos"),
    ("📊  DRE", "dre"),
    ("🏦  Balanço", "balanco"),
]


class App(ctk.CTk):
    """Janela principal com navegação integrada ao cabeçalho."""

    def __init__(self) -> None:
        """Configura janela, header com navegação e área de conteúdo."""
        super().__init__()
        self.title("💰 Gestão Financeira Pessoal")
        self.geometry("1280x780")
        self.minsize(1100, 680)
        self.configure(fg_color=CORES["fundo"])
        self._aba_ativa = "lancamentos"
        self._botoes_nav: dict[str, ctk.CTkButton] = {}
        self._indicadores: dict[str, ctk.CTkFrame] = {}
        self._frames_conteudo: dict[str, ctk.CTkFrame] = {}

        self._construir_header()
        self._construir_conteudo()
        self._navegar("lancamentos")

    def _construir_header(self) -> None:
        """Constrói o header com título à esquerda e navegação à direita."""
        self.header = ctk.CTkFrame(
            self, fg_color=CORES["card"], height=56, corner_radius=0
        )
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        # Título
        ctk.CTkLabel(
            self.header,
            text="💰  Gestão Financeira Pessoal",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=CORES["texto"],
        ).pack(side="left", padx=24)

        # Subtítulo à direita
        ctk.CTkLabel(
            self.header,
            text="Bootcamp DIO + Lovable  •  Vibe Coding",
            font=ctk.CTkFont(size=11),
            text_color=CORES["texto_secundario"],
        ).pack(side="right", padx=24)

        # Botões de navegação — âncora central-direita
        nav = ctk.CTkFrame(self.header, fg_color="transparent")
        nav.pack(side="left", padx=(32, 0), fill="y")

        for label, chave in ABAS:
            frame_btn = ctk.CTkFrame(nav, fg_color="transparent")
            frame_btn.pack(side="left", fill="y", padx=2)

            btn = ctk.CTkButton(
                frame_btn,
                text=label,
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                hover_color=CORES["fundo"],
                text_color=CORES["texto_secundario"],
                height=44,
                corner_radius=0,
                command=lambda c=chave: self._navegar(c),
            )
            btn.pack(side="top", fill="x")

            # Linha underline — visível só na aba ativa
            indicador = ctk.CTkFrame(
                frame_btn, fg_color=CORES["azul"], height=3, corner_radius=0
            )
            indicador.pack(side="bottom", fill="x")
            indicador.pack_forget()  # esconde até ser ativado

            self._botoes_nav[chave] = btn
            self._indicadores[chave] = indicador

    def _construir_conteudo(self) -> None:
        """Cria os frames de conteúdo de cada aba e instancia os componentes."""
        self.area_conteudo = ctk.CTkFrame(self, fg_color=CORES["fundo"], corner_radius=0)
        self.area_conteudo.pack(fill="both", expand=True)

        for _, chave in ABAS:
            frame = ctk.CTkFrame(self.area_conteudo, fg_color=CORES["fundo"], corner_radius=0)
            self._frames_conteudo[chave] = frame

        TabLancamentos(self._frames_conteudo["lancamentos"], CORES).pack(
            fill="both", expand=True
        )
        TabDRE(self._frames_conteudo["dre"], CORES).pack(fill="both", expand=True)
        TabBalanco(self._frames_conteudo["balanco"], CORES).pack(fill="both", expand=True)

    def _navegar(self, chave: str) -> None:
        """Troca a aba visível e atualiza o estilo dos botões de navegação.

        Args:
            chave: Identificador interno da aba ('lancamentos', 'dre', 'balanco').
        """
        # Esconde todos os frames e reseta botões
        for c, frame in self._frames_conteudo.items():
            frame.pack_forget()
            self._botoes_nav[c].configure(text_color=CORES["texto_secundario"])
            self._indicadores[c].pack_forget()

        # Exibe aba selecionada e destaca botão
        self._frames_conteudo[chave].pack(fill="both", expand=True)
        self._botoes_nav[chave].configure(text_color=CORES["texto"])
        self._indicadores[chave].pack(side="bottom", fill="x")
        self._aba_ativa = chave

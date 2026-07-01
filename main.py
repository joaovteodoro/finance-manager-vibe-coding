"""
Gestão Financeira Pessoal — Entry Point.

Bootcamp DIO + Lovable | Vibe Coding Exercise.
Inicializa o banco de dados e lança a interface gráfica.
"""

from database.connection import inicializar_banco
from ui.app import App


def main() -> None:
    """Inicializa o banco e executa a aplicação."""
    inicializar_banco()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

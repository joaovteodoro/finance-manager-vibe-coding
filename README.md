# Finance Manager Vibecoding
Projeto desenvolvido como exercício prático do Bootcamp DIO + Lovable, com foco em vibe coding. O objetivo foi construir um software desktop funcional de gestão financeira pessoal, partindo apenas de descrições textuais de intenção e deixando a IA responsável pela geração do código.

## Sobre o projeto

O software permite que uma pessoa física acompanhe suas finanças de forma organizada, separando o fluxo de caixa do mês (receitas e despesas) da posição patrimonial acumulada (ativos e passivos). Os relatórios de DRE e Balanço Patrimonial são gerados com índices financeiros adaptados para pessoa física, baseados em conceitos da análise fundamentalista.

As principais funcionalidades são:

- Lançamento de receitas e despesas com classificação automática por tipo
- Lançamento de ativos e passivos com suporte a partida dobrada simplificada
- Atualização manual do saldo devedor de passivos
- DRE com separação entre despesas operacionais e não operacionais, gráficos e índices calculados automaticamente
- Balanço Patrimonial com evolução do patrimônio líquido nos últimos 12 meses
- Exportação de relatórios em Excel com aba de índices e benchmarks

## Requisitos

- Python 3.11 ou superior
- As demais dependências estão listadas em `requirements.txt`

## Instalação

```bash
git clone https://github.com/seu-usuario/financeiro-pessoal.git
cd financeiro-pessoal
pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

O banco de dados SQLite é criado automaticamente na primeira execução. Não é necessária nenhuma configuração prévia.

## Estrutura do projeto

```
financeiro/
├── main.py                        # Entry point da aplicação
├── README.md
├── BOOTCAMP.md                    # Decisões técnicas e arquiteturais
├── requirements.txt
├── database/
│   └── connection.py              # Conexão e inicialização do banco
├── models/
│   ├── transacao.py               # Dataclass Transacao
│   └── categoria.py               # Mapa de categorias e grupos contábeis
├── repositories/
│   └── transacao_repo.py          # Acesso ao banco de dados
├── services/
│   ├── dre_service.py             # Cálculo do DRE e índices
│   └── balanco_service.py         # Cálculo do Balanço e partida dobrada
├── reports/
│   └── excel_exporter.py          # Geração dos arquivos .xlsx
└── ui/
    ├── app.py                     # Janela principal e navegação
    ├── tab_lancamentos.py         # Aba de lançamentos (layout duas colunas)
    ├── sub_lancamentos_dre.py     # Subaba de receitas e despesas
    ├── sub_lancamentos_bp.py      # Subaba de ativos e passivos
    ├── tab_dre.py                 # Aba de DRE com gráficos
    └── tab_balanco.py             # Aba de Balanço Patrimonial com gráficos
```

## Stack

| Biblioteca | Finalidade |
|---|---|
| Python 3.11+ | Linguagem principal |
| customtkinter | Interface gráfica desktop |
| matplotlib | Gráficos embutidos na janela |
| openpyxl | Exportação de relatórios Excel |
| sqlite3 | Banco de dados local (nativo) |
| Pillow | Suporte a assets visuais |

## Screenshots

> Screenshot: [Aba Lancamentos]

> Screenshot: [Aba DRE]

> Screenshot: [Aba Balanco Patrimonial]

## Contexto do bootcamp

Este projeto faz parte de um exercício do Bootcamp DIO + Lovable. O desafio proposto foi desenvolver um software completo utilizando vibe coding, uma abordagem em que o desenvolvedor descreve a intenção, o comportamento esperado e as regras de negócio em linguagem natural, e a IA gera o código correspondente. O desenvolvedor atua como arquiteto do sistema, refinando os prompts iterativamente até o resultado final.

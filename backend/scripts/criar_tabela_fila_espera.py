import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from database import engine


CREATE_TABLE_SQL = """
CREATE TABLE fila_espera (
    id SERIAL PRIMARY KEY,
    barbearia_slug VARCHAR NOT NULL,
    cliente_nome VARCHAR NOT NULL,
    telefone_cliente VARCHAR NOT NULL,
    servico VARCHAR NOT NULL,
    profissional_preferido VARCHAR NULL,
    data_desejada DATE NULL,
    periodo_preferido VARCHAR NULL,
    prioridade VARCHAR DEFAULT 'normal' NOT NULL,
    status VARCHAR DEFAULT 'aguardando' NOT NULL,
    observacao TEXT NULL,
    origem VARCHAR DEFAULT 'agenda_publica' NOT NULL,
    chamado_em TIMESTAMP NULL,
    agendado_em TIMESTAMP NULL,
    cancelado_em TIMESTAMP NULL,
    expirado_em TIMESTAMP NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
)
"""


INDEXES_SQL = [
    """
    CREATE INDEX IF NOT EXISTS ix_fila_espera_barbearia_slug
    ON fila_espera (barbearia_slug)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_fila_espera_status
    ON fila_espera (status)
    """,
]


def criar_tabela_fila_espera():
    inspector = inspect(engine)

    if not inspector.has_table("fila_espera"):
        with engine.begin() as conexao:
            conexao.execute(text(CREATE_TABLE_SQL))

        print("Tabela fila_espera criada com sucesso.")
    else:
        print("Tabela fila_espera ja existe.")

    for comando in INDEXES_SQL:
        with engine.begin() as conexao:
            conexao.execute(text(comando))

    print("Indices da tabela fila_espera verificados.")


if __name__ == "__main__":
    criar_tabela_fila_espera()

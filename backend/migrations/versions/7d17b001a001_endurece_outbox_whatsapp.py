"""endurece outbox whatsapp

Revision ID: 7d17b001a001
Revises: cd09894c0578
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7d17b001a001"
down_revision: Union[str, Sequence[str], None] = "cd09894c0578"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "outbox_mensagens_whatsapp"


def obter_colunas(inspector) -> set[str]:
    return {
        coluna["name"]
        for coluna in inspector.get_columns(
            TABELA
        )
    }


def obter_indices(inspector) -> set[str]:
    return {
        indice["name"]
        for indice in inspector.get_indexes(
            TABELA
        )
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if TABELA not in tabelas:
        op.create_table(
            TABELA,

            sa.Column(
                "id",
                sa.Integer(),
                nullable=False,
            ),

            sa.Column(
                "provedor",
                sa.String(length=40),
                nullable=False,
            ),

            sa.Column(
                "chave_idempotencia",
                sa.String(length=240),
                nullable=False,
            ),

            sa.Column(
                "barbearia_slug",
                sa.String(),
                nullable=False,
            ),

            sa.Column(
                "phone_number_id",
                sa.String(length=120),
                nullable=False,
            ),

            sa.Column(
                "telefone_destino",
                sa.String(length=40),
                nullable=False,
            ),

            sa.Column(
                "texto",
                sa.Text(),
                nullable=False,
            ),

            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="pendente",
            ),

            sa.Column(
                "tentativas",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),

            sa.Column(
                "provider_message_id",
                sa.String(length=240),
                nullable=True,
            ),

            sa.Column(
                "ultimo_erro",
                sa.Text(),
                nullable=True,
            ),

            sa.Column(
                "criado_em",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),

            sa.Column(
                "atualizado_em",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),

            sa.Column(
                "enviado_em",
                sa.DateTime(),
                nullable=True,
            ),

            sa.Column(
                "processando_desde",
                sa.DateTime(),
                nullable=True,
            ),

            sa.Column(
                "proxima_tentativa_em",
                sa.DateTime(),
                nullable=True,
            ),

            sa.PrimaryKeyConstraint(
                "id"
            ),

            sa.UniqueConstraint(
                "provedor",
                "chave_idempotencia",
                name=(
                    "uq_outbox_whatsapp_"
                    "provedor_chave"
                ),
            ),
        )

        inspector = sa.inspect(
            bind
        )

    else:
        colunas = obter_colunas(
            inspector
        )

        if (
            "processando_desde"
            not in colunas
        ):
            op.add_column(
                TABELA,
                sa.Column(
                    "processando_desde",
                    sa.DateTime(),
                    nullable=True,
                ),
            )

        if (
            "proxima_tentativa_em"
            not in colunas
        ):
            op.add_column(
                TABELA,
                sa.Column(
                    "proxima_tentativa_em",
                    sa.DateTime(),
                    nullable=True,
                ),
            )

        inspector = sa.inspect(
            bind
        )

    indices = obter_indices(
        inspector
    )

    indices_desejados = [
        (
            "ix_outbox_mensagens_whatsapp_"
            "processando_desde",
            ["processando_desde"],
        ),
        (
            "ix_outbox_mensagens_whatsapp_"
            "proxima_tentativa_em",
            ["proxima_tentativa_em"],
        ),
    ]

    for (
        nome_indice,
        colunas_indice,
    ) in indices_desejados:

        if nome_indice not in indices:
            op.create_index(
                nome_indice,
                TABELA,
                colunas_indice,
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if (
        TABELA
        not in inspector.get_table_names()
    ):
        return

    indices = obter_indices(
        inspector
    )

    for nome_indice in [
        (
            "ix_outbox_mensagens_whatsapp_"
            "proxima_tentativa_em"
        ),
        (
            "ix_outbox_mensagens_whatsapp_"
            "processando_desde"
        ),
    ]:
        if nome_indice in indices:
            op.drop_index(
                nome_indice,
                table_name=TABELA,
            )

    inspector = sa.inspect(
        bind
    )

    colunas = obter_colunas(
        inspector
    )

    if (
        "proxima_tentativa_em"
        in colunas
    ):
        op.drop_column(
            TABELA,
            "proxima_tentativa_em",
        )

    inspector = sa.inspect(
        bind
    )

    colunas = obter_colunas(
        inspector
    )

    if (
        "processando_desde"
        in colunas
    ):
        op.drop_column(
            TABELA,
            "processando_desde",
        )

"""adiciona campos stripe em barbearias

Revision ID: cd09894c0578
Revises: 28112461cbc4
Create Date: 2026-06-20 15:20:44.890935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd09894c0578'
down_revision: Union[str, Sequence[str], None] = '28112461cbc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def coluna_existe(
    inspector,
    tabela,
    coluna,
):
    return coluna in {
        item["name"]
        for item in inspector.get_columns(tabela)
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "barbearias" not in tabelas:
        return

    colunas = [
        ("gateway_pagamento", sa.Column("gateway_pagamento", sa.String(length=40), nullable=True)),
        ("plano_codigo", sa.Column("plano_codigo", sa.String(length=40), nullable=True)),
        ("plano_periodicidade", sa.Column("plano_periodicidade", sa.String(length=40), nullable=True)),
        ("status_assinatura", sa.Column("status_assinatura", sa.String(length=40), nullable=False, server_default="trial")),
        ("stripe_customer_id", sa.Column("stripe_customer_id", sa.String(), nullable=True)),
        ("stripe_subscription_id", sa.Column("stripe_subscription_id", sa.String(), nullable=True)),
        ("stripe_checkout_session_id", sa.Column("stripe_checkout_session_id", sa.String(), nullable=True)),
        ("assinatura_iniciada_em", sa.Column("assinatura_iniciada_em", sa.DateTime(), nullable=True)),
        ("assinatura_renova_em", sa.Column("assinatura_renova_em", sa.DateTime(), nullable=True)),
        ("periodo_trial_ate", sa.Column("periodo_trial_ate", sa.DateTime(), nullable=True)),
        ("ultima_cobranca_status", sa.Column("ultima_cobranca_status", sa.String(length=80), nullable=True)),
    ]

    for nome_coluna, coluna in colunas:
        if not coluna_existe(
            inspector,
            "barbearias",
            nome_coluna,
        ):
            op.add_column(
                "barbearias",
                coluna,
            )

    indices_existentes = {
        indice["name"]
        for indice in inspector.get_indexes("barbearias")
    }

    indices = [
        (
            op.f("ix_barbearias_stripe_customer_id"),
            ["stripe_customer_id"],
        ),
        (
            op.f("ix_barbearias_stripe_subscription_id"),
            ["stripe_subscription_id"],
        ),
        (
            op.f("ix_barbearias_stripe_checkout_session_id"),
            ["stripe_checkout_session_id"],
        ),
    ]

    for nome_indice, colunas_indice in indices:
        if nome_indice not in indices_existentes:
            op.create_index(
                nome_indice,
                "barbearias",
                colunas_indice,
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "barbearias" not in tabelas:
        return

    indices_existentes = {
        indice["name"]
        for indice in inspector.get_indexes("barbearias")
    }

    indices = [
        op.f("ix_barbearias_stripe_checkout_session_id"),
        op.f("ix_barbearias_stripe_subscription_id"),
        op.f("ix_barbearias_stripe_customer_id"),
    ]

    for nome_indice in indices:
        if nome_indice in indices_existentes:
            op.drop_index(
                nome_indice,
                table_name="barbearias",
            )

    colunas_para_remover = [
        "ultima_cobranca_status",
        "periodo_trial_ate",
        "assinatura_renova_em",
        "assinatura_iniciada_em",
        "stripe_checkout_session_id",
        "stripe_subscription_id",
        "stripe_customer_id",
        "status_assinatura",
        "plano_periodicidade",
        "plano_codigo",
        "gateway_pagamento",
    ]

    inspector = sa.inspect(bind)

    for nome_coluna in colunas_para_remover:
        if coluna_existe(
            inspector,
            "barbearias",
            nome_coluna,
        ):
            op.drop_column(
                "barbearias",
                nome_coluna,
            )
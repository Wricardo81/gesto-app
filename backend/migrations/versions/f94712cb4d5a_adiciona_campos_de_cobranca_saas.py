"""adiciona campos de cobranca saas

Revision ID: f94712cb4d5a
Revises: 09fb3d0b18d7
Create Date: 2026-06-18 16:02:52.095402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f94712cb4d5a'
down_revision: Union[str, Sequence[str], None] = '09fb3d0b18d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [
        coluna["name"]
        for coluna in inspector.get_columns("barbearias")
    ]

    if "plano_nome" not in colunas:
        op.add_column(
            "barbearias",
            sa.Column(
                "plano_nome",
                sa.String(),
                nullable=False,
                server_default="Profissional",
            ),
        )

    if "valor_mensal" not in colunas:
        op.add_column(
            "barbearias",
            sa.Column(
                "valor_mensal",
                sa.Float(),
                nullable=False,
                server_default="99",
            ),
        )

    if "status_pagamento" not in colunas:
        op.add_column(
            "barbearias",
            sa.Column(
                "status_pagamento",
                sa.String(),
                nullable=False,
                server_default="em_dia",
            ),
        )

    if "vencimento_plano" not in colunas:
        op.add_column(
            "barbearias",
            sa.Column(
                "vencimento_plano",
                sa.Date(),
                nullable=True,
            ),
        )

    if "dias_tolerancia" not in colunas:
        op.add_column(
            "barbearias",
            sa.Column(
                "dias_tolerancia",
                sa.Integer(),
                nullable=False,
                server_default="3",
            ),
        )

    if "ultimo_pagamento_em" not in colunas:
        op.add_column(
            "barbearias",
            sa.Column(
                "ultimo_pagamento_em",
                sa.DateTime(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [
        coluna["name"]
        for coluna in inspector.get_columns("barbearias")
    ]

    if "ultimo_pagamento_em" in colunas:
        op.drop_column("barbearias", "ultimo_pagamento_em")

    if "dias_tolerancia" in colunas:
        op.drop_column("barbearias", "dias_tolerancia")

    if "vencimento_plano" in colunas:
        op.drop_column("barbearias", "vencimento_plano")

    if "status_pagamento" in colunas:
        op.drop_column("barbearias", "status_pagamento")

    if "valor_mensal" in colunas:
        op.drop_column("barbearias", "valor_mensal")

    if "plano_nome" in colunas:
        op.drop_column("barbearias", "plano_nome")
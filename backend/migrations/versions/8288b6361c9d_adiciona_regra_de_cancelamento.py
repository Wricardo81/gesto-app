"""adiciona regra de cancelamento

Revision ID: 8288b6361c9d
Revises: f7314f61cd11
Create Date: 2026-06-16 21:25:02.475390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8288b6361c9d'
down_revision: Union[str, Sequence[str], None] = 'f7314f61cd11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [
        coluna["name"]
        for coluna in inspector.get_columns("configuracoes")
    ]

    if "limite_cancelamento_horas" not in colunas:
        op.add_column(
            "configuracoes",
            sa.Column(
                "limite_cancelamento_horas",
                sa.Integer(),
                nullable=False,
                server_default="3",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [
        coluna["name"]
        for coluna in inspector.get_columns("configuracoes")
    ]

    if "limite_cancelamento_horas" in colunas:
        op.drop_column(
            "configuracoes",
            "limite_cancelamento_horas",
        )
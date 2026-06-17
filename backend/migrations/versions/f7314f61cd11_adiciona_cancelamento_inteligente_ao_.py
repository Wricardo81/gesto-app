"""adiciona cancelamento inteligente ao agendamento

Revision ID: f7314f61cd11
Revises: 45bb0fca43d5
Create Date: 2026-06-16 19:53:34.773352

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7314f61cd11'
down_revision: Union[str, Sequence[str], None] = '45bb0fca43d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [
        coluna["name"]
        for coluna in inspector.get_columns("agendamentos")
    ]

    if "motivo_cancelamento" not in colunas:
        op.add_column(
            "agendamentos",
            sa.Column("motivo_cancelamento", sa.String(), nullable=True),
        )

    if "cancelado_por" not in colunas:
        op.add_column(
            "agendamentos",
            sa.Column("cancelado_por", sa.String(), nullable=True),
        )

    if "cancelado_em" not in colunas:
        op.add_column(
            "agendamentos",
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
        )

    if "observacao_interna" not in colunas:
        op.add_column(
            "agendamentos",
            sa.Column("observacao_interna", sa.String(), nullable=True),
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [
        coluna["name"]
        for coluna in inspector.get_columns("agendamentos")
    ]

    if "observacao_interna" in colunas:
        op.drop_column("agendamentos", "observacao_interna")

    if "cancelado_em" in colunas:
        op.drop_column("agendamentos", "cancelado_em")

    if "cancelado_por" in colunas:
        op.drop_column("agendamentos", "cancelado_por")

    if "motivo_cancelamento" in colunas:
        op.drop_column("agendamentos", "motivo_cancelamento")

    # ### end Alembic commands ###

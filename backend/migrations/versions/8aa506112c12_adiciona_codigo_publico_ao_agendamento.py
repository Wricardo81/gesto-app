"""adiciona codigo publico ao agendamento

Revision ID: 8aa506112c12
Revises: 8288b6361c9d
Create Date: 2026-06-16 22:38:01.758181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8aa506112c12'
down_revision: Union[str, Sequence[str], None] = '8288b6361c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [
        coluna["name"]
        for coluna in inspector.get_columns("agendamentos")
    ]

    indices = [
        indice["name"]
        for indice in inspector.get_indexes("agendamentos")
    ]

    if "codigo_publico" not in colunas:
        op.add_column(
            "agendamentos",
            sa.Column(
                "codigo_publico",
                sa.String(),
                nullable=True,
            ),
        )

    if "ix_agendamentos_codigo_publico" not in indices:
        op.create_index(
            "ix_agendamentos_codigo_publico",
            "agendamentos",
            ["codigo_publico"],
            unique=True,
        )

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [
        coluna["name"]
        for coluna in inspector.get_columns("agendamentos")
    ]

    indices = [
        indice["name"]
        for indice in inspector.get_indexes("agendamentos")
    ]

    if "ix_agendamentos_codigo_publico" in indices:
        op.drop_index(
            "ix_agendamentos_codigo_publico",
            table_name="agendamentos",
        )

    if "codigo_publico" in colunas:
        op.drop_column(
            "agendamentos",
            "codigo_publico",
        )
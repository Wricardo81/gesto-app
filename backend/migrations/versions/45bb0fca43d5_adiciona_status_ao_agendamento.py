"""adiciona status ao agendamento

Revision ID: 45bb0fca43d5
Revises: ae70d6cd4bfa
Create Date: 2026-06-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "45bb0fca43d5"
down_revision: Union[str, Sequence[str], None] = "ae70d6cd4bfa"
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

    if "status" not in colunas:
        op.add_column(
            "agendamentos",
            sa.Column(
                "status",
                sa.String(),
                nullable=True,
                server_default="confirmado",
            ),
        )

    op.execute(
        "UPDATE agendamentos "
        "SET status = 'confirmado' "
        "WHERE status IS NULL"
    )

    op.alter_column(
        "agendamentos",
        "status",
        existing_type=sa.String(),
        nullable=False,
        server_default="confirmado",
    )

    if "ix_agendamentos_status" not in indices:
        op.create_index(
            "ix_agendamentos_status",
            "agendamentos",
            ["status"],
            unique=False,
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

    if "ix_agendamentos_status" in indices:
        op.drop_index(
            "ix_agendamentos_status",
            table_name="agendamentos",
        )

    if "status" in colunas:
        op.drop_column(
            "agendamentos",
            "status",
        )
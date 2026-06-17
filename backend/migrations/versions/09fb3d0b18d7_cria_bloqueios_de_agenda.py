"""cria bloqueios de agenda

Revision ID: 09fb3d0b18d7
Revises: 8aa506112c12
Create Date: 2026-06-17 15:36:49.411789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09fb3d0b18d7'
down_revision: Union[str, Sequence[str], None] = '8aa506112c12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "bloqueios_agenda" not in tabelas:
        op.create_table(
            "bloqueios_agenda",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("barbearia_slug", sa.String(), nullable=False),
            sa.Column("profissional", sa.String(), nullable=True),
            sa.Column("data", sa.Date(), nullable=False),
            sa.Column("horario_inicio", sa.String(), nullable=True),
            sa.Column("horario_fim", sa.String(), nullable=True),
            sa.Column("dia_inteiro", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("motivo", sa.String(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    indices = [
        indice["name"]
        for indice in inspector.get_indexes("bloqueios_agenda")
    ]

    if "ix_bloqueios_agenda_barbearia_slug" not in indices:
        op.create_index(
            "ix_bloqueios_agenda_barbearia_slug",
            "bloqueios_agenda",
            ["barbearia_slug"],
        )

    if "ix_bloqueios_agenda_profissional" not in indices:
        op.create_index(
            "ix_bloqueios_agenda_profissional",
            "bloqueios_agenda",
            ["profissional"],
        )

    if "ix_bloqueios_agenda_data" not in indices:
        op.create_index(
            "ix_bloqueios_agenda_data",
            "bloqueios_agenda",
            ["data"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "bloqueios_agenda" in tabelas:
        op.drop_table("bloqueios_agenda")
"""cria avisos da plataforma

Revision ID: c560ccb50ff9
Revises: f94712cb4d5a
Create Date: 2026-06-19 11:31:44.068073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c560ccb50ff9'
down_revision: Union[str, Sequence[str], None] = 'f94712cb4d5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "avisos_plataforma" not in tabelas:
        op.create_table(
            "avisos_plataforma",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("titulo", sa.String(length=160), nullable=False),
            sa.Column("mensagem", sa.Text(), nullable=False),
            sa.Column("tipo", sa.String(length=40), nullable=False, server_default="info"),
            sa.Column("tenant_slug", sa.String(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("global_para_todos", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("fixado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("dispensavel", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("data_inicio", sa.Date(), nullable=True),
            sa.Column("data_fim", sa.Date(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )

        op.create_index(
            op.f("ix_avisos_plataforma_id"),
            "avisos_plataforma",
            ["id"],
            unique=False,
        )

        op.create_index(
            op.f("ix_avisos_plataforma_tenant_slug"),
            "avisos_plataforma",
            ["tenant_slug"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "avisos_plataforma" in tabelas:
        op.drop_index(
            op.f("ix_avisos_plataforma_tenant_slug"),
            table_name="avisos_plataforma",
        )

        op.drop_index(
            op.f("ix_avisos_plataforma_id"),
            table_name="avisos_plataforma",
        )

        op.drop_table("avisos_plataforma")
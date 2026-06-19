"""cria avisos dispensados por tenant

Revision ID: 8bac8d14e551
Revises: c560ccb50ff9
Create Date: 2026-06-19 13:04:43.196216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bac8d14e551'
down_revision: Union[str, Sequence[str], None] = 'c560ccb50ff9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "avisos_dispensados_tenant" not in tabelas:
        op.create_table(
            "avisos_dispensados_tenant",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("aviso_id", sa.Integer(), nullable=False),
            sa.Column("tenant_slug", sa.String(), nullable=False),
            sa.Column(
                "dispensado_em",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["aviso_id"],
                ["avisos_plataforma.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "aviso_id",
                "tenant_slug",
                name="uq_aviso_dispensado_tenant",
            ),
        )

        op.create_index(
            op.f("ix_avisos_dispensados_tenant_id"),
            "avisos_dispensados_tenant",
            ["id"],
            unique=False,
        )

        op.create_index(
            op.f("ix_avisos_dispensados_tenant_aviso_id"),
            "avisos_dispensados_tenant",
            ["aviso_id"],
            unique=False,
        )

        op.create_index(
            op.f("ix_avisos_dispensados_tenant_tenant_slug"),
            "avisos_dispensados_tenant",
            ["tenant_slug"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "avisos_dispensados_tenant" in tabelas:
        op.drop_index(
            op.f("ix_avisos_dispensados_tenant_tenant_slug"),
            table_name="avisos_dispensados_tenant",
        )

        op.drop_index(
            op.f("ix_avisos_dispensados_tenant_aviso_id"),
            table_name="avisos_dispensados_tenant",
        )

        op.drop_index(
            op.f("ix_avisos_dispensados_tenant_id"),
            table_name="avisos_dispensados_tenant",
        )

        op.drop_table("avisos_dispensados_tenant")
"""cria chamados de suporte

Revision ID: 28112461cbc4
Revises: 8bac8d14e551
Create Date: 2026-06-19 15:34:37.805520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28112461cbc4'
down_revision: Union[str, Sequence[str], None] = '8bac8d14e551'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "chamados_suporte" not in tabelas:
        op.create_table(
            "chamados_suporte",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_slug", sa.String(), nullable=False),
            sa.Column("tipo", sa.String(length=40), nullable=False, server_default="erro"),
            sa.Column("titulo", sa.String(length=160), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="aberto"),
            sa.Column("pagina_origem", sa.String(), nullable=True),
            sa.Column("contato_nome", sa.String(length=120), nullable=True),
            sa.Column("contato_email", sa.String(length=160), nullable=True),
            sa.Column("resposta_suporte", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("resolvido_em", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

        op.create_index(
            op.f("ix_chamados_suporte_id"),
            "chamados_suporte",
            ["id"],
            unique=False,
        )

        op.create_index(
            op.f("ix_chamados_suporte_tenant_slug"),
            "chamados_suporte",
            ["tenant_slug"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabelas = inspector.get_table_names()

    if "chamados_suporte" in tabelas:
        op.drop_index(
            op.f("ix_chamados_suporte_tenant_slug"),
            table_name="chamados_suporte",
        )

        op.drop_index(
            op.f("ix_chamados_suporte_id"),
            table_name="chamados_suporte",
        )

        op.drop_table("chamados_suporte")
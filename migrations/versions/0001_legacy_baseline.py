"""Esquema legado de referência.

Revision ID: 0001_legacy
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_legacy"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transacoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.Text()),
        sa.Column("valor", sa.REAL()),
        sa.Column("categoria", sa.Text()),
        sa.Column("descricao", sa.Text()),
        sa.Column("data", sa.Text()),
        sqlite_autoincrement=True
    )
    op.create_table(
        "metas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("categoria", sa.Text()),
        sa.Column("limite", sa.REAL()),
        sqlite_autoincrement=True
    )


def downgrade():
    op.drop_table("metas")
    op.drop_table("transacoes")

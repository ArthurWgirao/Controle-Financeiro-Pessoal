"""Torna obrigatória a propriedade dos dados financeiros.

Revision ID: 0004_auth_ownership_required
Revises: 0003_auth_ownership_nullable
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_auth_ownership_required"
down_revision = "0003_auth_ownership_nullable"
branch_labels = None
depends_on = None


def upgrade():
    conexao = op.get_bind()
    for tabela in ("transacoes", "metas"):
        quantidade = conexao.execute(
            sa.text(f"SELECT COUNT(*) FROM {tabela} WHERE usuario_id IS NULL")
        ).scalar_one()
        if quantidade:
            raise RuntimeError(
                f"Migração 0004 bloqueada: {quantidade} registro(s) em {tabela} sem proprietário. "
                "Crie o usuário e execute assign-legacy-data antes de continuar."
            )
    with op.batch_alter_table("transacoes") as batch:
        batch.alter_column("usuario_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("metas") as batch:
        batch.alter_column("usuario_id", existing_type=sa.Integer(), nullable=False)


def downgrade():
    with op.batch_alter_table("metas") as batch:
        batch.alter_column("usuario_id", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("transacoes") as batch:
        batch.alter_column("usuario_id", existing_type=sa.Integer(), nullable=True)

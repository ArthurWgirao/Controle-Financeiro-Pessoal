"""Adiciona autenticação e propriedade anulável para transição legada.

Revision ID: 0003_auth_ownership_nullable
Revises: 0002_orm
"""

from alembic import op
import sqlalchemy as sa

from migrations.sequence_helpers import capturar_sequencia, restaurar_sequencia


revision = "0003_auth_ownership_nullable"
down_revision = "0002_orm"
branch_labels = None
depends_on = None


def upgrade():
    conexao = op.get_bind()
    sequencias = {
        tabela: capturar_sequencia(conexao, tabela)
        for tabela in ("transacoes", "metas")
    }
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("senha_hash", sa.String(512), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
        sqlite_autoincrement=True
    )
    with op.batch_alter_table(
        "transacoes", table_kwargs={"sqlite_autoincrement": True}
    ) as batch:
        batch.add_column(sa.Column("usuario_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_transacoes_usuario", "usuarios", ["usuario_id"], ["id"])
        batch.create_index("ix_transacoes_usuario_id", ["usuario_id"])
    with op.batch_alter_table(
        "metas", table_kwargs={"sqlite_autoincrement": True}
    ) as batch:
        batch.drop_constraint("uq_metas_categoria", type_="unique")
        batch.add_column(sa.Column("usuario_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_metas_usuario", "usuarios", ["usuario_id"], ["id"])
        batch.create_index("ix_metas_usuario_id", ["usuario_id"])
        batch.create_unique_constraint("uq_metas_usuario_categoria", ["usuario_id", "categoria"])
    for tabela in ("transacoes", "metas"):
        restaurar_sequencia(conexao, tabela, sequencias[tabela])


def downgrade():
    conexao = op.get_bind()
    colisao = conexao.execute(sa.text(
        "SELECT categoria FROM metas GROUP BY categoria HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if colisao:
        raise RuntimeError(
            "Downgrade bloqueado: existem metas da mesma categoria para usuários diferentes."
        )
    sequencias = {
        tabela: capturar_sequencia(conexao, tabela)
        for tabela in ("transacoes", "metas")
    }
    with op.batch_alter_table(
        "metas", table_kwargs={"sqlite_autoincrement": True}
    ) as batch:
        batch.drop_constraint("uq_metas_usuario_categoria", type_="unique")
        batch.drop_index("ix_metas_usuario_id")
        batch.drop_constraint("fk_metas_usuario", type_="foreignkey")
        batch.drop_column("usuario_id")
        batch.create_unique_constraint("uq_metas_categoria", ["categoria"])
    with op.batch_alter_table(
        "transacoes", table_kwargs={"sqlite_autoincrement": True}
    ) as batch:
        batch.drop_index("ix_transacoes_usuario_id")
        batch.drop_constraint("fk_transacoes_usuario", type_="foreignkey")
        batch.drop_column("usuario_id")
    for tabela in ("transacoes", "metas"):
        restaurar_sequencia(conexao, tabela, sequencias[tabela])
    op.drop_table("usuarios")

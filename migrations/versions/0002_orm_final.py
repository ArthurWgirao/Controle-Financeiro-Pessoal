"""Converte o legado para tipos ORM seguros.

Revision ID: 0002_orm
Revises: 0001_legacy
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from alembic import context, op
import sqlalchemy as sa


revision = "0002_orm"
down_revision = "0001_legacy"
branch_labels = None
depends_on = None

MAXIMO = Decimal("9999999999.99")
TIPOS_RECONHECIDOS = {"receita", "despesa"}


def _simular_falha(ponto):
    """Permite testar recuperação sem afetar execuções normais."""
    argumentos = context.get_x_argument(as_dictionary=True)
    if argumentos.get("falhar_em") == ponto:
        raise RuntimeError(f"Falha simulada da migração: {ponto}")


def _decimal_valido(valor, tabela, identificador, coluna):
    try:
        convertido = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        convertido = None
    if (
        convertido is None
        or not convertido.is_finite()
        or convertido <= 0
        or convertido > MAXIMO
        or convertido.as_tuple().exponent < -2
    ):
        raise ValueError(
            f"{tabela} id={identificador}: {coluna} inválido ({valor!r})"
        )
    return convertido.quantize(Decimal("0.01"))


def _data_valida(valor, identificador):
    try:
        data = datetime.strptime(valor, "%d/%m/%Y").date()
    except (TypeError, ValueError):
        raise ValueError(
            f"transacoes id={identificador}: data inválida ({valor!r})"
        ) from None
    if data.strftime("%d/%m/%Y") != valor:
        raise ValueError(
            f"transacoes id={identificador}: data inválida ({valor!r})"
        )
    return data


def _validar_legado(conexao):
    transacoes = conexao.execute(
        sa.text(
            "SELECT id, tipo, valor, categoria, descricao, data "
            "FROM transacoes ORDER BY id"
        )
    ).mappings().all()
    metas = conexao.execute(
        sa.text(
            "SELECT id, categoria, limite FROM metas ORDER BY id"
        )
    ).mappings().all()

    convertidas = []
    for item in transacoes:
        for coluna in ("tipo", "categoria", "descricao"):
            if item[coluna] is None:
                raise ValueError(
                    f"transacoes id={item['id']}: {coluna} não pode ser nulo"
                )
        if item["tipo"] not in TIPOS_RECONHECIDOS:
            raise ValueError(
                f"transacoes id={item['id']}: tipo desconhecido "
                f"({item['tipo']!r})"
            )
        convertidas.append({
            "id": item["id"],
            "tipo": item["tipo"],
            "valor": _decimal_valido(
                item["valor"], "transacoes", item["id"], "valor"
            ),
            "categoria": item["categoria"],
            "descricao": item["descricao"],
            "data": _data_valida(item["data"], item["id"])
        })

    categorias = set()
    metas_convertidas = []
    for item in metas:
        categoria = item["categoria"]
        if categoria is None:
            raise ValueError(
                f"metas id={item['id']}: categoria não pode ser nula"
            )
        if categoria in categorias:
            raise ValueError(
                f"metas id={item['id']}: categoria duplicada ({categoria!r})"
            )
        categorias.add(categoria)
        metas_convertidas.append({
            "id": item["id"],
            "categoria": categoria,
            "limite": _decimal_valido(
                item["limite"], "metas", item["id"], "limite"
            )
        })
    return convertidas, metas_convertidas


def upgrade():
    conexao = op.get_bind()
    transacoes, metas = _validar_legado(conexao)
    _simular_falha("apos_validacao")

    nova_transacao = op.create_table(
        "_transacoes_orm",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("descricao", sa.String(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sqlite_autoincrement=True
    )
    _simular_falha("apos_criar_transacoes")
    nova_meta = op.create_table(
        "_metas_orm",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("limite", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("categoria", name="uq_metas_categoria"),
        sqlite_autoincrement=True
    )
    _simular_falha("apos_criar_temporarias")
    if transacoes:
        conexao.execute(nova_transacao.insert(), transacoes)
    _simular_falha("apos_copiar_transacoes")
    if metas:
        conexao.execute(nova_meta.insert(), metas)
    _simular_falha("antes_substituicao")
    op.drop_table("transacoes")
    op.drop_table("metas")
    op.rename_table("_transacoes_orm", "transacoes")
    op.rename_table("_metas_orm", "metas")


def downgrade():
    conexao = op.get_bind()
    transacoes = conexao.execute(
        sa.text(
            "SELECT id, tipo, valor, categoria, descricao, data "
            "FROM transacoes ORDER BY id"
        )
    ).mappings().all()
    metas = conexao.execute(
        sa.text("SELECT id, categoria, limite FROM metas ORDER BY id")
    ).mappings().all()

    legado_transacao = op.create_table(
        "_transacoes_legacy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.Text()),
        sa.Column("valor", sa.REAL()),
        sa.Column("categoria", sa.Text()),
        sa.Column("descricao", sa.Text()),
        sa.Column("data", sa.Text()),
        sqlite_autoincrement=True
    )
    legado_meta = op.create_table(
        "_metas_legacy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("categoria", sa.Text()),
        sa.Column("limite", sa.REAL()),
        sqlite_autoincrement=True
    )
    if transacoes:
        conexao.execute(legado_transacao.insert(), [
            {
                **dict(item),
                "valor": float(item["valor"]),
                "data": (
                    item["data"].strftime("%d/%m/%Y")
                    if not isinstance(item["data"], str)
                    else datetime.strptime(
                        item["data"], "%Y-%m-%d"
                    ).strftime("%d/%m/%Y")
                )
            }
            for item in transacoes
        ])
    if metas:
        conexao.execute(legado_meta.insert(), [
            {**dict(item), "limite": float(item["limite"])}
            for item in metas
        ])
    op.drop_table("transacoes")
    op.drop_table("metas")
    op.rename_table("_transacoes_legacy", "transacoes")
    op.rename_table("_metas_legacy", "metas")

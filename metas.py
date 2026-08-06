import sqlite3
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Meta, Transacao
from transacoes import escolher_categoria
from utils import ler_float, ler_int


class MetaDuplicadaError(Exception):
    """Indica conflito com a meta única do usuário para a categoria."""


def _violou_unicidade_da_meta(erro):
    origem = erro.orig
    diagnostico = getattr(origem, "diag", None)
    if (
        getattr(diagnostico, "constraint_name", None)
        == "uq_metas_usuario_categoria"
    ):
        return True
    return (
        getattr(origem, "sqlite_errorcode", None)
        == sqlite3.SQLITE_CONSTRAINT_UNIQUE
    )


def _confirmar():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _limites_periodo(mes_referencia):
    referencia = datetime.strptime(mes_referencia, "%m/%Y")
    inicio = date(referencia.year, referencia.month, 1)
    fim = (
        date(referencia.year + 1, 1, 1)
        if referencia.month == 12
        else date(referencia.year, referencia.month + 1, 1)
    )
    return inicio, fim


def listar_metas_mensais(mes_referencia, usuario_id):
    inicio, fim = _limites_periodo(mes_referencia)
    gasto = (
        select(
            Transacao.categoria.label("categoria"),
            func.sum(Transacao.valor).label("total")
        )
        .where(
            Transacao.tipo == "despesa",
            Transacao.data >= inicio,
            Transacao.data < fim,
            Transacao.usuario_id == usuario_id
        )
        .group_by(Transacao.categoria)
        .subquery()
    )
    registros = db.session.execute(
        select(Meta, func.coalesce(gasto.c.total, Decimal("0.00")))
        .outerjoin(gasto, gasto.c.categoria == Meta.categoria)
        .where(Meta.usuario_id == usuario_id)
        .order_by(Meta.categoria)
    ).all()
    return [calcular_dados_meta(meta, total) for meta, total in registros]


def buscar_meta_por_id(id_meta, usuario_id):
    return db.session.scalar(
        select(Meta).where(Meta.id == id_meta, Meta.usuario_id == usuario_id)
    )


def categoria_possui_meta(categoria, usuario_id):
    return db.session.scalar(
        select(Meta.id).where(
            Meta.categoria == categoria,
            Meta.usuario_id == usuario_id
        )
    ) is not None


def cadastrar_meta(categoria, limite, usuario_id):
    meta = Meta(categoria=categoria, limite=limite, usuario_id=usuario_id)
    db.session.add(meta)
    try:
        db.session.commit()
    except IntegrityError as erro:
        db.session.rollback()
        if (
            _violou_unicidade_da_meta(erro)
            and categoria_possui_meta(categoria, usuario_id)
        ):
            raise MetaDuplicadaError() from None
        raise
    return meta.id


def atualizar_limite_meta(id_meta, limite, usuario_id):
    meta = buscar_meta_por_id(id_meta, usuario_id)
    if meta is None:
        return False
    meta.limite = limite
    _confirmar()
    return True


def excluir_meta_por_id(id_meta, usuario_id):
    meta = buscar_meta_por_id(id_meta, usuario_id)
    if meta is None:
        return False
    db.session.delete(meta)
    _confirmar()
    return True


def calcular_gasto_mensal_por_categoria(categoria, mes_referencia, usuario_id):
    inicio, fim = _limites_periodo(mes_referencia)
    return db.session.scalar(
        select(func.coalesce(func.sum(Transacao.valor), Decimal("0.00")))
        .where(
            Transacao.categoria == categoria,
            Transacao.tipo == "despesa",
            Transacao.data >= inicio,
            Transacao.data < fim,
            Transacao.usuario_id == usuario_id
        )
    )


def calcular_dados_meta(meta, gasto):
    limite = meta["limite"]
    restante = limite - gasto
    percentual = (gasto / limite) * 100 if limite > 0 else Decimal("0")
    if percentual >= 100:
        situacao, classe = "Meta ultrapassada", "ultrapassada"
    elif percentual >= 80:
        situacao, classe = "Atenção", "atencao"
    else:
        situacao, classe = "Dentro da meta", "dentro"
    return {
        "id": meta["id"],
        "categoria": meta["categoria"],
        "limite": limite,
        "gasto": gasto,
        "restante": restante,
        "percentual": percentual,
        "largura_barra": min(percentual, Decimal("100")),
        "situacao": situacao,
        "classe_situacao": classe
    }


def _listar_metas(usuario_id):
    return db.session.scalars(
        select(Meta)
        .where(Meta.usuario_id == usuario_id)
        .order_by(Meta.id)
    ).all()


def adicionar_meta(usuario_id):
    categoria = escolher_categoria()
    limite = Decimal(str(ler_float("Digite o limite de gastos: ")))
    meta = db.session.scalar(select(Meta).where(
        Meta.categoria == categoria, Meta.usuario_id == usuario_id
    ))
    if meta:
        meta.limite = limite
        _confirmar()
        print("Meta atualizada!")
    else:
        cadastrar_meta(categoria, limite, usuario_id)
        print("Meta criada!")


def listar_metas(usuario_id):
    metas = _listar_metas(usuario_id)
    if not metas:
        print("Nenhuma meta cadastrada.")
        return
    print("\n===== METAS =====")
    for indice, meta in enumerate(metas):
        print(f"{indice} - {meta.categoria} | Limite: R$ {meta.limite:.2f}")


def remover_meta(usuario_id):
    metas = _listar_metas(usuario_id)
    if not metas:
        print("Nenhuma meta cadastrada.")
        return
    listar_metas(usuario_id)
    indice = ler_int("\nDigite o índice da meta: ")
    if 0 <= indice < len(metas):
        excluir_meta_por_id(metas[indice].id, usuario_id)
        print("Meta removida!")
    else:
        print("Índice inválido!")


def editar_meta(usuario_id):
    metas = _listar_metas(usuario_id)
    if not metas:
        print("Nenhuma meta cadastrada.")
        return
    listar_metas(usuario_id)
    indice = ler_int("\nDigite o índice da meta: ")
    if not 0 <= indice < len(metas):
        print("Índice inválido!")
        return
    meta = metas[indice]
    novo_limite = input(f"Novo limite ({meta.limite}): ").strip()
    if novo_limite:
        meta.limite = Decimal(novo_limite)
    if input("Deseja alterar categoria? (s/n): ").lower() == "s":
        meta.categoria = escolher_categoria()
    _confirmar()
    print("Meta atualizada!")


def verificar_metas(usuario_id):
    mes = date.today().strftime("%m/%Y")
    metas = listar_metas_mensais(mes, usuario_id)
    if not metas:
        print("Nenhuma meta cadastrada.")
        return
    for meta in metas:
        print(f"\nCategoria: {meta['categoria']}")
        print(f"Limite: R$ {meta['limite']:.2f}")
        print(f"Gasto atual: R$ {meta['gasto']:.2f}")
        print(
            "⚠️ LIMITE ULTRAPASSADO!"
            if meta["gasto"] > meta["limite"]
            else "✅ Dentro do limite"
        )

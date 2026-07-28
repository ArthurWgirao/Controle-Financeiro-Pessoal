from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Meta, Transacao


def test_modelos_criam_as_tabelas_no_banco_temporario(caminho_banco):
    assert {"transacoes", "metas"} <= set(inspect(db.engine).get_table_names())


def test_campos_tipos_nulabilidade_e_chaves(caminho_banco):
    inspetor = inspect(db.engine)
    transacoes = {
        coluna["name"]: coluna
        for coluna in inspetor.get_columns("transacoes")
    }
    metas = {
        coluna["name"]: coluna
        for coluna in inspetor.get_columns("metas")
    }
    assert set(transacoes) == {
        "id", "tipo", "valor", "categoria", "descricao", "data"
    }
    assert set(metas) == {"id", "categoria", "limite"}
    assert str(transacoes["valor"]["type"]) == "NUMERIC(12, 2)"
    assert str(transacoes["data"]["type"]) == "DATE"
    assert str(metas["limite"]["type"]) == "NUMERIC(12, 2)"
    assert all(
        not coluna["nullable"]
        for nome, coluna in transacoes.items()
        if nome != "id"
    )
    assert all(
        not coluna["nullable"]
        for nome, coluna in metas.items()
        if nome != "id"
    )
    assert inspetor.get_pk_constraint("transacoes")["constrained_columns"] == [
        "id"
    ]


def test_transacao_persiste_decimal_e_data(caminho_banco):
    transacao = Transacao(
        tipo="receita",
        valor=Decimal("10.25"),
        categoria="Outro",
        descricao="Teste",
        data=date(2026, 7, 28)
    )
    db.session.add(transacao)
    db.session.commit()
    db.session.expire_all()

    persistida = db.session.scalar(
        select(Transacao).where(Transacao.id == transacao.id)
    )
    assert persistida.valor == Decimal("10.25")
    assert persistida.data == date(2026, 7, 28)


def test_meta_tem_categoria_unica(caminho_banco):
    restricoes = inspect(db.engine).get_unique_constraints("metas")
    assert any(
        restricao["column_names"] == ["categoria"]
        for restricao in restricoes
    )


def test_repr_e_acesso_compativel_com_templates(caminho_banco):
    meta = Meta(id=1, categoria="Comida", limite=Decimal("100.00"))
    transacao = Transacao(
        id=2,
        tipo="despesa",
        valor=Decimal("20.00"),
        categoria="Comida",
        descricao="Mercado",
        data=date(2026, 7, 28)
    )
    assert meta["categoria"] == "Comida"
    assert transacao["data"] == date(2026, 7, 28)
    assert "despesa" in repr(transacao)


def test_rollback_recupera_sessao_apos_categoria_duplicada(caminho_banco):
    db.session.add(Meta(categoria="Comida", limite=Decimal("100.00")))
    db.session.commit()
    db.session.add(Meta(categoria="Comida", limite=Decimal("200.00")))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert db.session.scalar(select(Meta).where(Meta.categoria == "Comida"))

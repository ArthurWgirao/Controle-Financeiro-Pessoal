import re
from datetime import date
from decimal import Decimal

import pytest
from flask import g
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from autenticacao import autenticar_usuario, cadastrar_usuario
from extensions import db
from metas import cadastrar_meta
from models import Meta, Transacao, Usuario
from transacoes import cadastrar_transacao
from tests.infra_postgresql import banco_postgresql_temporario


pytestmark = pytest.mark.postgresql
@pytest.fixture(scope="module")
def url_postgresql_temporaria():
    try:
        with banco_postgresql_temporario() as (url, _):
            yield url
    except RuntimeError as erro:
        if "não configurada" in str(erro):
            pytest.skip(str(erro))
        raise


@pytest.fixture(scope="module")
def app_postgresql(url_postgresql_temporaria):
    from app import create_app

    aplicacao = create_app({
        "TESTING": True,
        "SECRET_KEY": "chave-generica-postgresql",
        "SQLALCHEMY_DATABASE_URI": url_postgresql_temporaria,
        "WTF_CSRF_ENABLED": False,
    })
    resultado = aplicacao.test_cli_runner().invoke(args=["db", "upgrade"])
    assert resultado.exit_code == 0, resultado.output
    contexto = aplicacao.app_context()
    contexto.push()
    yield aplicacao
    db.session.remove()
    db.engine.dispose()
    contexto.pop()


def autenticar_cliente(cliente, usuario_id):
    with cliente.session_transaction() as sessao:
        sessao["_user_id"] = str(usuario_id)
        sessao["_fresh"] = True


def test_postgresql_migracoes_modelos_constraints_e_rollback(app_postgresql):
    inspetor = inspect(db.engine)
    assert {"alembic_version", "usuarios", "transacoes", "metas"} <= set(
        inspetor.get_table_names()
    )
    assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004_auth_ownership_required"

    primeiro, erro = cadastrar_usuario(
        "Pessoa Um", "um@example.test", "senha-segura", "senha-segura"
    )
    assert erro is None and primeiro.verificar_senha("senha-segura")
    segundo, erro = cadastrar_usuario(
        "Pessoa Dois", "dois@example.test", "outra-senha", "outra-senha"
    )
    assert erro is None and autenticar_usuario(segundo.email, "outra-senha") == segundo
    assert segundo.id > primeiro.id

    receita = cadastrar_transacao(
        "receita", Decimal("123.45"), "Outro", "Genérica", primeiro.id
    )
    despesa = cadastrar_transacao(
        "despesa", Decimal("23.40"), "Comida", "Genérica", primeiro.id
    )
    cadastrar_transacao(
        "receita", Decimal("900.00"), "Outro", "Isolada", segundo.id
    )
    meta_um = cadastrar_meta("Comida", Decimal("100.00"), primeiro.id)
    meta_dois = cadastrar_meta("Comida", Decimal("200.00"), segundo.id)
    assert meta_dois > meta_um

    registro = db.session.get(Transacao, receita)
    assert registro.valor == Decimal("123.45")
    assert isinstance(registro.data, date)
    assert db.session.get(Transacao, despesa).valor == Decimal("23.40")

    db.session.add(Usuario(
        nome="Duplicada", email=primeiro.email,
        senha_hash="hash-generico"
    ))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert db.session.scalar(select(Usuario).where(Usuario.id == primeiro.id))


def test_postgresql_isolamento_rotas_relatorios_e_csrf(app_postgresql):
    usuarios = db.session.scalars(select(Usuario).order_by(Usuario.id)).all()
    primeiro, segundo = usuarios
    cliente = app_postgresql.test_client()
    autenticar_cliente(cliente, primeiro.id)

    for rota in ("/", "/receitas", "/despesas", "/metas", "/relatorios"):
        assert cliente.get(rota).status_code == 200
    html = cliente.get("/receitas").get_data(as_text=True)
    assert "Genérica" in html and "Isolada" not in html

    alheia = db.session.scalar(
        select(Transacao).where(Transacao.usuario_id == segundo.id)
    )
    assert cliente.get(f"/receitas/editar/{alheia.id}").status_code == 404
    assert cliente.post(f"/receitas/excluir/{alheia.id}").status_code == 404

    app_postgresql.config["WTF_CSRF_ENABLED"] = True
    cliente_csrf = app_postgresql.test_client()
    assert cliente_csrf.post("/login", data={
        "email": primeiro.email, "senha": "senha-segura"
    }).status_code == 400
    g.pop("csrf_token", None)
    g.pop("_login_user", None)
    pagina = cliente_csrf.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', pagina).group(1)
    assert cliente_csrf.post("/login", data={
        "csrf_token": token,
        "email": primeiro.email,
        "senha": "senha-segura",
    }).status_code == 302
    app_postgresql.config["WTF_CSRF_ENABLED"] = False

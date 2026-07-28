import hashlib
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from extensions import db
from models import Meta, Transacao


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
BANCO_REAL = RAIZ_PROJETO / "finance.db"
APLICACOES_TEMPORARIAS = {}


def pytest_configure(config):
    if config.option.basetemp is None:
        config.option.basetemp = str(
            RAIZ_PROJETO / f".pytest_tmp_{uuid.uuid4().hex}"
        )


def calcular_hash(caminho):
    if not caminho.exists():
        return None

    return hashlib.sha256(caminho.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def proteger_banco_real():
    banco_existia = BANCO_REAL.exists()
    hash_inicial = calcular_hash(BANCO_REAL)

    yield

    assert BANCO_REAL.exists() == banco_existia, (
        "A existência do finance.db real foi alterada pelos testes."
    )
    assert calcular_hash(BANCO_REAL) == hash_inicial, (
        "O finance.db real foi alterado pelos testes."
    )


@pytest.fixture
def caminho_banco(tmp_path, monkeypatch):
    caminho = tmp_path / "teste.db"
    monkeypatch.setenv("APP_ENV", "testing")
    from app import create_app

    aplicacao = create_app({
        "TESTING": True,
        "SECRET_KEY": "chave-fixa-da-fixture-de-testes",
        "DATABASE_PATH": str(caminho)
    })
    contexto = aplicacao.app_context()
    contexto.push()
    db.create_all()
    APLICACOES_TEMPORARIAS[str(caminho)] = aplicacao
    yield caminho
    db.session.remove()
    db.drop_all()
    db.engine.dispose()
    APLICACOES_TEMPORARIAS.pop(str(caminho), None)
    contexto.pop()


@pytest.fixture
def conexao_banco(caminho_banco):
    def consultar(sql, parametros=()):
        conexao = sqlite3.connect(caminho_banco)
        conexao.row_factory = sqlite3.Row
        try:
            registros = conexao.execute(sql, parametros).fetchall()
            resultado = []
            for registro in registros:
                item = dict(registro)
                data = item.get("data")
                if data:
                    try:
                        item["data"] = datetime.strptime(
                            data, "%Y-%m-%d"
                        ).strftime("%d/%m/%Y")
                    except ValueError:
                        pass
                resultado.append(item)
            return resultado
        finally:
            conexao.close()

    return consultar


@pytest.fixture
def inserir_transacao(caminho_banco):
    def inserir(
        tipo="despesa",
        valor=10,
        categoria="Comida",
        descricao="Teste",
        data=None
    ):
        data = data or datetime.now().strftime("%d/%m/%Y")
        transacao = Transacao(
            tipo=tipo,
            valor=valor,
            categoria=categoria,
            descricao=descricao,
            data=datetime.strptime(data, "%d/%m/%Y").date()
        )
        db.session.add(transacao)
        db.session.commit()
        return transacao.id

    return inserir


@pytest.fixture
def inserir_receita(inserir_transacao):
    def inserir(**dados):
        return inserir_transacao(tipo="receita", **dados)

    return inserir


@pytest.fixture
def inserir_despesa(inserir_transacao):
    def inserir(**dados):
        return inserir_transacao(tipo="despesa", **dados)

    return inserir


@pytest.fixture
def inserir_meta(caminho_banco):
    def inserir(categoria="Comida", limite=100):
        meta = Meta(categoria=categoria, limite=limite)
        db.session.add(meta)
        db.session.commit()
        return meta.id

    return inserir


@pytest.fixture
def data_atual():
    return datetime.now().strftime("%d/%m/%Y")


@pytest.fixture
def data_mes_anterior():
    return (datetime.now() - timedelta(days=40)).strftime("%d/%m/%Y")


@pytest.fixture
def aplicacao(caminho_banco, monkeypatch):
    return APLICACOES_TEMPORARIAS[str(caminho_banco)]


@pytest.fixture
def cliente(aplicacao):
    return aplicacao.test_client()

import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import database


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
BANCO_REAL = RAIZ_PROJETO / "finance.db"


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
    monkeypatch.setattr(database, "CAMINHO_BANCO", str(caminho))
    database.criar_tabela()
    return caminho


@pytest.fixture
def conexao_banco(caminho_banco):
    def consultar(sql, parametros=()):
        conexao = sqlite3.connect(caminho_banco)
        conexao.row_factory = sqlite3.Row
        try:
            return conexao.execute(sql, parametros).fetchall()
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
        conexao = sqlite3.connect(caminho_banco)
        try:
            cursor = conexao.execute(
                """
                INSERT INTO transacoes
                (tipo, valor, categoria, descricao, data)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tipo, valor, categoria, descricao, data)
            )
            conexao.commit()
            return cursor.lastrowid
        finally:
            conexao.close()

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
        conexao = sqlite3.connect(caminho_banco)
        try:
            cursor = conexao.execute(
                "INSERT INTO metas (categoria, limite) VALUES (?, ?)",
                (categoria, limite)
            )
            conexao.commit()
            return cursor.lastrowid
        finally:
            conexao.close()

    return inserir


@pytest.fixture
def data_atual():
    return datetime.now().strftime("%d/%m/%Y")


@pytest.fixture
def data_mes_anterior():
    return (datetime.now() - timedelta(days=40)).strftime("%d/%m/%Y")


@pytest.fixture
def aplicacao(caminho_banco, monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_PATH", raising=False)

    from app import create_app

    aplicacao_teste = create_app({
        "TESTING": True,
        "SECRET_KEY": "chave-fixa-da-fixture-de-testes",
        "DATABASE_PATH": str(caminho_banco)
    })
    database.criar_tabela()

    return aplicacao_teste


@pytest.fixture
def cliente(aplicacao):
    return aplicacao.test_client()

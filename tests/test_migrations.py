import sqlite3
from pathlib import Path

import pytest

from app import create_app
from extensions import db


APLICACOES = []


def criar_app(caminho):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "migracoes",
        "DATABASE_PATH": str(caminho)
    })
    APLICACOES.append(app)
    return app


@pytest.fixture(autouse=True)
def fechar_engines():
    yield
    for app in APLICACOES:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
    APLICACOES.clear()


def executar(app, *argumentos):
    resultado = app.test_cli_runner().invoke(args=["db", *argumentos])
    assert resultado.exit_code == 0, resultado.output
    return resultado


def criar_legado(caminho, transacoes=(), metas=()):
    conexao = sqlite3.connect(caminho)
    try:
        conexao.executescript(
            """
            CREATE TABLE transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                valor REAL,
                categoria TEXT,
                descricao TEXT,
                data TEXT
            );
            CREATE TABLE metas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT,
                limite REAL
            );
            """
        )
        conexao.executemany(
            """
            INSERT INTO transacoes
            (id, tipo, valor, categoria, descricao, data)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            transacoes
        )
        conexao.executemany(
            "INSERT INTO metas (id, categoria, limite) VALUES (?, ?, ?)",
            metas
        )
        conexao.commit()
    finally:
        conexao.close()


def consultar(caminho, sql):
    conexao = sqlite3.connect(caminho)
    try:
        return conexao.execute(sql).fetchall()
    finally:
        conexao.close()


def test_upgrade_completo_em_banco_novo_e_repeticao(tmp_path):
    caminho = tmp_path / "novo.db"
    app = criar_app(caminho)
    executar(app, "upgrade")
    assert consultar(
        caminho, "SELECT version_num FROM alembic_version"
    ) == [("0002_orm",)]
    colunas = {
        item[1]: (item[2], item[3])
        for item in consultar(caminho, "PRAGMA table_info(transacoes)")
    }
    assert colunas["valor"] == ("NUMERIC(12, 2)", 1)
    assert colunas["data"] == ("DATE", 1)

    executar(app, "upgrade")
    assert consultar(caminho, "SELECT COUNT(*) FROM transacoes") == [(0,)]


def test_upgrade_legado_preserva_ids_dados_e_datas(tmp_path):
    caminho = tmp_path / "legado.db"
    criar_legado(
        caminho,
        transacoes=[
            (7, "receita", 0.1, "Outro", "Janeiro", "31/01/2026"),
            (9, "despesa", 10.99, "Lazer", "Dezembro", "01/12/2026")
        ],
        metas=[(4, "Lazer", 9999999999.99)]
    )
    app = criar_app(caminho)
    executar(app, "stamp", "0001_legacy")
    executar(app, "upgrade")

    assert consultar(
        caminho,
        "SELECT id, tipo, valor, categoria, descricao, data "
        "FROM transacoes ORDER BY id"
    ) == [
        (7, "receita", 0.1, "Outro", "Janeiro", "2026-01-31"),
        (9, "despesa", 10.99, "Lazer", "Dezembro", "2026-12-01")
    ]
    assert consultar(
        caminho, "SELECT id, categoria, limite FROM metas"
    ) == [(4, "Lazer", 9999999999.99)]


def test_downgrade_restaura_formato_legado(tmp_path):
    caminho = tmp_path / "downgrade.db"
    criar_legado(
        caminho,
        transacoes=[
            (3, "receita", 10.25, "Outro", "Teste", "28/07/2026")
        ]
    )
    app = criar_app(caminho)
    executar(app, "stamp", "0001_legacy")
    executar(app, "upgrade")
    executar(app, "downgrade", "0001_legacy")
    assert consultar(
        caminho, "SELECT id, valor, data FROM transacoes"
    ) == [(3, 10.25, "28/07/2026")]
    tipos = {
        item[1]: item[2]
        for item in consultar(caminho, "PRAGMA table_info(transacoes)")
    }
    assert tipos["valor"] == "REAL"
    assert tipos["data"] == "TEXT"


@pytest.mark.parametrize(
    ("transacoes", "metas", "mensagem"),
    [
        (
            [(1, "receita", 10, "Outro", "Teste", "31/02/2026")],
            [],
            "transacoes id=1: data inválida"
        ),
        (
            [],
            [(1, "Comida", 100), (2, "Comida", 200)],
            "metas id=2: categoria duplicada"
        ),
        (
            [(5, "receita", float("inf"), "Outro", "Teste", "01/01/2026")],
            [],
            "transacoes id=5: valor inválido"
        ),
        (
            [(6, "receita", -1, "Outro", "Teste", "01/01/2026")],
            [],
            "transacoes id=6: valor inválido"
        )
    ]
)
def test_legado_invalido_falha_sem_alteracao_parcial(
    tmp_path,
    transacoes,
    metas,
    mensagem
):
    caminho = tmp_path / f"invalido-{len(transacoes)}-{len(metas)}.db"
    criar_legado(caminho, transacoes, metas)
    app = criar_app(caminho)
    executar(app, "stamp", "0001_legacy")
    resultado = app.test_cli_runner().invoke(args=["db", "upgrade"])

    assert resultado.exit_code != 0
    assert mensagem in str(resultado.exception)
    tabelas = {
        item[0]
        for item in consultar(
            caminho,
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert "_transacoes_orm" not in tabelas
    assert "_metas_orm" not in tabelas
    tipos = {
        item[1]: item[2]
        for item in consultar(caminho, "PRAGMA table_info(transacoes)")
    }
    assert tipos["valor"] == "REAL"
    assert tipos["data"] == "TEXT"

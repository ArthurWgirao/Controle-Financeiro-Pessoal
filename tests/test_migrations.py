import sqlite3
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app import create_app
from extensions import db
from migrations.env_helpers import (
    configurar_contexto_online,
    obter_url_offline
)
from models import Meta, Transacao
from sqlalchemy.engine import URL


APLICACOES = []
BANCO_REAL = Path(__file__).resolve().parents[1] / "finance.db"


def garantir_alvo_temporario(caminho):
    alvo = Path(caminho).resolve()
    if alvo == BANCO_REAL.resolve():
        raise RuntimeError("Migração bloqueada para o finance.db real.")
    return alvo


def criar_app(caminho):
    caminho = garantir_alvo_temporario(caminho)
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
    caminho = garantir_alvo_temporario(caminho)
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
    ) == [("0004_auth_ownership_required",)]
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
    executar(app, "upgrade", "0003_auth_ownership_nullable")

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
    colunas = {
        item[1]: item
        for item in consultar(caminho, "PRAGMA table_info(transacoes)")
    }
    assert colunas["tipo"][3] == 1
    assert colunas["valor"][2] == "NUMERIC(12, 2)"
    assert colunas["data"][2] == "DATE"
    assert any(
        indice[2] == 1
        for indice in consultar(caminho, "PRAGMA index_list(metas)")
    )

    with app.app_context():
        transacao = db.session.get(Transacao, 7)
        meta = db.session.get(Meta, 4)
        assert transacao.valor == Decimal("0.10")
        assert transacao.data == date(2026, 1, 31)
        assert meta.limite == Decimal("9999999999.99")


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
    executar(app, "upgrade", "0002_orm")
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
        ),
        (
            [(7, "outro", 10, "Outro", "Teste", "01/01/2026")],
            [],
            "transacoes id=7: tipo desconhecido"
        ),
        (
            [(8, "receita", 10.999, "Outro", "Teste", "01/01/2026")],
            [],
            "transacoes id=8: valor inválido"
        ),
        (
            [(9, "receita", None, "Outro", "Teste", "01/01/2026")],
            [],
            "transacoes id=9: valor inválido"
        ),
        (
            [(10, "receita", "", "Outro", "Teste", "01/01/2026")],
            [],
            "transacoes id=10: valor inválido"
        ),
        (
            [(11, "receita", 0, "Outro", "Teste", "01/01/2026")],
            [],
            "transacoes id=11: valor inválido"
        ),
        (
            [(12, "receita", float("nan"), "Outro", "Teste", "01/01/2026")],
            [],
            "transacoes id=12: valor inválido"
        ),
        (
            [],
            [(13, "Outro", -1)],
            "metas id=13: limite inválido"
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


@pytest.mark.parametrize(
    "ponto",
    [
        "apos_validacao",
        "apos_criar_transacoes",
        "apos_criar_temporarias",
        "apos_copiar_transacoes",
        "antes_substituicao"
    ]
)
def test_falha_intermediaria_preserva_origem_e_permite_recuperacao(
    tmp_path,
    ponto
):
    caminho = tmp_path / f"falha-{ponto}.db"
    backup = tmp_path / f"backup-{ponto}.db"
    recuperado = tmp_path / f"recuperado-{ponto}.db"
    dados = [(12, "receita", 20.25, "Outro", "Genérico", "02/02/2026")]
    criar_legado(caminho, transacoes=dados, metas=[(3, "Outro", 50)])
    app = criar_app(caminho)
    executar(app, "stamp", "0001_legacy")
    shutil.copy2(caminho, backup)

    resultado = app.test_cli_runner().invoke(
        args=["db", "-x", f"falhar_em={ponto}", "upgrade"]
    )

    assert resultado.exit_code != 0
    assert "Falha simulada" in resultado.output
    assert consultar(caminho, "PRAGMA integrity_check") == [("ok",)]
    assert consultar(
        caminho,
        "SELECT id, tipo, valor, categoria, descricao, data "
        "FROM transacoes ORDER BY id"
    ) == dados
    assert consultar(
        caminho, "SELECT version_num FROM alembic_version"
    ) == [("0001_legacy",)]

    shutil.copy2(backup, recuperado)
    app_recuperado = criar_app(recuperado)
    executar(app_recuperado, "upgrade", "0002_orm")
    assert consultar(
        recuperado, "SELECT version_num FROM alembic_version"
    ) == [("0002_orm",)]
    assert consultar(recuperado, "PRAGMA integrity_check") == [("ok",)]


def test_contexto_online_nao_armazena_nem_expoe_credencial(capsys, caplog):
    segredo = "senha%reservada"
    url = URL.create(
        "postgresql",
        username="usuario",
        password=segredo,
        host="servidor",
        database="banco"
    )

    class Engine:
        pass

    class Contexto:
        argumentos = None

        def configure(self, **argumentos):
            self.argumentos = argumentos

    engine = Engine()
    engine.url = url
    url_offline = obter_url_offline(engine)
    assert "senha" in url_offline
    assert "%%" in url_offline

    contexto = Contexto()
    conexao = object()
    configurar_contexto_online(contexto, conexao, "metadata", {})
    assert contexto.argumentos == {
        "connection": conexao,
        "target_metadata": "metadata"
    }
    assert "url" not in contexto.argumentos
    saida = capsys.readouterr()
    assert segredo not in saida.out
    assert segredo not in saida.err
    assert segredo not in caplog.text

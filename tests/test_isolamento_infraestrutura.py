import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from tests.infra_postgresql import (
    banco_postgresql_temporario,
    validar_nome_temporario,
)


def test_aplicacao_comum_usa_sqlite_temporario_sem_database_url(aplicacao, tmp_path):
    url = make_url(aplicacao.config["SQLALCHEMY_DATABASE_URI"])
    assert url.get_backend_name() == "sqlite"
    assert Path(url.database).resolve().is_relative_to(tmp_path.resolve())


@pytest.mark.parametrize("variavel", ["DATABASE_URL", "DATABASE_PATH",
                                      "POSTGRES_TRANSFER_DATABASE_URL"])
def test_variavel_perigosa_nao_redireciona_aplicacao_comum(
    monkeypatch, tmp_path, variavel
):
    monkeypatch.setenv(variavel, "postgresql://valor-invalido.example/teste")
    from app import create_app

    caminho = (tmp_path / f"isolado-{variavel}.db").resolve()
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": URL.create("sqlite", database=str(caminho)),
    })
    url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    assert url.get_backend_name() == "sqlite"
    assert Path(url.database).resolve() == caminho


def test_barreira_ambiental_ocorre_antes_da_importacao_da_aplicacao(tmp_path):
    ambiente = os.environ.copy()
    ambiente.update({
        "DATABASE_URL": "postgresql://invalido.example/protegido",
        "DATABASE_PATH": str(Path.cwd() / "finance.db"),
        "POSTGRES_TRANSFER_DATABASE_URL": "postgresql://invalido.example/outro",
    })
    codigo = (
        "import os; import tests.conftest; "
        "assert os.environ['APP_ENV']=='testing'; "
        "assert 'DATABASE_URL' not in os.environ; "
        "assert 'DATABASE_PATH' not in os.environ; "
        "assert 'POSTGRES_TRANSFER_DATABASE_URL' not in os.environ; "
        "import app"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], cwd=Path.cwd(), env=ambiente,
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert resultado.returncode == 0, resultado.stderr


@pytest.mark.parametrize("nome", [
    "sem_prefixo", "controle_financeiro_test_", "postgres", "template0",
    "template1", "controle_financeiro_test_uuid-invalido",
])
def test_nomes_nao_autorizados_sao_recusados(nome):
    with pytest.raises(RuntimeError, match="não autorizado"):
        validar_nome_temporario(nome, os.getenv("POSTGRES_DB"))


def test_url_administrativa_no_banco_de_desenvolvimento_e_recusada(
    monkeypatch, database_url_desenvolvimento
):
    url = database_url_desenvolvimento
    if not url:
        pytest.skip("DATABASE_URL de desenvolvimento não foi herdada")
    monkeypatch.setenv("POSTGRES_TEST_ADMIN_URL", url)
    with pytest.raises(RuntimeError, match="banco de desenvolvimento"):
        with banco_postgresql_temporario():
            pass


@pytest.mark.postgresql
def test_execucoes_consecutivas_e_falha_nao_deixam_bancos_residuais():
    nomes = []
    with pytest.raises(ValueError, match="falha genérica"):
        with banco_postgresql_temporario() as (_, nome):
            nomes.append(nome)
            raise ValueError("falha genérica")
    with banco_postgresql_temporario() as (_, nome):
        nomes.append(nome)
    assert len(set(nomes)) == 2

    admin = os.getenv("POSTGRES_TEST_ADMIN_URL")
    if not admin:
        pytest.skip("POSTGRES_TEST_ADMIN_URL não configurada")
    engine = create_engine(admin)
    try:
        with engine.connect() as conexao:
            restantes = conexao.execute(text(
                "SELECT datname FROM pg_database WHERE datname = ANY(:nomes)"
            ), {"nomes": nomes}).scalars().all()
            assert restantes == []
    finally:
        engine.dispose()

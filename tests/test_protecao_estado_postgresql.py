from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text

from app import create_app
from extensions import db
from tests.infra_postgresql import (
    banco_postgresql_temporario,
    comparar_estados_postgresql,
    estado_postgresql_desenvolvimento,
    validar_estado_postgresql,
)


pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.usefixtures("postgres_test_admin_url"),
]


@pytest.fixture
def banco_protegido_temporario():
    with banco_postgresql_temporario() as (url, nome):
        app = create_app({
            "TESTING": True,
            "SECRET_KEY": "estado-postgresql-generico",
            "SQLALCHEMY_DATABASE_URI": url,
        })
        resultado = app.test_cli_runner().invoke(args=["db", "upgrade"])
        assert resultado.exit_code == 0, resultado.output
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        yield url, nome


def preencher_generico(url):
    engine = create_engine(url)
    try:
        with engine.begin() as conexao:
            conexao.execute(text(
                "INSERT INTO usuarios(id,nome,email,senha_hash,ativo,criado_em) VALUES "
                "(5,'Pessoa Genérica A','a@example.test','hash-generico-a',true,:data),"
                "(9,'Pessoa Genérica B','b@example.test','hash-generico-b',false,:data)"
            ), {"data": datetime(2026, 1, 1, tzinfo=timezone.utc)})
            conexao.execute(text(
                "INSERT INTO transacoes(id,usuario_id,tipo,valor,categoria,descricao,data) "
                "VALUES (10,5,'receita',10.25,'Outro','Genérica A','2026-01-02'),"
                "(20,9,'despesa',2.50,'Comida','Genérica B','2026-01-03')"
            ))
            conexao.execute(text(
                "INSERT INTO metas(id,usuario_id,categoria,limite) "
                "VALUES (7,5,'Comida',100.00)"
            ))
            for tabela, valor in (("usuarios", 9), ("transacoes", 20), ("metas", 7)):
                sequence = conexao.execute(text(
                    "SELECT pg_get_serial_sequence(:tabela, 'id')"
                ), {"tabela": tabela}).scalar_one()
                conexao.execute(text(
                    "SELECT setval(CAST(:nome AS regclass), :valor, true)"
                ), {"nome": sequence, "valor": valor})
    finally:
        engine.dispose()


def executar_sql(url, comando):
    engine = create_engine(url)
    try:
        with engine.begin() as conexao:
            conexao.execute(text(comando))
    finally:
        engine.dispose()


def snapshot(url):
    return estado_postgresql_desenvolvimento(url)


def test_estado_vazio_valido_e_estavel(banco_protegido_temporario):
    url, _ = banco_protegido_temporario
    inicial = snapshot(url)
    validar_estado_postgresql(inicial, permitir_temporario=True)
    comparar_estados_postgresql(inicial, snapshot(url))


def test_estado_preenchido_valido_estavel_e_sanitizado(banco_protegido_temporario):
    url, _ = banco_protegido_temporario
    preencher_generico(url)
    inicial = snapshot(url)
    validar_estado_postgresql(inicial, permitir_temporario=True)
    assert inicial["counts"] == (2, 2, 1)
    comparar_estados_postgresql(inicial, snapshot(url))
    representacao = repr(inicial)
    for sensivel in (
        "Pessoa Genérica A", "a@example.test", "hash-generico-a",
        "Genérica A", "Comida",
    ):
        assert sensivel not in representacao


@pytest.mark.parametrize("comando", [
    "INSERT INTO transacoes(usuario_id,tipo,valor,categoria,descricao,data) "
    "VALUES(5,'receita',1.00,'Outro','Nova genérica','2026-02-01')",
    "UPDATE transacoes SET valor=11.00 WHERE id=10",
    "DELETE FROM transacoes WHERE id=20",
    "UPDATE transacoes SET usuario_id=9 WHERE id=10",
])
def test_detecta_mutacoes_de_dados(banco_protegido_temporario, comando):
    url, _ = banco_protegido_temporario
    preencher_generico(url)
    inicial = snapshot(url)
    executar_sql(url, comando)
    with pytest.raises(AssertionError, match="PostgreSQL protegido foi alterado"):
        comparar_estados_postgresql(inicial, snapshot(url))


def test_detecta_alteracao_apenas_de_sequence(banco_protegido_temporario):
    url, _ = banco_protegido_temporario
    preencher_generico(url)
    inicial = snapshot(url)
    executar_sql(url, "SELECT setval(pg_get_serial_sequence('transacoes','id'), 99, true)")
    with pytest.raises(AssertionError, match="schema"):
        comparar_estados_postgresql(inicial, snapshot(url))


def test_detecta_alteracao_de_schema(banco_protegido_temporario):
    url, _ = banco_protegido_temporario
    inicial = snapshot(url)
    executar_sql(url, "CREATE INDEX ix_teste_estado ON transacoes (categoria)")
    with pytest.raises(AssertionError, match="schema"):
        comparar_estados_postgresql(inicial, snapshot(url))


def test_revisao_invalida_falha_antes_da_protecao(banco_protegido_temporario):
    url, _ = banco_protegido_temporario
    executar_sql(url, "UPDATE alembic_version SET version_num='revisao_invalida'")
    with pytest.raises(AssertionError, match="Revisão inválida"):
        validar_estado_postgresql(snapshot(url), permitir_temporario=True)

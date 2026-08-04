"""Criação e remoção fail-safe de bancos PostgreSQL exclusivos dos testes."""

import os
import re
import hashlib
import json
from contextlib import contextmanager
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL, make_url
from sqlalchemy import create_engine, inspect, text


PREFIXO = "controle_financeiro_test_"
SISTEMA = frozenset({"postgres", "template0", "template1"})


def validar_nome_temporario(nome, banco_desenvolvimento=None):
    if not isinstance(nome, str) or not re.fullmatch(
            rf"{PREFIXO}([0-9a-f]{{32}})", nome):
        raise RuntimeError("Nome de banco temporário não autorizado.")
    UUID(nome[len(PREFIXO):])
    if nome in SISTEMA or nome == banco_desenvolvimento:
        raise RuntimeError("Banco protegido não pode ser alvo de testes.")
    return nome


def _configuracao_admin():
    valor = os.getenv("POSTGRES_TEST_ADMIN_URL")
    if not valor:
        raise RuntimeError("POSTGRES_TEST_ADMIN_URL não configurada.")
    url = make_url(valor)
    if (url.get_backend_name() != "postgresql" or not url.host
            or not url.database or not url.username or url.password is None):
        raise RuntimeError("URL administrativa de testes inválida.")
    banco_desenvolvimento = os.getenv("POSTGRES_DB")
    if not banco_desenvolvimento:
        raise RuntimeError("POSTGRES_DB não identifica o banco protegido.")
    if url.database == banco_desenvolvimento:
        raise RuntimeError("URL administrativa aponta ao banco de desenvolvimento.")
    return url, banco_desenvolvimento


def _parametros(url):
    return {
        "host": url.host, "port": url.port, "dbname": url.database,
        "user": url.username, "password": url.password, "autocommit": True,
    }


def estado_postgresql_desenvolvimento(url_valor):
    """Obtém uma fotografia lógica/estrutural sem modificar o banco."""
    url = make_url(url_valor)
    engine = create_engine(url)
    try:
        with engine.connect() as conexao:
            inspetor = inspect(conexao)
            tabelas = sorted(inspetor.get_table_names())
            schema = {}
            for tabela in tabelas:
                sequence = None
                estado_sequence = None
                if tabela in {"usuarios", "transacoes", "metas"}:
                    sequence = conexao.execute(
                        text("SELECT pg_get_serial_sequence(:t, 'id')"),
                        {"t": tabela},
                    ).scalar_one_or_none()
                if sequence:
                    citado = ".".join(
                        conexao.dialect.identifier_preparer.quote(parte)
                        for parte in sequence.split(".")
                    )
                    estado_sequence = tuple(conexao.execute(text(
                        f"SELECT last_value, is_called FROM {citado}"
                    )).one())
                schema[tabela] = {
                    "columns": tuple(
                        (c["name"], str(c["type"]), c["nullable"])
                        for c in inspetor.get_columns(tabela)
                    ),
                    "pk": inspetor.get_pk_constraint(tabela),
                    "fks": inspetor.get_foreign_keys(tabela),
                    "unique": inspetor.get_unique_constraints(tabela),
                    "checks": inspetor.get_check_constraints(tabela),
                    "indexes": inspetor.get_indexes(tabela),
                    "sequence": sequence,
                    "sequence_state": estado_sequence,
                }
            canonico = json.dumps(
                schema, sort_keys=True, default=str, separators=(",", ":")
            )
            tabelas_dados = ("usuarios", "transacoes", "metas")
            return {
                "database": conexao.execute(
                    text("SELECT current_database()")
                ).scalar_one(),
                "revision": conexao.execute(text(
                    "SELECT version_num FROM alembic_version"
                )).scalar_one(),
                "counts": tuple(conexao.execute(
                    text(f"SELECT count(*) FROM {t}")
                ).scalar_one() for t in tabelas_dados),
                "ids": tuple(tuple(conexao.execute(
                    text(f"SELECT id FROM {t} ORDER BY id")
                ).scalars()) for t in tabelas_dados),
                "schema_sha256": hashlib.sha256(canonico.encode()).hexdigest(),
                "schema": canonico,
            }
    finally:
        engine.dispose()


@contextmanager
def banco_postgresql_temporario(nome=None):
    admin, desenvolvimento = _configuracao_admin()
    nome = validar_nome_temporario(
        nome or f"{PREFIXO}{uuid4().hex}", desenvolvimento
    )
    parametros = _parametros(admin)
    criado = False
    with psycopg.connect(**parametros) as conexao:
        atual = conexao.execute("SELECT current_database()").fetchone()[0]
        if atual != admin.database or atual == desenvolvimento:
            raise RuntimeError("Conexão administrativa ambígua ou protegida.")
        conexao.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome)))
        criado = True

    url = URL.create(
        "postgresql+psycopg", username=admin.username, password=admin.password,
        host=admin.host, port=admin.port, database=nome,
    )
    try:
        with psycopg.connect(**{**parametros, "dbname": nome}) as alvo:
            if alvo.execute("SELECT current_database()").fetchone()[0] != nome:
                raise RuntimeError("Banco temporário resolvido incorretamente.")
        yield url, nome
    finally:
        if criado:
            validar_nome_temporario(nome, desenvolvimento)
            with psycopg.connect(**parametros) as conexao:
                if conexao.execute("SELECT current_database()").fetchone()[0] != admin.database:
                    raise RuntimeError("Conexão de limpeza não é administrativa.")
                conexao.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=%s AND pid<>pg_backend_pid()", (nome,)
                )
                validar_nome_temporario(nome, desenvolvimento)
                conexao.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(nome)))

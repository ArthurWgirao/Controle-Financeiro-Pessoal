import hashlib
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from migracao_dados import ErroConflito, PONTOS_FALHA, transferir
from tests.infra_postgresql import banco_postgresql_temporario as banco_seguro
pytestmark = pytest.mark.postgresql
def hash_arquivo(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def origem_generica(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("origem_transferencia") / "origem.db"
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "origem-generica",
        "SQLALCHEMY_DATABASE_URI": URL.create(
            "sqlite", database=str(caminho.resolve())
        ),
    })
    resultado = app.test_cli_runner().invoke(args=["db", "upgrade"])
    assert resultado.exit_code == 0, resultado.output
    conexao = sqlite3.connect(caminho)
    try:
        usuarios = [
            (5, "Pessoa Ativa", "ativa@example.test",
             generate_password_hash("senha-generica"), 1,
             "2026-08-01 10:00:00+00:00"),
            (9, "Pessoa Inativa", "inativa@example.test",
             generate_password_hash("outra-senha"), 0,
             "2026-08-02 11:00:00+00:00"),
        ]
        conexao.executemany(
            "INSERT INTO usuarios(id,nome,email,senha_hash,ativo,criado_em) "
            "VALUES(?,?,?,?,?,?)", usuarios
        )
        conexao.executemany(
            "INSERT INTO transacoes(id,usuario_id,tipo,valor,categoria,descricao,data) "
            "VALUES(?,?,?,?,?,?,?)",
            [
                (10, 5, "receita", "0.10", "Outro", "Genérica A", "2026-07-01"),
                (20, 5, "despesa", "0.20", "Comida", "Genérica B", "2026-07-02"),
                (30, 9, "receita", "9999999999.99", "Outro", "Genérica C", "2026-08-01"),
            ],
        )
        conexao.executemany(
            "INSERT INTO metas(id,usuario_id,categoria,limite) VALUES(?,?,?,?)",
            [(7, 5, "Comida", "100.00"), (11, 9, "Comida", "200.00")],
        )
        conexao.commit()
    finally:
        conexao.close()
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    return caminho


@contextmanager
def banco_postgresql_temporario():
    try:
        with banco_seguro() as (url, _):
            app = create_app({
                "TESTING": True,
                "SECRET_KEY": "transferencia-generica",
                "WTF_CSRF_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": url,
            })
            resultado = app.test_cli_runner().invoke(args=["db", "upgrade"])
            assert resultado.exit_code == 0, resultado.output
            try:
                yield url, app
            finally:
                with app.app_context():
                    db.session.remove()
                    db.engine.dispose()
    except RuntimeError as erro:
        if "não configurada" in str(erro):
            pytest.skip(str(erro))
        raise


def estado_destino(url):
    engine = create_engine(url)
    try:
        with engine.connect() as conexao:
            contagens = tuple(conexao.execute(
                text(f"SELECT count(*) FROM {t}")
            ).scalar_one() for t in ("usuarios", "transacoes", "metas"))
            sequences = {}
            for tabela in ("usuarios", "transacoes", "metas"):
                nome = conexao.execute(text(
                    "SELECT pg_get_serial_sequence(:t, 'id')"
                ), {"t": tabela}).scalar_one()
                valor = conexao.execute(text(
                    "SELECT last_value,is_called FROM " + nome
                )).one()
                sequences[tabela] = tuple(valor)
            return contagens, sequences
    finally:
        engine.dispose()


def test_dry_run_transferencia_idempotencia_e_smoke(origem_generica, monkeypatch):
    hash_inicial = hash_arquivo(origem_generica)
    with banco_postgresql_temporario() as (url, app):
        antes = estado_destino(url)
        resultado = transferir(origem_generica.resolve(), url, dry_run=True)
        assert resultado.dry_run and estado_destino(url) == antes

        monkeypatch.setenv("POSTGRES_TRANSFER_DATABASE_URL", url.render_as_string(hide_password=False))
        runner = app.test_cli_runner()
        sem_modo = runner.invoke(args=["transfer-sqlite-to-postgres", "--source", str(origem_generica)])
        assert sem_modo.exit_code == 2
        dry = runner.invoke(args=["transfer-sqlite-to-postgres", "--source", str(origem_generica), "--dry-run"])
        assert dry.exit_code == 0
        assert "NENHUM DADO TRANSFERIDO" in dry.output
        assert url.password not in dry.output

        confirmacao = runner.invoke(args=[
            "transfer-sqlite-to-postgres", "--source", str(origem_generica),
            "--confirm-transfer",
        ])
        assert confirmacao.exit_code == 0, confirmacao.output
        assert "TRANSFERÊNCIA CONCLUÍDA E VALIDADA" in confirmacao.output
        assert url.password not in confirmacao.output
        contagens, sequences = estado_destino(url)
        assert contagens == (2, 3, 2)
        assert sequences["usuarios"] == (9, True)
        assert sequences["transacoes"] == (30, True)
        assert sequences["metas"] == (11, True)
        with pytest.raises(ErroConflito):
            transferir(origem_generica.resolve(), url)
        estado_preenchido = estado_destino(url)
        with pytest.raises(ErroConflito):
            transferir(origem_generica.resolve(), url, dry_run=True)
        assert estado_destino(url) == estado_preenchido

        engine = create_engine(url)
        try:
            with engine.begin() as conexao:
                novo = conexao.execute(text(
                    "INSERT INTO transacoes(usuario_id,tipo,valor,categoria,descricao,data) "
                    "VALUES(5,'receita',1.00,'Outro','Nova genérica','2026-08-03') RETURNING id"
                )).scalar_one()
                assert novo == 31
        finally:
            engine.dispose()

        cliente = app.test_client()
        resposta = cliente.post("/login", data={
            "email": "ativa@example.test", "senha": "senha-generica"
        })
        assert resposta.status_code == 302
        for rota in ("/", "/receitas", "/despesas", "/metas", "/relatorios"):
            assert cliente.get(rota).status_code == 200
        assert "Genérica C" not in cliente.get("/receitas").get_data(as_text=True)
    assert hash_arquivo(origem_generica) == hash_inicial


def test_tabela_vazia_preserva_sequence_inicial(origem_generica, tmp_path):
    origem_sem_metas = tmp_path / "origem-sem-metas.db"
    shutil.copy2(origem_generica, origem_sem_metas)
    with sqlite3.connect(origem_sem_metas) as conexao:
        conexao.execute("DELETE FROM metas")
        conexao.commit()

    with banco_postgresql_temporario() as (url, _):
        sequence_antes = estado_destino(url)[1]["metas"]
        transferir(origem_sem_metas.resolve(), url)
        contagens, sequences = estado_destino(url)
        assert contagens == (2, 3, 0)
        assert sequences["metas"] == sequence_antes

        engine = create_engine(url)
        try:
            with engine.begin() as conexao:
                proximo = conexao.execute(text(
                    "INSERT INTO metas(usuario_id,categoria,limite) "
                    "VALUES(5,'Comida',10.00) RETURNING id"
                )).scalar_one()
                assert proximo == 1
        finally:
            engine.dispose()


@pytest.mark.parametrize("ponto", sorted(PONTOS_FALHA))
def test_falhas_restauram_dados_sequences_e_permitam_repeticao(
    origem_generica, ponto
):
    hash_inicial = hash_arquivo(origem_generica)
    with banco_postgresql_temporario() as (url, _):
        antes = estado_destino(url)
        with pytest.raises(RuntimeError, match="Falha simulada"):
            transferir(origem_generica.resolve(), url, falhar_em=ponto)
        assert estado_destino(url) == antes
        assert hash_arquivo(origem_generica) == hash_inicial
        resultado = transferir(origem_generica.resolve(), url)
        assert (resultado.usuarios, resultado.transacoes, resultado.metas) == (2, 3, 2)

import sqlite3

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from migrations.sequence_helpers import capturar_sequencia, restaurar_sequencia
from models import Meta, Transacao, Usuario
from tests.test_migrations import consultar, criar_app, criar_legado, executar


def executar_sql(caminho, sql, parametros=()):
    conexao = sqlite3.connect(caminho)
    try:
        conexao.execute(sql, parametros)
        conexao.commit()
    finally:
        conexao.close()


def ddl(caminho, tabela):
    conexao = sqlite3.connect(caminho)
    try:
        return conexao.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (tabela,)
        ).fetchone()[0]
    finally:
        conexao.close()


def sequencia(caminho, tabela):
    conexao = sqlite3.connect(caminho)
    try:
        registro = conexao.execute(
            "SELECT seq FROM sqlite_sequence WHERE name=?", (tabela,)
        ).fetchone()
        return registro[0] if registro else None
    finally:
        conexao.close()


def preparar_0002_com_historico(caminho):
    criar_legado(
        caminho,
        transacoes=[
            (10, "receita", 100, "Outro", "Genérico", "01/07/2026"),
            (12, "despesa", 20, "Comida", "Genérico", "02/07/2026")
        ]
    )
    app = criar_app(caminho)
    executar(app, "stamp", "0001_legacy")
    executar(app, "upgrade", "0002_orm")
    executar_sql(caminho, "UPDATE sqlite_sequence SET seq=20 WHERE name='transacoes'")
    executar_sql(
        caminho,
        "INSERT INTO metas(id,categoria,limite) VALUES(8,'Lazer',100)"
    )
    executar_sql(caminho, "DELETE FROM metas WHERE id=8")
    return app


def test_0003_preserva_autoincrement_e_historico_vazio(tmp_path):
    caminho = tmp_path / "sequencia-0003.db"
    app = preparar_0002_com_historico(caminho)
    executar(app, "upgrade", "0003_auth_ownership_nullable")

    assert "AUTOINCREMENT" in ddl(caminho, "transacoes")
    assert "AUTOINCREMENT" in ddl(caminho, "metas")
    assert "AUTOINCREMENT" in ddl(caminho, "usuarios")
    assert sequencia(caminho, "transacoes") == 20
    assert sequencia(caminho, "metas") == 8
    assert sequencia(caminho, "usuarios") is None
    assert consultar(caminho, "SELECT id FROM transacoes ORDER BY id") == [(10,), (12,)]
    assert consultar(caminho, "PRAGMA integrity_check") == [("ok",)]


def test_0004_e_downgrades_preservam_sequencias(tmp_path):
    caminho = tmp_path / "sequencia-ciclo.db"
    app = preparar_0002_com_historico(caminho)
    executar(app, "upgrade", "0003_auth_ownership_nullable")
    executar_sql(
        caminho,
        "INSERT INTO usuarios(id,nome,email,senha_hash,ativo,criado_em) "
        "VALUES(5,'Pessoa','pessoa@example.test','hash-generico',1,'2026-08-03 00:00:00')"
    )
    executar_sql(caminho, "UPDATE transacoes SET usuario_id=5")
    executar(app, "upgrade", "0004_auth_ownership_required")

    assert sequencia(caminho, "usuarios") == 5
    assert sequencia(caminho, "transacoes") == 20
    assert sequencia(caminho, "metas") == 8
    for tabela in ("usuarios", "transacoes", "metas"):
        assert "AUTOINCREMENT" in ddl(caminho, tabela)

    executar(app, "downgrade", "0003_auth_ownership_nullable")
    assert sequencia(caminho, "transacoes") == 20
    assert sequencia(caminho, "metas") == 8
    executar(app, "downgrade", "0002_orm")
    assert sequencia(caminho, "transacoes") == 20
    assert sequencia(caminho, "metas") == 8
    assert consultar(caminho, "SELECT id FROM transacoes ORDER BY id") == [(10,), (12,)]
    assert consultar(caminho, "PRAGMA integrity_check") == [("ok",)]


def test_sequencia_abaixo_do_id_e_acima_do_id_nao_regride(tmp_path):
    caminho = tmp_path / "limites-sequencia.db"
    app = preparar_0002_com_historico(caminho)
    executar_sql(caminho, "UPDATE sqlite_sequence SET seq=2 WHERE name='transacoes'")
    executar(app, "upgrade", "0003_auth_ownership_nullable")
    assert sequencia(caminho, "transacoes") == 12

    executar_sql(caminho, "UPDATE sqlite_sequence SET seq=30 WHERE name='transacoes'")
    executar(app, "downgrade", "0002_orm")
    assert sequencia(caminho, "transacoes") == 30


def test_head_nao_reutiliza_ids_excluidos(tmp_path):
    caminho = tmp_path / "nao-reutiliza.db"
    app = criar_app(caminho)
    executar(app, "upgrade")
    conexao = sqlite3.connect(caminho)
    try:
        conexao.execute(
            "INSERT INTO usuarios(nome,email,senha_hash,ativo,criado_em) "
            "VALUES('Pessoa','um@example.test','hash',1,'2026-08-03')"
        )
        usuario_antigo = conexao.execute("SELECT last_insert_rowid()").fetchone()[0]
        conexao.execute("DELETE FROM usuarios WHERE id=?", (usuario_antigo,))
        conexao.execute(
            "INSERT INTO usuarios(nome,email,senha_hash,ativo,criado_em) "
            "VALUES('Pessoa','dois@example.test','hash',1,'2026-08-03')"
        )
        usuario_novo = conexao.execute("SELECT last_insert_rowid()").fetchone()[0]
        for tabela, colunas, valores in (
            ("transacoes", "usuario_id,tipo,valor,categoria,descricao,data", (usuario_novo,"receita",10,"Outro","Genérico","2026-08-03")),
            ("metas", "usuario_id,categoria,limite", (usuario_novo,"Comida",100)),
        ):
            marcas = ",".join("?" for _ in valores)
            conexao.execute(f"INSERT INTO {tabela}({colunas}) VALUES({marcas})", valores)
            antigo = conexao.execute("SELECT last_insert_rowid()").fetchone()[0]
            conexao.execute(f"DELETE FROM {tabela} WHERE id=?", (antigo,))
            conexao.execute(f"INSERT INTO {tabela}({colunas}) VALUES({marcas})", valores)
            novo = conexao.execute("SELECT last_insert_rowid()").fetchone()[0]
            assert novo > antigo
        assert usuario_novo > usuario_antigo
        conexao.commit()
    finally:
        conexao.close()


def test_helpers_nao_executam_sql_fora_do_sqlite():
    class ConexaoFalsa:
        class Dialeto:
            name = "postgresql"
        dialect = Dialeto()
        def execute(self, *args, **kwargs):
            raise AssertionError("SQL SQLite não pode ser executado")

    conexao = ConexaoFalsa()
    assert capturar_sequencia(conexao, "transacoes") is None
    restaurar_sequencia(conexao, "transacoes", None)
    for tabela in (Usuario.__table__, Transacao.__table__, Meta.__table__):
        assert "CREATE TABLE" in str(CreateTable(tabela).compile(dialect=postgresql.dialect()))

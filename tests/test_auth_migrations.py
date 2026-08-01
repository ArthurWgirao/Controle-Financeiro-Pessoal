from datetime import date
from decimal import Decimal

from extensions import db
from models import Meta, Transacao, Usuario
from tests.test_migrations import consultar, criar_app, criar_legado, executar


def test_fluxo_legado_0003_associacao_e_head(tmp_path):
    caminho = tmp_path / "legado-auth.db"
    criar_legado(
        caminho,
        transacoes=[
            (10, "receita", 100.25, "Outro", "Legado A", "01/07/2026"),
            (11, "despesa", 20.00, "Comida", "Legado B", "02/07/2026")
        ],
        metas=[(5, "Comida", 80.00)]
    )
    app = criar_app(caminho)
    executar(app, "stamp", "0001_legacy")
    executar(app, "upgrade", "0003_auth_ownership_nullable")
    assert consultar(caminho, "SELECT usuario_id FROM transacoes ORDER BY id") == [(None,), (None,)]

    criado = app.test_cli_runner().invoke(
        args=["create-user", "--nome", "Pessoa Migração", "--email", "migracao@example.test"],
        input="senha-segura\nsenha-segura\n"
    )
    assert criado.exit_code == 0
    recusado = app.test_cli_runner().invoke(
        args=["assign-legacy-data", "--email", "migracao@example.test"]
    )
    assert recusado.exit_code != 0
    associado = app.test_cli_runner().invoke(
        args=["assign-legacy-data", "--email", "MIGRACAO@example.test", "--confirm"]
    )
    assert associado.exit_code == 0
    repetido = app.test_cli_runner().invoke(
        args=["assign-legacy-data", "--email", "migracao@example.test", "--confirm"]
    )
    assert repetido.exit_code == 0
    assert "0 transações e 0 metas" in repetido.output

    executar(app, "upgrade")
    assert consultar(caminho, "SELECT version_num FROM alembic_version") == [("0004_auth_ownership_required",)]
    assert consultar(caminho, "SELECT id FROM transacoes ORDER BY id") == [(10,), (11,)]
    assert consultar(caminho, "SELECT data, valor FROM transacoes ORDER BY id") == [
        ("2026-07-01", 100.25), ("2026-07-02", 20)
    ]
    assert all(item[3] == 1 for item in consultar(caminho, "PRAGMA table_info(transacoes)") if item[1] == "usuario_id")


def test_0004_falha_antes_do_ddl_com_orfaos(tmp_path):
    caminho = tmp_path / "orfaos.db"
    criar_legado(caminho, transacoes=[(3, "receita", 10, "Outro", "Legado", "01/01/2026")])
    app = criar_app(caminho)
    executar(app, "stamp", "0001_legacy")
    executar(app, "upgrade", "0003_auth_ownership_nullable")
    resultado = app.test_cli_runner().invoke(args=["db", "upgrade"])
    assert resultado.exit_code != 0
    assert "sem proprietário" in resultado.output
    assert consultar(caminho, "SELECT version_num FROM alembic_version") == [("0003_auth_ownership_nullable",)]
    coluna = [item for item in consultar(caminho, "PRAGMA table_info(transacoes)") if item[1] == "usuario_id"][0]
    assert coluna[3] == 0


def test_downgrade_bloqueia_colisao_global_de_metas(tmp_path):
    caminho = tmp_path / "colisao.db"
    app = criar_app(caminho)
    executar(app, "upgrade")
    with app.app_context():
        primeiro = Usuario(nome="Um", email="um@example.test")
        primeiro.definir_senha("senha-segura")
        segundo = Usuario(nome="Dois", email="dois@example.test")
        segundo.definir_senha("senha-segura")
        db.session.add_all([primeiro, segundo])
        db.session.flush()
        db.session.add_all([
            Meta(usuario_id=primeiro.id, categoria="Comida", limite=Decimal("10")),
            Meta(usuario_id=segundo.id, categoria="Comida", limite=Decimal("20"))
        ])
        db.session.commit()
    executar(app, "downgrade", "0003_auth_ownership_nullable")
    resultado = app.test_cli_runner().invoke(args=["db", "downgrade", "0002_orm"])
    assert resultado.exit_code != 0
    assert "Downgrade bloqueado" in resultado.output
    assert consultar(caminho, "SELECT COUNT(*) FROM metas")[0][0] == 2

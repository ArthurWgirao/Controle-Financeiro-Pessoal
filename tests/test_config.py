import importlib

import pytest
from flask import Flask

from config import CHAVE_DESENVOLVIMENTO


def limpar_ambiente(monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    for nome in [
        "APP_ENV", "SECRET_KEY", "DATABASE_PATH", "DATABASE_URL"
    ]:
        monkeypatch.delenv(nome, raising=False)


def test_ambiente_padrao_e_desenvolvimento(monkeypatch):
    limpar_ambiente(monkeypatch)
    from app import create_app

    aplicacao = create_app()
    assert aplicacao.testing is False
    assert aplicacao.debug is False
    assert aplicacao.secret_key == CHAVE_DESENVOLVIMENTO
    assert aplicacao.config["DATABASE_PATH"] == "finance.db"
    assert aplicacao.config["SESSION_COOKIE_SECURE"] is False
    assert aplicacao.config["REMEMBER_COOKIE_SECURE"] is False
    assert aplicacao.config["SESSION_COOKIE_HTTPONLY"] is True
    assert aplicacao.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert aplicacao.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert aplicacao.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"


def test_ambiente_testing(monkeypatch, tmp_path):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "testing.db"))
    from app import create_app

    aplicacao = create_app()
    assert aplicacao.testing is True
    assert aplicacao.secret_key == "chave-fixa-exclusiva-para-testes"
    assert aplicacao.config["SESSION_COOKIE_SECURE"] is False
    assert aplicacao.config["REMEMBER_COOKIE_SECURE"] is False
    assert aplicacao.config["SESSION_COOKIE_HTTPONLY"] is True
    assert aplicacao.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert aplicacao.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert aplicacao.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"


def test_app_env_invalido_falha_com_mensagem(monkeypatch):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "desconhecido")
    from app import create_app

    with pytest.raises(ValueError, match="APP_ENV inválido"):
        create_app()


def test_dicionario_sobrescreve_ambiente(monkeypatch, tmp_path):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "chave-do-ambiente")
    monkeypatch.setenv("DATABASE_PATH", "ambiente.db")
    from app import create_app

    caminho = tmp_path / "prioritario.db"
    aplicacao = create_app({
        "TESTING": False,
        "SECRET_KEY": "chave-do-dicionario",
        "DATABASE_PATH": str(caminho)
    })
    assert aplicacao.testing is False
    assert aplicacao.secret_key == "chave-do-dicionario"
    assert aplicacao.config["DATABASE_PATH"] == str(caminho)
    assert str(caminho.resolve()) in str(
        aplicacao.config["SQLALCHEMY_DATABASE_URI"]
    )


def test_variaveis_de_ambiente_sao_aplicadas(monkeypatch, tmp_path):
    limpar_ambiente(monkeypatch)
    caminho = tmp_path / "ambiente.db"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "chave-vinda-do-ambiente")
    monkeypatch.setenv("DATABASE_PATH", str(caminho))
    from app import create_app

    aplicacao = create_app()
    assert aplicacao.secret_key == "chave-vinda-do-ambiente"
    assert aplicacao.config["DATABASE_PATH"] == str(caminho)


@pytest.mark.parametrize("chave", [None, ""])
def test_producao_rejeita_chave_ausente_ou_vazia(
    monkeypatch,
    chave
):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    if chave is not None:
        monkeypatch.setenv("SECRET_KEY", chave)
    from app import create_app

    with pytest.raises(RuntimeError, match="SECRET_KEY segura"):
        create_app()


def test_producao_rejeita_chave_de_desenvolvimento(monkeypatch):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", CHAVE_DESENVOLVIMENTO)
    from app import create_app

    with pytest.raises(RuntimeError, match="SECRET_KEY segura"):
        create_app()


def test_producao_com_chave_valida_e_debug_desativado(
    monkeypatch,
):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    from app import create_app

    aplicacao = create_app({
        "SECRET_KEY": "uma-chave-segura-de-producao",
        "SQLALCHEMY_DATABASE_URI": "postgresql://usuario:senha@inacessivel.example/producao",
        "DEBUG": True,
        "TESTING": True,
        "SESSION_COOKIE_SECURE": False,
        "SESSION_COOKIE_HTTPONLY": False,
        "SESSION_COOKIE_SAMESITE": None,
        "REMEMBER_COOKIE_SECURE": False,
        "REMEMBER_COOKIE_HTTPONLY": False,
        "REMEMBER_COOKIE_SAMESITE": None,
    })
    assert aplicacao.secret_key == "uma-chave-segura-de-producao"
    assert aplicacao.testing is False
    assert aplicacao.debug is False
    assert aplicacao.config["SESSION_COOKIE_SECURE"] is True
    assert aplicacao.config["SESSION_COOKIE_HTTPONLY"] is True
    assert aplicacao.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert aplicacao.config["REMEMBER_COOKIE_SECURE"] is True
    assert aplicacao.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert aplicacao.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"


def test_factory_nao_cria_banco_antes_do_request(
    monkeypatch,
    tmp_path
):
    limpar_ambiente(monkeypatch)
    from app import create_app

    caminho = tmp_path / "sob-demanda.db"
    create_app({"DATABASE_PATH": str(caminho)})
    assert not caminho.exists()


def test_primeiro_request_exige_migracao_previa(monkeypatch, tmp_path):
    limpar_ambiente(monkeypatch)
    from app import create_app

    caminho = tmp_path / "primeiro-request.db"
    aplicacao = create_app({
        "TESTING": True,
        "SECRET_KEY": "teste",
        "DATABASE_PATH": str(caminho)
    })
    resposta = aplicacao.test_client().get("/")
    assert resposta.status_code == 302
    assert "/login" in resposta.headers["Location"]
    from extensions import db
    with aplicacao.app_context():
        db.session.remove()
        db.engine.dispose()


def test_duas_instancias_sao_independentes(monkeypatch, tmp_path):
    limpar_ambiente(monkeypatch)
    from app import create_app

    caminho_primeira = tmp_path / "primeira.db"
    caminho_segunda = tmp_path / "segunda.db"
    primeira = create_app({
        "SECRET_KEY": "primeira",
        "DATABASE_PATH": str(caminho_primeira)
    })
    segunda = create_app({
        "SECRET_KEY": "segunda",
        "DATABASE_PATH": str(caminho_segunda)
    })
    assert primeira is not segunda
    assert primeira.secret_key == "primeira"
    assert segunda.secret_key == "segunda"
    from extensions import db
    for aplicacao in (primeira, segunda):
        with aplicacao.app_context():
            db.create_all()
        assert aplicacao.test_client().get("/").status_code == 302
        with aplicacao.app_context():
            db.session.remove()
            db.engine.dispose()
    assert caminho_primeira.exists()
    assert caminho_segunda.exists()


def test_rotas_nao_sao_duplicadas_entre_instancias(
    monkeypatch,
    tmp_path
):
    limpar_ambiente(monkeypatch)
    from app import create_app

    primeira = create_app({"DATABASE_PATH": str(tmp_path / "a.db")})
    segunda = create_app({"DATABASE_PATH": str(tmp_path / "b.db")})

    regras_primeira = [
        regra.rule for regra in primeira.url_map.iter_rules()
    ]
    regras_segunda = [
        regra.rule for regra in segunda.url_map.iter_rules()
    ]
    assert regras_primeira == regras_segunda
    assert len(regras_primeira) == len(set(regras_primeira))


def test_todas_as_rotas_e_metodos_foram_preservados(
    monkeypatch,
    tmp_path
):
    limpar_ambiente(monkeypatch)
    from app import create_app

    aplicacao = create_app({
        "DATABASE_PATH": str(tmp_path / "rotas.db")
    })
    regras = {
        (
            regra.rule,
            tuple(sorted(regra.methods - {"HEAD", "OPTIONS"}))
        )
        for regra in aplicacao.url_map.iter_rules()
        if regra.endpoint != "static"
    }
    assert regras == {
            ("/", ("GET",)),
            ("/health", ("GET",)),
        ("/receitas", ("GET",)),
        ("/receitas/nova", ("GET", "POST")),
        ("/receitas/editar/<int:id>", ("GET", "POST")),
        ("/receitas/excluir/<int:id>", ("POST",)),
        ("/despesas", ("GET",)),
        ("/despesas/nova", ("GET", "POST")),
        ("/despesas/editar/<int:id>", ("GET", "POST")),
        ("/despesas/excluir/<int:id>", ("POST",)),
        ("/metas", ("GET",)),
        ("/metas/nova", ("GET", "POST")),
        ("/metas/editar/<int:id>", ("GET", "POST")),
        ("/metas/excluir/<int:id>", ("POST",)),
        ("/relatorios", ("GET",))
        ,("/cadastro", ("GET", "POST"))
        ,("/login", ("GET", "POST"))
        ,("/logout", ("POST",))
    }


def test_objeto_wsgi_e_factory_compativeis(monkeypatch):
    limpar_ambiente(monkeypatch)
    modulo = importlib.import_module("app")
    assert isinstance(modulo.app, Flask)
    assert callable(modulo.create_app)


@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        ("postgres://user:pass@host/db", "postgresql+psycopg://user:pass@host/db"),
        ("postgresql://user:pass@host/db", "postgresql+psycopg://user:pass@host/db"),
        (
            "postgresql://user:p%40ss%3Aword@host/db?sslmode=require",
            "postgresql+psycopg://user:p%40ss%3Aword@host/db?sslmode=require",
        ),
        ("postgresql+psycopg://user:pass@host/db", "postgresql+psycopg://user:pass@host/db"),
    ]
)
def test_normalizacao_url_postgresql_preserva_conteudo(entrada, esperada):
    from config import normalizar_url_banco
    assert normalizar_url_banco(entrada) == esperada


def test_sqlite_continua_fallback_sem_database_url(monkeypatch, tmp_path):
    limpar_ambiente(monkeypatch)
    from app import create_app
    aplicacao = create_app({"DATABASE_PATH": str(tmp_path / "fallback.db")})
    assert aplicacao.config["SQLALCHEMY_DATABASE_URI"].drivername == "sqlite"


def test_importacao_nao_inicia_servidor(monkeypatch):
    limpar_ambiente(monkeypatch)
    modulo = importlib.import_module("app")

    def falhar(*args, **kwargs):
        raise AssertionError("Servidor não deve iniciar no import")

    monkeypatch.setattr(modulo.app, "run", falhar)
    assert modulo.app.name == "app"


def test_producao_sem_postgresql_rejeita_fallback_sqlite(
    monkeypatch,
    tmp_path
):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "chave-segura-de-producao")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "nao-criar.db"))
    from app import create_app

    with pytest.raises(RuntimeError, match="URI PostgreSQL válida"):
        create_app()
    assert not (tmp_path / "nao-criar.db").exists()


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "   ",
        "sqlite:///producao.db",
        "mysql+pymysql://usuario:senha@host/banco",
        "://senha-supersecreta@host/banco",
    ]
)
def test_producao_rejeita_database_url_invalida(
    monkeypatch,
    database_url
):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "chave-segura-de-producao")
    monkeypatch.setenv("DATABASE_URL", database_url)
    from app import create_app

    with pytest.raises(RuntimeError, match="URI PostgreSQL válida") as erro:
        create_app()
    assert "senha-supersecreta" not in str(erro.value)
    if database_url:
        assert database_url not in str(erro.value)


@pytest.mark.parametrize(
    "database_url",
    [
        "postgres://usuario:senha@inacessivel.example/banco",
        "postgresql://usuario:senha@inacessivel.example/banco",
        "postgresql+psycopg://usuario:senha@inacessivel.example/banco",
        (
            "postgresql://usuario:p%40ss%3Aword@inacessivel.example/"
            "banco?sslmode=require"
        ),
    ]
)
def test_producao_aceita_formatos_postgresql_sem_conectar(
    monkeypatch,
    database_url
):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "chave-segura-de-producao")
    monkeypatch.setenv("DATABASE_URL", database_url)
    import psycopg
    from app import create_app

    monkeypatch.setattr(
        psycopg,
        "connect",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("A factory não deve abrir conexão.")
        )
    )
    aplicacao = create_app()
    uri = aplicacao.config["SQLALCHEMY_DATABASE_URI"]
    assert uri.startswith("postgresql+psycopg://")


def test_producao_aceita_override_postgresql_explicito(monkeypatch):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    from app import create_app

    aplicacao = create_app({
        "SECRET_KEY": "chave-segura-de-producao",
        "SQLALCHEMY_DATABASE_URI": (
            "postgresql://usuario:senha@inacessivel.example/integracao"
        )
    })
    assert str(aplicacao.config["SQLALCHEMY_DATABASE_URI"]).startswith(
        "postgresql+psycopg://"
    )


@pytest.mark.parametrize(
    "override",
    [
        {"DATABASE_URL": "sqlite:///override.db"},
        {"SQLALCHEMY_DATABASE_URI": "sqlite:///override.db"},
        {"SQLALCHEMY_DATABASE_URI": ""},
    ]
)
def test_override_final_nao_substitui_postgresql_por_sqlite_ou_vazio(
    monkeypatch,
    override
):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "chave-segura-de-producao")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://usuario:senha@inacessivel.example/principal"
    )
    from app import create_app

    with pytest.raises(RuntimeError, match="URI PostgreSQL válida"):
        create_app(override)


def test_uri_invalida_falha_antes_de_inicializar_extensao(monkeypatch):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "chave-segura-de-producao")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///proibido.db")
    from app import create_app
    from extensions import db

    monkeypatch.setattr(
        db,
        "init_app",
        lambda app: (_ for _ in ()).throw(
            AssertionError("Extensão não deve ser inicializada.")
        )
    )
    with pytest.raises(RuntimeError, match="URI PostgreSQL válida"):
        create_app()


def test_desenvolvimento_permite_override_consciente_de_cookie(monkeypatch):
    limpar_ambiente(monkeypatch)
    from app import create_app

    aplicacao = create_app({
        "SESSION_COOKIE_SECURE": True,
        "REMEMBER_COOKIE_SECURE": True,
    })
    assert aplicacao.config["SESSION_COOKIE_SECURE"] is True
    assert aplicacao.config["REMEMBER_COOKIE_SECURE"] is True


def test_testing_aceita_sqlite_explicito_sem_criar_arquivo(
    monkeypatch,
    tmp_path
):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    caminho = tmp_path / "testing-explicito.db"
    from sqlalchemy.engine import URL
    from app import create_app

    aplicacao = create_app({
        "SQLALCHEMY_DATABASE_URI": URL.create(
            "sqlite", database=str(caminho)
        )
    })
    assert aplicacao.testing is True
    assert aplicacao.config["SESSION_COOKIE_SECURE"] is False
    assert aplicacao.config["REMEMBER_COOKIE_SECURE"] is False
    assert not caminho.exists()

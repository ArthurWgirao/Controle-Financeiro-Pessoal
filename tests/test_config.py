import importlib

import pytest
from flask import Flask

from config import CHAVE_DESENVOLVIMENTO


def limpar_ambiente(monkeypatch):
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


def test_ambiente_testing(monkeypatch, tmp_path):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "testing.db"))
    from app import create_app

    aplicacao = create_app()
    assert aplicacao.testing is True
    assert aplicacao.secret_key == "chave-fixa-exclusiva-para-testes"


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
    tmp_path
):
    limpar_ambiente(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    from app import create_app

    aplicacao = create_app({
        "SECRET_KEY": "uma-chave-segura-de-producao",
        "DATABASE_PATH": str(tmp_path / "producao.db"),
        "DEBUG": True
    })
    assert aplicacao.secret_key == "uma-chave-segura-de-producao"
    assert aplicacao.testing is False
    assert aplicacao.debug is False


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
    with pytest.raises(Exception, match="no such table"):
        aplicacao.test_client().get("/")
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
        assert aplicacao.test_client().get("/").status_code == 200
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
    }


def test_objeto_wsgi_e_factory_compativeis(monkeypatch):
    limpar_ambiente(monkeypatch)
    modulo = importlib.import_module("app")
    assert isinstance(modulo.app, Flask)
    assert callable(modulo.create_app)


def test_importacao_nao_inicia_servidor(monkeypatch):
    limpar_ambiente(monkeypatch)
    modulo = importlib.import_module("app")

    def falhar(*args, **kwargs):
        raise AssertionError("Servidor não deve iniciar no import")

    monkeypatch.setattr(modulo.app, "run", falhar)
    assert modulo.app.name == "app"

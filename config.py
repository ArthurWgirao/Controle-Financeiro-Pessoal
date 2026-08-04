import os
from datetime import timedelta
from pathlib import Path

from sqlalchemy.engine import URL


CHAVE_DESENVOLVIMENTO = "chave-local-insegura-de-desenvolvimento"


class Config:
    TESTING = False
    DEBUG = False
    SECRET_KEY = None
    DATABASE_URL = None
    DATABASE_PATH = "finance.db"
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    SECRET_KEY = CHAVE_DESENVOLVIMENTO


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "chave-fixa-exclusiva-para-testes"


class ProductionConfig(Config):
    TESTING = False
    DEBUG = False
    SESSION_COOKIE_SECURE = True


CONFIGURACOES = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig
}


def obter_ambiente():
    return os.getenv("APP_ENV", "development").strip().lower()


def obter_classe_configuracao(ambiente):
    if ambiente not in CONFIGURACOES:
        opcoes = ", ".join(CONFIGURACOES)
        raise ValueError(
            f"APP_ENV inválido: {ambiente!r}. "
            f"Use uma destas opções: {opcoes}."
        )

    return CONFIGURACOES[ambiente]


def aplicar_variaveis_ambiente(configuracao):
    if "SECRET_KEY" in os.environ:
        configuracao["SECRET_KEY"] = os.environ["SECRET_KEY"]

    if "DATABASE_PATH" in os.environ:
        configuracao["DATABASE_PATH"] = os.environ["DATABASE_PATH"]

    if "DATABASE_URL" in os.environ:
        configuracao["DATABASE_URL"] = os.environ["DATABASE_URL"]


def criar_uri_sqlite(caminho):
    caminho_absoluto = Path(caminho).expanduser().resolve()
    return URL.create("sqlite", database=str(caminho_absoluto))


def normalizar_url_banco(url):
    if not isinstance(url, str):
        return url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def configurar_uri_banco(configuracao, sobrescritas=None):
    sobrescritas = sobrescritas or {}

    if sobrescritas.get("SQLALCHEMY_DATABASE_URI"):
        return

    if configuracao.get("DATABASE_URL"):
        configuracao["SQLALCHEMY_DATABASE_URI"] = normalizar_url_banco(
            configuracao["DATABASE_URL"]
        )
        return

    configuracao["SQLALCHEMY_DATABASE_URI"] = criar_uri_sqlite(
        configuracao.get("DATABASE_PATH", "finance.db")
    )


def validar_configuracao_producao(configuracao):
    chave = configuracao.get("SECRET_KEY")

    if not chave or chave == CHAVE_DESENVOLVIMENTO:
        raise RuntimeError(
            "SECRET_KEY segura é obrigatória no ambiente de produção."
        )

    configuracao["DEBUG"] = False

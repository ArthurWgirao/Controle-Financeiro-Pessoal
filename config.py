import os


CHAVE_DESENVOLVIMENTO = "chave-local-insegura-de-desenvolvimento"


class Config:
    TESTING = False
    DEBUG = False
    SECRET_KEY = None
    DATABASE_PATH = "finance.db"


class DevelopmentConfig(Config):
    SECRET_KEY = CHAVE_DESENVOLVIMENTO


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "chave-fixa-exclusiva-para-testes"


class ProductionConfig(Config):
    TESTING = False
    DEBUG = False


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


def validar_configuracao_producao(configuracao):
    chave = configuracao.get("SECRET_KEY")

    if not chave or chave == CHAVE_DESENVOLVIMENTO:
        raise RuntimeError(
            "SECRET_KEY segura é obrigatória no ambiente de produção."
        )

    configuracao["DEBUG"] = False

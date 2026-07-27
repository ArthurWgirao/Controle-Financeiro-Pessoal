import math

import pytest

from validacoes import (
    validar_limite_meta,
    validar_meta,
    validar_numero_positivo,
    validar_transacao
)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [(1, 1.0), (1.25, 1.25), ("2.50", 2.5)]
)
def test_numero_positivo_valido(entrada, esperado):
    valor, erro = validar_numero_positivo(
        entrada,
        "obrigatório",
        "inválido",
        "positivo"
    )
    assert valor == pytest.approx(esperado)
    assert erro is None


@pytest.mark.parametrize(
    ("entrada", "mensagem"),
    [
        ("", "obrigatório"),
        ("0", "positivo"),
        ("-1", "positivo"),
        ("texto", "inválido"),
        ("inf", "positivo"),
        ("-inf", "positivo"),
        ("NaN", "positivo")
    ]
)
def test_numero_positivo_invalido(entrada, mensagem):
    valor, erro = validar_numero_positivo(
        entrada,
        "obrigatório",
        "inválido",
        "positivo"
    )
    assert valor is None
    assert erro == mensagem


def test_transacao_valida():
    valor, erro = validar_transacao(
        "Salário",
        "Salário",
        "100",
        ["Salário"],
        "receita"
    )
    assert valor == 100
    assert erro is None


@pytest.mark.parametrize(
    ("descricao", "categoria", "trecho"),
    [
        ("", "Comida", "descrição"),
        ("Mercado", "Inválida", "categoria")
    ]
)
def test_transacao_rejeita_descricao_ou_categoria(
    descricao,
    categoria,
    trecho
):
    valor, erro = validar_transacao(
        descricao,
        categoria,
        "10",
        ["Comida"],
        "despesa"
    )
    assert valor is None
    assert trecho in erro


def test_meta_valida():
    valor, erro = validar_meta("Comida", "100.50", ["Comida"])
    assert valor == pytest.approx(100.50)
    assert erro is None


def test_meta_rejeita_categoria_invalida():
    valor, erro = validar_meta("Outra", "100", ["Comida"])
    assert valor is None
    assert "categoria" in erro


@pytest.mark.parametrize("entrada", ["", "0", "-2", "abc", "inf", "-inf", "NaN"])
def test_limite_meta_invalido(entrada):
    valor, erro = validar_limite_meta(entrada)
    assert valor is None
    assert erro


def test_nan_real_tambem_e_rejeitado():
    valor, erro = validar_numero_positivo(
        math.nan,
        "obrigatório",
        "inválido",
        "positivo"
    )
    assert valor is None
    assert erro == "positivo"

import math
from decimal import Decimal

import pytest

from validacoes import (
    validar_limite_meta,
    validar_meta,
    validar_numero_positivo,
    validar_transacao
)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (1, Decimal("1.00")),
        (1.25, Decimal("1.25")),
        ("2.50", Decimal("2.50")),
        ("9999999999.99", Decimal("9999999999.99"))
    ]
)
def test_numero_positivo_valido(entrada, esperado):
    valor, erro = validar_numero_positivo(
        entrada,
        "obrigatório",
        "inválido",
        "positivo"
    )
    assert valor == esperado
    assert erro is None


@pytest.mark.parametrize(
    ("entrada", "mensagem"),
    [
        ("", "obrigatório"),
        ("0", "positivo"),
        ("-1", "positivo"),
        ("texto", "inválido"),
        ("inf", "inválido"),
        ("-inf", "inválido"),
        ("NaN", "inválido")
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
    assert erro == "inválido"


@pytest.mark.parametrize("entrada", ["10.999", "9999999999.999", "10000000000"])
def test_numero_rejeita_excesso_de_escala_ou_precisao(entrada):
    valor, erro = validar_numero_positivo(
        entrada, "obrigatório", "inválido", "positivo"
    )
    assert valor is None
    assert erro


def test_decimal_nao_acumula_erro_binario():
    primeiro, _ = validar_limite_meta("0.10")
    segundo, _ = validar_limite_meta("0.20")
    assert primeiro + segundo == Decimal("0.30")

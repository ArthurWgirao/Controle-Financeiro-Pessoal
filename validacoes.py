import math


def validar_numero_positivo(
    valor_informado,
    mensagem_obrigatorio,
    mensagem_invalido,
    mensagem_positivo
):

    if not valor_informado:
        return None, mensagem_obrigatorio

    try:
        valor = float(valor_informado)
    except ValueError:
        return None, mensagem_invalido

    if not math.isfinite(valor) or valor <= 0:
        return None, mensagem_positivo

    return valor, None


def validar_transacao(
    descricao,
    categoria,
    valor_informado,
    categorias_permitidas,
    tipo
):

    if not descricao:
        return None, f"Informe uma descrição para a {tipo}."

    if categoria not in categorias_permitidas:
        return None, "Selecione uma categoria válida."

    return validar_numero_positivo(
        valor_informado,
        f"Informe o valor da {tipo}.",
        "Informe um valor numérico válido.",
        "O valor deve ser maior que zero."
    )


def validar_meta(categoria, limite_informado, categorias_permitidas):

    if categoria not in categorias_permitidas:
        return None, "Selecione uma categoria válida."

    return validar_limite_meta(limite_informado)


def validar_limite_meta(limite_informado):

    return validar_numero_positivo(
        limite_informado,
        "Informe o limite mensal.",
        "Informe um limite numérico válido.",
        "O limite deve ser maior que zero."
    )

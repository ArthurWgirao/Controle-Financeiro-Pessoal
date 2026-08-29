from decimal import Decimal, InvalidOperation


VALOR_MAXIMO = Decimal("9999999999.99")
CATEGORIA_OUTRO = "Outro"
TAMANHO_MAXIMO_CATEGORIA = 100


def validar_categoria(categoria, categoria_personalizada, categorias_permitidas):
    """Retorna a categoria que deve ser persistida ou uma mensagem de erro."""
    if categoria == CATEGORIA_OUTRO:
        categoria_personalizada = categoria_personalizada.strip()
        if not categoria_personalizada:
            return None, "Informe o nome da categoria personalizada."
        if len(categoria_personalizada) > TAMANHO_MAXIMO_CATEGORIA:
            return None, (
                "A categoria personalizada deve ter no máximo "
                f"{TAMANHO_MAXIMO_CATEGORIA} caracteres."
            )
        return categoria_personalizada, None

    if categoria not in categorias_permitidas:
        return None, "Selecione uma categoria válida."

    return categoria, None


def validar_numero_positivo(
    valor_informado,
    mensagem_obrigatorio,
    mensagem_invalido,
    mensagem_positivo
):
    if valor_informado is None or str(valor_informado).strip() == "":
        return None, mensagem_obrigatorio

    try:
        valor = Decimal(str(valor_informado).strip())
    except (InvalidOperation, ValueError):
        return None, mensagem_invalido

    if not valor.is_finite():
        return None, mensagem_invalido

    if valor <= 0:
        return None, mensagem_positivo

    if valor.as_tuple().exponent < -2:
        return None, "Use no máximo duas casas decimais."

    if valor > VALOR_MAXIMO:
        return None, "O valor informado é muito alto."

    return valor.quantize(Decimal("0.01")), None


def validar_transacao(
    descricao,
    categoria,
    valor_informado,
    categorias_permitidas,
    tipo,
    categoria_personalizada=""
):
    if not descricao:
        return None, f"Informe uma descrição para a {tipo}."

    _, erro_categoria = validar_categoria(
        categoria, categoria_personalizada, categorias_permitidas
    )
    if erro_categoria:
        return None, erro_categoria

    return validar_numero_positivo(
        valor_informado,
        f"Informe o valor da {tipo}.",
        "Informe um valor numérico válido.",
        "O valor deve ser maior que zero."
    )


def validar_meta(
    categoria,
    limite_informado,
    categorias_permitidas,
    categoria_personalizada=""
):
    _, erro_categoria = validar_categoria(
        categoria, categoria_personalizada, categorias_permitidas
    )
    if erro_categoria:
        return None, erro_categoria

    return validar_limite_meta(limite_informado)


def validar_limite_meta(limite_informado):
    return validar_numero_positivo(
        limite_informado,
        "Informe o limite mensal.",
        "Informe um limite numérico válido.",
        "O limite deve ser maior que zero."
    )

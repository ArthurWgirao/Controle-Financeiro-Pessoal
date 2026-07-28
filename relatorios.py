from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from extensions import db
from models import Transacao


MESES = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro"
]

MESES_ABREVIADOS = [
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez"
]


def validar_periodo(mes_informado, ano_informado, agora=None):

    agora = agora or datetime.now()

    if mes_informado is None and ano_informado is None:
        return agora.month, agora.year, None

    if mes_informado is None or ano_informado is None:
        return None, None, "Informe o mês e o ano para consultar."

    if not mes_informado or not ano_informado:
        return None, None, "Informe o mês e o ano para consultar."

    try:
        mes = int(mes_informado)
    except ValueError:
        return None, None, "Informe um mês válido."

    try:
        ano = int(ano_informado)
    except ValueError:
        return None, None, "Informe um ano válido."

    if mes < 1 or mes > 12:
        return None, None, "O mês deve estar entre 1 e 12."

    if ano < 1900 or ano > 2100:
        return None, None, "O ano deve estar entre 1900 e 2100."

    return mes, ano, None


def gerar_seis_periodos(mes, ano):

    periodos = []

    for deslocamento in range(5, -1, -1):
        indice = ano * 12 + (mes - 1) - deslocamento
        ano_periodo, indice_mes = divmod(indice, 12)
        mes_periodo = indice_mes + 1

        periodos.append({
            "mes": mes_periodo,
            "ano": ano_periodo,
            "rotulo": (
                f"{MESES_ABREVIADOS[mes_periodo - 1]}/"
                f"{ano_periodo}"
            )
        })

    return periodos


def buscar_movimentacoes_reconhecidas(data_inicio=None, data_fim=None):
    consulta = select(Transacao).where(
        Transacao.tipo.in_(("receita", "despesa"))
    )
    if data_inicio is not None:
        consulta = consulta.where(Transacao.data >= data_inicio)
    if data_fim is not None:
        consulta = consulta.where(Transacao.data < data_fim)

    return [
        {
            "tipo": registro.tipo,
            "valor": registro.valor,
            "categoria": registro.categoria,
            "data": registro.data
        }
        for registro in db.session.scalars(consulta)
    ]


def converter_data(data_informada):

    if isinstance(data_informada, datetime):
        return data_informada
    if isinstance(data_informada, date):
        return datetime.combine(data_informada, datetime.min.time())
    if not isinstance(data_informada, str):
        return None

    if (
        len(data_informada) != 10
        or data_informada[2] != "/"
        or data_informada[5] != "/"
    ):
        return None

    try:
        return datetime.strptime(data_informada, "%d/%m/%Y")
    except ValueError:
        return None


def obter_resumo_periodo(movimentacoes, mes, ano):

    receitas = Decimal("0.00")
    despesas = Decimal("0.00")
    quantidade_receitas = 0
    quantidade_despesas = 0

    for movimentacao in movimentacoes:
        if (
            movimentacao["data"].month != mes
            or movimentacao["data"].year != ano
        ):
            continue

        if movimentacao["tipo"] == "receita":
            receitas += movimentacao["valor"]
            quantidade_receitas += 1
        elif movimentacao["tipo"] == "despesa":
            despesas += movimentacao["valor"]
            quantidade_despesas += 1

    saldo = receitas - despesas

    if saldo > 0:
        classe_saldo = "positivo"
    elif saldo < 0:
        classe_saldo = "negativo"
    else:
        classe_saldo = "zerado"

    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": saldo,
        "quantidade_receitas": quantidade_receitas,
        "quantidade_despesas": quantidade_despesas,
        "classe_saldo": classe_saldo
    }


def obter_despesas_por_categoria(movimentacoes, mes, ano):

    agrupamento = {}

    for movimentacao in movimentacoes:
        if (
            movimentacao["tipo"] != "despesa"
            or movimentacao["data"].month != mes
            or movimentacao["data"].year != ano
        ):
            continue

        categoria = movimentacao["categoria"]

        if categoria not in agrupamento:
            agrupamento[categoria] = {
                "categoria": categoria,
                "total": Decimal("0.00"),
                "quantidade": 0
            }

        agrupamento[categoria]["total"] += movimentacao["valor"]
        agrupamento[categoria]["quantidade"] += 1

    total_despesas = sum(
        item["total"]
        for item in agrupamento.values()
    )

    categorias = []

    for item in agrupamento.values():
        percentual = (
            (item["total"] / total_despesas) * 100
            if total_despesas > 0
        else Decimal("0")
        )

        categorias.append({
            **item,
            "percentual": float(percentual)
        })

    return sorted(
        categorias,
        key=lambda item: item["total"],
        reverse=True
    )


def obter_evolucao_mensal(movimentacoes, mes, ano):

    periodos = gerar_seis_periodos(mes, ano)
    totais = {
        (periodo["mes"], periodo["ano"]): {
            "receitas": Decimal("0.00"),
            "despesas": Decimal("0.00")
        }
        for periodo in periodos
    }

    for movimentacao in movimentacoes:
        chave = (
            movimentacao["data"].month,
            movimentacao["data"].year
        )

        if chave not in totais:
            continue

        if movimentacao["tipo"] == "receita":
            totais[chave]["receitas"] += movimentacao["valor"]
        elif movimentacao["tipo"] == "despesa":
            totais[chave]["despesas"] += movimentacao["valor"]

    receitas = []
    despesas = []
    saldos = []

    for periodo in periodos:
        total = totais[(periodo["mes"], periodo["ano"])]
        receitas.append(total["receitas"])
        despesas.append(total["despesas"])
        saldos.append(total["receitas"] - total["despesas"])

    return {
        "rotulos": [periodo["rotulo"] for periodo in periodos],
        "receitas": receitas,
        "despesas": despesas,
        "saldos": saldos
    }


def preparar_relatorio(mes, ano):

    periodos = gerar_seis_periodos(mes, ano)
    primeiro = periodos[0]
    data_inicio = date(primeiro["ano"], primeiro["mes"], 1)
    data_fim = (
        date(ano + 1, 1, 1)
        if mes == 12
        else date(ano, mes + 1, 1)
    )
    movimentacoes = buscar_movimentacoes_reconhecidas(
        data_inicio,
        data_fim
    )
    resumo = obter_resumo_periodo(movimentacoes, mes, ano)
    despesas_categorias = obter_despesas_por_categoria(
        movimentacoes,
        mes,
        ano
    )
    evolucao = obter_evolucao_mensal(movimentacoes, mes, ano)

    return {
        "mes": mes,
        "ano": ano,
        "periodo": f"{MESES[mes - 1]} de {ano}",
        "resumo": resumo,
        "despesas_categorias": despesas_categorias,
        "grafico_categorias": {
            "rotulos": [
                item["categoria"]
                for item in despesas_categorias
            ],
            "valores": [
                float(item["total"])
                for item in despesas_categorias
            ]
        },
        "evolucao": {
            "rotulos": evolucao["rotulos"],
            "receitas": [float(valor) for valor in evolucao["receitas"]],
            "despesas": [float(valor) for valor in evolucao["despesas"]],
            "saldos": [float(valor) for valor in evolucao["saldos"]]
        },
        "tem_movimentacoes": (
            resumo["quantidade_receitas"]
            + resumo["quantidade_despesas"]
            > 0
        )
    }

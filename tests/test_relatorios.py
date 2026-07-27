from datetime import datetime
from pathlib import Path

import pytest

import relatorios


@pytest.mark.parametrize(
    ("mes", "ano", "tem_erro"),
    [
        (None, None, False),
        ("7", "2026", False),
        ("0", "2026", True),
        ("13", "2026", True),
        ("abc", "2026", True),
        ("7", "", True),
        ("7", "abc", True),
        ("7", "1899", True),
        ("7", "2101", True),
        ("7", None, True),
        (None, "2026", True)
    ]
)
def test_validacao_do_periodo(mes, ano, tem_erro):
    mes_validado, ano_validado, erro = relatorios.validar_periodo(
        mes, ano
    )
    assert bool(erro) is tem_erro
    if not tem_erro:
        assert 1 <= mes_validado <= 12
        assert 1900 <= ano_validado <= 2100


def test_rota_preserva_filtros_invalidos(cliente):
    resposta = cliente.get("/relatorios?mes=abc&ano=xyz")
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 400
    assert 'value="abc"' in html
    assert 'value="xyz"' in html


def test_rota_sem_parametros_usa_periodo_atual(cliente):
    html = cliente.get("/relatorios").get_data(as_text=True)
    assert relatorios.MESES[datetime.now().month - 1] in html
    assert str(datetime.now().year) in html


def test_resumo_ignora_tipo_desconhecido_e_data_invalida(
    inserir_transacao
):
    inserir_transacao(
        tipo="receita", valor=100, data="01/07/2026"
    )
    inserir_transacao(
        tipo="despesa", valor=40, data="02/07/2026"
    )
    inserir_transacao(
        tipo="outro", valor=999, data="03/07/2026"
    )
    inserir_transacao(
        tipo="receita", valor=999, data="99/07/2026"
    )

    resumo = relatorios.preparar_relatorio(7, 2026)["resumo"]
    assert resumo["receitas"] == 100
    assert resumo["despesas"] == 40
    assert resumo["saldo"] == 60
    assert resumo["quantidade_receitas"] == 1
    assert resumo["quantidade_despesas"] == 1


@pytest.mark.parametrize(
    ("receita", "despesa", "classe"),
    [(100, 0, "positivo"), (0, 100, "negativo"), (100, 100, "zerado")]
)
def test_estados_do_saldo(
    inserir_transacao,
    receita,
    despesa,
    classe
):
    if receita:
        inserir_transacao(
            tipo="receita", valor=receita, data="01/07/2026"
        )
    if despesa:
        inserir_transacao(
            tipo="despesa", valor=despesa, data="02/07/2026"
        )

    assert relatorios.preparar_relatorio(
        7, 2026
    )["resumo"]["classe_saldo"] == classe


def test_categorias_agrupadas_ordenadas_e_com_percentual(
    inserir_transacao
):
    inserir_transacao(
        tipo="despesa",
        valor=100,
        categoria="Educação",
        data="01/07/2026"
    )
    inserir_transacao(
        tipo="despesa",
        valor=150,
        categoria="Comida",
        data="02/07/2026"
    )
    inserir_transacao(
        tipo="despesa",
        valor=50,
        categoria="Comida",
        data="03/07/2026"
    )
    inserir_transacao(
        tipo="receita",
        valor=500,
        categoria="Comida",
        data="04/07/2026"
    )

    categorias = relatorios.preparar_relatorio(
        7, 2026
    )["despesas_categorias"]
    assert [item["categoria"] for item in categorias] == [
        "Comida", "Educação"
    ]
    assert categorias[0]["quantidade"] == 2
    assert categorias[0]["percentual"] == pytest.approx(66.666, rel=0.01)
    assert sum(item["percentual"] for item in categorias) == pytest.approx(
        100
    )


def test_periodo_sem_despesa_nao_divide_por_zero(inserir_receita):
    inserir_receita(valor=100, data="01/07/2026")
    assert relatorios.preparar_relatorio(
        7, 2026
    )["despesas_categorias"] == []


def test_evolucao_de_seis_meses_com_zeros(inserir_transacao):
    inserir_transacao(
        tipo="receita", valor=100, data="01/02/2026"
    )
    inserir_transacao(
        tipo="despesa", valor=20, data="01/03/2026"
    )
    inserir_transacao(
        tipo="receita", valor=50, data="01/07/2026"
    )

    evolucao = relatorios.preparar_relatorio(7, 2026)["evolucao"]
    assert evolucao["rotulos"] == [
        "fev/2026", "mar/2026", "abr/2026",
        "mai/2026", "jun/2026", "jul/2026"
    ]
    assert evolucao["receitas"] == [100, 0, 0, 0, 0, 50]
    assert evolucao["despesas"] == [0, 20, 0, 0, 0, 0]
    assert evolucao["saldos"] == [100, -20, 0, 0, 0, 50]


def test_janela_de_seis_meses_trata_virada_de_ano():
    periodos = relatorios.gerar_seis_periodos(1, 2026)
    assert [item["rotulo"] for item in periodos] == [
        "ago/2025", "set/2025", "out/2025",
        "nov/2025", "dez/2025", "jan/2026"
    ]


@pytest.mark.parametrize("data", [None, "1/7/2026", "31/02/2026"])
def test_conversao_ignora_datas_invalidas(data):
    assert relatorios.converter_data(data) is None


def test_evolucao_ignora_movimentacao_fora_da_janela():
    movimentacoes = [{
        "tipo": "receita",
        "valor": 999,
        "categoria": "Outro",
        "data": datetime(2020, 1, 1)
    }]
    evolucao = relatorios.obter_evolucao_mensal(
        movimentacoes, 7, 2026
    )
    assert evolucao["receitas"] == [0, 0, 0, 0, 0, 0]


def test_estado_vazio_mantem_apenas_grafico_de_evolucao(cliente):
    html = cliente.get(
        "/relatorios?mes=12&ano=2099"
    ).get_data(as_text=True)
    assert "Nenhuma movimentação" in html
    assert 'id="graficoCategorias"' not in html
    assert 'id="graficoEvolucao"' in html
    assert "[0, 0, 0, 0, 0, 0]" in html


def test_template_usa_tojson_e_chart_apenas_em_relatorios():
    raiz = Path(__file__).resolve().parents[1]
    relatorio = (
        raiz / "templates" / "relatorios.html"
    ).read_text(encoding="utf-8")
    outros = [
        caminho.read_text(encoding="utf-8")
        for caminho in (raiz / "templates").glob("*.html")
        if caminho.name != "relatorios.html"
    ]
    assert relatorio.count("| tojson") >= 2
    assert "chart.js@4.4.9" in relatorio
    assert all("chart.js@" not in conteudo for conteudo in outros)

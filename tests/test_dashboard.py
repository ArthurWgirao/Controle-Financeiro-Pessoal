import ast
import importlib
from pathlib import Path


def test_dashboard_vazio(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert html.count("R$ 0,00") >= 3
    assert "Nenhuma movimentação no período" in html
    assert "Nenhuma meta cadastrada" in html


def test_dashboard_exibe_totais(cliente, inserir_receita, inserir_despesa):
    inserir_receita(valor=100)
    inserir_despesa(valor=40)
    html = cliente.get("/").get_data(as_text=True)
    assert "R$ 100,00" in html
    assert "R$ 40,00" in html
    assert "R$ 60,00" in html


def test_rotas_principais_estao_registradas(aplicacao):
    rotas = {regra.rule for regra in aplicacao.url_map.iter_rules()}
    assert {
        "/",
        "/receitas",
        "/despesas",
        "/metas",
        "/relatorios"
    } <= rotas


def test_templates_principais_renderizam(cliente):
    for rota in [
        "/",
        "/receitas",
        "/receitas/nova",
        "/despesas",
        "/despesas/nova",
        "/metas",
        "/metas/nova"
    ]:
        assert cliente.get(rota).status_code == 200


def test_relatorios_redireciona_para_dashboard(cliente):
    resposta = cliente.get("/relatorios?mes=8&ano=2026&outro=ignorado")
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/?mes=8&ano=2026"


def test_dashboard_rejeita_filtro_invalido_e_preserva_valores(cliente):
    resposta = cliente.get("/?mes=abc&ano=xyz")
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 400
    assert 'value="abc"' in html
    assert 'value="xyz"' in html
    assert 'role="alert"' in html


def test_metas_do_dashboard_usam_mes_atual_independente_do_filtro(
    cliente, inserir_meta, inserir_despesa, data_atual
):
    inserir_meta(categoria="Comida", limite=100)
    inserir_despesa(categoria="Comida", valor=120, data=data_atual)
    html = cliente.get("/?mes=1&ano=2020").get_data(as_text=True)
    assert "As metas sempre refletem o mês atual" in html
    assert "Meta ultrapassada" in html
    assert "120.00%" in html
    assert 'id="graficoMetas"' in html
    assert "dadosMetas" in html


def test_dashboard_vazio_nao_inicializa_graficos_de_categoria_ou_meta(cliente):
    html = cliente.get("/?mes=1&ano=2020").get_data(as_text=True)
    assert 'id="graficoDespesasCategorias"' not in html
    assert 'id="graficoReceitasCategorias"' not in html
    assert 'id="graficoMetas"' not in html
    assert "Gerenciar metas" in html


def test_main_importavel_sem_iniciar_menu(monkeypatch):
    def falhar(*args, **kwargs):
        raise AssertionError("input() não deveria ser chamado no import")

    monkeypatch.setattr("builtins.input", falhar)
    modulo = importlib.import_module("main")
    assert callable(modulo.main)


def test_app_nao_contem_sql_e_dominios_nao_importam_flask():
    raiz = Path(__file__).resolve().parents[1]
    app = (raiz / "app.py").read_text(encoding="utf-8").upper()
    assert not any(
        comando in app
        for comando in ["SELECT ", "INSERT ", "UPDATE ", "DELETE "]
    )

    for nome in ["transacoes.py", "metas.py", "validacoes.py", "relatorios.py"]:
        conteudo = (raiz / nome).read_text(encoding="utf-8").lower()
        assert "from flask" not in conteudo
        assert "import flask" not in conteudo


def test_sintaxe_de_todos_os_arquivos_python():
    raiz = Path(__file__).resolve().parents[1]
    for caminho in raiz.glob("*.py"):
        ast.parse(
            caminho.read_text(encoding="utf-8"),
            filename=str(caminho)
        )


def test_modulos_importam_sem_ciclo():
    for nome in [
        "extensions",
        "models",
        "validacoes",
        "transacoes",
        "metas",
        "relatorios",
        "app"
    ]:
        assert importlib.import_module(nome)

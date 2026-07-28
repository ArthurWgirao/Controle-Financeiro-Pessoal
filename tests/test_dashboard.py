import ast
import importlib
from pathlib import Path


def test_dashboard_vazio(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert resposta.get_data(as_text=True).count("R$ 0.00") == 3


def test_dashboard_exibe_totais(cliente, inserir_receita, inserir_despesa):
    inserir_receita(valor=100)
    inserir_despesa(valor=40)
    html = cliente.get("/").get_data(as_text=True)
    assert "R$ 100.00" in html
    assert "R$ 40.00" in html
    assert "R$ 60.00" in html


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
        "/metas/nova",
        "/relatorios"
    ]:
        assert cliente.get(rota).status_code == 200


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

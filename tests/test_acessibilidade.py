from html.parser import HTMLParser
from pathlib import Path

import pytest


class DocumentoHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.html = html
        self.elementos = []
        self.pilha_formularios = 0
        self.formularios_aninhados = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        self.elementos.append((tag, atributos))
        if tag == "form":
            if self.pilha_formularios:
                self.formularios_aninhados = True
            self.pilha_formularios += 1

    def handle_endtag(self, tag):
        if tag == "form":
            self.pilha_formularios -= 1

    def buscar(self, tag=None, **atributos):
        return [
            attrs for nome, attrs in self.elementos
            if (tag is None or nome == tag)
            and all(attrs.get(chave) == valor for chave, valor in atributos.items())
        ]

    @property
    def ids(self):
        return [attrs["id"] for _, attrs in self.elementos if attrs.get("id")]


def documento(resposta):
    html = resposta.get_data(as_text=True)
    assert "{%" not in html and "{{" not in html
    resultado = DocumentoHTML(html)
    assert not resultado.formularios_aninhados
    assert resultado.pilha_formularios == 0
    assert len(resultado.ids) == len(set(resultado.ids))
    return resultado


def assert_labels_resolvidos(doc):
    ids = set(doc.ids)
    for label in doc.buscar("label"):
        assert label.get("for") in ids
    for tag in ("input", "select"):
        for controle in doc.buscar(tag):
            if controle.get("type") in {"hidden", "submit"}:
                continue
            assert controle.get("id")
            assert any(
                label.get("for") == controle["id"]
                for label in doc.buscar("label")
            )


@pytest.mark.parametrize(
    ("rota", "trecho_ativo"),
    [
        ("/", 'href="/" aria-current="page"'),
        ("/receitas", 'href="/receitas" aria-current="page"'),
        ("/despesas", 'href="/despesas" aria-current="page"'),
        ("/metas", 'href="/metas" aria-current="page"'),
        ("/relatorios", 'href="/relatorios" aria-current="page"'),
    ]
)
def test_estrutura_base_skip_link_e_navegacao_ativa(
    cliente,
    rota,
    trecho_ativo
):
    resposta = cliente.get(rota)
    assert resposta.status_code == 200
    doc = documento(resposta)
    assert doc.buscar("html", lang="pt-BR")
    assert doc.buscar("meta", name="viewport")
    assert doc.buscar("a", href="#conteudo-principal", **{"class": "skip-link"})
    assert doc.buscar("main", id="conteudo-principal")
    assert doc.buscar("nav", **{"aria-label": "Navegação principal"})
    assert resposta.get_data(as_text=True).count('aria-current="page"') == 1
    assert trecho_ativo in resposta.get_data(as_text=True)


@pytest.mark.parametrize(
    ("rota", "anonimo"),
    [
        ("/login", True),
        ("/cadastro", True),
        ("/receitas/nova", False),
        ("/despesas/nova", False),
        ("/metas/nova", False),
        ("/relatorios", False),
    ]
)
def test_labels_ids_e_csrf_dos_formularios(
    cliente,
    cliente_anonimo,
    rota,
    anonimo
):
    resposta = (cliente_anonimo if anonimo else cliente).get(rota)
    assert resposta.status_code == 200
    doc = documento(resposta)
    assert_labels_resolvidos(doc)
    for formulario in doc.buscar("form"):
        if formulario.get("method", "GET").upper() == "POST":
            assert any(
                campo.get("name") == "csrf_token"
                for campo in doc.buscar("input", type="hidden")
            )


@pytest.mark.parametrize(
    ("rota", "dados"),
    [
        ("/login", {"email": "invalido", "senha": ""}),
        ("/cadastro", {"nome": "", "email": "", "senha": "", "confirmacao_senha": ""}),
        ("/receitas/nova", {"descricao": "", "categoria": "", "valor": ""}),
        ("/despesas/nova", {"descricao": "", "categoria": "", "valor": ""}),
        ("/metas/nova", {"categoria": "", "limite": ""}),
    ]
)
def test_erros_sao_alertas_e_formulario_os_descreve(
    cliente,
    cliente_anonimo,
    rota,
    dados
):
    usado = cliente_anonimo if rota in {"/login", "/cadastro"} else cliente
    resposta = usado.post(rota, data=dados)
    assert resposta.status_code in {400, 401}
    doc = documento(resposta)
    assert doc.buscar(role="alert", id="erro-formulario")
    assert doc.buscar("form", **{"aria-describedby": "erro-formulario"})
    assert_labels_resolvidos(doc)


@pytest.mark.parametrize(
    ("rota", "mensagem"),
    [
        ("/receitas", "Nenhuma receita cadastrada"),
        ("/despesas", "Nenhuma despesa cadastrada"),
        ("/metas", "Nenhuma meta cadastrada"),
    ]
)
def test_estados_vazios(cliente, rota, mensagem):
    resposta = cliente.get(rota)
    assert resposta.status_code == 200
    assert mensagem in resposta.get_data(as_text=True)


@pytest.mark.parametrize(
    ("rota", "regiao", "descricao"),
    [
        ("/receitas", "Lista de receitas", "Salário acessível"),
        ("/despesas", "Lista de despesas", "Transporte acessível"),
    ]
)
def test_tabelas_responsivas_semanticas_e_acoes_nomeadas(
    cliente,
    inserir_receita,
    inserir_despesa,
    rota,
    regiao,
    descricao
):
    inserir = inserir_receita if rota == "/receitas" else inserir_despesa
    inserir(descricao=descricao)
    resposta = cliente.get(rota)
    doc = documento(resposta)
    assert doc.buscar("div", role="region", **{"aria-label": regiao})
    assert doc.buscar("thead") and doc.buscar("tbody") and doc.buscar("caption")
    assert len(doc.buscar("th", scope="col")) == 5
    assert len(doc.buscar(**{"aria-label": f"Editar {rota[1:-1]}: {descricao}"})) == 1
    assert len(doc.buscar(**{"aria-label": f"Excluir {rota[1:-1]}: {descricao}"})) == 1
    html = resposta.get_data(as_text=True)
    assert 'method="POST"' in html and "confirm(" in html


def test_meta_acima_de_cem_mantem_aria_valida_e_texto_real(
    cliente,
    inserir_meta,
    inserir_despesa,
    data_atual
):
    inserir_meta(categoria="Comida", limite=100)
    inserir_despesa(categoria="Comida", valor=120, data=data_atual)
    resposta = cliente.get("/metas")
    doc = documento(resposta)
    barra = doc.buscar("div", role="progressbar")[0]
    assert float(barra["aria-valuemin"]) <= float(barra["aria-valuenow"])
    assert float(barra["aria-valuenow"]) <= float(barra["aria-valuemax"])
    assert barra["aria-valuenow"] == "100"
    assert "120.00%" in resposta.get_data(as_text=True)
    assert "Meta ultrapassada" in barra["aria-valuetext"]
    assert barra.get("aria-describedby") in doc.ids


def test_relatorio_renderiza_tabela_e_graficos_acessiveis(
    cliente,
    inserir_receita,
    inserir_despesa,
    data_atual
):
    inserir_receita(valor=200, data=data_atual)
    inserir_despesa(valor=50, data=data_atual)
    resposta = cliente.get("/relatorios")
    doc = documento(resposta)
    for canvas_id, descricao_id in (
        ("graficoCategorias", "descricao-grafico-categorias"),
        ("graficoEvolucao", "descricao-grafico-evolucao"),
    ):
        canvas = doc.buscar("canvas", id=canvas_id, role="img")[0]
        assert canvas.get("aria-label")
        assert canvas.get("aria-describedby") == descricao_id
        assert descricao_id in doc.ids
    html = resposta.get_data(as_text=True)
    assert 'new Chart(document.getElementById("graficoCategorias")' in html
    assert 'new Chart(document.getElementById("graficoEvolucao")' in html
    assert "{{" not in html and "{%" not in html
    template = Path("templates/relatorios.html").read_text(encoding="utf-8")
    assert "| tojson" in template


def test_relatorio_sem_categorias_e_com_erro(cliente):
    vazio = cliente.get("/relatorios")
    assert "Não há despesas para analisar" in vazio.get_data(as_text=True)
    erro = cliente.get("/relatorios?mes=13&ano=2025")
    assert erro.status_code == 400
    assert documento(erro).buscar(role="alert")


def test_usuario_anonimo_continua_redirecionado(cliente_anonimo):
    resposta = cliente_anonimo.get("/receitas")
    assert resposta.status_code == 302
    assert "/login" in resposta.headers["Location"]

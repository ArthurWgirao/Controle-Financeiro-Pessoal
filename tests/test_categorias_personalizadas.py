import pytest

from datetime import datetime

from metas import listar_metas_mensais


@pytest.mark.parametrize(
    ("url", "tipo", "descricao", "categoria_personalizada"),
    [
        ("/receitas/nova", "receita", "Projeto", "Freelance"),
        ("/despesas/nova", "despesa", "Presente", "Presente de aniversário"),
    ]
)
def test_transacao_com_categoria_personalizada_persiste_nome_resolvido(
    cliente,
    conexao_banco,
    url,
    tipo,
    descricao,
    categoria_personalizada
):
    resposta = cliente.post(url, data={
        "descricao": descricao,
        "categoria": "Outro",
        "categoria_personalizada": f"  {categoria_personalizada}  ",
        "valor": "100"
    })

    assert resposta.status_code == 302
    categoria = conexao_banco(
        "SELECT categoria FROM transacoes WHERE tipo = ?", (tipo,)
    )[0]["categoria"]
    assert categoria == categoria_personalizada


@pytest.mark.parametrize("url", ["/receitas/nova", "/despesas/nova", "/metas/nova"])
@pytest.mark.parametrize("categoria_personalizada", ["", "   "])
def test_categoria_outro_sem_nome_e_rejeitada(
    cliente, conexao_banco, url, categoria_personalizada
):
    dados = {
        "categoria": "Outro",
        "categoria_personalizada": categoria_personalizada,
        "valor": "100",
        "descricao": "Teste",
        "limite": "100"
    }
    resposta = cliente.post(url, data=dados)

    assert resposta.status_code == 400
    assert "nome da categoria personalizada" in resposta.get_data(as_text=True)
    tabela = "metas" if url == "/metas/nova" else "transacoes"
    assert not conexao_banco(f"SELECT id FROM {tabela}")


def test_meta_personalizada_e_relatorio_usam_a_categoria_persistida(
    cliente, conexao_banco, inserir_despesa, data_atual, usuario
):
    assert cliente.post("/metas/nova", data={
        "categoria": "Outro",
        "categoria_personalizada": "Viagens",
        "limite": "300"
    }).status_code == 302
    inserir_despesa(categoria="Viagens", valor=120, data=data_atual)

    assert conexao_banco("SELECT categoria FROM metas")[0]["categoria"] == "Viagens"
    metas = listar_metas_mensais(datetime.now().strftime("%m/%Y"), usuario.id)
    assert metas[0]["gasto"] == 120
    html = cliente.get("/metas").get_data(as_text=True)
    assert "Viagens" in html
    assert "120,00" in html


@pytest.mark.parametrize(
    ("url_base", "inserir", "tipo"),
    [
        ("/receitas/editar", "inserir_receita", "receita"),
        ("/despesas/editar", "inserir_despesa", "despesa"),
    ]
)
def test_edicao_de_transacao_aceita_categoria_personalizada(
    request, cliente, conexao_banco, url_base, inserir, tipo
):
    identificador = request.getfixturevalue(inserir)(categoria="Comida")
    resposta = cliente.post(f"{url_base}/{identificador}", data={
        "categoria": "Outro",
        "categoria_personalizada": "Academia",
        "valor": "50"
    })

    assert resposta.status_code == 302
    assert conexao_banco(
        "SELECT categoria FROM transacoes WHERE id = ?", (identificador,)
    )[0]["categoria"] == "Academia"


def test_categoria_predefinida_tem_prioridade_sobre_valor_personalizado(
    cliente, conexao_banco
):
    resposta = cliente.post("/despesas/nova", data={
        "descricao": "Mercado",
        "categoria": "Comida",
        "categoria_personalizada": "Não deve ser salva",
        "valor": "40"
    })

    assert resposta.status_code == 302
    assert conexao_banco("SELECT categoria FROM transacoes")[0]["categoria"] == "Comida"


def test_formulario_exibe_campo_dinamico_e_edita_categoria_personalizada(
    cliente, inserir_receita
):
    html_novo = cliente.get("/receitas/nova").get_data(as_text=True)
    assert 'id="categoria_personalizada"' in html_novo
    assert "categoria.addEventListener('change', atualizar)" in html_novo

    identificador = inserir_receita(categoria="Freelance")
    html_edicao = cliente.get(f"/receitas/editar/{identificador}").get_data(as_text=True)
    assert 'value="Freelance"' in html_edicao
    assert 'value="Outro"' in html_edicao

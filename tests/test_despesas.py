import pytest


def test_paginas_e_separacao_da_listagem(
    cliente,
    inserir_receita,
    inserir_despesa
):
    inserir_receita(descricao="Somente receita")
    inserir_despesa(descricao="Somente despesa")

    html = cliente.get("/despesas").get_data(as_text=True)
    assert "Somente despesa" in html
    assert "Somente receita" not in html
    assert cliente.get("/despesas/nova").status_code == 200


def test_cadastro_de_despesa_persiste_com_data(
    cliente,
    conexao_banco,
    data_atual
):
    resposta = cliente.post(
        "/despesas/nova",
        data={
            "descricao": "Mercado",
            "categoria": "Comida",
            "valor": "40"
        }
    )
    assert resposta.status_code == 302
    despesa = conexao_banco(
        "SELECT * FROM transacoes WHERE tipo = 'despesa'"
    )[0]
    assert despesa["valor"] == 40
    assert despesa["data"] == data_atual


@pytest.mark.parametrize("valor", ["", "0", "-1", "texto", "inf", "NaN"])
def test_despesa_rejeita_valor_invalido(cliente, valor):
    resposta = cliente.post(
        "/despesas/nova",
        data={
            "descricao": "Preservada",
            "categoria": "Comida",
            "valor": valor
        }
    )
    assert resposta.status_code == 400
    assert "Preservada" in resposta.get_data(as_text=True)


def test_despesa_rejeita_categoria_invalida(cliente):
    resposta = cliente.post(
        "/despesas/nova",
        data={
            "descricao": "Teste",
            "categoria": "Inválida",
            "valor": "10"
        }
    )
    assert resposta.status_code == 400


def test_edita_despesa_preservando_tipo_e_data(
    cliente,
    inserir_despesa,
    conexao_banco
):
    identificador = inserir_despesa(data="01/02/2026")
    assert cliente.post(
        f"/despesas/editar/{identificador}",
        data={"valor": "30"}
    ).status_code == 302

    despesa = conexao_banco(
        "SELECT * FROM transacoes WHERE id = ?",
        (identificador,)
    )[0]
    assert despesa["tipo"] == "despesa"
    assert despesa["data"] == "01/02/2026"
    assert despesa["valor"] == 30


def test_formulario_de_edicao_e_valor_invalido(
    cliente,
    inserir_despesa
):
    identificador = inserir_despesa(descricao="Preservada")
    assert cliente.get(
        f"/despesas/editar/{identificador}"
    ).status_code == 200

    resposta = cliente.post(
        f"/despesas/editar/{identificador}",
        data={"valor": "NaN"}
    )
    assert resposta.status_code == 400
    assert "Preservada" in resposta.get_data(as_text=True)


def test_rotas_de_despesa_nao_modificam_receita(
    cliente,
    inserir_receita,
    conexao_banco
):
    identificador = inserir_receita(valor=80)
    assert cliente.get(
        f"/despesas/editar/{identificador}"
    ).status_code == 404
    assert cliente.post(
        f"/despesas/editar/{identificador}",
        data={"valor": "1"}
    ).status_code == 404
    assert cliente.post(
        f"/despesas/excluir/{identificador}"
    ).status_code == 404
    assert conexao_banco(
        "SELECT valor FROM transacoes WHERE id = ?",
        (identificador,)
    )[0]["valor"] == 80


def test_exclusao_despesa_por_post_e_confirmacao(
    cliente,
    inserir_despesa,
    conexao_banco
):
    identificador = inserir_despesa()
    html = cliente.get("/despesas").get_data(as_text=True)
    assert "confirm(" in html
    assert cliente.get(
        f"/despesas/excluir/{identificador}"
    ).status_code == 405
    assert cliente.post(
        f"/despesas/excluir/{identificador}"
    ).status_code == 302
    assert not conexao_banco(
        "SELECT id FROM transacoes WHERE id = ?",
        (identificador,)
    )


def test_exclusao_de_despesa_inexistente_retorna_404(cliente):
    assert cliente.post("/despesas/excluir/999999").status_code == 404

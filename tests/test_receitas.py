import pytest


def test_paginas_de_receita_renderizam(cliente):
    assert cliente.get("/receitas").status_code == 200
    resposta = cliente.get("/receitas/nova")
    assert resposta.status_code == 200
    assert b'name="valor"' in resposta.data


def test_cadastro_de_receita_persiste_e_redireciona(
    cliente,
    conexao_banco,
    data_atual
):
    resposta = cliente.post(
        "/receitas/nova",
        data={
            "descricao": "Salário",
            "categoria": "Salário",
            "valor": "1000"
        }
    )
    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/receitas")

    receita = conexao_banco(
        "SELECT * FROM transacoes WHERE tipo = 'receita'"
    )[0]
    assert receita["valor"] == 1000
    assert receita["data"] == data_atual


@pytest.mark.parametrize("valor", ["", "0", "-1", "texto", "inf", "NaN"])
def test_cadastro_rejeita_valor_invalido_e_preserva_dados(
    cliente,
    valor
):
    resposta = cliente.post(
        "/receitas/nova",
        data={
            "descricao": "Preservada",
            "categoria": "Salário",
            "valor": valor
        }
    )
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 400
    assert "Preservada" in texto
    assert f'value="{valor}"' in texto


def test_cadastro_rejeita_categoria_invalida(cliente):
    resposta = cliente.post(
        "/receitas/nova",
        data={
            "descricao": "Teste",
            "categoria": "Inválida",
            "valor": "10"
        }
    )
    assert resposta.status_code == 400
    assert "categoria válida" in resposta.get_data(as_text=True)


def test_edicao_preserva_identidade_e_data(
    cliente,
    inserir_receita,
    conexao_banco
):
    identificador = inserir_receita(
        valor=10,
        categoria="Outro",
        descricao="Original",
        data="01/01/2026"
    )
    resposta = cliente.post(
        f"/receitas/editar/{identificador}",
        data={"valor": "25"}
    )
    assert resposta.status_code == 302

    receita = conexao_banco(
        "SELECT * FROM transacoes WHERE id = ?",
        (identificador,)
    )[0]
    assert receita["tipo"] == "receita"
    assert receita["data"] == "01/01/2026"
    assert receita["descricao"] == "Original"
    assert receita["valor"] == 25


def test_formulario_de_edicao_e_valor_invalido(
    cliente,
    inserir_receita
):
    identificador = inserir_receita(descricao="Preservada")
    assert cliente.get(
        f"/receitas/editar/{identificador}"
    ).status_code == 200

    resposta = cliente.post(
        f"/receitas/editar/{identificador}",
        data={"valor": "NaN"}
    )
    assert resposta.status_code == 400
    assert "Preservada" in resposta.get_data(as_text=True)


def test_edicao_rejeita_id_inexistente_ou_despesa(
    cliente,
    inserir_despesa
):
    despesa_id = inserir_despesa()
    assert cliente.get("/receitas/editar/999999").status_code == 404
    assert cliente.get(
        f"/receitas/editar/{despesa_id}"
    ).status_code == 404
    assert cliente.post(
        f"/receitas/editar/{despesa_id}",
        data={"valor": "1"}
    ).status_code == 404


def test_exclusao_receita_somente_por_post(
    cliente,
    inserir_receita,
    conexao_banco
):
    identificador = inserir_receita()
    assert cliente.get(
        f"/receitas/excluir/{identificador}"
    ).status_code == 405

    resposta = cliente.post(f"/receitas/excluir/{identificador}")
    assert resposta.status_code == 302
    assert not conexao_banco(
        "SELECT id FROM transacoes WHERE id = ?",
        (identificador,)
    )


def test_listagem_tem_confirmacao_visual(cliente, inserir_receita):
    inserir_receita()
    html = cliente.get("/receitas").get_data(as_text=True)
    assert "confirm(" in html


def test_exclusao_de_receita_inexistente_retorna_404(cliente):
    assert cliente.post("/receitas/excluir/999999").status_code == 404

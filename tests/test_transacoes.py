from datetime import datetime

import pytest

import transacoes


def test_cadastra_e_busca_transacoes_por_tipo(caminho_banco, usuario):
    receita_id = transacoes.cadastrar_transacao(
        "receita", 100, "Salário", "Pagamento", usuario.id
    )
    despesa_id = transacoes.cadastrar_transacao(
        "despesa", 30, "Comida", "Mercado", usuario.id
    )

    receitas = transacoes.buscar_transacoes_por_tipo("receita", usuario.id)
    despesas = transacoes.buscar_transacoes_por_tipo("despesa", usuario.id)

    assert [item["id"] for item in receitas] == [receita_id]
    assert [item["id"] for item in despesas] == [despesa_id]
    assert receitas[0]["data"] == datetime.now().date()


def test_busca_ordenada_por_id_decrescente(caminho_banco, usuario):
    primeiro = transacoes.cadastrar_transacao(
        "receita", 10, "Outro", "Primeiro", usuario.id
    )
    segundo = transacoes.cadastrar_transacao(
        "receita", 20, "Outro", "Segundo", usuario.id
    )

    ids = [
        item["id"]
        for item in transacoes.buscar_transacoes_por_tipo("receita", usuario.id)
    ]
    assert ids == [segundo, primeiro]


def test_busca_por_id_exige_tipo_correto(caminho_banco, usuario):
    identificador = transacoes.cadastrar_transacao(
        "receita", 10, "Outro", "Teste", usuario.id
    )

    assert transacoes.buscar_transacao_por_id_e_tipo(
        identificador, "receita", usuario.id
    )
    assert transacoes.buscar_transacao_por_id_e_tipo(
        identificador, "despesa", usuario.id
    ) is None
    assert transacoes.buscar_transacao_por_id_e_tipo(
        999999, "receita", usuario.id
    ) is None


def test_atualizacao_preserva_id_tipo_e_data(caminho_banco, usuario):
    identificador = transacoes.cadastrar_transacao(
        "despesa", 10, "Comida", "Original", usuario.id
    )
    antes = transacoes.buscar_transacao_por_id_e_tipo(
        identificador, "despesa", usuario.id
    )

    assert transacoes.atualizar_transacao(
        identificador, "despesa", 25, "Lazer", "Atualizada", usuario.id
    )

    depois = transacoes.buscar_transacao_por_id_e_tipo(
        identificador, "despesa", usuario.id
    )
    assert depois["id"] == antes["id"]
    assert depois["tipo"] == antes["tipo"]
    assert depois["data"] == antes["data"]
    assert depois["valor"] == 25


def test_atualizacao_e_exclusao_bloqueiam_tipo_cruzado(caminho_banco, usuario):
    identificador = transacoes.cadastrar_transacao(
        "receita", 50, "Outro", "Protegida", usuario.id
    )

    assert not transacoes.atualizar_transacao(
        identificador, "despesa", 1, "Comida", "Ataque", usuario.id
    )
    assert not transacoes.excluir_transacao(identificador, "despesa", usuario.id)
    assert transacoes.buscar_transacao_por_id_e_tipo(
        identificador, "receita", usuario.id
    )["valor"] == 50


def test_exclusao_e_id_inexistente(caminho_banco, usuario):
    identificador = transacoes.cadastrar_transacao(
        "despesa", 10, "Outro", "Excluir", usuario.id
    )
    assert transacoes.excluir_transacao(identificador, "despesa", usuario.id)
    assert not transacoes.excluir_transacao(identificador, "despesa", usuario.id)


@pytest.mark.parametrize(
    ("receitas", "despesas", "saldo"),
    [(100, 40, 60), (40, 100, -60), (100, 100, 0)]
)
def test_resumo_e_estados_de_saldo(
    caminho_banco,
    receitas,
    despesas,
    saldo,
    usuario
):
    transacoes.cadastrar_transacao(
        "receita", receitas, "Outro", "Receita", usuario.id
    )
    transacoes.cadastrar_transacao(
        "despesa", despesas, "Outro", "Despesa", usuario.id
    )

    assert transacoes.calcular_resumo(usuario.id) == (
        receitas,
        despesas,
        saldo
    )


def test_resumo_ignora_tipo_desconhecido(inserir_transacao, usuario):
    inserir_transacao(tipo="outro", valor=999)
    inserir_transacao(tipo="receita", valor=20)

    assert transacoes.calcular_resumo(usuario.id) == (20, 0, 20)


def test_funcoes_antigas_do_terminal_permanecem_disponiveis():
    nomes = [
        "add_receita",
        "add_despesa",
        "listar_transacoes",
        "ver_saldo",
        "remover_transacao",
        "editar_transacao",
        "filtrar_por_categoria",
        "total_por_categoria",
        "relatorio_mensal"
    ]
    assert all(callable(getattr(transacoes, nome)) for nome in nomes)

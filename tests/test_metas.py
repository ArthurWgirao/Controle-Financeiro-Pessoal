from datetime import datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

import metas
from extensions import db
from models import Meta


def test_funcoes_de_persistencia_de_meta(caminho_banco, usuario):
    identificador = metas.cadastrar_meta("Comida", 100, usuario.id)
    assert metas.categoria_possui_meta("Comida", usuario.id)
    assert metas.buscar_meta_por_id(identificador, usuario.id)["limite"] == 100

    assert metas.atualizar_limite_meta(identificador, 150, usuario.id)
    atualizada = metas.buscar_meta_por_id(identificador, usuario.id)
    assert atualizada["categoria"] == "Comida"
    assert atualizada["limite"] == 150

    assert metas.excluir_meta_por_id(identificador, usuario.id)
    assert metas.buscar_meta_por_id(identificador, usuario.id) is None


@pytest.mark.parametrize(
    ("gasto", "situacao", "classe", "restante", "largura"),
    [
        (0, "Dentro da meta", "dentro", 100, 0),
        (79, "Dentro da meta", "dentro", 21, 79),
        (80, "Atenção", "atencao", 20, 80),
        (100, "Meta ultrapassada", "ultrapassada", 0, 100),
        (120, "Meta ultrapassada", "ultrapassada", -20, 100)
    ]
)
def test_calculo_dos_estados_da_meta(
    gasto,
    situacao,
    classe,
    restante,
    largura
):
    dados = metas.calcular_dados_meta(
        {"id": 1, "categoria": "Comida", "limite": 100},
        gasto
    )
    assert dados["situacao"] == situacao
    assert dados["classe_situacao"] == classe
    assert dados["restante"] == restante
    assert dados["percentual"] == pytest.approx(gasto)
    assert dados["largura_barra"] == largura


def test_gasto_mensal_ignora_receita_e_despesa_antiga(
    caminho_banco,
    inserir_despesa,
    inserir_receita,
    data_atual,
    data_mes_anterior,
    usuario
):
    inserir_despesa(valor=30, data=data_atual)
    inserir_despesa(valor=500, data=data_mes_anterior)
    inserir_receita(valor=900, data=data_atual)

    mes = datetime.now().strftime("%m/%Y")
    assert metas.calcular_gasto_mensal_por_categoria(
        "Comida", mes, usuario.id
    ) == 30


def test_listagem_mensal_integra_despesas(
    inserir_meta,
    inserir_despesa,
    data_atual,
    usuario
):
    inserir_meta(limite=100)
    inserir_despesa(valor=40, data=data_atual)

    lista = metas.listar_metas_mensais(
        datetime.now().strftime("%m/%Y"), usuario.id
    )
    assert lista[0]["gasto"] == 40
    assert lista[0]["restante"] == 60


def test_pagina_vazia_de_metas(cliente):
    resposta = cliente.get("/metas")
    assert resposta.status_code == 200
    assert "Nenhuma meta cadastrada" in resposta.get_data(as_text=True)


def test_cadastro_web_de_meta_e_duplicidade(cliente, conexao_banco):
    dados = {"categoria": "Comida", "limite": "100"}
    assert cliente.post("/metas/nova", data=dados).status_code == 302
    resposta = cliente.post("/metas/nova", data=dados)
    assert resposta.status_code == 400
    assert "Já existe" in resposta.get_data(as_text=True)
    assert len(conexao_banco("SELECT * FROM metas")) == 1


def test_servico_converte_duplicidade_e_recupera_sessao(
    caminho_banco,
    usuario
):
    primeiro_id = metas.cadastrar_meta("Comida", 100, usuario.id)

    with pytest.raises(metas.MetaDuplicadaError):
        metas.cadastrar_meta("Comida", 200, usuario.id)

    assert db.session.scalar(
        select(func.count()).select_from(Meta).where(
            Meta.usuario_id == usuario.id,
            Meta.categoria == "Comida"
        )
    ) == 1
    assert db.session.get(Meta, primeiro_id).limite == 100

    segundo_id = metas.cadastrar_meta("Lazer", 300, usuario.id)
    assert db.session.get(Meta, segundo_id).categoria == "Lazer"


def test_mesma_categoria_permitida_para_usuarios_diferentes(
    caminho_banco,
    usuario,
    segundo_usuario
):
    metas.cadastrar_meta("Comida", 100, usuario.id)
    metas.cadastrar_meta("Comida", 200, segundo_usuario.id)

    registros = db.session.scalars(
        select(Meta).where(Meta.categoria == "Comida").order_by(Meta.id)
    ).all()
    assert [meta.usuario_id for meta in registros] == [
        usuario.id,
        segundo_usuario.id
    ]


def test_integrity_error_nao_relacionada_nao_e_mascarada(
    caminho_banco,
    usuario,
    monkeypatch
):
    metas.cadastrar_meta("Educação", 80, usuario.id)
    erro_original = IntegrityError(
        "falha simulada",
        {},
        RuntimeError("integridade não relacionada")
    )
    rollback_original = db.session.rollback
    rollback_executado = False

    def registrar_rollback():
        nonlocal rollback_executado
        rollback_executado = True
        rollback_original()

    monkeypatch.setattr(db.session, "commit", lambda: (_ for _ in ()).throw(
        erro_original
    ))
    monkeypatch.setattr(db.session, "rollback", registrar_rollback)

    with pytest.raises(IntegrityError) as capturada:
        metas.cadastrar_meta("Educação", 100, usuario.id)

    assert capturada.value is erro_original
    assert rollback_executado
    assert metas.categoria_possui_meta("Educação", usuario.id)


def test_rota_trata_janela_de_corrida_sem_erro_500(
    cliente,
    inserir_meta,
    conexao_banco,
    monkeypatch
):
    inserir_meta(categoria="Comida", limite=100)
    monkeypatch.setattr("app.categoria_possui_meta", lambda *args: False)

    resposta = cliente.post(
        "/metas/nova",
        data={"categoria": "Comida", "limite": "275.50"}
    )
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 400
    assert "Já existe uma meta para esta categoria." in html
    assert 'value="275.50"' in html
    assert 'value="Comida"' in html
    assert len(conexao_banco("SELECT * FROM metas")) == 1
    assert db.session.scalar(select(func.count()).select_from(Meta)) == 1


@pytest.mark.parametrize("limite", ["", "0", "-1", "texto", "inf", "NaN"])
def test_rota_meta_rejeita_limite_invalido(cliente, limite):
    resposta = cliente.post(
        "/metas/nova",
        data={"categoria": "Comida", "limite": limite}
    )
    assert resposta.status_code == 400
    assert f'value="{limite}"' in resposta.get_data(as_text=True)


def test_rota_meta_rejeita_categoria_invalida(cliente):
    assert cliente.post(
        "/metas/nova",
        data={"categoria": "Inválida", "limite": "100"}
    ).status_code == 400


def test_edicao_web_preserva_categoria(
    cliente,
    inserir_meta,
    conexao_banco
):
    identificador = inserir_meta(categoria="Comida", limite=100)
    resposta = cliente.post(
        f"/metas/editar/{identificador}",
        data={"categoria": "Lazer", "limite": "200"}
    )
    assert resposta.status_code == 302
    meta = conexao_banco(
        "SELECT * FROM metas WHERE id = ?",
        (identificador,)
    )[0]
    assert meta["categoria"] == "Comida"
    assert meta["limite"] == 200


def test_formulario_de_edicao_e_limite_invalido(
    cliente,
    inserir_meta
):
    identificador = inserir_meta(categoria="Comida", limite=100)
    resposta_get = cliente.get(f"/metas/editar/{identificador}")
    assert resposta_get.status_code == 200
    assert "Comida" in resposta_get.get_data(as_text=True)

    resposta_post = cliente.post(
        f"/metas/editar/{identificador}",
        data={"limite": "NaN"}
    )
    assert resposta_post.status_code == 400
    assert 'value="NaN"' in resposta_post.get_data(as_text=True)


def test_ids_inexistentes_de_meta_retornam_404(cliente):
    assert cliente.get("/metas/editar/999999").status_code == 404
    assert cliente.post(
        "/metas/editar/999999",
        data={"limite": "100"}
    ).status_code == 404
    assert cliente.post("/metas/excluir/999999").status_code == 404


def test_exclusao_meta_nao_exclui_transacoes(
    cliente,
    inserir_meta,
    inserir_despesa,
    conexao_banco
):
    meta_id = inserir_meta()
    transacao_id = inserir_despesa()
    html = cliente.get("/metas").get_data(as_text=True)
    assert "confirm(" in html
    assert cliente.get(f"/metas/excluir/{meta_id}").status_code == 405
    assert cliente.post(f"/metas/excluir/{meta_id}").status_code == 302
    assert conexao_banco(
        "SELECT id FROM transacoes WHERE id = ?",
        (transacao_id,)
    )


def test_barra_visual_limitada_em_cem(
    cliente,
    inserir_meta,
    inserir_despesa,
    data_atual
):
    inserir_meta(limite=100)
    inserir_despesa(valor=120, data=data_atual)
    html = cliente.get("/metas").get_data(as_text=True)
    assert "120.00%" in html
    assert "width: 100%;" in html

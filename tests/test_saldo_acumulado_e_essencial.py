from categorias import categorias
from extensions import db
from models import Transacao
from relatorios import preparar_relatorio


def _resumo(usuario_id, mes, ano):
    return preparar_relatorio(mes, ano, usuario_id)["resumo"]


def test_saldo_acumulado_mantem_continuidade_entre_meses(
    inserir_transacao, usuario
):
    inserir_transacao(tipo="receita", valor=2000, data="01/08/2026")
    inserir_transacao(tipo="despesa", valor=1900, data="02/08/2026")
    inserir_transacao(tipo="receita", valor=500, data="01/10/2026")
    inserir_transacao(tipo="despesa", valor=30, data="01/11/2026")

    agosto = _resumo(usuario.id, 8, 2026)
    setembro = _resumo(usuario.id, 9, 2026)
    outubro = _resumo(usuario.id, 10, 2026)
    novembro = _resumo(usuario.id, 11, 2026)

    assert (agosto["saldo_anterior"], agosto["saldo"]) == (0, 100)
    assert (setembro["saldo_anterior"], setembro["saldo"]) == (100, 100)
    assert (outubro["saldo_anterior"], outubro["saldo"]) == (100, 600)
    assert (novembro["saldo_anterior"], novembro["saldo"]) == (600, 570)


def test_saldo_acumulado_considera_todos_os_anos_anteriores(
    inserir_transacao, usuario
):
    inserir_transacao(tipo="receita", valor=500, data="01/12/2025")
    inserir_transacao(tipo="despesa", valor=100, data="02/01/2026")
    inserir_transacao(tipo="receita", valor=300, data="01/03/2026")

    resumo = _resumo(usuario.id, 3, 2026)
    assert resumo["saldo_anterior"] == 400
    assert resumo["saldo"] == 700


def test_saldo_acumulado_recalcula_apos_alteracao_retroativa(
    inserir_transacao, usuario
):
    identificador = inserir_transacao(
        tipo="receita", valor=100, data="01/08/2026"
    )
    assert _resumo(usuario.id, 9, 2026)["saldo"] == 100

    db.session.get(Transacao, identificador).valor = 60
    db.session.commit()
    assert _resumo(usuario.id, 9, 2026)["saldo"] == 60

    db.session.delete(db.session.get(Transacao, identificador))
    db.session.commit()
    assert _resumo(usuario.id, 9, 2026)["saldo"] == 0


def test_grafico_de_saldos_e_acumulado_com_mes_sem_movimentacao(
    inserir_transacao, usuario
):
    inserir_transacao(tipo="receita", valor=100, data="01/02/2026")
    inserir_transacao(tipo="despesa", valor=20, data="01/03/2026")
    relatorio = preparar_relatorio(7, 2026, usuario.id)

    assert relatorio["evolucao"]["saldos"] == [100, 80, 80, 80, 80, 80]


def test_categoria_essencial_e_disponivel_e_funciona_nos_fluxos(
    cliente, conexao_banco, inserir_despesa, data_atual
):
    assert "Essencial" in categorias
    assert "Outro" in categorias
    assert "Essencial" in cliente.get("/despesas/nova").get_data(as_text=True)

    assert cliente.post("/receitas/nova", data={
        "descricao": "Reembolso", "categoria": "Essencial", "valor": "50"
    }).status_code == 302
    assert cliente.post("/despesas/nova", data={
        "descricao": "Óculos", "categoria": "Essencial", "valor": "80"
    }).status_code == 302
    assert cliente.post("/metas/nova", data={
        "categoria": "Essencial", "limite": "300"
    }).status_code == 302

    inserir_despesa(categoria="Essencial", valor=20, data=data_atual)
    html = cliente.get("/metas").get_data(as_text=True)
    assert "Essencial" in html
    assert "100,00" in html
    assert "Essencial" in cliente.get("/").get_data(as_text=True)
    assert conexao_banco(
        "SELECT categoria FROM transacoes WHERE descricao = ?", ("Óculos",)
    )[0]["categoria"] == "Essencial"


def test_edicao_aceita_categoria_essencial_e_outro_permanece_funcional(
    cliente, inserir_despesa, conexao_banco
):
    identificador = inserir_despesa(categoria="Comida")
    assert cliente.post(f"/despesas/editar/{identificador}", data={
        "categoria": "Essencial", "valor": "30"
    }).status_code == 302
    assert conexao_banco(
        "SELECT categoria FROM transacoes WHERE id = ?", (identificador,)
    )[0]["categoria"] == "Essencial"

    assert cliente.post("/despesas/nova", data={
        "descricao": "Academia", "categoria": "Outro",
        "categoria_personalizada": "Academia", "valor": "90"
    }).status_code == 302

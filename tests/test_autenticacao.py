import re

import pytest
from flask import g

from autenticacao import autenticar_usuario, cadastrar_usuario
from extensions import db
from models import Usuario


def test_cadastro_normaliza_email_e_hash(caminho_banco):
    usuario, erro = cadastrar_usuario(
        "  Pessoa Teste  ", "  PESSOA@EXAMPLE.TEST  ",
        "senha-segura", "senha-segura"
    )
    assert erro is None
    assert usuario.nome == "Pessoa Teste"
    assert usuario.email == "pessoa@example.test"
    assert usuario.senha_hash != "senha-segura"
    assert usuario.verificar_senha("senha-segura")
    assert not usuario.verificar_senha("incorreta")


@pytest.mark.parametrize(
    ("nome", "email", "senha", "confirmacao", "trecho"),
    [
        ("", "pessoa@example.test", "senha-segura", "senha-segura", "nome"),
        ("Pessoa", "invalido", "senha-segura", "senha-segura", "e-mail"),
        ("Pessoa", "pessoa@example.test", "", "", "senha"),
        ("Pessoa", "pessoa@example.test", "curta", "curta", "8"),
        ("Pessoa", "pessoa@example.test", "x" * 129, "x" * 129, "128"),
        ("Pessoa", "pessoa@example.test", "senha-segura", "diferente", "confirmação"),
    ]
)
def test_cadastro_rejeita_dados_invalidos(caminho_banco, nome, email, senha, confirmacao, trecho):
    usuario, erro = cadastrar_usuario(nome, email, senha, confirmacao)
    assert usuario is None
    assert trecho in erro.lower()


def test_duplicidade_independe_de_caixa(caminho_banco):
    assert cadastrar_usuario("Um", "conta@example.test", "senha-segura", "senha-segura")[0]
    usuario, erro = cadastrar_usuario("Dois", "CONTA@EXAMPLE.TEST", "outra-senha", "outra-senha")
    assert usuario is None
    assert "existe" in erro


def test_autenticacao_generica_e_usuario_inativo(caminho_banco):
    usuario, _ = cadastrar_usuario("Pessoa", "pessoa@example.test", "senha-segura", "senha-segura")
    assert autenticar_usuario("PESSOA@example.test", "senha-segura") == usuario
    assert autenticar_usuario("ausente@example.test", "senha-segura") is None
    assert autenticar_usuario(usuario.email, "incorreta") is None
    usuario.ativo = False
    db.session.commit()
    assert autenticar_usuario(usuario.email, "senha-segura") is None


def test_fluxo_web_login_next_logout(aplicacao, cliente_anonimo, usuario):
    assert cliente_anonimo.get("/").status_code == 302
    resposta = cliente_anonimo.post("/login?next=/receitas", data={
        "email": usuario.email, "senha": "senha-segura"
    })
    assert resposta.headers["Location"].endswith("/receitas")
    assert cliente_anonimo.get("/logout").status_code == 405
    assert cliente_anonimo.post("/logout").status_code == 302
    assert cliente_anonimo.get("/").status_code == 302


@pytest.mark.parametrize("destino", ["https://site-malicioso.example", "//site-malicioso.example"])
def test_login_bloqueia_next_externo(cliente_anonimo, usuario, destino):
    resposta = cliente_anonimo.post(f"/login?next={destino}", data={
        "email": usuario.email, "senha": "senha-segura"
    })
    assert resposta.headers["Location"].endswith("/")


def test_login_nao_enumera_usuario(cliente_anonimo, usuario):
    inexistente = cliente_anonimo.post("/login", data={"email": "ausente@example.test", "senha": "senha-segura"})
    incorreta = cliente_anonimo.post("/login", data={"email": usuario.email, "senha": "incorreta"})
    assert "E-mail ou senha inválidos" in inexistente.get_data(as_text=True)
    assert "E-mail ou senha inválidos" in incorreta.get_data(as_text=True)


def test_isolamento_completo_web(cliente, usuario, segundo_usuario, inserir_transacao, inserir_meta):
    receita_outro = inserir_transacao(tipo="receita", valor=900, descricao="Outro", usuario_id=segundo_usuario.id)
    despesa_outro = inserir_transacao(tipo="despesa", valor=400, descricao="Privada", usuario_id=segundo_usuario.id)
    meta_outro = inserir_meta(categoria="Comida", limite=700, usuario_id=segundo_usuario.id)
    inserir_transacao(tipo="receita", valor=100, descricao="Minha", usuario_id=usuario.id)
    inserir_transacao(tipo="despesa", valor=20, descricao="Minha despesa", usuario_id=usuario.id)
    inserir_meta(categoria="Comida", limite=100, usuario_id=usuario.id)

    dashboard = cliente.get("/").get_data(as_text=True)
    receitas = cliente.get("/receitas").get_data(as_text=True)
    despesas = cliente.get("/despesas").get_data(as_text=True)
    relatorio = cliente.get("/relatorios", follow_redirects=True).get_data(as_text=True)
    assert "900,00" not in dashboard and "400,00" not in dashboard
    assert "Outro" not in receitas and "Privada" not in despesas
    assert "Privada" not in relatorio and "Outro" not in relatorio
    assert cliente.get(f"/receitas/editar/{receita_outro}").status_code == 404
    assert cliente.post(f"/despesas/excluir/{despesa_outro}").status_code == 404
    assert cliente.get(f"/metas/editar/{meta_outro}").status_code == 404


def _token_csrf(cliente, caminho):
    g.pop("csrf_token", None)
    html = cliente.get(caminho).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_csrf_global_logout_e_exclusao(aplicacao, usuario, inserir_receita):
    aplicacao.config["WTF_CSRF_ENABLED"] = True
    cliente = aplicacao.test_client()
    token = _token_csrf(cliente, "/login")
    assert cliente.post("/login", data={"email": usuario.email, "senha": "senha-segura"}).status_code == 400
    assert cliente.post("/login", data={"csrf_token": "invalido", "email": usuario.email, "senha": "senha-segura"}).status_code == 400
    assert cliente.post("/login", data={"csrf_token": token, "email": usuario.email, "senha": "senha-segura"}).status_code == 302
    receita_id = inserir_receita()
    assert cliente.post(f"/receitas/excluir/{receita_id}").status_code == 400
    token = _token_csrf(cliente, "/receitas")
    resposta_exclusao = cliente.post(
        f"/receitas/excluir/{receita_id}", data={"csrf_token": token}
    )
    assert resposta_exclusao.status_code == 302, resposta_exclusao.get_data(as_text=True)
    assert cliente.post("/logout").status_code == 400
    token = _token_csrf(cliente, "/")
    assert cliente.post("/logout", data={"csrf_token": token}).status_code == 302

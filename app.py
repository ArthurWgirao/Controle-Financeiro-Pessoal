from datetime import datetime

from dotenv import load_dotenv
from urllib.parse import urljoin, urlparse

import click
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

load_dotenv(override=False)

from categorias import categorias
from config import (
    aplicar_variaveis_ambiente,
    configurar_uri_banco,
    obter_ambiente,
    obter_classe_configuracao,
    validar_configuracao_producao
)
from autenticacao import autenticar_usuario, cadastrar_usuario, normalizar_email
from extensions import csrf, db, login_manager, migrate
from models import Meta, Transacao, Usuario
from sqlalchemy import select
from metas import (
    MetaDuplicadaError,
    atualizar_limite_meta,
    buscar_meta_por_id,
    cadastrar_meta,
    categoria_possui_meta,
    excluir_meta_por_id,
    listar_metas_mensais
)
from relatorios import MESES, preparar_relatorio, validar_periodo
from transacoes import (
    atualizar_transacao,
    buscar_transacao_por_id_e_tipo,
    buscar_transacoes_por_tipo,
    cadastrar_transacao,
    excluir_transacao
)
from validacoes import (
    validar_limite_meta,
    validar_meta,
    validar_transacao
)
from migracao_dados import comando_transferencia


@login_required
def dashboard():

    mes_informado = request.args.get("mes")
    ano_informado = request.args.get("ano")
    mes, ano, erro = validar_periodo(mes_informado, ano_informado)
    agora = datetime.now()
    mes_metas = agora.strftime("%m/%Y")
    periodo_metas = f"{MESES[agora.month - 1]} de {agora.year}"
    relatorio = preparar_relatorio(mes, ano, current_user.id) if not erro else None
    lista_metas = listar_metas_mensais(mes_metas, current_user.id)

    return render_template(
        "dashboard.html",
        relatorio=relatorio,
        metas=lista_metas,
        grafico_metas={
            "rotulos": [meta["categoria"] for meta in lista_metas],
            "limites": [float(meta["limite"]) for meta in lista_metas],
            "gastos": [float(meta["gasto"]) for meta in lista_metas]
        },
        periodo_metas=periodo_metas,
        meses=MESES,
        mes_selecionado=(mes_informado if erro else str(mes)),
        ano_selecionado=(ano_informado if erro else str(ano)),
        erro=erro,
        formatar_moeda=formatar_moeda
    ), (400 if erro else 200)


# Receitas

@login_required
def receitas():

    lista_receitas = buscar_transacoes_por_tipo("receita", current_user.id)

    return render_template(
        "receitas.html",
        receitas=lista_receitas
    )


@login_required
def nova_receita():

    if request.method == "POST":

        descricao = request.form.get("descricao", "").strip()
        categoria = request.form.get("categoria", "").strip()
        valor_informado = request.form.get("valor", "").strip()

        dados_formulario = {
            "descricao": descricao,
            "categoria": categoria,
            "valor": valor_informado
        }

        valor, erro = validar_transacao(
            descricao,
            categoria,
            valor_informado,
            categorias,
            "receita"
        )

        if erro:
            return render_template(
                "form_receita.html",
                titulo="Nova Receita",
                receita=dados_formulario,
                categorias=categorias,
                erro=erro
            ), 400

        cadastrar_transacao(
            "receita",
            valor,
            categoria,
            descricao,
            current_user.id
        )

        return redirect("/receitas")

    return render_template(
        "form_receita.html",
        titulo="Nova Receita",
        receita=None,
        categorias=categorias,
        erro=None
    )


@login_required
def editar_receita(id):

    receita = buscar_transacao_por_id_e_tipo(id, "receita", current_user.id)

    if receita is None:
        abort(404)

    if request.method == "POST":

        descricao_informada = request.form.get("descricao")
        categoria_informada = request.form.get("categoria")
        valor_informado = request.form.get("valor", "").strip()

        descricao = (
            descricao_informada.strip()
            if descricao_informada and descricao_informada.strip()
            else receita["descricao"]
        )
        categoria = (
            categoria_informada.strip()
            if categoria_informada and categoria_informada.strip()
            else receita["categoria"]
        )

        dados_formulario = {
            "id": receita["id"],
            "tipo": receita["tipo"],
            "descricao": descricao,
            "categoria": categoria,
            "valor": valor_informado,
            "data": receita["data"]
        }

        valor, erro = validar_transacao(
            descricao,
            categoria,
            valor_informado,
            categorias,
            "receita"
        )

        if erro:
            return render_template(
                "form_receita.html",
                titulo="Editar Receita",
                receita=dados_formulario,
                categorias=categorias,
                erro=erro
            ), 400

        if not atualizar_transacao(
            id,
            "receita",
            valor,
            categoria,
            descricao,
            current_user.id
        ):
            abort(404)

        return redirect("/receitas")

    return render_template(
        "form_receita.html",
        titulo="Editar Receita",
        receita=receita,
        categorias=categorias,
        erro=None
    )


@login_required
def excluir_receita(id):

    if not excluir_transacao(id, "receita", current_user.id):
        abort(404)

    return redirect("/receitas")


# Despesas

@login_required
def despesas():

    lista_despesas = buscar_transacoes_por_tipo("despesa", current_user.id)

    return render_template(
        "despesas.html",
        despesas=lista_despesas
    )


@login_required
def nova_despesa():

    if request.method == "POST":

        descricao = request.form.get("descricao", "").strip()
        categoria = request.form.get("categoria", "").strip()
        valor_informado = request.form.get("valor", "").strip()

        dados_formulario = {
            "descricao": descricao,
            "categoria": categoria,
            "valor": valor_informado
        }

        valor, erro = validar_transacao(
            descricao,
            categoria,
            valor_informado,
            categorias,
            "despesa"
        )

        if erro:
            return render_template(
                "form_despesa.html",
                titulo="Nova Despesa",
                despesa=dados_formulario,
                categorias=categorias,
                erro=erro
            ), 400

        cadastrar_transacao(
            "despesa",
            valor,
            categoria,
            descricao,
            current_user.id
        )

        return redirect("/despesas")

    return render_template(
        "form_despesa.html",
        titulo="Nova Despesa",
        despesa=None,
        categorias=categorias,
        erro=None
    )


@login_required
def editar_despesa(id):

    despesa = buscar_transacao_por_id_e_tipo(id, "despesa", current_user.id)

    if despesa is None:
        abort(404)

    if request.method == "POST":

        descricao_informada = request.form.get("descricao")
        categoria_informada = request.form.get("categoria")
        valor_informado = request.form.get("valor", "").strip()

        descricao = (
            descricao_informada.strip()
            if descricao_informada and descricao_informada.strip()
            else despesa["descricao"]
        )
        categoria = (
            categoria_informada.strip()
            if categoria_informada and categoria_informada.strip()
            else despesa["categoria"]
        )

        dados_formulario = {
            "id": despesa["id"],
            "tipo": despesa["tipo"],
            "descricao": descricao,
            "categoria": categoria,
            "valor": valor_informado,
            "data": despesa["data"]
        }

        valor, erro = validar_transacao(
            descricao,
            categoria,
            valor_informado,
            categorias,
            "despesa"
        )

        if erro:
            return render_template(
                "form_despesa.html",
                titulo="Editar Despesa",
                despesa=dados_formulario,
                categorias=categorias,
                erro=erro
            ), 400

        if not atualizar_transacao(
            id,
            "despesa",
            valor,
            categoria,
            descricao,
            current_user.id
        ):
            abort(404)

        return redirect("/despesas")

    return render_template(
        "form_despesa.html",
        titulo="Editar Despesa",
        despesa=despesa,
        categorias=categorias,
        erro=None
    )


@login_required
def excluir_despesa(id):

    if not excluir_transacao(id, "despesa", current_user.id):
        abort(404)

    return redirect("/despesas")


# Metas

@login_required
def metas():

    mes_referencia = datetime.now().strftime("%m/%Y")
    lista_metas = listar_metas_mensais(mes_referencia, current_user.id)

    return render_template(
        "metas.html",
        metas=lista_metas,
        mes_referencia=mes_referencia,
        formatar_moeda=formatar_moeda
    )


@login_required
def nova_meta():

    if request.method == "POST":

        categoria = request.form.get("categoria", "").strip()
        limite_informado = request.form.get("limite", "").strip()

        dados_formulario = {
            "categoria": categoria,
            "limite": limite_informado
        }

        limite, erro = validar_meta(
            categoria,
            limite_informado,
            categorias
        )

        if not erro and categoria_possui_meta(categoria, current_user.id):
            erro = "Já existe uma meta para esta categoria."

        if not erro:
            try:
                cadastrar_meta(categoria, limite, current_user.id)
            except MetaDuplicadaError:
                erro = "Já existe uma meta para esta categoria."

        if erro:
            return render_template(
                "form_meta.html",
                titulo="Nova Meta Mensal",
                meta=dados_formulario,
                categorias=categorias,
                erro=erro,
                edicao=False
            ), 400

        return redirect("/metas")

    return render_template(
        "form_meta.html",
        titulo="Nova Meta Mensal",
        meta=None,
        categorias=categorias,
        erro=None,
        edicao=False
    )


@login_required
def editar_meta(id):

    meta = buscar_meta_por_id(id, current_user.id)

    if meta is None:
        abort(404)

    if request.method == "POST":

        limite_informado = request.form.get("limite", "").strip()
        limite, erro = validar_limite_meta(limite_informado)

        if erro:
            dados_formulario = {
                "id": meta["id"],
                "categoria": meta["categoria"],
                "limite": limite_informado
            }

            return render_template(
                "form_meta.html",
                titulo="Editar Meta Mensal",
                meta=dados_formulario,
                categorias=categorias,
                erro=erro,
                edicao=True
            ), 400

        if not atualizar_limite_meta(id, limite, current_user.id):
            abort(404)

        return redirect("/metas")

    return render_template(
        "form_meta.html",
        titulo="Editar Meta Mensal",
        meta=meta,
        categorias=categorias,
        erro=None,
        edicao=True
    )


@login_required
def excluir_meta(id):

    if not excluir_meta_por_id(id, current_user.id):
        abort(404)

    return redirect("/metas")


def formatar_moeda(valor):

    valor_formatado = f"{valor:,.2f}"

    return (
        valor_formatado
        .replace(",", "TEMP")
        .replace(".", ",")
        .replace("TEMP", ".")
    )


# Relatórios

@login_required
def relatorios():
    parametros = {
        nome: request.args[nome]
        for nome in ("mes", "ano")
        if nome in request.args
    }
    return redirect(url_for("dashboard", **parametros))


def _destino_local(destino):
    if not destino:
        return None
    base = urlparse(request.host_url)
    alvo = urlparse(urljoin(request.host_url, destino))
    return destino if alvo.scheme in ("http", "https") and alvo.netloc == base.netloc else None


def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    nome = request.form.get("nome", "").strip()
    email = normalizar_email(request.form.get("email"))
    erro = None
    if request.method == "POST":
        usuario, erro = cadastrar_usuario(
            nome, email, request.form.get("senha", ""),
            request.form.get("confirmacao_senha", "")
        )
        if usuario:
            session.clear()
            login_user(usuario)
            flash("Conta criada com sucesso.", "sucesso")
            return redirect(url_for("dashboard"))
    return render_template("cadastro.html", nome=nome, email=email, erro=erro), (400 if erro else 200)


def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    email = normalizar_email(request.form.get("email"))
    erro = None
    if request.method == "POST":
        usuario = autenticar_usuario(email, request.form.get("senha", ""))
        if usuario:
            lembrar = request.form.get("lembrar") == "1"
            destino = _destino_local(request.args.get("next"))
            session.clear()
            login_user(usuario, remember=lembrar, fresh=True)
            return redirect(destino or url_for("dashboard"))
        erro = "E-mail ou senha inválidos."
    return render_template("login.html", email=email, erro=erro), (401 if erro else 200)


@login_required
def logout():
    logout_user()
    session.clear()
    flash("Sessão encerrada.", "sucesso")
    return redirect(url_for("login"))


def registrar_rotas(app):
    app.add_url_rule("/cadastro", view_func=cadastro, methods=["GET", "POST"])
    app.add_url_rule("/login", view_func=login, methods=["GET", "POST"])
    app.add_url_rule("/logout", view_func=logout, methods=["POST"])
    app.add_url_rule("/", view_func=dashboard)
    app.add_url_rule("/receitas", view_func=receitas)
    app.add_url_rule(
        "/receitas/nova",
        view_func=nova_receita,
        methods=["GET", "POST"]
    )
    app.add_url_rule(
        "/receitas/editar/<int:id>",
        view_func=editar_receita,
        methods=["GET", "POST"]
    )
    app.add_url_rule(
        "/receitas/excluir/<int:id>",
        view_func=excluir_receita,
        methods=["POST"]
    )
    app.add_url_rule("/despesas", view_func=despesas)
    app.add_url_rule(
        "/despesas/nova",
        view_func=nova_despesa,
        methods=["GET", "POST"]
    )
    app.add_url_rule(
        "/despesas/editar/<int:id>",
        view_func=editar_despesa,
        methods=["GET", "POST"]
    )
    app.add_url_rule(
        "/despesas/excluir/<int:id>",
        view_func=excluir_despesa,
        methods=["POST"]
    )
    app.add_url_rule("/metas", view_func=metas)
    app.add_url_rule(
        "/metas/nova",
        view_func=nova_meta,
        methods=["GET", "POST"]
    )
    app.add_url_rule(
        "/metas/editar/<int:id>",
        view_func=editar_meta,
        methods=["GET", "POST"]
    )
    app.add_url_rule(
        "/metas/excluir/<int:id>",
        view_func=excluir_meta,
        methods=["POST"]
    )
    app.add_url_rule("/relatorios", view_func=relatorios)


def create_app(configuracao=None):
    ambiente = obter_ambiente()
    classe_configuracao = obter_classe_configuracao(ambiente)

    aplicacao = Flask(__name__)
    aplicacao.config.from_object(classe_configuracao)
    aplicar_variaveis_ambiente(aplicacao.config)

    if configuracao:
        aplicacao.config.update(configuracao)

    configurar_uri_banco(aplicacao.config, configuracao)

    if ambiente == "production":
        validar_configuracao_producao(aplicacao.config)

    db.init_app(aplicacao)
    migrate.init_app(aplicacao, db)
    login_manager.init_app(aplicacao)
    csrf.init_app(aplicacao)

    login_manager.login_view = "login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "aviso"

    import models

    registrar_rotas(aplicacao)
    registrar_cli(aplicacao)

    return aplicacao


@login_manager.user_loader
def carregar_usuario(identificador):
    try:
        usuario_id = int(identificador)
    except (TypeError, ValueError):
        return None
    usuario = db.session.get(Usuario, usuario_id)
    return usuario if usuario and usuario.is_active else None


def registrar_cli(aplicacao):
    aplicacao.cli.add_command(comando_transferencia)

    @aplicacao.cli.command("create-user")
    @click.option("--nome", prompt=True)
    @click.option("--email", prompt=True)
    def criar_usuario_cli(nome, email):
        senha = click.prompt("Senha", hide_input=True)
        confirmacao = click.prompt("Confirme a senha", hide_input=True)
        usuario, erro = cadastrar_usuario(nome, email, senha, confirmacao)
        if erro:
            raise click.ClickException(erro)
        click.echo(f"Usuário criado com ID {usuario.id}.")

    @aplicacao.cli.command("assign-legacy-data")
    @click.option("--email", required=True)
    @click.option("--confirm", is_flag=True)
    def associar_dados_legados(email, confirm):
        usuario = db.session.scalar(
            select(Usuario).where(Usuario.email == normalizar_email(email))
        )
        if not usuario:
            raise click.ClickException("Usuário não encontrado.")
        transacoes = db.session.scalars(
            select(Transacao).where(Transacao.usuario_id.is_(None))
        ).all()
        metas = db.session.scalars(
            select(Meta).where(Meta.usuario_id.is_(None))
        ).all()
        click.echo(f"Registros sem proprietário: {len(transacoes)} transações e {len(metas)} metas.")
        if not confirm:
            raise click.ClickException("Use --confirm para autorizar a associação.")
        try:
            for registro in (*transacoes, *metas):
                registro.usuario_id = usuario.id
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        click.echo(f"Associação concluída ao usuário ID {usuario.id}.")


app = create_app()


if __name__ == "__main__":
    app.run()

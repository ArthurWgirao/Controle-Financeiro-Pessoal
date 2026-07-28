from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request

load_dotenv(override=False)

from categorias import categorias
from config import (
    aplicar_variaveis_ambiente,
    obter_ambiente,
    obter_classe_configuracao,
    validar_configuracao_producao
)
from database import configurar_caminho_banco, criar_tabela
from metas import (
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
    calcular_resumo,
    excluir_transacao
)
from validacoes import (
    validar_limite_meta,
    validar_meta,
    validar_transacao
)

def dashboard():

    receitas, despesas, saldo = calcular_resumo()

    return render_template(
        "dashboard.html",
        receitas=receitas,
        despesas=despesas,
        saldo=saldo
    )


# Receitas

def receitas():

    lista_receitas = buscar_transacoes_por_tipo("receita")

    return render_template(
        "receitas.html",
        receitas=lista_receitas
    )


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
            descricao
        )

        return redirect("/receitas")

    return render_template(
        "form_receita.html",
        titulo="Nova Receita",
        receita=None,
        categorias=categorias,
        erro=None
    )


def editar_receita(id):

    receita = buscar_transacao_por_id_e_tipo(id, "receita")

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
            descricao
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


def excluir_receita(id):

    if not excluir_transacao(id, "receita"):
        abort(404)

    return redirect("/receitas")


# Despesas

def despesas():

    lista_despesas = buscar_transacoes_por_tipo("despesa")

    return render_template(
        "despesas.html",
        despesas=lista_despesas
    )


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
            descricao
        )

        return redirect("/despesas")

    return render_template(
        "form_despesa.html",
        titulo="Nova Despesa",
        despesa=None,
        categorias=categorias,
        erro=None
    )


def editar_despesa(id):

    despesa = buscar_transacao_por_id_e_tipo(id, "despesa")

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
            descricao
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


def excluir_despesa(id):

    if not excluir_transacao(id, "despesa"):
        abort(404)

    return redirect("/despesas")


# Metas

def metas():

    mes_referencia = datetime.now().strftime("%m/%Y")
    lista_metas = listar_metas_mensais(mes_referencia)

    return render_template(
        "metas.html",
        metas=lista_metas,
        mes_referencia=mes_referencia,
        formatar_moeda=formatar_moeda
    )


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

        if not erro and categoria_possui_meta(categoria):
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

        cadastrar_meta(categoria, limite)

        return redirect("/metas")

    return render_template(
        "form_meta.html",
        titulo="Nova Meta Mensal",
        meta=None,
        categorias=categorias,
        erro=None,
        edicao=False
    )


def editar_meta(id):

    meta = buscar_meta_por_id(id)

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

        if not atualizar_limite_meta(id, limite):
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


def excluir_meta(id):

    if not excluir_meta_por_id(id):
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

def relatorios():

    mes_informado = request.args.get("mes")
    ano_informado = request.args.get("ano")

    mes, ano, erro = validar_periodo(
        mes_informado,
        ano_informado
    )

    if erro:
        return render_template(
            "relatorios.html",
            relatorio=None,
            meses=MESES,
            mes_selecionado=mes_informado,
            ano_selecionado=ano_informado,
            erro=erro,
            formatar_moeda=formatar_moeda
        ), 400

    relatorio = preparar_relatorio(mes, ano)

    return render_template(
        "relatorios.html",
        relatorio=relatorio,
        meses=MESES,
        mes_selecionado=str(mes),
        ano_selecionado=str(ano),
        erro=None,
        formatar_moeda=formatar_moeda
    )


def registrar_rotas(app):
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

    if ambiente == "production":
        validar_configuracao_producao(aplicacao.config)

    configurar_caminho_banco(aplicacao.config["DATABASE_PATH"])
    registrar_rotas(aplicacao)

    banco_inicializado = False

    @aplicacao.before_request
    def inicializar_banco():
        nonlocal banco_inicializado

        configurar_caminho_banco(
            aplicacao.config["DATABASE_PATH"]
        )

        if not banco_inicializado:
            criar_tabela()
            banco_inicializado = True

    return aplicacao


app = create_app()


if __name__ == "__main__":
    app.run()

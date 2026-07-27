from datetime import datetime

from flask import Flask, abort, redirect, render_template, request

from categorias import categorias
from database import criar_tabela
from metas import (
    atualizar_limite_meta,
    buscar_meta_por_id,
    cadastrar_meta,
    categoria_possui_meta,
    excluir_meta_por_id,
    listar_metas_mensais
)
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

app = Flask(__name__)

criar_tabela()


@app.route("/")
def dashboard():

    receitas, despesas, saldo = calcular_resumo()

    return render_template(
        "dashboard.html",
        receitas=receitas,
        despesas=despesas,
        saldo=saldo
    )


# Receitas

@app.route("/receitas")
def receitas():

    lista_receitas = buscar_transacoes_por_tipo("receita")

    return render_template(
        "receitas.html",
        receitas=lista_receitas
    )


@app.route("/receitas/nova", methods=["GET", "POST"])
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


@app.route("/receitas/editar/<int:id>", methods=["GET", "POST"])
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


@app.route("/receitas/excluir/<int:id>", methods=["POST"])
def excluir_receita(id):

    if not excluir_transacao(id, "receita"):
        abort(404)

    return redirect("/receitas")


# Despesas

@app.route("/despesas")
def despesas():

    lista_despesas = buscar_transacoes_por_tipo("despesa")

    return render_template(
        "despesas.html",
        despesas=lista_despesas
    )


@app.route("/despesas/nova", methods=["GET", "POST"])
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


@app.route("/despesas/editar/<int:id>", methods=["GET", "POST"])
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


@app.route("/despesas/excluir/<int:id>", methods=["POST"])
def excluir_despesa(id):

    if not excluir_transacao(id, "despesa"):
        abort(404)

    return redirect("/despesas")


# Metas

@app.route("/metas")
def metas():

    mes_referencia = datetime.now().strftime("%m/%Y")
    lista_metas = listar_metas_mensais(mes_referencia)

    return render_template(
        "metas.html",
        metas=lista_metas,
        mes_referencia=mes_referencia,
        formatar_moeda=formatar_moeda
    )


@app.route("/metas/nova", methods=["GET", "POST"])
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


@app.route("/metas/editar/<int:id>", methods=["GET", "POST"])
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


@app.route("/metas/excluir/<int:id>", methods=["POST"])
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

@app.route("/relatorios")
def relatorios():

    return render_template("relatorios.html")


if __name__ == "__main__":
    app.run(debug=True)

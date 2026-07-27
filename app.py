from datetime import datetime
import math

from flask import Flask, abort, render_template, request, redirect

from categorias import categorias
from database import (
    conectar,
    criar_tabela
)

app = Flask(__name__)

criar_tabela()


def obter_resumo():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT tipo, valor
        FROM transacoes
    """)

    transacoes = cursor.fetchall()

    conexao.close()

    receitas = 0
    despesas = 0

    for tipo, valor in transacoes:

        if tipo.lower() == "receita":
            receitas += valor

        elif tipo.lower() == "despesa":
            despesas += valor

    saldo = receitas - despesas

    return receitas, despesas, saldo

def testar_banco():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT *
        FROM transacoes
    """)

    dados = cursor.fetchall()

    print("DADOS DO BANCO:")
    print(dados)

    conexao.close()

# Dashboard
@app.route("/")
def dashboard():

    receitas, despesas, saldo = obter_resumo()

    return render_template(
        "dashboard.html",
        receitas=receitas,
        despesas=despesas,
        saldo=saldo
    )

# Receitas

def buscar_receitas():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id, descricao, categoria, valor, data
        FROM transacoes
        WHERE tipo = 'receita'
        ORDER BY id DESC
    """)


    receitas = cursor.fetchall()

    conexao.close()

    return receitas

@app.route("/receitas")
def receitas():

    lista_receitas = buscar_receitas()

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

        erro = validar_receita(
            descricao,
            categoria,
            valor_informado
        )

        if erro:
            return render_template(
                "form_receita.html",
                titulo="Nova Receita",
                receita=dados_formulario,
                categorias=categorias,
                erro=erro
            ), 400

        valor = float(valor_informado)
        data = datetime.now().strftime("%d/%m/%Y")

        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO transacoes
            (tipo, valor, categoria, descricao, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "receita",
            valor,
            categoria,
            descricao,
            data
        ))

        conexao.commit()
        conexao.close()

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

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, tipo, valor, categoria, descricao, data
        FROM transacoes
        WHERE id = ? AND tipo = 'receita'
        """,
        (id,)
    )

    receita = cursor.fetchone()

    if receita is None:
        conexao.close()
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

        erro = validar_receita(
            descricao,
            categoria,
            valor_informado
        )

        if erro:
            conexao.close()
            return render_template(
                "form_receita.html",
                titulo="Editar Receita",
                receita=dados_formulario,
                categorias=categorias,
                erro=erro
            ), 400

        valor = float(valor_informado)

        cursor.execute("""
            UPDATE transacoes
            SET tipo = 'receita',
                descricao = ?,
                categoria = ?,
                valor = ?
            WHERE id = ? AND tipo = 'receita'
        """, (
            descricao,
            categoria,
            valor,
            id
        ))

        conexao.commit()
        conexao.close()

        return redirect("/receitas")


    conexao.close()


    return render_template(
        "form_receita.html",
        titulo="Editar Receita",
        receita=receita,
        categorias=categorias,
        erro=None
    )


@app.route("/receitas/excluir/<int:id>", methods=["POST"])
def excluir_receita(id):

    conexao = conectar()
    cursor = conexao.cursor()


    cursor.execute(
        """
        DELETE FROM transacoes
        WHERE id = ? AND tipo = 'receita'
        """,
        (id,)
    )

    excluiu = cursor.rowcount

    conexao.commit()
    conexao.close()

    if not excluiu:
        abort(404)

    return redirect("/receitas")


def validar_receita(descricao, categoria, valor_informado):

    if not descricao:
        return "Informe uma descrição para a receita."

    if categoria not in categorias:
        return "Selecione uma categoria válida."

    if not valor_informado:
        return "Informe o valor da receita."

    try:
        valor = float(valor_informado)
    except ValueError:
        return "Informe um valor numérico válido."

    if not math.isfinite(valor) or valor <= 0:
        return "O valor deve ser maior que zero."

    return None



# Despesas

def buscar_despesas():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id, descricao, categoria, valor, data
        FROM transacoes
        WHERE tipo = 'despesa'
        ORDER BY id DESC
    """)

    despesas = cursor.fetchall()

    conexao.close()

    return despesas


@app.route("/despesas")
def despesas():

    lista_despesas = buscar_despesas()

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

        erro = validar_despesa(
            descricao,
            categoria,
            valor_informado
        )

        if erro:
            return render_template(
                "form_despesa.html",
                titulo="Nova Despesa",
                despesa=dados_formulario,
                categorias=categorias,
                erro=erro
            ), 400

        valor = float(valor_informado)
        data = datetime.now().strftime("%d/%m/%Y")

        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO transacoes
            (tipo, valor, categoria, descricao, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "despesa",
            valor,
            categoria,
            descricao,
            data
        ))

        conexao.commit()
        conexao.close()

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

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, tipo, valor, categoria, descricao, data
        FROM transacoes
        WHERE id = ? AND tipo = 'despesa'
        """,
        (id,)
    )

    despesa = cursor.fetchone()

    if despesa is None:
        conexao.close()
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

        erro = validar_despesa(
            descricao,
            categoria,
            valor_informado
        )

        if erro:
            conexao.close()
            return render_template(
                "form_despesa.html",
                titulo="Editar Despesa",
                despesa=dados_formulario,
                categorias=categorias,
                erro=erro
            ), 400

        valor = float(valor_informado)

        cursor.execute("""
            UPDATE transacoes
            SET tipo = 'despesa',
                descricao = ?,
                categoria = ?,
                valor = ?
            WHERE id = ? AND tipo = 'despesa'
        """, (
            descricao,
            categoria,
            valor,
            id
        ))

        conexao.commit()
        conexao.close()

        return redirect("/despesas")

    conexao.close()

    return render_template(
        "form_despesa.html",
        titulo="Editar Despesa",
        despesa=despesa,
        categorias=categorias,
        erro=None
    )


@app.route("/despesas/excluir/<int:id>", methods=["POST"])
def excluir_despesa(id):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        DELETE FROM transacoes
        WHERE id = ? AND tipo = 'despesa'
        """,
        (id,)
    )

    excluiu = cursor.rowcount

    conexao.commit()
    conexao.close()

    if not excluiu:
        abort(404)

    return redirect("/despesas")


def validar_despesa(descricao, categoria, valor_informado):

    if not descricao:
        return "Informe uma descrição para a despesa."

    if categoria not in categorias:
        return "Selecione uma categoria válida."

    if not valor_informado:
        return "Informe o valor da despesa."

    try:
        valor = float(valor_informado)
    except ValueError:
        return "Informe um valor numérico válido."

    if not math.isfinite(valor) or valor <= 0:
        return "O valor deve ser maior que zero."

    return None

# Metas
@app.route("/metas")
def metas():

    return render_template("metas.html")


# Relatórios
@app.route("/relatorios")
def relatorios():

    return render_template("relatorios.html")

if __name__ == "__main__":
    app.run(debug=True)

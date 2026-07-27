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

def buscar_metas_mensais(mes_referencia):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            m.id,
            m.categoria,
            m.limite,
            COALESCE(SUM(t.valor), 0) AS gasto
        FROM metas AS m
        LEFT JOIN transacoes AS t
            ON t.categoria = m.categoria
            AND t.tipo = 'despesa'
            AND substr(t.data, 4, 7) = ?
        GROUP BY m.id, m.categoria, m.limite
        ORDER BY m.categoria
        """,
        (mes_referencia,)
    )

    registros = cursor.fetchall()
    conexao.close()

    metas_calculadas = []

    for registro in registros:

        limite = registro["limite"]
        gasto = registro["gasto"]
        restante = limite - gasto
        percentual = (gasto / limite) * 100 if limite > 0 else 0

        if percentual >= 100:
            situacao = "Meta ultrapassada"
            classe_situacao = "ultrapassada"
        elif percentual >= 80:
            situacao = "Atenção"
            classe_situacao = "atencao"
        else:
            situacao = "Dentro da meta"
            classe_situacao = "dentro"

        metas_calculadas.append({
            "id": registro["id"],
            "categoria": registro["categoria"],
            "limite": limite,
            "gasto": gasto,
            "restante": restante,
            "percentual": percentual,
            "largura_barra": min(percentual, 100),
            "situacao": situacao,
            "classe_situacao": classe_situacao
        })

    return metas_calculadas


@app.route("/metas")
def metas():

    mes_referencia = datetime.now().strftime("%m/%Y")
    lista_metas = buscar_metas_mensais(mes_referencia)

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

        erro = validar_meta(categoria, limite_informado)

        if not erro:
            conexao = conectar()
            cursor = conexao.cursor()

            cursor.execute(
                "SELECT id FROM metas WHERE categoria = ?",
                (categoria,)
            )

            if cursor.fetchone():
                erro = "Já existe uma meta para esta categoria."

            if erro:
                conexao.close()
            else:
                cursor.execute(
                    """
                    INSERT INTO metas (categoria, limite)
                    VALUES (?, ?)
                    """,
                    (categoria, float(limite_informado))
                )

                conexao.commit()
                conexao.close()

                return redirect("/metas")

        return render_template(
            "form_meta.html",
            titulo="Nova Meta Mensal",
            meta=dados_formulario,
            categorias=categorias,
            erro=erro,
            edicao=False
        ), 400

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

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT id, categoria, limite FROM metas WHERE id = ?",
        (id,)
    )

    meta = cursor.fetchone()

    if meta is None:
        conexao.close()
        abort(404)

    if request.method == "POST":

        limite_informado = request.form.get("limite", "").strip()
        erro = validar_limite_meta(limite_informado)

        if erro:
            dados_formulario = {
                "id": meta["id"],
                "categoria": meta["categoria"],
                "limite": limite_informado
            }

            conexao.close()

            return render_template(
                "form_meta.html",
                titulo="Editar Meta Mensal",
                meta=dados_formulario,
                categorias=categorias,
                erro=erro,
                edicao=True
            ), 400

        cursor.execute(
            """
            UPDATE metas
            SET limite = ?
            WHERE id = ?
            """,
            (float(limite_informado), id)
        )

        conexao.commit()
        conexao.close()

        return redirect("/metas")

    conexao.close()

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

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        "DELETE FROM metas WHERE id = ?",
        (id,)
    )

    excluiu = cursor.rowcount

    conexao.commit()
    conexao.close()

    if not excluiu:
        abort(404)

    return redirect("/metas")


def validar_meta(categoria, limite_informado):

    if categoria not in categorias:
        return "Selecione uma categoria válida."

    return validar_limite_meta(limite_informado)


def validar_limite_meta(limite_informado):

    if not limite_informado:
        return "Informe o limite mensal."

    try:
        limite = float(limite_informado)
    except ValueError:
        return "Informe um limite numérico válido."

    if not math.isfinite(limite) or limite <= 0:
        return "O limite deve ser maior que zero."

    return None


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

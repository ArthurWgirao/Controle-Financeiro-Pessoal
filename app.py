from flask import Flask, render_template

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

        if tipo == "receita":
            receitas += valor

        else:
            despesas += valor

    saldo = receitas - despesas

    return receitas, despesas, saldo

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
@app.route("/receitas")
def receitas():

    return render_template("receitas.html")

# Despesas 
@app.route("/despesas")
def despesas():

    return render_template("despesas.html")

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
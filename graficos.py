import matplotlib.pyplot as plt

from database import conectar



def grafico_despesas_categoria():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT categoria, SUM(valor)
        FROM transacoes
        WHERE tipo = 'despesa'
        GROUP BY categoria
        """
    )

    dados = cursor.fetchall()

    conexao.close()

    categorias = []
    valores = []

    for categoria, total in dados:
        categorias.append(categoria)
        valores.append(total)

    plt.bar(categorias, valores)

    plt.title("Despesas por Categoria")
    plt.xlabel("Categorias")
    plt.ylabel("Valor Gasto (R$)")

    plt.show()
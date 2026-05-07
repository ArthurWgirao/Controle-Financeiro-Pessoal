import matplotlib.pyplot as plt


def grafico_despesas_categoria(transacoes):

    totais = {}

    # Percorre transações
    for t in transacoes:

        # Apenas despesas
        if t["tipo"] == "despesa":

            categoria = t["categoria"]
            valor = t["valor"]

            # Soma valores por categoria
            if categoria in totais:
                totais[categoria] += valor
            else:
                totais[categoria] = valor

    # Dados do gráfico
    categorias = list(totais.keys())
    valores = list(totais.values())

    # Criação do gráfico
    plt.bar(categorias, valores)

    plt.title("Despesas por Categoria")
    plt.xlabel("Categorias")
    plt.ylabel("Valor Gasto (R$)")

    plt.show()
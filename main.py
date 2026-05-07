from data import load_data

from transacoes import (
    add_receita,
    add_despesa,
    listar_transacoes,
    ver_saldo,
    remover_transacao,
    editar_transacao,
    filtrar_por_categoria,
    total_por_categoria
)

from graficos import grafico_despesas_categoria


def menu():
    print("""
===== CONTROLE FINANCEIRO =====

1 - Adicionar Receita
2 - Adicionar Despesa
3 - Listar Transações
4 - Ver Saldo
5 - Remover Transação
6 - Editar Transação
7 - Filtrar por Categoria
8 - Total por Categoria
9 - Gráfico de Despesas por Categoria
10 - Sair
""")


def main():

    transacoes = load_data()

    opcoes = {
        "1": add_receita,
        "2": add_despesa,
        "3": listar_transacoes,
        "4": ver_saldo,
        "5": remover_transacao,
        "6": editar_transacao,
        "7": filtrar_por_categoria,
        "8": total_por_categoria,
        "9": grafico_despesas_categoria
    }

    while True:

        menu()

        opcao = input("Escolha uma opção: ")

        if opcao == "10":
            print("Saindo...")
            break

        elif opcao in opcoes:
            opcoes[opcao](transacoes)

        else:
            print("Opção inválida!")


main()
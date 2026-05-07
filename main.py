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
9 - Sair
""")


def main():
    transacoes = load_data()

    while True:
        menu()

        opcao = input("Escolha uma opção: ")

        if opcao == "1":
            add_receita(transacoes)

        elif opcao == "2":
            add_despesa(transacoes)

        elif opcao == "3":
            listar_transacoes(transacoes)

        elif opcao == "4":
            ver_saldo(transacoes)

        elif opcao == "5":
            remover_transacao(transacoes)

        elif opcao == "6":
            editar_transacao(transacoes)

        elif opcao == "7":
            filtrar_por_categoria(transacoes)

        elif opcao == "8":
            total_por_categoria(transacoes)

        elif opcao == "9":
            print("Saindo...")
            break

        else:
            print("Opção inválida!")


main()
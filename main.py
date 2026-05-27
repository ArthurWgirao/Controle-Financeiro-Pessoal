from database import criar_tabela

from transacoes import (
    add_receita,
    add_despesa,
    listar_transacoes,
    ver_saldo,
    remover_transacao,
    editar_transacao,
    filtrar_por_categoria,
    total_por_categoria,
    relatorio_mensal
)

from metas import(
    definit_meta,
    verificar_metas
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
10 - Definir Meta
11 - Verificar Metas
12 - Relatório Mensal
13 - Sair
""")



def main():

    criar_tabela()

    opcoes = {
        "1": add_receita,
        "2": add_despesa,
        "3": listar_transacoes,
        "4": ver_saldo,
        "5": remover_transacao,
        "6": editar_transacao,
        "7": filtrar_por_categoria,
        "8": total_por_categoria,
        "9": grafico_despesas_categoria,
        "10": definit_meta,
        "11": verificar_metas,
        "12": relatorio_mensal
    }

    while True:

        menu()

        opcao = input("Escolha uma opção: ")

        if opcao == "13":
            print("Saindo...")
            break

        elif opcao in opcoes:
            opcoes[opcao]()

        else:
            print("Opção inválida!")


main()
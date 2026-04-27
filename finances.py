import json

# Carregar dados
def load_data():
    try:
        with open("transacoes.json", "r") as arquivo:
            transacoes = json.load(arquivo)
    except:
        return = []

# Salvar dados
def save_data(transacoes):
    with open("transacoes.json", "w") as arquivo:
        json.dump(transacoes, arquivo)

# Funções do Sistema

def add_receita(transacoes):
    valor = float(input("Digite o valor da receita: "))
    categoria = input("Digite a categoria: ")
    descricao = input("Digite uma descrição: ")

    transacoes.append({
        "tipo": "receita",
        "valor": valor,
        "categoria": categoria,
        "descrição": descricao
    })
    save_data(transacoes)
    print("Receita adicionada!")

def add_despesa(transacoes):
    valor = float(input("Digite o valor da despesa: "))
    categoria = input("Digite a categoria: ")
    descricao = input("Digite uma descrição: ")

    transacoes.append({
        "tipo": "despesa",
        "valor": valor,
        "categoria": categoria,
        "descrição": descricao
    })
    save_data(transacoes)
    print("Despesa adicionada!")

def listar_transacoes(transacoes):
    if len(transacoes) == 0:
        print("Nenhuma transação cadastrada.")
    else:
        for i, t in enumerate(transacoes):
            print(f"{i} - {t['tipo']} | R$ {t['valor']} | {t['categoria']} | {t['descricao']}")

def ver_saldo(transacoes):
    receitas = 0
    despesas = 0

    for t in transacoes:
        if t["tipo"] == "receita":
            receitas += t["valor"]
        else:
            despesas += t["valor"]
    saldo = receitas - despesas

    print(f"Total de receitas: R${receitas}")
    print(f"Total de despesas: R${despesas}")
    print(f"Saldo atual: R${saldo}")

def remover_transacao(transacoes):
    if len(transacoes) == 0:
        print("Nenhuma transação para remover.")
        return
    listar_transacoes(transacoes)

    indice = int(input("Digite o índice da transação que deseja remover: "))

    if 0 <= indice < len(transacoes):
        transacoes.pop(indice)
        save_data(transacoes)
        print("Transação removida!")
    else:
        print("Índice inválido!")

# Menu

def menu():
    print("""
CONTROLE FINANCEIRO
1 - Adicionar Receita
2 - Adicionar Despesa
3 - Listar Transações
4 - Ver Saldo Total
5 - Remover Transação
6 - Sair
""")
    
# Função Principal

def main():
    transacoes = load_data()

    while True:
        menu()
        opcao = input("Escolha uma ação: ")

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
            print("Saindo...")
            break
        
        else:
            print("Opção inválida!")

main()



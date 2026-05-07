import json
from datetime import datetime

# Carregar dados
def load_data():
    try:
        with open("transacoes.json", "r") as arquivo:
            return json.load(arquivo)
    except:
        return []

# Salvar dados
def save_data(transacoes):
    with open("transacoes.json", "w") as arquivo:
        json.dump(transacoes, arquivo, indent=4)

# Funções do Sistema

def add_receita(transacoes):
    valor = float(input("Digite o valor da receita: "))
    categoria = input("Digite a categoria: ").lower().strip()
    descricao = input("Digite uma descrição: ")
    date = datetime.now().strftime("%d/%m/%Y")

    transacoes.append({
        "tipo": "receita",
        "valor": valor,
        "categoria": categoria,
        "descrição": descricao,
        "data": date
    })

    save_data(transacoes)
    print("Receita adicionada!")

def add_despesa(transacoes):
    valor = float(input("Digite o valor da despesa: "))
    categoria = input("Digite a categoria: ").lower().strip()
    descricao = input("Digite uma descrição: ")
    date = datetime.now().strftime("%d/%m/%Y")

    transacoes.append({

        "tipo": "despesa",
        "valor": valor,
        "categoria": categoria,
        "descrição": descricao,
        "data": date
    })

    save_data(transacoes)
    print("Despesa adicionada!")

def listar_transacoes(transacoes):
    if len(transacoes) == 0:
        print("Nenhuma transação cadastrada.")
    else:
         print("\n===== TRANSAÇÕES =====")
         for i, t in enumerate(transacoes):
                print(
                    f"{i} - [{t['tipo'].upper()}] "
                    f"R$ {t['valor']:.2f} | "
                    f"{t['categoria']} | "
                    f"{t['descrição']} | "
                    f"{t.get('data', '')}"
                )
         print()

def ver_saldo(transacoes):
    receitas = 0
    despesas = 0

    for t in transacoes:
        if t["tipo"] == "receita":
            receitas += t["valor"]
        else:
            despesas += t["valor"]
    saldo = receitas - despesas

    print("\n==== RESUMO ====")
    print(f"Total de receitas: R${receitas:.2f}")
    print(f"Total de despesas: R${despesas:.2f}")
    print(f"Saldo atual: R${saldo:.2f}")

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


def  editar_transacao(transacoes):
    if len(transacoes) == 0:
        print("Nenhuma transação para editar.")
        return
    
    listar_transacoes(transacoes)

    indice = int(input("Digite o índice da transação que deseja editar: "))

    if 0 <= indice < len(transacoes):
        t = transacoes[indice]

        print("Pressione enter para não alterar.")

        novo_valor = input(f"Novo valor (atual: {t['valor']}): ").strip()
        nova_categoria = input(f"Nova categoria (atual: {t['categoria']}): ").strip()
        nova_descricao = input(f"Nova descrição (atual: {t['descrição']}): ").strip()

        if novo_valor != " ":
            t['valor'] = float(novo_valor)
        
        if nova_categoria != " ":
            t['categoria'] = nova_categoria.lower()
        
        if nova_descricao != " ":
            t['descrição'] = nova_descricao

        save_data(transacoes)
        print("Transação atualizada!")

    else:
        print("Índice inválido")

def filtrar_por_categoria(transacoes):
    categoria = input("Digite a categoria para filtrar: ").lower().strip()

    filtradas = [t for t in transacoes if t["categoria"] == categoria]

    if len(filtradas) == 0:
        print("Nenhuma transação encontrada para essa categoria.")
        return

    print(f"\n===== TRANSAÇÕES ({categoria}) =====")
    for i, t in enumerate(filtradas):
        print(
            f"[{t['tipo'].upper()}] "
            f"R$ {t['valor']:.2f} | "
            f"{t['descrição']} | "
            f"{t.get('data', '')}"
        )
    print()


def total_por_categoria(transacoes):
    totais = {}

    for t in transacoes:
        categoria = t["categoria"]
        valor = t["valor"]

        if categoria not in totais:
            totais[categoria] = 0

        if t["tipo"] == "receita":
            totais[categoria] += valor
        else:
            totais[categoria] -= valor

    print("\n===== TOTAL POR CATEGORIA =====")
    for categoria, total in totais.items():
        print(f"{categoria}: R$ {total:.2f}")
    print()

        

# Menu

def menu():
    print("""
CONTROLE FINANCEIRO
1 - Adicionar Receita
2 - Adicionar Despesa
3 - Listar Transações
4 - Ver Saldo Total
5 - Remover Transação
6 - Editar Transação
7 - Filtrar por Categoria
8 - Total por Categoria
9 -  Sair
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



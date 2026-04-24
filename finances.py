import json
# Carregar dados
try:
    with open("transacoes.json", "r") as arquivo:
        transacoes = json.load(arquivo)
except:
    transacoes = []

# Salvar dados
def save_data():
    with open("transacoes.json", "w") as arquivo:
        json.dump(transacoes, arquivo)

while True: 
    print("""
------- CONTROLE DE GASTOS -------
          
1 - Adicionar Receita 
2 - Adicionar Gasto
3 - Listar Transações
4 - Ver Saldo Total
5 - Remover Transação
6 - Sair
          
----------------------------------
 """)
    opcao = input("Escolha uma ação: ")

    if opcao == "1":
        valor = float(input("Digite o valor da receita: "))
        categoria = input("Digite a categoria: ")

        transacoes.append({
            "tipo": "receita",
            "valor": valor,
            "categoria": categoria
        })
        save_data()
        print("\nReceita adicionada!")

    elif opcao == "2":
        valor = float(input("Digite o valor do gasto: "))
        categoria = input("Digite a categoria: ")

        transacoes.append({
            "tipo": "gasto",
            "valor": valor,
            "categoria": categoria
        })
        save_data()
        print("\nGasto registrado!")

    elif opcao == "3":
        if len(transacoes) == 0:
            print("\nNenhuma transação cadastrada") 
        else:
            for i, t in enumerate(transacoes):
                print(f"{i} - {t['tipo']} | R$ {t['valor']} | {t['categoria']}")

    elif opcao == "4":
        receitas = 0
        gastos = 0

        for t in transacoes:
            if t["tipo"] == "receita":
                receitas += t["valor"]
            else:
                gastos += t["valor"]
        saldo = receitas - gastos

        print(f"Total de receitas: R$ {receitas}")
        print(f"Total de gastos: R$ {gastos}")
        print(f"Saldo atual: R$ {saldo}")

    elif opcao == "5":
        if len(transacoes) == 0:
            print("\nNenhuma transação para remover.")
        else: 
            for i, t in enumerate(transacoes):
                print(f"{i} - {t['tipo']} | R$ {t['valor']} | {t['categoria']}")

            indice = int(input("Digite o índice da transação que deseja remover: "))

            if 0 <= indice <= len(transacoes):
                transacoes.pop(indice)
                save_data()
                print("\nTransação removida!")
            else:
                print("\nÍndice inválido")
    
    elif opcao == "6":
        print("\nSaindo...")
        break
    
    else:
        print("\nOpção inválida")


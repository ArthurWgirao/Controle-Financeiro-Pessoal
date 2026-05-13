from datetime import datetime
from data import save_data
from database import conectar
from categorias import categorias


def escolher_categoria():
    print("\n===== CATEGORIAS =====")

    for i, categoria in enumerate(categorias):
        print(f"{i + 1} - {categoria}")

    opcao = int(input("Escolha uma categoria: "))

    if 1 <= opcao <= len(categorias):
        return categorias[opcao - 1]

    print("Categoria inválida!")
    return escolher_categoria()


def add_receita(transacoes):

    valor = float(input("Digite o valor da receita: "))
    categoria = escolher_categoria()
    descricao = input("Digite uma descrição: ")
    data = datetime.now().strftime("%d/%m/%Y")

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        INSERT INTO transacoes
        (tipo, valor, categoria, descricao, data)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("receita", valor, categoria, descricao, data)
    )

    conexao.commit()
    conexao.close()

    
    print("Receita adicionada!")


def add_despesa(transacoes):
    valor = float(input("Digite o valor da despesa: "))
    categoria = escolher_categoria()
    descricao = input("Digite uma descrição: ")
    data = datetime.now().strftime("%d/%m/%Y")

    transacoes.append({
        "tipo": "despesa",
        "valor": valor,
        "categoria": categoria,
        "descrição": descricao,
        "data": data
    })

    save_data(transacoes)
    print("Despesa adicionada!")


def listar_transacoes(transacoes):
    if len(transacoes) == 0:
        print("Nenhuma transação cadastrada.")
        return

    print("\n===== TRANSAÇÕES =====")

    for i, t in enumerate(transacoes):
        print(
            f"{i + 1} - [{t['tipo'].upper()}] "
            f"R$ {t['valor']:.2f} | "
            f"{t['categoria']} | "
            f"{t['descrição']} | "
            f"{t['data']}"
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

    print("\n===== RESUMO =====")
    print(f"Receitas: R$ {receitas:.2f}")
    print(f"Despesas: R$ {despesas:.2f}")
    print(f"Saldo:    R$ {saldo:.2f}")


def remover_transacao(transacoes):
    if len(transacoes) == 0:
        print("Nenhuma transação para remover.")
        return

    listar_transacoes(transacoes)

    indice = int(input("Digite o índice da transação: "))

    if 0 <= indice < len(transacoes):
        transacoes.pop(indice)
        save_data(transacoes)
        print("Transação removida!")
    else:
        print("Índice inválido!")


def editar_transacao(transacoes):
    if len(transacoes) == 0:
        print("Nenhuma transação para editar.")
        return

    listar_transacoes(transacoes)

    indice = int(input("Digite o índice da transação: "))

    if 0 <= indice < len(transacoes):
        t = transacoes[indice]

        print("Pressione ENTER para não alterar.")

        novo_valor = input(f"Novo valor (atual: {t['valor']}): ").strip()
        nova_descricao = input(f"Nova descrição (atual: {t['descrição']}): ").strip()

        if novo_valor != "":
            t["valor"] = float(novo_valor)

        if nova_descricao != "":
            t["descrição"] = nova_descricao

        alterar_categoria = input("Deseja alterar categoria? (s/n): ").lower()

        if alterar_categoria == "s":
            t["categoria"] = escolher_categoria()

        save_data(transacoes)
        print("Transação atualizada!")

    else:
        print("Índice inválido!")


def filtrar_por_categoria(transacoes):
    categoria = escolher_categoria()

    filtradas = [t for t in transacoes if t["categoria"] == categoria]

    if len(filtradas) == 0:
        print("Nenhuma transação encontrada.")
        return

    print(f"\n===== {categoria.upper()} =====")

    for t in filtradas:
        print(
            f"[{t['tipo'].upper()}] "
            f"R$ {t['valor']:.2f} | "
            f"{t['descrição']} | "
            f"{t['data']}"
        )


def total_por_categoria(transacoes):
    totais = {}

    for t in transacoes:
        categoria = t["categoria"]

        if categoria not in totais:
            totais[categoria] = 0

        if t["tipo"] == "receita":
            totais[categoria] += t["valor"]
        else:
            totais[categoria] -= t["valor"]

    print("\n===== TOTAL POR CATEGORIA =====")

    for categoria, total in totais.items():
        print(f"{categoria}: R$ {total:.2f}")
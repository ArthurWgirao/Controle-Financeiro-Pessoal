from datetime import datetime
from database import conectar
from categorias import categorias

# ==================
# ESCOLHER CATEGORIA
# ==================

def escolher_categoria():
    print("\n===== CATEGORIAS =====")

    for i, categoria in enumerate(categorias):
        print(f"{i + 1} - {categoria}")

    opcao = int(input("Escolha uma categoria: "))

    if 1 <= opcao <= len(categorias):
        return categorias[opcao - 1]

    print("Categoria inválida!")
    return escolher_categoria()

# ===================
# RECEITAS E DESPESAS
# ===================

def add_receita():

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


def add_despesa():
    valor = float(input("Digite o valor da despesa: "))
    categoria = escolher_categoria()
    descricao = input("Digite uma descrição: ")
    data = datetime.now().strftime("%d/%m/%Y")

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        INSERT INTO transacoes
        (tipo, valor, categoria, descricao, data)
        VALUES(?, ?, ?, ?, ?)    
        """,
        ("despesa", valor, categoria, descricao, data)
    )

    conexao.commit()
    conexao.close()

    print("Despesa adicionada!")

# =================
# LISTAR TRANSAÇÕES
# =================

def listar_transacoes():
    
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM transacoes")

    transacoes = cursor.fetchall()

    conexao.close()

    if len(transacoes) == 0:
        print("Nenhuma transação cadastrada.")
        return

    print("\n===== TRANSAÇÕES =====")

    for indice, t in enumerate(transacoes):
        print(
            f"{indice} - "
            f"[{t[1].upper()}] | "
            f"R$ {t[2]:.2f} | "
            f"{t[3]} | "
            f"{t[4]} | "
            f"{t[5]}"
        )

# =================
# VER SALDO
# =================


def ver_saldo():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT tipo, valor FROM transacoes")

    transacoes = cursor.fetchall()

    conexao.close()

    receitas = 0
    despesas = 0

    for t in transacoes:
        if t[0] == "receita":
            receitas += t[1]
        else:
            despesas += t[1]

    saldo = receitas - despesas

    print("\n===== RESUMO =====")
    print(f"Receitas: R$ {receitas:.2f}")
    print(f"Despesas: R$ {despesas:.2f}")
    print(f"Saldo:    R$ {saldo:.2f}")


# ===================
# REMVOVER TRANSAÇÕES
# ===================


def remover_transacao():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM transacoes")

    transacoes = cursor.fetchall()

    if len(transacoes) == 0:
        print("Nenhuma transação cadastrada.")
        conexao.close()
        return

    print("\n===== TRANSAÇÕES =====")

    for indice, t in enumerate(transacoes):

        print(
            f"{indice} - "
            f"[{t[1].upper()}] | "
            f"R$ {t[2]:.2f} | "
            f"{t[3]} | "
            f"{t[4]} | "
            f"{t[5]}"
        )

    indice_visual = int(
        input("\nDigite o índice da transação que deseja remover: ")
    )

    # Verifica se índice existe
    if 0 <= indice_visual < len(transacoes):

        # Pega transação correspondente
        transacao = transacoes[indice_visual]

        # ID real do banco
        id_real = transacao[0]

        # Remove do banco
        cursor.execute(
            "DELETE FROM transacoes WHERE id = ?",
            (id_real,)
        )

        conexao.commit()

        print("Transação removida!")

    else:
        print("Índice inválido!")

    conexao.close()



# =================
# EDITAR TRANSAÇÕES
# =================


def editar_transacao():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM transacoes")

    transacoes = cursor.fetchall()

    if len(transacoes) == 0:
        print("Nenhuma transação cadastrada.")
        conexao.close()
        return

    print("\n===== TRANSAÇÕES =====")

    for indice, t in enumerate(transacoes):

        print(
            f"{indice} - "
            f"[{t[1].upper()}] | "
            f"R$ {t[2]:.2f} | "
            f"{t[3]} | "
            f"{t[4]} | "
            f"{t[5]}"
        )

    indice_visual = int(
        input("\nDigite o índice da transação que deseja editar: ")
    )

    if 0 <= indice_visual < len(transacoes):

        transacao = transacoes[indice_visual]

        id_real = transacao[0]

        print("\nPressione ENTER para não alterar.\n")

        novo_valor = input(
            f"Novo valor (atual: {transacao[2]}): "
        ).strip()

        nova_descricao = input(
            f"Nova descrição (atual: {transacao[4]}): "
        ).strip()

        # Valores atuais
        valor = transacao[2]
        descricao = transacao[4]
        categoria = transacao[3]

        # Atualiza valor
        if novo_valor != "":
            valor = float(novo_valor)

        # Atualiza descrição
        if nova_descricao != "":
            descricao = nova_descricao

        # Atualiza categoria
        alterar_categoria = input(
            "Deseja alterar a categoria? (s/n): "
        ).lower()

        if alterar_categoria == "s":
            categoria = escolher_categoria()

        cursor.execute(
            """
            UPDATE transacoes
            SET valor = ?,
                categoria = ?,
                descricao = ?
            WHERE id = ?
            """,
            (valor, categoria, descricao, id_real)
        )

        conexao.commit()

        print("Transação atualizada!")

    else:
        print("Índice inválido!")

    conexao.close()


# ==================
# FILTRAR TRANSAÇÕES
# ==================


def filtrar_por_categoria():

    categoria = escolher_categoria()

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT * FROM transacoes WHERE categoria = ?",
        (categoria,)
    )

    transacoes = cursor.fetchall()

    conexao.close()

    if len(transacoes) == 0:
        print("Nenhuma transação encontrada.")
        return
    print(f"\n===== {categoria.upper()} =====")

    for t in transacoes:
        print(
            f"[{t[1].upper()}] "
            f"R$ {t[2]: 2f} | "
            f"{t[4]} | "
            f"{t[5]} "
        )


# ====================
# TOTAL POR CATEGORIA
# ====================


def total_por_categoria():

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

    totais = cursor.fetchall()

    conexao.close()

    print("\n===== TOTAL POR CATEGORIA =====")

    for categoria, total in totais.items():
        print(f"{categoria}: R$ {total:.2f}")
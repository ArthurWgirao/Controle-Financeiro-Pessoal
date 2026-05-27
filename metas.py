from database import conectar
from transacoes import escolher_categoria

from utils import ler_float

def definit_meta():

    categoria = escolher_categoria()
    limite = ler_float(
        "Digite o limite de gastos: "
    )

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        INSERT INTO metas
        (categoria, limite)
        VALUES (?, ?)
        """,
        (categoria,limite)
    )

    conexao.commit()
    conexao.close()

    print("Meta cadastrada!")


def verificar_metas():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
    SELECT categoria, limite
    FROM metas
    """)

    metas = cursor.fetchall()

    if len(metas) == 0:
        print("Nenhuma meta cadastrada.")
        conexao.close()
        return
    
    for meta in metas:
        categoria = meta[0]
        limite = meta[1]

        cursor.execute(
            """ 
            SELECT SUM(valor)
            FROM transacoes
            WHERE categoria = ?
            AND tipo = 'despesa'
            """,
            (categoria,)
        )

        total = cursor.fetchall()[0]

        if total is None:
            total = 0
        
        print(f"\nCategoria: {categoria}")
        print(f"Limite: R$ {limite:.2f}")
        print(f"Gasto atual: R$ {total:.2f}")

        if total > limite:
            print("⚠️ LIMITE ULTRAPASSADO!")
        else:
            print("✅ Dentro do limite")
    
    conexao.close()
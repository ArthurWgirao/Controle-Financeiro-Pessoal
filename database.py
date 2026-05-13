import sqlite3

def conectar():
    conexao = sqlite3.connect("finance.db")
    return conexao


def criar_tabela():

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        valor REAL,
        categoria TEXT,
        descricao TEXT,
        data TEXT

    )
    """)

    conexao.commit()
    conexao.close()
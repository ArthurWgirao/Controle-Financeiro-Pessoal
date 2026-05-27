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
        descrição TEXT,
        data TEXT

    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT,
        limite REAL
    
    )
    """)

    conexao.commit()
    conexao.close()
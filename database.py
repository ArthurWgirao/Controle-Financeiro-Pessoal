import sqlite3

CAMINHO_BANCO = "finance.db"


def configurar_caminho_banco(caminho):
    global CAMINHO_BANCO
    CAMINHO_BANCO = caminho


def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT,
        limite REAL
    
    )
    """)

    conexao.commit()
    conexao.close()

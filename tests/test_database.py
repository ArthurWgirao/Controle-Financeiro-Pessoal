import sqlite3

import database


def test_cria_tabelas_no_banco_temporario(caminho_banco):
    conexao = sqlite3.connect(caminho_banco)
    try:
        tabelas = {
            linha[0]
            for linha in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        conexao.close()

    assert {"transacoes", "metas"} <= tabelas


def test_conexao_utiliza_sqlite_row(caminho_banco):
    conexao = database.conectar()
    try:
        assert conexao.row_factory is sqlite3.Row
    finally:
        conexao.close()


def test_escrita_persiste_apos_commit(caminho_banco):
    conexao = database.conectar()
    conexao.execute(
        """
        INSERT INTO metas (categoria, limite)
        VALUES (?, ?)
        """,
        ("Comida", 100)
    )
    conexao.commit()
    conexao.close()

    outra_conexao = database.conectar()
    try:
        assert outra_conexao.execute(
            "SELECT limite FROM metas"
        ).fetchone()[0] == 100
    finally:
        outra_conexao.close()


def test_banco_configurado_e_o_temporario(caminho_banco):
    assert database.CAMINHO_BANCO == str(caminho_banco)
    assert caminho_banco.exists()

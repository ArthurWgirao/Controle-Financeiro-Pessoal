"""Preservação segura de sequências durante recriações de tabelas."""

import sqlalchemy as sa


TABELAS_AUTOINCREMENT = frozenset({"usuarios", "transacoes", "metas"})


def _validar_tabela(tabela):
    if tabela not in TABELAS_AUTOINCREMENT:
        raise ValueError(f"Tabela não autorizada para sequência: {tabela!r}")


def _sqlite(conexao):
    return conexao.dialect.name == "sqlite"


def capturar_sequencia(conexao, tabela):
    """Retorna sequência histórica e maior ID; fora do SQLite, não consulta."""
    _validar_tabela(tabela)
    if not _sqlite(conexao):
        return None

    existe = conexao.execute(sa.text(
        "SELECT 1 FROM sqlite_master "
        "WHERE type = 'table' AND name = 'sqlite_sequence'"
    )).first()
    historica = None
    if existe:
        historica = conexao.execute(
            sa.text("SELECT seq FROM sqlite_sequence WHERE name = :nome"),
            {"nome": tabela}
        ).scalar_one_or_none()
    maior_id = conexao.execute(
        sa.text(f'SELECT MAX(id) FROM "{tabela}"')
    ).scalar_one_or_none()
    return {"historica": historica, "maior_id": maior_id}


def restaurar_sequencia(conexao, tabela, captura):
    """Restaura max(histórica, MAX(id)) sem inventar histórico vazio."""
    _validar_tabela(tabela)
    if not _sqlite(conexao) or captura is None:
        return

    ddl = conexao.execute(
        sa.text(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'table' AND name = :nome"
        ),
        {"nome": tabela}
    ).scalar_one_or_none()
    if not ddl or "AUTOINCREMENT" not in ddl.upper():
        raise RuntimeError(
            f"A tabela {tabela} foi recriada sem AUTOINCREMENT."
        )

    maior_atual = conexao.execute(
        sa.text(f'SELECT MAX(id) FROM "{tabela}"')
    ).scalar_one_or_none()
    candidatos = [
        valor for valor in (
            captura.get("historica"),
            captura.get("maior_id"),
            maior_atual
        )
        if valor is not None
    ]
    if not candidatos:
        return
    final = max(candidatos)
    resultado = conexao.execute(
        sa.text("UPDATE sqlite_sequence SET seq = :seq WHERE name = :nome"),
        {"seq": final, "nome": tabela}
    )
    if resultado.rowcount == 0:
        conexao.execute(
            sa.text("INSERT INTO sqlite_sequence (name, seq) VALUES (:nome, :seq)"),
            {"nome": tabela, "seq": final}
        )

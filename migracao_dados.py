"""Transferência controlada de um snapshot SQLite para PostgreSQL vazio."""

import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import click
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


REVISAO = "0004_auth_ownership_required"
TABELAS = ("usuarios", "transacoes", "metas")
COLUNAS = {
    "usuarios": {"id", "nome", "email", "senha_hash", "ativo", "criado_em"},
    "transacoes": {
        "id", "usuario_id", "tipo", "valor", "categoria", "descricao", "data"
    },
    "metas": {"id", "usuario_id", "categoria", "limite"},
}
LOCK_ID = 0x4350465452414E53
PONTOS_FALHA = frozenset({
    "antes_inserts", "apos_usuarios", "apos_transacoes", "apos_metas",
    "durante_validacao", "antes_sequences", "primeira_sequence",
    "apos_sequences",
})


class ErroValidacao(Exception):
    pass


class ErroConflito(ErroValidacao):
    pass


@dataclass(frozen=True)
class UsuarioDados:
    id: int
    nome: str
    email: str
    senha_hash: str
    ativo: bool
    criado_em: datetime


@dataclass(frozen=True)
class TransacaoDados:
    id: int
    tipo: str
    valor: Decimal
    categoria: str
    descricao: str
    data: date
    usuario_id: int


@dataclass(frozen=True)
class MetaDados:
    id: int
    categoria: str
    limite: Decimal
    usuario_id: int


@dataclass(frozen=True)
class Snapshot:
    usuarios: tuple[UsuarioDados, ...]
    transacoes: tuple[TransacaoDados, ...]
    metas: tuple[MetaDados, ...]


@dataclass(frozen=True)
class EstadoSequence:
    nome: str
    last_value: int
    is_called: bool


@dataclass(frozen=True)
class ResultadoTransferencia:
    dry_run: bool
    usuarios: int
    transacoes: int
    metas: int
    duracao: float


def _decimal_positivo(valor, campo):
    try:
        convertido = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        convertido = None
    if (convertido is None or not convertido.is_finite() or convertido <= 0
            or convertido > Decimal("9999999999.99")):
        raise ErroValidacao(f"Valor inválido em {campo}.")
    if convertido.as_tuple().exponent < -2:
        raise ErroValidacao(f"Escala inválida em {campo}.")
    return convertido.quantize(Decimal("0.01"))


def _data(valor, campo):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ErroValidacao(f"Data inválida em {campo}.") from None


def _timestamp_utc(valor):
    try:
        convertido = datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ErroValidacao("Timestamp de usuário inválido.") from None
    if convertido.tzinfo is None:
        convertido = convertido.replace(tzinfo=timezone.utc)
    return convertido.astimezone(timezone.utc)


def _validar_colunas(conexao, tabela, esperadas):
    atuais = {linha[1] for linha in conexao.execute(f'PRAGMA table_info("{tabela}")')}
    if atuais != set(esperadas):
        raise ErroValidacao(f"Esquema SQLite inesperado em {tabela}.")


def ler_snapshot_sqlite(caminho_origem):
    caminho = Path(caminho_origem)
    if not caminho.is_absolute():
        raise ErroValidacao("Informe um caminho SQLite absoluto.")
    caminho = caminho.resolve(strict=False)
    if not caminho.is_file():
        raise ErroValidacao("Arquivo SQLite de origem não encontrado.")
    conexao = sqlite3.connect(
        caminho.as_uri() + "?mode=ro&immutable=1", uri=True
    )
    conexao.row_factory = sqlite3.Row
    try:
        conexao.execute("BEGIN")
        if conexao.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ErroValidacao("Integridade da origem SQLite inválida.")
        revisao = conexao.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        if not revisao or revisao[0] != REVISAO:
            raise ErroValidacao("Revisão SQLite incompatível.")
        tabelas = {r[0] for r in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if not {"alembic_version", *TABELAS} <= tabelas:
            raise ErroValidacao("Tabelas obrigatórias ausentes na origem.")
        _validar_colunas(conexao, "usuarios", (
            "id", "nome", "email", "senha_hash", "ativo", "criado_em"
        ))
        _validar_colunas(conexao, "transacoes", (
            "id", "usuario_id", "tipo", "valor", "categoria",
            "descricao", "data"
        ))
        _validar_colunas(conexao, "metas", (
            "id", "usuario_id", "categoria", "limite"
        ))
        if list(conexao.execute("PRAGMA foreign_key_check")):
            raise ErroValidacao("A origem contém relacionamento inválido.")

        linhas_usuarios = list(conexao.execute(
            "SELECT id,nome,email,senha_hash,ativo,criado_em "
            "FROM usuarios ORDER BY id"
        ))
        if any(r["ativo"] not in (0, 1) for r in linhas_usuarios):
            raise ErroValidacao("Indicador ativo inválido na origem.")
        if any(not r[c] for r in linhas_usuarios for c in (
                "nome", "email", "senha_hash", "criado_em")):
            raise ErroValidacao("Usuário com campo obrigatório inválido.")
        usuarios = tuple(UsuarioDados(
            id=int(r["id"]), nome=str(r["nome"]), email=str(r["email"]),
            senha_hash=str(r["senha_hash"]), ativo=bool(r["ativo"]),
            criado_em=_timestamp_utc(r["criado_em"]),
        ) for r in linhas_usuarios)
        ids_usuarios = {u.id for u in usuarios}
        if len({u.email for u in usuarios}) != len(usuarios):
            raise ErroValidacao("E-mails duplicados na origem.")
        transacoes = tuple(TransacaoDados(
            id=int(r["id"]), tipo=str(r["tipo"]),
            valor=_decimal_positivo(r["valor"], "transação"),
            categoria=str(r["categoria"]), descricao=str(r["descricao"]),
            data=_data(r["data"], "transação"),
            usuario_id=int(r["usuario_id"]),
        ) for r in conexao.execute(
            "SELECT id,tipo,valor,categoria,descricao,data,usuario_id "
            "FROM transacoes ORDER BY id"
        ))
        metas = tuple(MetaDados(
            id=int(r["id"]), categoria=str(r["categoria"]),
            limite=_decimal_positivo(r["limite"], "meta"),
            usuario_id=int(r["usuario_id"]),
        ) for r in conexao.execute(
            "SELECT id,categoria,limite,usuario_id FROM metas ORDER BY id"
        ))
        if any(t.tipo not in {"receita", "despesa"} for t in transacoes):
            raise ErroValidacao("Tipo de transação desconhecido na origem.")
        if any(t.usuario_id not in ids_usuarios for t in transacoes):
            raise ErroValidacao("Transação com usuário inexistente.")
        if any(m.usuario_id not in ids_usuarios for m in metas):
            raise ErroValidacao("Meta com usuário inexistente.")
        pares = {(m.usuario_id, m.categoria) for m in metas}
        if len(pares) != len(metas):
            raise ErroValidacao("Metas duplicadas na origem.")
        conexao.rollback()
        return Snapshot(usuarios, transacoes, metas)
    except sqlite3.Error as erro:
        raise ErroValidacao("Origem não é um SQLite válido no esquema esperado.") from erro
    finally:
        conexao.close()


def _validar_destino(conexao, banco_esperado):
    if conexao.dialect.name != "postgresql":
        raise ErroValidacao("O destino deve usar PostgreSQL.")
    if conexao.execute(text("SELECT current_database() ")).scalar_one() != banco_esperado:
        raise ErroValidacao("O banco PostgreSQL conectado diverge do configurado.")
    revisao = conexao.execute(text(
        "SELECT version_num FROM alembic_version"
    )).scalar_one_or_none()
    if revisao != REVISAO:
        raise ErroValidacao("Revisão PostgreSQL incompatível.")
    inspetor = inspect(conexao)
    if not {"alembic_version", *TABELAS} <= set(inspetor.get_table_names()):
        raise ErroValidacao("Schema PostgreSQL incompleto.")
    for tabela, esperadas in COLUNAS.items():
        atuais = {coluna["name"] for coluna in inspetor.get_columns(tabela)}
        if atuais != esperadas:
            raise ErroValidacao(f"Schema PostgreSQL inesperado em {tabela}.")


def _contagens(conexao):
    return tuple(conexao.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in TABELAS)


def _sequences(conexao):
    estados = {}
    for tabela in TABELAS:
        nome = conexao.execute(text(
            "SELECT pg_get_serial_sequence(:tabela, 'id')"
        ), {"tabela": tabela}).scalar_one_or_none()
        if not nome or not re.fullmatch(r'[A-Za-z_][\w$]*\.[A-Za-z_][\w$]*', nome):
            raise ErroValidacao(f"Sequence não descoberta para {tabela}.")
        schema, objeto = nome.split(".", 1)
        preparador = conexao.dialect.identifier_preparer
        citado = f"{preparador.quote(schema)}.{preparador.quote(objeto)}"
        valor, chamada = conexao.execute(text(
            f"SELECT last_value, is_called FROM {citado}"
        )).one()
        estados[tabela] = EstadoSequence(nome, int(valor), bool(chamada))
    return estados


def _restaurar_sequences(engine, estados):
    with engine.begin() as conexao:
        for estado in estados.values():
            conexao.execute(text(
                "SELECT setval(CAST(:nome AS regclass), :valor, :chamada)"
            ), {"nome": estado.nome, "valor": estado.last_value,
                "chamada": estado.is_called})


def _inserir(conexao, tabela, registros):
    if not registros:
        return
    dados = [r.__dict__ for r in registros]
    colunas = tuple(dados[0])
    valores = ",".join(f":{c}" for c in colunas)
    conexao.execute(text(
        f"INSERT INTO {tabela} ({','.join(colunas)}) VALUES ({valores})"
    ), dados)


def _snapshot_destino(conexao):
    usuarios = tuple(UsuarioDados(*r) for r in conexao.execute(text(
        "SELECT id,nome,email,senha_hash,ativo,criado_em "
        "FROM usuarios ORDER BY id"
    )))
    transacoes = tuple(TransacaoDados(
        int(r[0]), r[1], Decimal(r[2]), r[3], r[4], r[5], int(r[6])
    ) for r in conexao.execute(text(
        "SELECT id,tipo,valor,categoria,descricao,data,usuario_id "
        "FROM transacoes ORDER BY id"
    )))
    metas = tuple(MetaDados(
        int(r[0]), r[1], Decimal(r[2]), int(r[3])
    ) for r in conexao.execute(text(
        "SELECT id,categoria,limite,usuario_id FROM metas ORDER BY id"
    )))
    return Snapshot(usuarios, transacoes, metas)


def _falhar(ponto_atual, solicitado):
    if solicitado == ponto_atual:
        raise RuntimeError(f"Falha simulada: {ponto_atual}")


def transferir(caminho_origem, url_destino, *, dry_run=False,
               falhar_em=None):
    inicio = time.monotonic()
    if falhar_em is not None and falhar_em not in PONTOS_FALHA:
        raise ValueError("Ponto de falha desconhecido.")
    snapshot = ler_snapshot_sqlite(caminho_origem)
    url = make_url(url_destino)
    if url.get_backend_name() != "postgresql":
        raise ErroValidacao("O destino configurado não é PostgreSQL.")
    engine = create_engine(url, pool_pre_ping=True)
    estados = None
    sequences_alteradas = False
    destino_validado = False
    destino_inicialmente_vazio = False
    try:
        with engine.connect() as conexao:
            transacao = conexao.begin()
            try:
                _validar_destino(conexao, url.database)
                destino_validado = True
                if not conexao.execute(text(
                    "SELECT pg_try_advisory_xact_lock(:lock_id)"
                ), {"lock_id": LOCK_ID}).scalar_one():
                    raise ErroConflito("Outra transferência está em andamento.")
                conexao.execute(text(
                    "LOCK TABLE usuarios, transacoes, metas "
                    "IN ACCESS EXCLUSIVE MODE"
                ))
                if _contagens(conexao) != (0, 0, 0):
                    raise ErroConflito("O destino PostgreSQL não está vazio.")
                destino_inicialmente_vazio = True
                estados = _sequences(conexao)
                _falhar("antes_inserts", falhar_em)
                _inserir(conexao, "usuarios", snapshot.usuarios)
                _falhar("apos_usuarios", falhar_em)
                _inserir(conexao, "transacoes", snapshot.transacoes)
                _falhar("apos_transacoes", falhar_em)
                _inserir(conexao, "metas", snapshot.metas)
                _falhar("apos_metas", falhar_em)
                destino = _snapshot_destino(conexao)
                _falhar("durante_validacao", falhar_em)
                if destino != snapshot:
                    raise RuntimeError("Comparação semântica divergente.")
                _falhar("antes_sequences", falhar_em)
                if dry_run:
                    transacao.rollback()
                else:
                    for indice, (tabela, registros) in enumerate((
                        ("usuarios", snapshot.usuarios),
                        ("transacoes", snapshot.transacoes),
                        ("metas", snapshot.metas),
                    )):
                        if registros:
                            maior = max(r.id for r in registros)
                            conexao.execute(text(
                                "SELECT setval(CAST(:nome AS regclass), :valor, true)"
                            ), {"nome": estados[tabela].nome, "valor": maior})
                            sequences_alteradas = True
                        if indice == 0:
                            _falhar("primeira_sequence", falhar_em)
                    _falhar("apos_sequences", falhar_em)
                    transacao.commit()
            except Exception:
                if transacao.is_active:
                    transacao.rollback()
                raise
        return ResultadoTransferencia(
            dry_run, len(snapshot.usuarios), len(snapshot.transacoes),
            len(snapshot.metas), time.monotonic() - inicio
        )
    except Exception:
        if sequences_alteradas and estados is not None:
            _restaurar_sequences(engine, estados)
        if destino_validado and destino_inicialmente_vazio:
            with engine.connect() as verificacao:
                if _contagens(verificacao) != (0, 0, 0):
                    raise RuntimeError("Rollback deixou dados no destino.")
                if estados is not None and _sequences(verificacao) != estados:
                    raise RuntimeError("Compensação de sequences falhou.")
        raise
    finally:
        engine.dispose()


@click.command("transfer-sqlite-to-postgres")
@click.option("--source", type=click.Path(path_type=Path), required=True)
@click.option("--dry-run", is_flag=True)
@click.option("--confirm-transfer", is_flag=True)
def comando_transferencia(source, dry_run, confirm_transfer):
    """Valida ou transfere um snapshot SQLite para PostgreSQL vazio."""
    if dry_run == confirm_transfer:
        click.echo("Use exatamente --dry-run ou --confirm-transfer.", err=True)
        raise SystemExit(2)
    url = os.getenv("POSTGRES_TRANSFER_DATABASE_URL")
    if not url:
        click.echo("POSTGRES_TRANSFER_DATABASE_URL não configurada.", err=True)
        raise SystemExit(2)
    destino = make_url(url)
    click.echo(
        f"Destino: host={destino.host or 'local'} "
        f"porta={destino.port or 5432} banco={destino.database}"
    )
    try:
        resultado = transferir(source, url, dry_run=dry_run)
    except ErroConflito as erro:
        click.echo(f"CONFLITO: {erro}", err=True)
        raise SystemExit(3) from None
    except ErroValidacao as erro:
        click.echo(f"VALIDAÇÃO: {erro}", err=True)
        raise SystemExit(2) from None
    except Exception:
        click.echo("FALHA INTERNA — destino validado após rollback.", err=True)
        raise SystemExit(4) from None
    click.echo(
        f"Validados: usuários={resultado.usuarios}, "
        f"transações={resultado.transacoes}, metas={resultado.metas}."
    )
    click.echo(
        "Status: usuarios=igual, transacoes=igual, metas=igual; "
        f"duração={resultado.duracao:.3f}s."
    )
    if dry_run:
        click.echo("DRY-RUN APROVADO — NENHUM DADO TRANSFERIDO")
    else:
        click.echo("TRANSFERÊNCIA CONCLUÍDA E VALIDADA")

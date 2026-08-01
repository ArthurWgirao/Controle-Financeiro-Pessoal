from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select

from categorias import categorias
from extensions import db
from models import Transacao
from utils import ler_float, ler_int


def _confirmar():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def buscar_transacoes_por_tipo(tipo, usuario_id):
    return db.session.scalars(
        select(Transacao)
        .where(Transacao.tipo == tipo, Transacao.usuario_id == usuario_id)
        .order_by(Transacao.id.desc())
    ).all()


def buscar_transacao_por_id_e_tipo(id_transacao, tipo, usuario_id):
    return db.session.scalar(
        select(Transacao).where(
            Transacao.id == id_transacao,
            Transacao.tipo == tipo,
            Transacao.usuario_id == usuario_id
        )
    )


def cadastrar_transacao(tipo, valor, categoria, descricao, usuario_id):
    transacao = Transacao(
        tipo=tipo,
        usuario_id=usuario_id,
        valor=valor,
        categoria=categoria,
        descricao=descricao,
        data=date.today()
    )
    db.session.add(transacao)
    _confirmar()
    return transacao.id


def atualizar_transacao(id_transacao, tipo, valor, categoria, descricao, usuario_id):
    transacao = buscar_transacao_por_id_e_tipo(id_transacao, tipo, usuario_id)
    if transacao is None:
        return False

    transacao.valor = valor
    transacao.categoria = categoria
    transacao.descricao = descricao
    _confirmar()
    return True


def excluir_transacao(id_transacao, tipo, usuario_id):
    transacao = buscar_transacao_por_id_e_tipo(id_transacao, tipo, usuario_id)
    if transacao is None:
        return False

    db.session.delete(transacao)
    _confirmar()
    return True


def calcular_resumo(usuario_id):
    registros = db.session.execute(
        select(Transacao.tipo, func.sum(Transacao.valor))
        .where(
            Transacao.tipo.in_(("receita", "despesa")),
            Transacao.usuario_id == usuario_id
        )
        .group_by(Transacao.tipo)
    ).all()
    totais = {tipo: total for tipo, total in registros}
    receitas = totais.get("receita", Decimal("0.00"))
    despesas = totais.get("despesa", Decimal("0.00"))
    return receitas, despesas, receitas - despesas


def _listar_todas(usuario_id):
    return db.session.scalars(
        select(Transacao)
        .where(Transacao.usuario_id == usuario_id)
        .order_by(Transacao.id)
    ).all()


def escolher_categoria():
    print("\n===== CATEGORIAS =====")
    for indice, categoria in enumerate(categorias, start=1):
        print(f"{indice} - {categoria}")
    opcao = ler_int("Escolha uma categoria: ")
    if 1 <= opcao <= len(categorias):
        return categorias[opcao - 1]
    print("Categoria inválida!")
    return escolher_categoria()


def add_receita(usuario_id):
    cadastrar_transacao(
        "receita",
        ler_float("Digite o valor da receita: "),
        escolher_categoria(),
        input("Digite uma descrição: ").strip(),
        usuario_id
    )
    print("Receita adicionada!")


def add_despesa(usuario_id):
    cadastrar_transacao(
        "despesa",
        ler_float("Digite o valor da despesa: "),
        escolher_categoria(),
        input("Digite uma descrição: ").strip(),
        usuario_id
    )
    print("Despesa adicionada!")


def listar_transacoes(usuario_id):
    transacoes = _listar_todas(usuario_id)
    if not transacoes:
        print("Nenhuma transação cadastrada.")
        return
    print("\n===== TRANSAÇÕES =====")
    for indice, transacao in enumerate(transacoes):
        print(
            f"{indice} - [{transacao.tipo.upper()}] | "
            f"R$ {transacao.valor:.2f} | {transacao.categoria} | "
            f"{transacao.descricao} | {transacao.data:%d/%m/%Y}"
        )


def ver_saldo(usuario_id):
    receitas, despesas, saldo = calcular_resumo(usuario_id)
    print("\n===== RESUMO =====")
    print(f"Receitas: R$ {receitas:.2f}")
    print(f"Despesas: R$ {despesas:.2f}")
    print(f"Saldo:    R$ {saldo:.2f}")


def remover_transacao(usuario_id):
    transacoes = _listar_todas(usuario_id)
    if not transacoes:
        print("Nenhuma transação cadastrada.")
        return
    listar_transacoes(usuario_id)
    indice = ler_int(
        "\nDigite o índice da transação que deseja remover: ",
        permite_zero=True
    )
    if 0 <= indice < len(transacoes):
        transacao = transacoes[indice]
        excluir_transacao(transacao.id, transacao.tipo, usuario_id)
        print("Transação removida!")
    else:
        print("Índice inválido!")


def editar_transacao(usuario_id):
    transacoes = _listar_todas(usuario_id)
    if not transacoes:
        print("Nenhuma transação cadastrada.")
        return
    listar_transacoes(usuario_id)
    indice = ler_int("\nDigite o índice da transação que deseja editar: ")
    if not 0 <= indice < len(transacoes):
        print("Índice inválido!")
        return

    transacao = transacoes[indice]
    print("\nPressione ENTER para não alterar.\n")
    novo_valor = input(f"Novo valor (atual: {transacao.valor}): ").strip()
    nova_descricao = input(
        f"Nova descrição (atual: {transacao.descricao}): "
    ).strip()
    valor = Decimal(novo_valor) if novo_valor else transacao.valor
    descricao = nova_descricao or transacao.descricao
    categoria = transacao.categoria
    if input("Deseja alterar a categoria? (s/n): ").lower() == "s":
        categoria = escolher_categoria()
    atualizar_transacao(
        transacao.id, transacao.tipo, valor, categoria, descricao, usuario_id
    )
    print("Transação atualizada!")


def filtrar_por_categoria(usuario_id):
    categoria = escolher_categoria()
    transacoes = db.session.scalars(
        select(Transacao)
        .where(
            Transacao.categoria == categoria,
            Transacao.usuario_id == usuario_id
        )
        .order_by(Transacao.id)
    ).all()
    if not transacoes:
        print("Nenhuma transação encontrada.")
        return
    print(f"\n===== {categoria.upper()} =====")
    for transacao in transacoes:
        print(
            f"[{transacao.tipo.upper()}] R$ {transacao.valor:.2f} | "
            f"{transacao.descricao} | {transacao.data:%d/%m/%Y}"
        )


def total_por_categoria(usuario_id):
    totais = db.session.execute(
        select(Transacao.categoria, func.sum(Transacao.valor))
        .where(
            Transacao.tipo == "despesa",
            Transacao.usuario_id == usuario_id
        )
        .group_by(Transacao.categoria)
        .order_by(Transacao.categoria)
    ).all()
    print("\n===== TOTAL POR CATEGORIA =====")
    for categoria, total in totais:
        print(f"{categoria}: R$ {total:.2f}")


def relatorio_mensal(usuario_id):
    mes_informado = input("Digite o mês e ano (MM/AAAA): ").strip()
    try:
        referencia = datetime.strptime(mes_informado, "%m/%Y")
    except ValueError:
        print("Período inválido.")
        return
    inicio = date(referencia.year, referencia.month, 1)
    fim = (
        date(referencia.year + 1, 1, 1)
        if referencia.month == 12
        else date(referencia.year, referencia.month + 1, 1)
    )
    transacoes = db.session.scalars(
        select(Transacao).where(
            Transacao.data >= inicio,
            Transacao.data < fim,
            Transacao.tipo.in_(("receita", "despesa")),
            Transacao.usuario_id == usuario_id
        )
    ).all()
    if not transacoes:
        print("Nenhuma transação encontrada.")
        return
    receitas = sum(
        (item.valor for item in transacoes if item.tipo == "receita"),
        Decimal("0.00")
    )
    despesas = sum(
        (item.valor for item in transacoes if item.tipo == "despesa"),
        Decimal("0.00")
    )
    print("\n===== RELATÓRIO MENSAL =====")
    print(f"Mês: {mes_informado}")
    print(f"\nReceitas: R$ {receitas:.2f}")
    print(f"Despesas: R$ {despesas:.2f}")
    print(f"Saldo: R$ {receitas - despesas:.2f}")

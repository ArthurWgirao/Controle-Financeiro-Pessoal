import matplotlib.pyplot as plt
from sqlalchemy import func, select

from extensions import db
from models import Transacao


def grafico_despesas_categoria():
    dados = db.session.execute(
        select(Transacao.categoria, func.sum(Transacao.valor))
        .where(Transacao.tipo == "despesa")
        .group_by(Transacao.categoria)
        .order_by(Transacao.categoria)
    ).all()

    categorias = [categoria for categoria, _ in dados]
    valores = [float(total) for _, total in dados]
    plt.bar(categorias, valores)
    plt.title("Despesas por Categoria")
    plt.xlabel("Categorias")
    plt.ylabel("Valor Gasto (R$)")
    plt.show()

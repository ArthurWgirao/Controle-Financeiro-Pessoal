from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class Transacao(db.Model):
    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    valor: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    descricao: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)

    def __getitem__(self, chave):
        return getattr(self, chave)

    def __repr__(self):
        return (
            f"<Transacao id={self.id} "
            f"tipo={self.tipo!r} valor={self.valor}>"
        )


class Meta(db.Model):
    __tablename__ = "metas"
    __table_args__ = (
        UniqueConstraint("categoria", name="uq_metas_categoria"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    limite: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    def __getitem__(self, chave):
        return getattr(self, chave)

    def __repr__(self):
        return (
            f"<Meta id={self.id} categoria={self.categoria!r} "
            f"limite={self.limite}>"
        )

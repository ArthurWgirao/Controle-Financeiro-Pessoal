from datetime import date, datetime, timezone
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="usuario")
    metas: Mapped[list["Meta"]] = relationship(back_populates="usuario")

    @property
    def is_active(self):
        return self.ativo

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @validates("email")
    def _normalizar_email(self, chave, email):
        return (email or "").strip().lower()

    def __repr__(self):
        return f"<Usuario id={self.id} email={self.email!r}>"


class Transacao(db.Model):
    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    valor: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    descricao: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    usuario: Mapped[Usuario] = relationship(back_populates="transacoes")

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
        UniqueConstraint("usuario_id", "categoria", name="uq_metas_usuario_categoria"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False, index=True
    )
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    limite: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )
    usuario: Mapped[Usuario] = relationship(back_populates="metas")

    def __getitem__(self, chave):
        return getattr(self, chave)

    def __repr__(self):
        return (
            f"<Meta id={self.id} categoria={self.categoria!r} "
            f"limite={self.limite}>"
        )

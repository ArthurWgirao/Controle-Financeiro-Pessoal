import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Usuario


TAMANHO_MINIMO_SENHA = 8
TAMANHO_MAXIMO_SENHA = 128
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalizar_email(email):
    return (email or "").strip().lower()


def buscar_usuario_por_email(email):
    return db.session.scalar(
        select(Usuario).where(Usuario.email == normalizar_email(email))
    )


def validar_cadastro(nome, email, senha, confirmacao):
    nome = (nome or "").strip()
    email = normalizar_email(email)
    if not nome:
        return nome, email, "Informe seu nome."
    if len(nome) > 120:
        return nome, email, "O nome deve ter no máximo 120 caracteres."
    if not EMAIL_RE.fullmatch(email) or len(email) > 254:
        return nome, email, "Informe um e-mail válido."
    if not senha:
        return nome, email, "Informe uma senha."
    if len(senha) < TAMANHO_MINIMO_SENHA:
        return nome, email, "A senha deve ter pelo menos 8 caracteres."
    if len(senha) > TAMANHO_MAXIMO_SENHA:
        return nome, email, "A senha deve ter no máximo 128 caracteres."
    if senha != confirmacao:
        return nome, email, "A confirmação da senha não corresponde."
    return nome, email, None


def cadastrar_usuario(nome, email, senha, confirmacao):
    nome, email, erro = validar_cadastro(nome, email, senha, confirmacao)
    if erro:
        return None, erro
    if buscar_usuario_por_email(email):
        return None, "Já existe uma conta com este e-mail."
    usuario = Usuario(nome=nome, email=email)
    usuario.definir_senha(senha)
    db.session.add(usuario)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "Já existe uma conta com este e-mail."
    except Exception:
        db.session.rollback()
        raise
    return usuario, None


def autenticar_usuario(email, senha):
    usuario = buscar_usuario_por_email(email)
    if not usuario or not usuario.is_active or not senha:
        return None
    return usuario if usuario.verificar_senha(senha) else None

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import (
    criar_token_acesso,
    gerar_hash_senha,
    obter_saas_admin_logado,
    verificar_senha,
)
from settings import settings


router = APIRouter(
    prefix="/api/saas",
    tags=["Painel Mestre SaaS"],
)


def get_db():
    db = SessaoLocal()

    try:
        yield db

    finally:
        db.close()


class RequisicaoLoginSaaS(BaseModel):
    email: EmailStr
    senha: str = Field(
        min_length=8,
        max_length=72,
    )


class NovaBarbearia(BaseModel):
    nome: str = Field(
        min_length=2,
        max_length=120,
    )

    slug: str = Field(
        min_length=3,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    email: EmailStr

    senha: str = Field(
        min_length=8,
        max_length=72,
    )


def serializar_barbearia(
    barbearia: models.Barbearia,
) -> dict:
    return {
        "id": barbearia.id,
        "nome": barbearia.nome,
        "slug": barbearia.slug,
        "email": barbearia.email,
        "plano_ativo": barbearia.plano_ativo,
    }


@router.post("/login")
def login_saas(
    credenciais: RequisicaoLoginSaaS,
):
    if (
        not settings.saas_admin_email
        or not settings.saas_admin_password_hash
    ):
        raise HTTPException(
            status_code=503,
            detail="Painel Mestre ainda não configurado.",
        )

    email_informado = str(
        credenciais.email
    ).strip().lower()

    email_configurado = (
        settings
        .saas_admin_email
        .strip()
        .lower()
    )

    email_valido = secrets.compare_digest(
        email_informado,
        email_configurado,
    )

    senha_valida = verificar_senha(
        credenciais.senha,
        settings.saas_admin_password_hash,
    )

    if not (
        email_valido
        and senha_valida
    ):
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha incorretos.",
        )

    token = criar_token_acesso(
        {
            "sub": email_configurado,
            "role": "saas_admin",
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/barbearias")
def listar_clientes_do_software(
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    clientes = (
        db.query(models.Barbearia)
        .order_by(models.Barbearia.id.desc())
        .all()
    )

    return [
        serializar_barbearia(cliente)
        for cliente in clientes
    ]


@router.post(
    "/barbearias",
    status_code=201,
)
def registrar_nova_barbearia(
    dados: NovaBarbearia,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    nome = dados.nome.strip()
    slug = dados.slug.strip().lower()
    email = str(dados.email).strip().lower()

    existe = (
        db.query(models.Barbearia)
        .filter(
            or_(
                models.Barbearia.slug == slug,
                models.Barbearia.email == email,
            )
        )
        .first()
    )

    if existe:
        raise HTTPException(
            status_code=409,
            detail="Esse link ou e-mail já estão em uso.",
        )

    nova_barbearia = models.Barbearia(
        nome=nome,
        slug=slug,
        email=email,
        senha_hash=gerar_hash_senha(
            dados.senha
        ),
        plano_ativo=True,
    )

    try:
        db.add(nova_barbearia)
        db.commit()
        db.refresh(nova_barbearia)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Esse link ou e-mail já estão em uso.",
        )

    return serializar_barbearia(
        nova_barbearia
    )


@router.put(
    "/barbearias/{barbearia_id}/status"
)
def alterar_status_assinatura(
    barbearia_id: int,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    cliente = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.id
            == barbearia_id
        )
        .first()
    )

    if not cliente:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado.",
        )

    cliente.plano_ativo = not bool(
        cliente.plano_ativo
    )

    db.commit()
    db.refresh(cliente)

    return serializar_barbearia(
        cliente
    )
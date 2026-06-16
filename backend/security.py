from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from passlib.context import CryptContext

from settings import settings


SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = (
    settings.access_token_expire_minutes
)


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",
)


def gerar_hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(
    senha_plana: str,
    senha_hasheada: str,
) -> bool:
    return pwd_context.verify(
        senha_plana,
        senha_hasheada,
    )


def criar_token_acesso(dados: dict) -> str:
    payload = dados.copy()

    expiracao = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload.update(
        {
            "exp": expiracao,
        }
    )

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


esquema_seguranca = HTTPBearer()


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Seu acesso expirou. Faça login novamente.",
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido. Faça login novamente.",
        )


def obter_usuario_logado(
    credenciais: HTTPAuthorizationCredentials = Depends(
        esquema_seguranca
    ),
) -> str:
    payload = decodificar_token(
        credenciais.credentials
    )

    tenant_slug = payload.get("sub")

    # Tokens antigos podem não possuir role.
    # Eles continuam válidos temporariamente como tenant_admin.
    role = payload.get(
        "role",
        "tenant_admin",
    )

    if (
        not tenant_slug
        or role != "tenant_admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Você não possui permissão para acessar este recurso.",
        )

    return tenant_slug


def obter_saas_admin_logado(
    credenciais: HTTPAuthorizationCredentials = Depends(
        esquema_seguranca
    ),
) -> str:
    payload = decodificar_token(
        credenciais.credentials
    )

    usuario = payload.get("sub")
    role = payload.get("role")

    if (
        not usuario
        or role != "saas_admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito ao administrador mestre.",
        )

    return usuario


def validar_tenant_logado(
    tenant_slug: str,
    usuario_logado: str = Depends(
        obter_usuario_logado
    ),
) -> str:
    """
    Impede que o administrador de uma empresa altere
    os dados pertencentes a outro tenant.
    """

    if tenant_slug != usuario_logado:
        raise HTTPException(
            status_code=403,
            detail=(
                "Você não possui permissão para alterar "
                "os dados deste estabelecimento."
            ),
        )

    return usuario_logado
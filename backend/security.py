from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from passlib.context import CryptContext

from settings import settings


def validar_jwt_secret_key(
    valor: str | None,
) -> str:
    segredo = str(
        valor or ""
    ).strip()

    if not segredo:
        raise RuntimeError(
            "JWT_SECRET_KEY nao configurado."
        )

    return segredo


SECRET_KEY = validar_jwt_secret_key(
    settings.jwt_secret_key
)

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


ROLE_TENANT_ADMIN = "tenant_admin"
ROLE_SAAS_ADMIN = "saas_admin"

PAPEL_GESTOR = "gestor"
PAPEL_RECEPCAO = "recepcao"
PAPEL_PRESTADOR = "prestador"

PAPEIS_OPERACIONAIS_VALIDOS = {
    PAPEL_GESTOR,
    PAPEL_RECEPCAO,
    PAPEL_PRESTADOR,
}


def normalizar_papel_operacional(payload: dict) -> str:
    papel = (
        payload.get("papel")
        or payload.get("perfil_operacional")
        or payload.get("papel_operacional")
        or payload.get("perfil_usuario")
        or payload.get("perfil")
        or payload.get("tipo_usuario")
        or payload.get("tipo")
        or payload.get("role")
    )

    if not papel:
        return PAPEL_GESTOR

    papel_normalizado = str(papel).strip().lower()

    if papel_normalizado in {
        "tenant_admin",
        "admin",
        "administrador",
        "dono",
        "owner",
        "gestor",
    }:
        return PAPEL_GESTOR

    if papel_normalizado in {"recepcao", "atendimento"}:
        return PAPEL_RECEPCAO

    if papel_normalizado in {"prestador", "profissional", "colaborador"}:
        return PAPEL_PRESTADOR

    return PAPEL_GESTOR


def obter_permissoes_operacionais(payload: dict) -> list[str]:
    permissoes = payload.get("permissoes")

    if isinstance(permissoes, list):
        return [
            str(permissao).strip()
            for permissao in permissoes
            if str(permissao).strip()
        ]

    return []


def montar_contexto_usuario(payload: dict) -> dict:
    tenant_slug = (
        payload.get("tenant_slug")
        or payload.get("tenant")
        or payload.get("barbearia_slug")
        or payload.get("slug")
        or payload.get("sub")
    )

    return {
        "sub": payload.get("sub"),
        "tenant_slug": tenant_slug,
        "tenant_id": payload.get("tenant_id")
        or payload.get("barbearia_id")
        or payload.get("empresa_id"),
        "email": payload.get("email"),
        "role": payload.get("role", ROLE_TENANT_ADMIN),
        "papel": normalizar_papel_operacional(payload),
        "permissoes": obter_permissoes_operacionais(payload),
        "profissional_nome": payload.get("profissional_nome"),
        "usuario_operacional_id": payload.get("usuario_operacional_id"),
        "nome": payload.get("nome"),
    }


def obter_contexto_usuario_logado(
    credenciais: HTTPAuthorizationCredentials = Depends(
        esquema_seguranca
    ),
) -> dict:
    payload = decodificar_token(
        credenciais.credentials
    )

    contexto = montar_contexto_usuario(payload)

    if (
        not contexto["tenant_slug"]
        or contexto["role"] != ROLE_TENANT_ADMIN
    ):
        raise HTTPException(
            status_code=403,
            detail="Voce nao possui permissao para acessar este recurso.",
        )

    return contexto




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
    contexto = obter_contexto_usuario_logado(credenciais)
    return contexto["tenant_slug"]


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
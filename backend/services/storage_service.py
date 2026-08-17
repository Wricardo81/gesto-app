from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import requests
from fastapi import HTTPException, Request, UploadFile

from settings import settings


TIPOS_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

TAMANHO_MAXIMO_BYTES = 2 * 1024 * 1024

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_BASE_DIR = PROJECT_ROOT / "uploads" / "branding"


def normalizar_slug_storage(valor: str) -> str:
    return (
        str(valor or "")
        .strip()
        .lower()
        .replace("\\", "-")
        .replace("/", "-")
        .replace(" ", "-")
    )


def validar_tipo_branding(tipo: str) -> str:
    tipo_normalizado = str(tipo or "logo").strip().lower()

    if tipo_normalizado not in {"logo", "logomarca"}:
        raise HTTPException(
            status_code=400,
            detail="Tipo de imagem inválido.",
        )

    return tipo_normalizado


async def ler_e_validar_imagem(
    arquivo: UploadFile,
) -> tuple[bytes, str]:
    extensao = TIPOS_PERMITIDOS.get(arquivo.content_type)

    if not extensao:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Use JPG, PNG ou WEBP.",
        )

    conteudo = await arquivo.read()

    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Imagem muito grande. Envie arquivo de até 2MB.",
        )

    return conteudo, extensao


def storage_supabase_configurado() -> bool:
    return bool(
        settings.supabase_url
        and settings.supabase_service_role_key
        and settings.supabase_storage_bucket
    )


def montar_nome_arquivo(
    tipo: str,
    extensao: str,
) -> str:
    return f"{tipo}-{uuid4().hex}{extensao}"


def upload_local_branding(
    *,
    tenant_slug: str,
    tipo: str,
    nome_arquivo: str,
    conteudo: bytes,
    request: Request,
) -> dict:
    tenant_normalizado = normalizar_slug_storage(tenant_slug)

    pasta_tenant = UPLOAD_BASE_DIR / tenant_normalizado
    pasta_tenant.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_arquivo = pasta_tenant / nome_arquivo
    caminho_arquivo.write_bytes(conteudo)

    base_url = str(request.base_url).rstrip("/")

    url_publica = (
        f"{base_url}/uploads/branding/"
        f"{tenant_normalizado}/{nome_arquivo}"
    )

    return {
        "url": url_publica,
        "tipo": tipo,
        "arquivo": nome_arquivo,
        "storage": "local",
    }


def upload_supabase_branding(
    *,
    tenant_slug: str,
    tipo: str,
    nome_arquivo: str,
    conteudo: bytes,
    content_type: str,
) -> dict:
    tenant_normalizado = normalizar_slug_storage(tenant_slug)
    bucket = settings.supabase_storage_bucket.strip()
    supabase_url = settings.supabase_url.rstrip("/")
    caminho_storage = f"branding/{tenant_normalizado}/{nome_arquivo}"

    endpoint = (
        f"{supabase_url}/storage/v1/object/"
        f"{bucket}/{caminho_storage}"
    )

    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    try:
        resposta = requests.post(
            endpoint,
            headers=headers,
            data=conteudo,
            timeout=30,
        )
    except requests.RequestException as erro:
        raise HTTPException(
            status_code=502,
            detail=(
                "Não foi possível enviar a imagem para o storage. "
                "Tente novamente em instantes."
            ),
        ) from erro

    if resposta.status_code not in {200, 201}:
        raise HTTPException(
            status_code=502,
            detail=(
                "Erro ao salvar imagem no storage. "
                f"Status: {resposta.status_code}"
            ),
        )

    url_publica = (
        f"{supabase_url}/storage/v1/object/public/"
        f"{bucket}/{caminho_storage}"
    )

    return {
        "url": url_publica,
        "tipo": tipo,
        "arquivo": nome_arquivo,
        "storage": "supabase",
    }


async def salvar_imagem_branding(
    *,
    tenant_slug: str,
    tipo: str,
    arquivo: UploadFile,
    request: Request,
) -> dict:
    tipo_validado = validar_tipo_branding(tipo)
    conteudo, extensao = await ler_e_validar_imagem(arquivo)

    nome_arquivo = montar_nome_arquivo(
        tipo=tipo_validado,
        extensao=extensao,
    )

    if storage_supabase_configurado():
        return upload_supabase_branding(
            tenant_slug=tenant_slug,
            tipo=tipo_validado,
            nome_arquivo=nome_arquivo,
            conteudo=conteudo,
            content_type=arquivo.content_type or "application/octet-stream",
        )

    return upload_local_branding(
        tenant_slug=tenant_slug,
        tipo=tipo_validado,
        nome_arquivo=nome_arquivo,
        conteudo=conteudo,
        request=request,
    )

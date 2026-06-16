from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from security import validar_tenant_logado


router = APIRouter(
    prefix="/api",
    tags=["Uploads"],
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_BASE_DIR = PROJECT_ROOT / "uploads" / "branding"

TIPOS_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

TAMANHO_MAXIMO_BYTES = 2 * 1024 * 1024


@router.post("/{tenant_slug}/admin/uploads/branding")
async def upload_imagem_branding(
    tenant_slug: str,
    request: Request,
    tipo: str = Form("logo"),
    arquivo: UploadFile = File(...),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    if tipo not in ["logo", "logomarca"]:
        raise HTTPException(
            status_code=400,
            detail="Tipo de imagem inválido.",
        )

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

    pasta_tenant = UPLOAD_BASE_DIR / tenant_slug
    pasta_tenant.mkdir(
        parents=True,
        exist_ok=True,
    )

    nome_arquivo = f"{tipo}-{uuid4().hex}{extensao}"
    caminho_arquivo = pasta_tenant / nome_arquivo

    caminho_arquivo.write_bytes(conteudo)

    base_url = str(request.base_url).rstrip("/")

    url_publica = (
        f"{base_url}/uploads/branding/"
        f"{tenant_slug}/{nome_arquivo}"
    )

    return {
        "url": url_publica,
        "tipo": tipo,
        "arquivo": nome_arquivo,
    }
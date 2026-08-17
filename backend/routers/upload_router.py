from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
)

from security import validar_tenant_logado
from services.storage_service import salvar_imagem_branding


router = APIRouter(
    prefix="/api",
    tags=["Uploads"],
)


@router.post("/{tenant_slug}/admin/uploads/branding")
async def upload_imagem_branding(
    tenant_slug: str,
    request: Request,
    tipo: str = Form("logo"),
    arquivo: UploadFile = File(...),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    return await salvar_imagem_branding(
        tenant_slug=tenant_slug,
        tipo=tipo,
        arquivo=arquivo,
        request=request,
    )

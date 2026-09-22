from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessaoLocal
from security import validar_tenant_logado, obter_contexto_usuario_logado
from services import fila_espera_service


router = APIRouter()


def get_db():
    db = SessaoLocal()

    try:
        yield db
    finally:
        db.close()


def validar_acesso_fila_espera_admin(
    contexto_usuario: dict,
    *,
    gerenciar: bool = False,
) -> None:
    papel = str(
        contexto_usuario.get("papel_operacional")
        or contexto_usuario.get("papel")
        or ""
    ).strip().lower()

    permissoes = contexto_usuario.get("permissoes") or []

    if "*" in permissoes:
        return

    if papel in {"gestor", "recepcao"}:
        return

    permissao_necessaria = (
        "gerenciar_fila_espera"
        if gerenciar
        else "ver_fila_espera"
    )

    if permissao_necessaria in permissoes:
        return

    if (
        not gerenciar
        and "gerenciar_fila_espera" in permissoes
    ):
        return

    raise HTTPException(
        status_code=403,
        detail="Seu perfil nao possui permissao para acessar a fila de espera.",
    )


@router.post("/api/{tenant_slug}/fila-espera", status_code=201)
def criar_entrada_fila_espera_publica(
    tenant_slug: str,
    dados: fila_espera_service.EntradaFilaEsperaPublica,
    db: Session = Depends(get_db),
):
    return fila_espera_service.criar_entrada_fila_espera(
        db=db,
        tenant_slug=tenant_slug,
        dados=dados,
    )


@router.get("/api/{tenant_slug}/admin/fila-espera")
def listar_fila_espera_admin(
    tenant_slug: str,
    status: str | None = None,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
    contexto_usuario: dict = Depends(obter_contexto_usuario_logado),
):
    validar_acesso_fila_espera_admin(
        contexto_usuario,
        gerenciar=False,
    )

    return {
        "fila_espera": fila_espera_service.listar_fila_espera(
            db=db,
            tenant_slug=tenant_slug,
            status=status,
        )
    }


@router.put("/api/{tenant_slug}/admin/fila-espera/{item_id}/status")
def atualizar_status_fila_espera_admin(
    tenant_slug: str,
    item_id: int,
    dados: fila_espera_service.AtualizacaoStatusFilaEspera,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
    contexto_usuario: dict = Depends(obter_contexto_usuario_logado),
):
    validar_acesso_fila_espera_admin(
        contexto_usuario,
        gerenciar=True,
    )

    return {
        "mensagem": "Status da fila de espera atualizado com sucesso.",
        "item": fila_espera_service.atualizar_status_fila_espera(
            db=db,
            tenant_slug=tenant_slug,
            item_id=item_id,
            dados=dados,
        ),
    }

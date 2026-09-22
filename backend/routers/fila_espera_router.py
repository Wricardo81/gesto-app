from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models

from database import SessaoLocal
from security import validar_tenant_logado, obter_contexto_usuario_logado
from services import fila_espera_service
from services import agendamento_service


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


@router.delete(
    "/api/{tenant_slug}/admin/fila-espera/{item_id}"
)
def excluir_item_fila_espera_admin(
    tenant_slug: str,
    item_id: int,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
    contexto_usuario: dict = Depends(
        obter_contexto_usuario_logado
    ),
):
    validar_acesso_fila_espera_admin(
        contexto_usuario,
        gerenciar=True,
    )

    return {
        "mensagem": (
            "Item da fila de espera excluido "
            "definitivamente."
        ),
        "item": (
            fila_espera_service
            .excluir_item_fila_espera(
                db=db,
                tenant_slug=tenant_slug,
                item_id=item_id,
            )
        ),
    }


@router.post(
    "/api/{tenant_slug}/admin/fila-espera/{item_id}/agendar",
    status_code=201,
)
def converter_fila_espera_em_agendamento(
    tenant_slug: str,
    item_id: int,
    dados: fila_espera_service.ConverterFilaEsperaAgendamento,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
    contexto_usuario: dict = Depends(obter_contexto_usuario_logado),
):
    validar_acesso_fila_espera_admin(
        contexto_usuario,
        gerenciar=True,
    )

    item = (
        db.query(models.FilaEspera)
        .filter(
            models.FilaEspera.id == item_id,
            models.FilaEspera.barbearia_slug == tenant_slug,
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item da fila de espera nao encontrado.",
        )

    status_atual = str(item.status or "").strip().lower()

    if status_atual == "agendado":
        raise HTTPException(
            status_code=409,
            detail="Este item da fila ja foi convertido em agendamento.",
        )

    if status_atual in {"cancelado", "expirado"}:
        raise HTTPException(
            status_code=409,
            detail="Este item da fila nao esta mais ativo.",
        )

    data_agendamento = (
        str(dados.data or "").strip()
        or (
            item.data_desejada.isoformat()
            if item.data_desejada
            else ""
        )
    )

    profissional = (
        str(dados.profissional or "").strip()
        or str(item.profissional_preferido or "").strip()
    )

    horario = str(dados.horario or "").strip()

    if not data_agendamento:
        raise HTTPException(
            status_code=422,
            detail="Informe a data do agendamento.",
        )

    if not profissional:
        raise HTTPException(
            status_code=422,
            detail="Informe o profissional do agendamento.",
        )

    ficha = agendamento_service.FichaAgendamento(
        cliente_nome=item.cliente_nome,
        telefone_cliente=item.telefone_cliente,
        servico=item.servico,
        profissional=profissional,
        data=data_agendamento,
        horario=horario,
        valor=0,
        aceita_lembrete_whatsapp=True,
        aceita_promocoes_whatsapp=False,
    )

    agendamento = agendamento_service.criar_novo_agendamento(
        db=db,
        tenant_slug=tenant_slug,
        dados=ficha,
    )

    # Somente depois da criacao real do agendamento.
    item.status = "agendado"
    item.agendado_em = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()
    db.refresh(item)

    return {
        "mensagem": "Item da fila convertido em agendamento com sucesso.",
        "agendamento": agendamento,
        "item_fila": fila_espera_service.serializar_item_fila_espera(item),
    }


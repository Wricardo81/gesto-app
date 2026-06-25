import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
import re

import models
from database import SessaoLocal
from security import (
    criar_token_acesso,
    gerar_hash_senha,
    obter_saas_admin_logado,
    verificar_senha,
)
from settings import settings
from typing import Optional


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

class AtualizacaoFinanceiraBarbearia(BaseModel):
    plano_nome: str | None = None
    valor_mensal: float | None = None
    status_pagamento: str | None = None
    vencimento_plano: str | None = None
    dias_tolerancia: int | None = None
    marcar_como_pago: bool = False


class AtualizarAtivacaoEmpresaSaas(BaseModel):
    ativa: bool


class AtualizacaoDadosBarbearia(BaseModel):
    nome: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )

    slug: str | None = Field(
        default=None,
        min_length=3,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    email: EmailStr | None = None

    plano_ativo: bool | None = None


class RedefinicaoSenhaBarbearia(BaseModel):
    nova_senha: str = Field(
        min_length=8,
        max_length=72,
    )


class ExcluirEmpresaTesteSaas(BaseModel):
    confirmacao: str


STATUS_PAGAMENTO_VALIDOS = {
    "em_dia",
    "pendente",
    "vencido",
    "cancelado",
    "teste",
}


def converter_data_opcional(data_texto: str | None) -> date | None:
    if not data_texto:
        return None

    try:
        return datetime.strptime(
            data_texto,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Data inválida. Use o formato YYYY-MM-DD.",
        )


def calcular_acesso_financeiro(barbearia: models.Barbearia) -> dict:
    status_pagamento = getattr(
        barbearia,
        "status_pagamento",
        "em_dia",
    ) or "em_dia"

    vencimento = getattr(
        barbearia,
        "vencimento_plano",
        None,
    )

    dias_tolerancia = int(
        getattr(
            barbearia,
            "dias_tolerancia",
            3,
        ) or 0
    )

    hoje = date.today()

    dias_em_atraso = 0
    pagamento_vencido = False
    acesso_financeiro_ativo = True

    if vencimento and hoje > vencimento:
        dias_em_atraso = (hoje - vencimento).days
        pagamento_vencido = True

    if status_pagamento in {"cancelado", "vencido"}:
        acesso_financeiro_ativo = False

    if (
        pagamento_vencido
        and dias_em_atraso > dias_tolerancia
        and status_pagamento not in {"teste"}
    ):
        acesso_financeiro_ativo = False

    return {
        "pagamento_vencido": pagamento_vencido,
        "dias_em_atraso": dias_em_atraso,
        "acesso_financeiro_ativo": acesso_financeiro_ativo,
    }


def validar_slug_email_unicos(
    db: Session,
    barbearia_id: int,
    slug: str | None,
    email: str | None,
):
    filtros = []

    if slug:
        filtros.append(
            models.Barbearia.slug == slug
        )

    if email:
        filtros.append(
            models.Barbearia.email == email
        )

    if not filtros:
        return

    existente = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.id != barbearia_id,
            or_(*filtros),
        )
        .first()
    )

    if existente:
        raise HTTPException(
            status_code=409,
            detail="Slug ou e-mail já está em uso por outra empresa.",
        )




def serializar_barbearia_saas(barbearia: models.Barbearia) -> dict:
    financeiro = calcular_acesso_financeiro(barbearia)

    plano_ativo_manual = bool(
        getattr(
            barbearia,
            "plano_ativo",
            True,
        )
    )

    acesso_ativo = (
        plano_ativo_manual
        and financeiro["acesso_financeiro_ativo"]
    )

    return {
        "id": barbearia.id,
        "nome": barbearia.nome,
        "slug": barbearia.slug,
                "link_publico": (
            f"agendamento.html?tenant={barbearia.slug}"
        ),
        "link_admin": (
            f"admin.html?tenant={barbearia.slug}"
        ),
        "email": barbearia.email,
        "plano_ativo": plano_ativo_manual,
        "acesso_ativo": acesso_ativo,

        "plano_nome": getattr(
            barbearia,
            "plano_nome",
            "Profissional",
        ),
        "valor_mensal": float(
            getattr(
                barbearia,
                "valor_mensal",
                99.0,
            ) or 0
        ),
        "status_pagamento": getattr(
            barbearia,
            "status_pagamento",
            "em_dia",
        ),
        "vencimento_plano": (
            barbearia.vencimento_plano.isoformat()
            if getattr(barbearia, "vencimento_plano", None)
            else None
        ),
        "dias_tolerancia": int(
            getattr(
                barbearia,
                "dias_tolerancia",
                3,
            ) or 0
        ),
        "ultimo_pagamento_em": (
            barbearia.ultimo_pagamento_em.isoformat()
            if getattr(barbearia, "ultimo_pagamento_em", None)
            else None
        ),

        "pagamento_vencido": financeiro["pagamento_vencido"],
        "dias_em_atraso": financeiro["dias_em_atraso"],
        "gateway_pagamento": barbearia.gateway_pagamento,
        "plano_codigo": barbearia.plano_codigo,
        "plano_periodicidade": barbearia.plano_periodicidade,
        "status_assinatura": barbearia.status_assinatura,
        "stripe_customer_id": barbearia.stripe_customer_id,
        "stripe_subscription_id": barbearia.stripe_subscription_id,
        "stripe_checkout_session_id": barbearia.stripe_checkout_session_id,
        "assinatura_iniciada_em": (
            barbearia.assinatura_iniciada_em.isoformat()
            if barbearia.assinatura_iniciada_em
            else None
        ),
        "assinatura_renova_em": (
            barbearia.assinatura_renova_em.isoformat()
            if barbearia.assinatura_renova_em
            else None
        ),
        "periodo_trial_ate": (
            barbearia.periodo_trial_ate.isoformat()
            if barbearia.periodo_trial_ate
            else None
        ),
        "ultima_cobranca_status": barbearia.ultima_cobranca_status,
    }


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
        serializar_barbearia_saas(cliente)
        for cliente in clientes
    ]


@router.put("/barbearias/{barbearia_id}/ativacao")
def atualizar_ativacao_empresa_saas(
    barbearia_id: int,
    dados: AtualizarAtivacaoEmpresaSaas,
    db: Session = Depends(get_db),
    _saas_admin=Depends(obter_saas_admin_logado),
):
    barbearia = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.id == barbearia_id)
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

    if dados.ativa:
        barbearia.plano_ativo = True

        if barbearia.status_assinatura == "desativada":
            barbearia.status_assinatura = "trial"

        if barbearia.status_pagamento == "cancelado":
            barbearia.status_pagamento = "teste"

    else:
        barbearia.plano_ativo = False
        barbearia.status_assinatura = "desativada"
        barbearia.status_pagamento = "cancelado"

    db.commit()
    db.refresh(barbearia)

    return {
        "mensagem": (
            "Empresa reativada com sucesso."
            if dados.ativa
            else "Empresa desativada com sucesso."
        ),
        "barbearia": serializar_barbearia_saas(barbearia),
    }


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
        plano_nome="Profissional",
        valor_mensal=99.0,
        status_pagamento="teste",
        vencimento_plano=date.today() + timedelta(days=7),
        dias_tolerancia=3,
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

    return serializar_barbearia_saas(
        nova_barbearia
    )


@router.put("/barbearias/{barbearia_id}/status")
def alterar_status_assinatura(
    barbearia_id: int,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(obter_saas_admin_logado),
):
    barbearia = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.id == barbearia_id)
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado.",
        )

    barbearia.plano_ativo = not bool(barbearia.plano_ativo)

    db.commit()
    db.refresh(barbearia)

    return {
        "mensagem": "Status manual atualizado com sucesso.",
        "barbearia": serializar_barbearia_saas(barbearia),
    }


@router.put("/barbearias/{barbearia_id}/dados")
def atualizar_dados_barbearia(
    barbearia_id: int,
    dados: AtualizacaoDadosBarbearia,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    barbearia = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.id == barbearia_id)
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

    novo_nome = None
    novo_slug = None
    novo_email = None

    if dados.nome is not None:
        novo_nome = dados.nome.strip()

        if len(novo_nome) < 2:
            raise HTTPException(
                status_code=422,
                detail="O nome da empresa deve ter pelo menos 2 caracteres.",
            )

    if dados.slug is not None:
        novo_slug = dados.slug.strip().lower()

        if not re.match(
            r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
            novo_slug,
        ):
            raise HTTPException(
                status_code=422,
                detail="Slug inválido. Use apenas letras minúsculas, números e hífens.",
            )

    if dados.email is not None:
        novo_email = str(dados.email).strip().lower()

    validar_slug_email_unicos(
        db=db,
        barbearia_id=barbearia.id,
        slug=novo_slug,
        email=novo_email,
    )

    if novo_nome is not None:
        barbearia.nome = novo_nome

    if novo_slug is not None:
        barbearia.slug = novo_slug

    if novo_email is not None:
        barbearia.email = novo_email

    if dados.plano_ativo is not None:
        barbearia.plano_ativo = dados.plano_ativo

    try:
        db.commit()
        db.refresh(barbearia)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Slug ou e-mail já está em uso.",
        )

    return {
        "mensagem": "Dados da empresa atualizados com sucesso.",
        "barbearia": serializar_barbearia_saas(barbearia),
        "aviso": (
            "Se o slug foi alterado, os links antigos de agendamento podem deixar de funcionar."
        ),
    }


@router.put("/barbearias/{barbearia_id}/senha")
def redefinir_senha_barbearia(
    barbearia_id: int,
    dados: RedefinicaoSenhaBarbearia,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    barbearia = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.id == barbearia_id)
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

    barbearia.senha_hash = gerar_hash_senha(
        dados.nova_senha
    )

    db.commit()

    return {
        "mensagem": "Senha redefinida com sucesso.",
        "barbearia_id": barbearia.id,
        "slug": barbearia.slug,
        "email": barbearia.email,
    }


@router.get("/barbearias/{barbearia_id}/diagnostico")
def diagnosticar_barbearia(
    barbearia_id: int,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    barbearia = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.id == barbearia_id)
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

    total_servicos = (
        db.query(models.ServicoBarbearia)
        .filter(
            models.ServicoBarbearia.barbearia_slug == barbearia.slug
        )
        .count()
    )

    total_profissionais = (
        db.query(models.Profissional)
        .filter(
            models.Profissional.barbearia_slug == barbearia.slug
        )
        .count()
    )

    total_agendamentos = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == barbearia.slug
        )
        .count()
    )

    configuracao_existe = (
        db.query(models.ConfiguracaoAgenda)
        .filter(
            models.ConfiguracaoAgenda.barbearia_slug == barbearia.slug
        )
        .first()
        is not None
    )

    problemas = []

    if not barbearia.plano_ativo:
        problemas.append(
            "Empresa bloqueada manualmente."
        )

    if total_servicos == 0:
        problemas.append(
            "Nenhum serviço cadastrado."
        )

    if total_profissionais == 0:
        problemas.append(
            "Nenhum profissional cadastrado."
        )

    if not configuracao_existe:
        problemas.append(
            "Configuração de agenda ainda não encontrada."
        )

    return {
        "empresa": serializar_barbearia_saas(barbearia),
        "diagnostico": {
            "configuracao_existe": configuracao_existe,
            "total_servicos": total_servicos,
            "total_profissionais": total_profissionais,
            "total_agendamentos": total_agendamentos,
            "possui_problemas": bool(problemas),
            "problemas": problemas,
        },
    }


@router.delete("/barbearias/{barbearia_id}")
def excluir_empresa_teste_saas(
    barbearia_id: int,
    dados: ExcluirEmpresaTesteSaas,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(obter_saas_admin_logado),
):
    confirmacao_esperada = f"EXCLUIR-{barbearia_id}"

    if dados.confirmacao != confirmacao_esperada:
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirmação inválida. "
                f"Digite exatamente {confirmacao_esperada} para excluir."
            ),
        )

    barbearia = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.id == barbearia_id)
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

    status_assinatura = (
        barbearia.status_assinatura
        or ""
    ).strip().lower()

    if status_assinatura != "desativada":
        raise HTTPException(
            status_code=409,
            detail=(
                "Por segurança, somente empresas desativadas podem ser excluídas. "
                "Desative a empresa antes de excluir."
            ),
        )

    tenant_slug = barbearia.slug

    inspector = inspect(db.bind)
    tabela_barbearias = models.Barbearia.__tablename__

    parametros = {
        "barbearia_id": barbearia.id,
        "tenant_slug": tenant_slug,
        "barbearia_slug": tenant_slug,
        "empresa_id": barbearia.id,
        "tenant_id": barbearia.id,
    }

    total_registros_removidos = {}

    for tabela in inspector.get_table_names():
        if tabela == tabela_barbearias:
            continue

        colunas = {
            coluna["name"]
            for coluna in inspector.get_columns(tabela)
        }

        condicoes = []

        if "barbearia_id" in colunas:
            condicoes.append("barbearia_id = :barbearia_id")

        if "tenant_slug" in colunas:
            condicoes.append("tenant_slug = :tenant_slug")

        if "barbearia_slug" in colunas:
            condicoes.append("barbearia_slug = :barbearia_slug")

        if "empresa_id" in colunas:
            condicoes.append("empresa_id = :empresa_id")

        if "tenant_id" in colunas:
            condicoes.append("tenant_id = :tenant_id")

        if not condicoes:
            continue

        where_sql = " OR ".join(condicoes)

        total = db.execute(
            text(
                f'SELECT COUNT(*) FROM "{tabela}" WHERE {where_sql}'
            ),
            parametros,
        ).scalar() or 0

        if total > 0:
            db.execute(
                text(
                    f'DELETE FROM "{tabela}" WHERE {where_sql}'
                ),
                parametros,
            )

            total_registros_removidos[tabela] = int(total)

    db.delete(barbearia)
    db.commit()

    return {
        "mensagem": "Empresa de teste excluída com sucesso.",
        "empresa_id": barbearia_id,
        "tenant_slug": tenant_slug,
        "registros_removidos": total_registros_removidos,
    }
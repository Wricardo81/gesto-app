from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models

from services import whatsapp_outbound_service


STATUS_PENDENTE = "pendente"
STATUS_ENVIADA = "enviada"
STATUS_ERRO = "erro"


def agora_utc_naive() -> datetime:
    return datetime.now(
        UTC
    ).replace(
        tzinfo=None
    )


def normalizar_chave_idempotencia(
    valor: str,
) -> str:
    chave = str(
        valor or ""
    ).strip()

    if not chave:
        raise HTTPException(
            status_code=422,
            detail=(
                "Chave de idempotencia "
                "da outbox nao informada."
            ),
        )

    return chave


def buscar_mensagem_outbox(
    db: Session,
    *,
    provedor: str,
    chave_idempotencia: str,
):
    chave = normalizar_chave_idempotencia(
        chave_idempotencia
    )

    return (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .filter(
            models.OutboxMensagemWhatsApp.provedor
            == provedor,

            models.OutboxMensagemWhatsApp
            .chave_idempotencia
            == chave,
        )
        .first()
    )


def criar_ou_obter_mensagem_outbox(
    db: Session,
    *,
    provedor: str,
    chave_idempotencia: str,
    barbearia_slug: str,
    phone_number_id: str,
    telefone_destino: str,
    texto: str,
):
    chave = normalizar_chave_idempotencia(
        chave_idempotencia
    )

    existente = buscar_mensagem_outbox(
        db,
        provedor=provedor,
        chave_idempotencia=chave,
    )

    if existente:
        return existente

    origem = str(
        phone_number_id or ""
    ).strip()

    tenant = str(
        barbearia_slug or ""
    ).strip()

    telefone = (
        whatsapp_outbound_service
        .normalizar_telefone_destino(
            telefone_destino
        )
    )

    mensagem = (
        whatsapp_outbound_service
        .validar_texto_saida(
            texto
        )
    )

    if not origem:
        raise HTTPException(
            status_code=422,
            detail=(
                "phone_number_id "
                "nao informado."
            ),
        )

    if not tenant:
        raise HTTPException(
            status_code=422,
            detail=(
                "Tenant da mensagem "
                "nao informado."
            ),
        )

    registro = (
        models.OutboxMensagemWhatsApp(
            provedor=str(
                provedor or ""
            ).strip(),

            chave_idempotencia=chave,
            barbearia_slug=tenant,
            phone_number_id=origem,
            telefone_destino=telefone,
            texto=mensagem,
            status=STATUS_PENDENTE,
            tentativas=0,
            criado_em=agora_utc_naive(),
            atualizado_em=agora_utc_naive(),
        )
    )

    db.add(
        registro
    )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        concorrente = (
            buscar_mensagem_outbox(
                db,
                provedor=provedor,
                chave_idempotencia=chave,
            )
        )

        if concorrente:
            return concorrente

        raise

    db.refresh(
        registro
    )

    return registro


def marcar_mensagem_enviada(
    db: Session,
    *,
    mensagem:
        models.OutboxMensagemWhatsApp,
    provider_message_id: str,
):
    identificador = str(
        provider_message_id or ""
    ).strip()

    if not identificador:
        raise HTTPException(
            status_code=502,
            detail=(
                "Provider message id "
                "nao informado."
            ),
        )

    mensagem.status = STATUS_ENVIADA
    mensagem.provider_message_id = identificador
    mensagem.ultimo_erro = None
    mensagem.enviado_em = agora_utc_naive()
    mensagem.atualizado_em = agora_utc_naive()

    db.commit()
    db.refresh(
        mensagem
    )

    return mensagem


def marcar_mensagem_erro(
    db: Session,
    *,
    mensagem:
        models.OutboxMensagemWhatsApp,
    erro: str,
):
    mensagem.status = STATUS_ERRO

    mensagem.ultimo_erro = str(
        erro or "erro desconhecido"
    )

    mensagem.atualizado_em = agora_utc_naive()

    db.commit()
    db.refresh(
        mensagem
    )

    return mensagem


def tentar_entregar_mensagem_outbox(
    db: Session,
    *,
    mensagem:
        models.OutboxMensagemWhatsApp,
    transporte:
        whatsapp_outbound_service
        .TransporteWhatsApp,
) -> dict:
    if mensagem.status == STATUS_ENVIADA:
        return {
            "enviado":
                True,

            "idempotente":
                True,

            "provider":
                "persistido",

            "provider_message_id":
                mensagem.provider_message_id,
        }

    mensagem.tentativas = int(
        mensagem.tentativas or 0
    ) + 1

    mensagem.atualizado_em = (
        agora_utc_naive()
    )

    db.commit()

    try:
        resultado = (
            whatsapp_outbound_service
            .enviar_texto_whatsapp(
                transporte=transporte,
                phone_number_id=
                    mensagem.phone_number_id,
                telefone_destino=
                    mensagem.telefone_destino,
                texto=mensagem.texto,
            )
        )

    except HTTPException as erro:
        marcar_mensagem_erro(
            db,
            mensagem=mensagem,
            erro=str(
                erro.detail
            ),
        )

        raise

    except Exception as erro:
        marcar_mensagem_erro(
            db,
            mensagem=mensagem,
            erro=type(
                erro
            ).__name__,
        )

        raise

    marcar_mensagem_enviada(
        db,
        mensagem=mensagem,
        provider_message_id=
            resultado.get(
                "provider_message_id",
                "",
            ),
    )

    return resultado


STATUS_PROCESSANDO = "processando"
STATUS_ESGOTADA = "esgotada"

MAX_TENTATIVAS_OUTBOX = 5

CLAIM_EXPIRA_SEGUNDOS = 300

BACKOFF_SEGUNDOS = (
    30,
    120,
    300,
    900,
    3600,
)


def calcular_backoff_segundos(
    tentativas: int,
) -> int:
    indice = max(
        0,
        min(
            int(
                tentativas
            ) - 1,
            len(
                BACKOFF_SEGUNDOS
            ) - 1,
        ),
    )

    return BACKOFF_SEGUNDOS[
        indice
    ]


def claim_expirado_em(
    *,
    agora: datetime,
) -> datetime:
    from datetime import timedelta

    return agora - timedelta(
        seconds=
            CLAIM_EXPIRA_SEGUNDOS
    )


def listar_mensagens_recuperaveis(
    db: Session,
    *,
    limite: int = 50,
):
    if (
        not isinstance(
            limite,
            int,
        )
        or limite <= 0
        or limite > 500
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Limite da outbox invalido."
            ),
        )

    agora = agora_utc_naive()

    expirado_antes = (
        claim_expirado_em(
            agora=agora
        )
    )

    return (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .filter(
            models.OutboxMensagemWhatsApp
            .tentativas
            < MAX_TENTATIVAS_OUTBOX,

            (
                (
                    models.OutboxMensagemWhatsApp
                    .status.in_(
                        [
                            STATUS_PENDENTE,
                            STATUS_ERRO,
                        ]
                    )
                )
                &
                (
                    (
                        models.OutboxMensagemWhatsApp
                        .proxima_tentativa_em
                        .is_(None)
                    )
                    |
                    (
                        models.OutboxMensagemWhatsApp
                        .proxima_tentativa_em
                        <= agora
                    )
                )
            )
            |
            (
                (
                    models.OutboxMensagemWhatsApp
                    .status
                    == STATUS_PROCESSANDO
                )
                &
                (
                    models.OutboxMensagemWhatsApp
                    .processando_desde
                    <= expirado_antes
                )
            )
        )
        .order_by(
            models.OutboxMensagemWhatsApp
            .criado_em.asc(),

            models.OutboxMensagemWhatsApp
            .id.asc(),
        )
        .limit(
            limite
        )
        .all()
    )


def claim_mensagens_outbox(
    db: Session,
    *,
    limite: int = 50,
):
    if (
        not isinstance(
            limite,
            int,
        )
        or limite <= 0
        or limite > 500
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Limite da outbox invalido."
            ),
        )

    agora = agora_utc_naive()

    expirado_antes = (
        claim_expirado_em(
            agora=agora
        )
    )

    query = (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .filter(
            models.OutboxMensagemWhatsApp
            .tentativas
            < MAX_TENTATIVAS_OUTBOX,

            (
                (
                    models.OutboxMensagemWhatsApp
                    .status.in_(
                        [
                            STATUS_PENDENTE,
                            STATUS_ERRO,
                        ]
                    )
                )
                &
                (
                    (
                        models.OutboxMensagemWhatsApp
                        .proxima_tentativa_em
                        .is_(None)
                    )
                    |
                    (
                        models.OutboxMensagemWhatsApp
                        .proxima_tentativa_em
                        <= agora
                    )
                )
            )
            |
            (
                (
                    models.OutboxMensagemWhatsApp
                    .status
                    == STATUS_PROCESSANDO
                )
                &
                (
                    models.OutboxMensagemWhatsApp
                    .processando_desde
                    <= expirado_antes
                )
            )
        )
        .order_by(
            models.OutboxMensagemWhatsApp
            .criado_em.asc(),

            models.OutboxMensagemWhatsApp
            .id.asc(),
        )
        .limit(
            limite
        )
    )

    dialecto = (
        db.get_bind()
        .dialect
        .name
    )

    if dialecto == "postgresql":
        query = query.with_for_update(
            skip_locked=True
        )

    mensagens = query.all()

    for mensagem in mensagens:
        mensagem.status = (
            STATUS_PROCESSANDO
        )

        mensagem.processando_desde = (
            agora
        )

        mensagem.proxima_tentativa_em = (
            None
        )

        mensagem.atualizado_em = (
            agora
        )

    db.commit()

    return mensagens


def marcar_mensagem_enviada(
    db: Session,
    *,
    mensagem:
        models.OutboxMensagemWhatsApp,
    provider_message_id: str,
):
    identificador = str(
        provider_message_id or ""
    ).strip()

    if not identificador:
        raise HTTPException(
            status_code=502,
            detail=(
                "Provider message id "
                "nao informado."
            ),
        )

    mensagem.status = STATUS_ENVIADA
    mensagem.provider_message_id = (
        identificador
    )

    mensagem.ultimo_erro = None
    mensagem.enviado_em = agora_utc_naive()

    mensagem.processando_desde = None
    mensagem.proxima_tentativa_em = None

    mensagem.atualizado_em = (
        agora_utc_naive()
    )

    db.commit()
    db.refresh(
        mensagem
    )

    return mensagem


def marcar_mensagem_erro(
    db: Session,
    *,
    mensagem:
        models.OutboxMensagemWhatsApp,
    erro: str,
):
    from datetime import timedelta

    agora = agora_utc_naive()

    tentativas = int(
        mensagem.tentativas or 0
    )

    mensagem.ultimo_erro = str(
        erro or "erro desconhecido"
    )

    mensagem.processando_desde = None

    if (
        tentativas
        >= MAX_TENTATIVAS_OUTBOX
    ):
        mensagem.status = (
            STATUS_ESGOTADA
        )

        mensagem.proxima_tentativa_em = (
            None
        )

    else:
        mensagem.status = STATUS_ERRO

        segundos = (
            calcular_backoff_segundos(
                tentativas
            )
        )

        mensagem.proxima_tentativa_em = (
            agora
            + timedelta(
                seconds=segundos
            )
        )

    mensagem.atualizado_em = agora

    db.commit()
    db.refresh(
        mensagem
    )

    return mensagem


def tentar_entregar_mensagem_outbox(
    db: Session,
    *,
    mensagem:
        models.OutboxMensagemWhatsApp,
    transporte:
        whatsapp_outbound_service
        .TransporteWhatsApp,
) -> dict:
    if mensagem.status == STATUS_ENVIADA:
        return {
            "enviado":
                True,

            "idempotente":
                True,

            "provider":
                "persistido",

            "provider_message_id":
                mensagem.provider_message_id,
        }

    if (
        mensagem.status
        == STATUS_ESGOTADA
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Mensagem da outbox "
                "esgotou tentativas."
            ),
        )

    mensagem.tentativas = int(
        mensagem.tentativas or 0
    ) + 1

    mensagem.atualizado_em = (
        agora_utc_naive()
    )

    db.commit()

    try:
        resultado = (
            whatsapp_outbound_service
            .enviar_texto_whatsapp(
                transporte=transporte,
                phone_number_id=
                    mensagem.phone_number_id,
                telefone_destino=
                    mensagem.telefone_destino,
                texto=
                    mensagem.texto,
            )
        )

    except HTTPException as erro:
        marcar_mensagem_erro(
            db,
            mensagem=mensagem,
            erro=str(
                erro.detail
            ),
        )

        raise

    except Exception as erro:
        marcar_mensagem_erro(
            db,
            mensagem=mensagem,
            erro=type(
                erro
            ).__name__,
        )

        raise

    marcar_mensagem_enviada(
        db,
        mensagem=mensagem,
        provider_message_id=
            resultado.get(
                "provider_message_id",
                "",
            ),
    )

    return resultado


def processar_lote_outbox(
    db: Session,
    *,
    transporte:
        whatsapp_outbound_service
        .TransporteWhatsApp,
    limite: int = 50,
) -> dict:
    mensagens = claim_mensagens_outbox(
        db,
        limite=limite,
    )

    enviados = []
    falhas = []

    for mensagem in mensagens:
        try:
            resultado = (
                tentar_entregar_mensagem_outbox(
                    db=db,
                    mensagem=
                        mensagem,
                    transporte=
                        transporte,
                )
            )

            enviados.append(
                {
                    "outbox_id":
                        mensagem.id,

                    "provider_message_id":
                        resultado.get(
                            "provider_message_id"
                        ),
                }
            )

        except HTTPException as erro:
            falhas.append(
                {
                    "outbox_id":
                        mensagem.id,

                    "status_code":
                        erro.status_code,

                    "erro":
                        str(
                            erro.detail
                        ),
                }
            )

        except Exception as erro:
            falhas.append(
                {
                    "outbox_id":
                        mensagem.id,

                    "status_code":
                        500,

                    "erro":
                        type(
                            erro
                        ).__name__,
                }
            )

    return {
        "selecionadas":
            len(
                mensagens
            ),

        "enviadas":
            len(
                enviados
            ),

        "falhas":
            len(
                falhas
            ),

        "envios":
            enviados,

        "erros":
            falhas,
    }

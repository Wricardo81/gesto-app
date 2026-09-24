from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from services import agendamento_service


TEMPO_SESSAO_BOOKING_MINUTOS = 30


STATUS_SESSAO_BOOKING = {
    "ativa",
    "concluida",
    "expirada",
    "cancelada",
}


ETAPAS_SESSAO_BOOKING = {
    "inicio",
    "aguardando_servico",
    "aguardando_profissional",
    "aguardando_data",
    "aguardando_horario",
    "aguardando_nome",
    "confirmacao",
    "concluido",
}


def agora_utc_naive() -> datetime:
    return datetime.now(
        UTC
    ).replace(
        tzinfo=None
    )


def normalizar_telefone_booking(
    telefone: str | None,
) -> str:
    return "".join(
        caractere
        for caractere
        in str(
            telefone or ""
        )
        if caractere.isdigit()
    )


def validar_etapa_booking(
    etapa: str,
) -> str:
    etapa_normalizada = str(
        etapa or ""
    ).strip().lower()

    if etapa_normalizada not in ETAPAS_SESSAO_BOOKING:
        raise HTTPException(
            status_code=422,
            detail="Etapa da conversa invalida.",
        )

    return etapa_normalizada


def serializar_sessao_booking(
    sessao: models.SessaoBookingWhatsApp,
) -> dict:
    return {
        "id":
            sessao.id,

        "barbearia_slug":
            sessao.barbearia_slug,

        "telefone_cliente":
            sessao.telefone_cliente,

        "status":
            sessao.status,

        "etapa":
            sessao.etapa,

        "cliente_nome":
            sessao.cliente_nome,

        "servico":
            sessao.servico,

        "profissional":
            sessao.profissional,

        "data":
            (
                sessao.data.isoformat()
                if sessao.data
                else None
            ),

        "horario":
            sessao.horario,

        "canal":
            sessao.canal,

        "criado_em":
            (
                sessao.criado_em.isoformat()
                if sessao.criado_em
                else None
            ),

        "atualizado_em":
            (
                sessao.atualizado_em.isoformat()
                if sessao.atualizado_em
                else None
            ),

        "expira_em":
            (
                sessao.expira_em.isoformat()
                if sessao.expira_em
                else None
            ),
    }


def marcar_sessoes_expiradas(
    db: Session,
    tenant_slug: str,
    telefone_cliente: str,
) -> None:
    agora = agora_utc_naive()

    sessoes = (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .filter(
            models.SessaoBookingWhatsApp.barbearia_slug
            == tenant_slug,

            models.SessaoBookingWhatsApp.telefone_cliente
            == telefone_cliente,

            models.SessaoBookingWhatsApp.status
            == "ativa",

            models.SessaoBookingWhatsApp.expira_em
            <= agora,
        )
        .all()
    )

    if not sessoes:
        return

    for sessao in sessoes:
        sessao.status = "expirada"
        sessao.atualizado_em = agora

    db.commit()


def obter_sessao_ativa(
    db: Session,
    tenant_slug: str,
    telefone_cliente: str,
):
    telefone = normalizar_telefone_booking(
        telefone_cliente
    )

    if not telefone:
        return None

    marcar_sessoes_expiradas(
        db=db,
        tenant_slug=tenant_slug,
        telefone_cliente=telefone,
    )

    agora = agora_utc_naive()

    return (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .filter(
            models.SessaoBookingWhatsApp.barbearia_slug
            == tenant_slug,

            models.SessaoBookingWhatsApp.telefone_cliente
            == telefone,

            models.SessaoBookingWhatsApp.status
            == "ativa",

            models.SessaoBookingWhatsApp.expira_em
            > agora,
        )
        .order_by(
            models.SessaoBookingWhatsApp.id.desc()
        )
        .first()
    )


def criar_ou_obter_sessao(
    db: Session,
    tenant_slug: str,
    telefone_cliente: str,
):
    tenant = str(
        tenant_slug or ""
    ).strip()

    telefone = normalizar_telefone_booking(
        telefone_cliente
    )

    if not tenant:
        raise HTTPException(
            status_code=422,
            detail="Tenant invalido.",
        )

    if len(telefone) < 8:
        raise HTTPException(
            status_code=422,
            detail="Telefone invalido.",
        )

    sessao_existente = obter_sessao_ativa(
        db=db,
        tenant_slug=tenant,
        telefone_cliente=telefone,
    )

    if sessao_existente:
        return sessao_existente

    agora = agora_utc_naive()

    sessao = models.SessaoBookingWhatsApp(
        barbearia_slug=tenant,
        telefone_cliente=telefone,
        status="ativa",
        etapa="inicio",
        canal="whatsapp",
        criado_em=agora,
        atualizado_em=agora,
        expira_em=(
            agora
            + timedelta(
                minutes=TEMPO_SESSAO_BOOKING_MINUTOS
            )
        ),
    )

    db.add(sessao)
    db.commit()
    db.refresh(sessao)

    return sessao


def atualizar_sessao(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
    *,
    etapa: str | None = None,
    cliente_nome: str | None = None,
    servico: str | None = None,
    profissional: str | None = None,
    data_agendamento: date | None = None,
    horario: str | None = None,
):
    if sessao.status != "ativa":
        raise HTTPException(
            status_code=409,
            detail="A sessao nao esta mais ativa.",
        )

    agora = agora_utc_naive()

    if (
        sessao.expira_em
        and sessao.expira_em <= agora
    ):
        sessao.status = "expirada"
        sessao.atualizado_em = agora

        db.commit()

        raise HTTPException(
            status_code=409,
            detail="A sessao expirou.",
        )

    if etapa is not None:
        sessao.etapa = validar_etapa_booking(
            etapa
        )

    if cliente_nome is not None:
        sessao.cliente_nome = (
            str(cliente_nome).strip()
            or None
        )

    if servico is not None:
        sessao.servico = (
            str(servico).strip()
            or None
        )

    if profissional is not None:
        sessao.profissional = (
            str(profissional).strip()
            or None
        )

    if data_agendamento is not None:
        sessao.data = data_agendamento

    if horario is not None:
        sessao.horario = (
            str(horario).strip()
            or None
        )

    sessao.atualizado_em = agora

    sessao.expira_em = (
        agora
        + timedelta(
            minutes=TEMPO_SESSAO_BOOKING_MINUTOS
        )
    )

    db.commit()
    db.refresh(sessao)

    return sessao


def concluir_sessao(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
):
    if sessao.status != "ativa":
        raise HTTPException(
            status_code=409,
            detail="A sessao nao esta ativa.",
        )

    agora = agora_utc_naive()

    sessao.status = "concluida"
    sessao.etapa = "concluido"
    sessao.atualizado_em = agora

    db.commit()
    db.refresh(sessao)

    return sessao


def normalizar_texto_booking(
    valor: str | None,
) -> str:
    return str(
        valor or ""
    ).strip()


def listar_servicos_booking(
    db: Session,
    tenant_slug: str,
) -> list[models.ServicoBarbearia]:
    return (
        db.query(
            models.ServicoBarbearia
        )
        .filter(
            models.ServicoBarbearia.barbearia_slug
            == tenant_slug
        )
        .order_by(
            models.ServicoBarbearia.nome.asc()
        )
        .all()
    )


def listar_profissionais_booking(
    db: Session,
    tenant_slug: str,
    servico_nome: str,
) -> list[models.Profissional]:
    servico = (
        db.query(
            models.ServicoBarbearia
        )
        .filter(
            models.ServicoBarbearia.barbearia_slug
            == tenant_slug,

            models.ServicoBarbearia.nome
            == servico_nome,
        )
        .first()
    )

    if not servico:
        return []

    vinculos = (
        db.query(
            models.ServicoProfissional
        )
        .filter(
            models.ServicoProfissional.barbearia_slug
            == tenant_slug,

            models.ServicoProfissional.servico_id
            == servico.id,
        )
        .all()
    )

    ids_profissionais = [
        vinculo.profissional_id
        for vinculo in vinculos
    ]

    if not ids_profissionais:
        return []

    return (
        db.query(
            models.Profissional
        )
        .filter(
            models.Profissional.barbearia_slug
            == tenant_slug,

            models.Profissional.id.in_(
                ids_profissionais
            ),
        )
        .order_by(
            models.Profissional.nome.asc()
        )
        .all()
    )


def escolher_opcao_booking(
    texto: str,
    opcoes,
    atributo: str = "nome",
):
    entrada = normalizar_texto_booking(
        texto
    )

    if not entrada:
        return None

    if entrada.isdigit():
        indice = int(entrada) - 1

        if 0 <= indice < len(opcoes):
            return opcoes[indice]

    entrada_lower = entrada.lower()

    for opcao in opcoes:
        valor = normalizar_texto_booking(
            getattr(
                opcao,
                atributo,
                "",
            )
        )

        if valor.lower() == entrada_lower:
            return opcao

    return None


def formatar_opcoes_booking(
    opcoes,
    atributo: str = "nome",
) -> list[str]:
    return [
        (
            f"{indice}. "
            f"{normalizar_texto_booking(getattr(opcao, atributo, ''))}"
        )
        for indice, opcao
        in enumerate(
            opcoes,
            start=1,
        )
    ]


def montar_resposta_booking(
    sessao: models.SessaoBookingWhatsApp,
    mensagem: str,
    opcoes: list[str] | None = None,
) -> dict:
    return {
        "sessao":
            serializar_sessao_booking(
                sessao
            ),

        "etapa":
            sessao.etapa,

        "mensagem":
            mensagem,

        "opcoes":
            opcoes or [],
    }


def iniciar_fluxo_booking(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
) -> dict:
    servicos = listar_servicos_booking(
        db=db,
        tenant_slug=sessao.barbearia_slug,
    )

    if not servicos:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "No momento nao ha servicos "
                "disponiveis para agendamento."
            ),
        )

    atualizar_sessao(
        db=db,
        sessao=sessao,
        etapa="aguardando_servico",
    )

    opcoes = formatar_opcoes_booking(
        servicos
    )

    return montar_resposta_booking(
        sessao=sessao,
        mensagem=(
            "Ola! Vou ajudar voce a agendar. "
            "Escolha um servico respondendo "
            "com o numero ou com o nome."
        ),
        opcoes=opcoes,
    )


def processar_escolha_servico_booking(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
    mensagem: str,
) -> dict:
    servicos = listar_servicos_booking(
        db=db,
        tenant_slug=sessao.barbearia_slug,
    )

    escolhido = escolher_opcao_booking(
        mensagem,
        servicos,
    )

    if not escolhido:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Nao encontrei esse servico. "
                "Escolha uma das opcoes."
            ),
            opcoes=formatar_opcoes_booking(
                servicos
            ),
        )

    profissionais = listar_profissionais_booking(
        db=db,
        tenant_slug=sessao.barbearia_slug,
        servico_nome=escolhido.nome,
    )

    atualizar_sessao(
        db=db,
        sessao=sessao,
        etapa="aguardando_profissional",
        servico=escolhido.nome,
    )

    if not profissionais:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "O servico foi selecionado, "
                "mas ainda nao ha profissionais "
                "disponiveis para ele."
            ),
        )

    return montar_resposta_booking(
        sessao=sessao,
        mensagem=(
            f"Perfeito. Voce escolheu "
            f"{escolhido.nome}. "
            "Agora escolha o profissional."
        ),
        opcoes=formatar_opcoes_booking(
            profissionais
        ),
    )


def processar_mensagem_booking(
    db: Session,
    tenant_slug: str,
    telefone_cliente: str,
    mensagem: str,
) -> dict:
    sessao = criar_ou_obter_sessao(
        db=db,
        tenant_slug=tenant_slug,
        telefone_cliente=telefone_cliente,
    )

    texto = normalizar_texto_booking(
        mensagem
    )

    if sessao.etapa == "inicio":
        return iniciar_fluxo_booking(
            db=db,
            sessao=sessao,
        )

    if (
        sessao.etapa
        == "aguardando_servico"
    ):
        return (
            processar_escolha_servico_booking(
                db=db,
                sessao=sessao,
                mensagem=texto,
            )
        )

    if (
        sessao.etapa
        == "aguardando_profissional"
    ):
        return (
            processar_escolha_profissional_booking(
                db=db,
                sessao=sessao,
                mensagem=texto,
            )
        )

    if (
        sessao.etapa
        == "aguardando_data"
    ):
        return processar_data_booking(
            db=db,
            sessao=sessao,
            mensagem=texto,
        )

    if (
        sessao.etapa
        == "aguardando_horario"
    ):
        return (
            processar_escolha_horario_booking(
                db=db,
                sessao=sessao,
                mensagem=texto,
            )
        )

    if (
        sessao.etapa
        == "aguardando_nome"
    ):
        return processar_nome_booking(
            db=db,
            sessao=sessao,
            mensagem=texto,
        )

    if (
        sessao.etapa
        == "confirmacao"
    ):
        return processar_confirmacao_booking(
            db=db,
            sessao=sessao,
            mensagem=texto,
        )

    return montar_resposta_booking(
        sessao=sessao,
        mensagem=(
            "Sua conversa de agendamento "
            "esta em andamento."
        ),
    )


def interpretar_data_booking(
    valor: str,
) -> date | None:
    texto = normalizar_texto_booking(
        valor
    )

    # YYYY-MM-DD
    try:
        return datetime.strptime(
            texto,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        pass

    # DD/MM/YYYY
    try:
        return datetime.strptime(
            texto,
            "%d/%m/%Y",
        ).date()
    except ValueError:
        pass

    # DD/MM
    partes = texto.split("/")

    if len(partes) != 2:
        return None

    try:
        dia = int(partes[0])
        mes = int(partes[1])
    except ValueError:
        return None

    hoje = date.today()

    try:
        data_convertida = date(
            hoje.year,
            mes,
            dia,
        )
    except ValueError:
        return None

    if data_convertida < hoje:
        try:
            data_convertida = date(
                hoje.year + 1,
                mes,
                dia,
            )
        except ValueError:
            return None

    return data_convertida

def listar_horarios_booking(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
) -> list[str]:
    if (
        not sessao.servico
        or not sessao.profissional
        or not sessao.data
    ):
        return []

    servico = (
        db.query(
            models.ServicoBarbearia
        )
        .filter(
            models.ServicoBarbearia.barbearia_slug
            == sessao.barbearia_slug,

            models.ServicoBarbearia.nome
            == sessao.servico,
        )
        .first()
    )

    if not servico:
        return []

    resultado = (
        agendamento_service
        .obter_horarios_disponiveis(
            db=db,
            tenant_slug=sessao.barbearia_slug,
            data_agendamento=sessao.data.isoformat(),
            duracao_minutos=servico.duracao,
            profissional_nome=sessao.profissional,
        )
    )

    return list(
        resultado.get(
            "horarios_disponiveis",
            []
        )
    )


def processar_escolha_profissional_booking(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
    mensagem: str,
) -> dict:
    profissionais = listar_profissionais_booking(
        db=db,
        tenant_slug=sessao.barbearia_slug,
        servico_nome=sessao.servico or "",
    )

    escolhido = escolher_opcao_booking(
        mensagem,
        profissionais,
    )

    if not escolhido:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Nao encontrei esse profissional. "
                "Escolha uma das opcoes."
            ),
            opcoes=formatar_opcoes_booking(
                profissionais
            ),
        )

    atualizar_sessao(
        db=db,
        sessao=sessao,
        etapa="aguardando_data",
        profissional=escolhido.nome,
    )

    return montar_resposta_booking(
        sessao=sessao,
        mensagem=(
            f"Perfeito. Voce escolheu "
            f"{escolhido.nome}. "
            "Agora informe a data desejada. "
            "Voce pode responder, por exemplo, "
            "25/09 ou 25/09/2026."
        ),
    )


def processar_data_booking(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
    mensagem: str,
) -> dict:
    data_escolhida = interpretar_data_booking(
        mensagem
    )

    if not data_escolhida:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Nao consegui entender a data. "
                "Envie no formato DD/MM "
                "ou DD/MM/AAAA."
            ),
        )

    if data_escolhida < date.today():
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Essa data ja passou. "
                "Escolha uma data futura."
            ),
        )

    atualizar_sessao(
        db=db,
        sessao=sessao,
        etapa="aguardando_horario",
        data_agendamento=data_escolhida,
    )

    horarios = listar_horarios_booking(
        db=db,
        sessao=sessao,
    )

    if not horarios:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Nao encontrei horarios livres "
                "para essa data. "
                "Envie outra data."
            ),
        )

    opcoes = [
        f"{indice}. {horario}"
        for indice, horario
        in enumerate(
            horarios,
            start=1,
        )
    ]

    return montar_resposta_booking(
        sessao=sessao,
        mensagem=(
            "Encontrei estes horarios. "
            "Escolha respondendo com "
            "o numero ou com o horario."
        ),
        opcoes=opcoes,
    )


def processar_escolha_horario_booking(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
    mensagem: str,
) -> dict:
    horarios = listar_horarios_booking(
        db=db,
        sessao=sessao,
    )

    texto = normalizar_texto_booking(
        mensagem
    )

    escolhido = None

    if texto.isdigit():
        indice = int(texto) - 1

        if 0 <= indice < len(horarios):
            escolhido = horarios[indice]

    if (
        escolhido is None
        and texto in horarios
    ):
        escolhido = texto

    if not escolhido:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Esse horario nao esta disponivel. "
                "Escolha uma das opcoes atuais."
            ),
            opcoes=[
                f"{indice}. {horario}"
                for indice, horario
                in enumerate(
                    horarios,
                    start=1,
                )
            ],
        )

    atualizar_sessao(
        db=db,
        sessao=sessao,
        etapa="aguardando_nome",
        horario=escolhido,
    )

    return montar_resposta_booking(
        sessao=sessao,
        mensagem=(
            f"Horario {escolhido} selecionado. "
            "Agora me informe seu nome."
        ),
    )


def processar_nome_booking(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
    mensagem: str,
) -> dict:
    nome = normalizar_texto_booking(
        mensagem
    )

    if len(nome) < 2:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Informe um nome valido "
                "para concluir o agendamento."
            ),
        )

    atualizar_sessao(
        db=db,
        sessao=sessao,
        etapa="confirmacao",
        cliente_nome=nome,
    )

    data_formatada = (
        sessao.data.strftime(
            "%d/%m/%Y"
        )
        if sessao.data
        else "-"
    )

    return montar_resposta_booking(
        sessao=sessao,
        mensagem=(
            "Confira seu agendamento:\n"
            f"Nome: {sessao.cliente_nome}\n"
            f"Servico: {sessao.servico}\n"
            f"Profissional: {sessao.profissional}\n"
            f"Data: {data_formatada}\n"
            f"Horario: {sessao.horario}\n\n"
            "Responda CONFIRMAR para concluir "
            "ou CANCELAR para encerrar."
        ),
    )


def montar_ficha_agendamento_booking(
    sessao: models.SessaoBookingWhatsApp,
):
    if not all([
        sessao.cliente_nome,
        sessao.servico,
        sessao.profissional,
        sessao.data,
        sessao.horario,
        sessao.telefone_cliente,
    ]):
        raise HTTPException(
            status_code=409,
            detail=(
                "A sessao ainda nao possui "
                "todos os dados do agendamento."
            ),
        )

    return agendamento_service.FichaAgendamento(
        cliente_nome=sessao.cliente_nome,
        servico=sessao.servico,
        data=sessao.data.isoformat(),
        horario=sessao.horario,
        valor=0,
        profissional=sessao.profissional,
        telefone_cliente=sessao.telefone_cliente,
        aceita_lembrete_whatsapp=True,
        aceita_promocoes_whatsapp=False,
    )


def processar_confirmacao_booking(
    db: Session,
    sessao: models.SessaoBookingWhatsApp,
    mensagem: str,
) -> dict:
    texto = normalizar_texto_booking(
        mensagem
    ).lower()

    if texto in {
        "cancelar",
        "cancela",
        "cancelado",
    }:
        agora = agora_utc_naive()

        sessao.status = "cancelada"
        sessao.atualizado_em = agora

        db.commit()
        db.refresh(sessao)

        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Tudo certo. "
                "O agendamento foi cancelado "
                "antes da confirmacao."
            ),
        )

    if texto not in {
        "confirmar",
        "confirmo",
        "sim",
        "s",
    }:
        return montar_resposta_booking(
            sessao=sessao,
            mensagem=(
                "Para concluir, responda "
                "CONFIRMAR. "
                "Para desistir, responda CANCELAR."
            ),
        )

    ficha = montar_ficha_agendamento_booking(
        sessao
    )

    try:
        agendamento = (
            agendamento_service
            .criar_novo_agendamento(
                db=db,
                tenant_slug=sessao.barbearia_slug,
                dados=ficha,
            )
        )

    except HTTPException as erro:
        if erro.status_code != 409:
            raise

        atualizar_sessao(
            db=db,
            sessao=sessao,
            etapa="aguardando_horario",
            horario="",
        )

        horarios = listar_horarios_booking(
            db=db,
            sessao=sessao,
        )

        return {
            "sessao":
                serializar_sessao_booking(
                    sessao
                ),

            "etapa":
                sessao.etapa,

            "mensagem":
                (
                    "Esse horario acabou de ficar "
                    "indisponivel. "
                    "Escolha outro horario."
                ),

            "opcoes":
                [
                    f"{indice}. {horario}"
                    for indice, horario
                    in enumerate(
                        horarios,
                        start=1,
                    )
                ],

            "agendamento":
                None,
        }

    concluir_sessao(
        db=db,
        sessao=sessao,
    )

    return {
        "sessao":
            serializar_sessao_booking(
                sessao
            ),

        "etapa":
            sessao.etapa,

        "mensagem":
            (
                "Agendamento confirmado com sucesso."
            ),

        "opcoes":
            [],

        "agendamento":
            agendamento,
    }

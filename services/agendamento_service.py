from sqlalchemy.orm import Session
from fastapi import HTTPException
from repositories import agendamento_repository
import models
from pydantic import BaseModel
from datetime import datetime, timedelta, date

class FichaAgendamento(BaseModel):
    cliente_nome: str
    servico: str
    data: str  # ADICIONADO: Formato "YYYY-MM-DD"
    horario: str
    valor: float
    profissional: str 
    telefone_cliente: str

def criar_novo_agendamento(db: Session, tenant_slug: str, dados: FichaAgendamento):
    # 1. Validação de Regra de Negócio
    empresa = db.query(models.Barbearia).filter(models.Barbearia.slug == tenant_slug).first()
    if empresa and not empresa.plano_ativo:
        raise HTTPException(status_code=403, detail="Agenda temporariamente indisponível. Assinatura pendente.")

    # 2. O BLOQUEIO: Repassamos a data também para o repositório verificar corretamente
    conflito = agendamento_repository.verificar_disponibilidade_e_bloquear(
        db, tenant_slug, dados.profissional, dados.data, dados.horario
    )
    
    if conflito:
        raise HTTPException(status_code=409, detail="Este horário acabou de ser reservado por outra pessoa.")

    # 3. Preparação dos dados convertendo a string de data para objeto Date do Python
    data_formatada = datetime.strptime(dados.data, "%Y-%m-%d").date()

    novo_agendamento = models.Agendamento(
        barbearia_slug=tenant_slug,
        cliente_nome=dados.cliente_nome,
        servico=dados.servico,
        data=data_formatada, # SALVANDO A DATA AQUI
        horario=dados.horario,
        valor=dados.valor,
        profissional=dados.profissional,
        telefone_cliente=dados.telefone_cliente
    )

    # 4. Salva no banco e solta o Lock
    return agendamento_repository.salvar_agendamento(db, novo_agendamento)


# ==========================================
# MOTOR DE HORÁRIOS DISPONÍVEIS
# ==========================================

def obter_horarios_disponiveis(db: Session, tenant_slug: str, data_str: str, duracao_minutos: int, profissional: str):
    # 1. Busca configurações (Model ajustado)
    config = db.query(models.ConfiguracaoAgenda).filter(
        models.ConfiguracaoAgenda.barbearia_slug == tenant_slug
    ).first()
    
    abertura = config.hora_abertura if config else 9
    fechamento = config.hora_fechamento if config else 18

    # 2. Busca agendamentos DAQUELE DIA específico
    data_alvo = datetime.strptime(data_str, "%Y-%m-%d").date()
    agendamentos = db.query(models.Agendamento).filter(
        models.Agendamento.barbearia_slug == tenant_slug,
        models.Agendamento.profissional == profissional,
        models.Agendamento.data == data_alvo  # O FILTRO SALVADOR DA DATA
    ).all()
    
    # 3. Calcula os intervalos já ocupados
    intervalos_ocupados = []
    for agendamento in agendamentos:
        # Model ajustado para 'Servico'
        servico = db.query(models.ServicoBarbearia).filter(
            models.Servico.barbearia_slug == tenant_slug, 
            models.Servico.nome == agendamento.servico
        ).first()
        
        duracao_ocupada = servico.duracao if servico else 30 
        inicio_existente = datetime.strptime(agendamento.horario, "%H:%M")
        fim_existente = inicio_existente + timedelta(minutes=duracao_ocupada)
        intervalos_ocupados.append((inicio_existente, fim_existente))

    # 4. Motor de Fatiamento (A sua lógica matemática excelente!)
    hora_atual = datetime.strptime(f"{abertura}:00", "%H:%M")
    hora_fim = datetime.strptime(f"{fechamento}:00", "%H:%M")
    passo_grade = timedelta(minutes=duracao_minutos)
    horarios_livres = []
    
    while (hora_atual + timedelta(minutes=duracao_minutos)) <= hora_fim:
        inicio_proposto = hora_atual
        fim_proposto = hora_atual + timedelta(minutes=duracao_minutos)
        colisao = False
        
        for inicio_existente, fim_existente in intervalos_ocupados:
            if max(inicio_proposto, inicio_existente) < min(fim_proposto, fim_existente):
                colisao = True
                break
                
        if not colisao: 
            horarios_livres.append(hora_atual.strftime("%H:%M"))
            
        hora_atual += passo_grade
        
    return {"horarios_disponiveis": horarios_livres}
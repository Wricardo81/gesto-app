from sqlalchemy.orm import Session
from fastapi import HTTPException
from repositories import agendamento_repository
import models
from pydantic import BaseModel
from datetime import datetime, timedelta

# Trazemos o seu Pydantic Model para cá (pode criar um arquivo schemas.py no futuro para organizá-los)
class FichaAgendamento(BaseModel):
    cliente_nome: str
    servico: str
    horario: str
    valor: float
    profissional: str 
    telefone_cliente: str

def criar_novo_agendamento(db: Session, tenant_slug: str, dados: FichaAgendamento):
    # 1. Validação de Regra de Negócio: O cliente (barbearia) pagou a assinatura?
    empresa = db.query(models.Barbearia).filter(models.Barbearia.slug == tenant_slug).first()
    if empresa and not empresa.plano_ativo:
        raise HTTPException(status_code=403, detail="Agenda temporariamente indisponível. Assinatura pendente.")

    # 2. O BLOQUEIO: Verificamos se o horário já está tomado (com o Lock ativado)
    conflito = agendamento_repository.verificar_disponibilidade_e_bloquear(
        db, tenant_slug, dados.profissional, dados.horario
    )
    
    if conflito:
        # Se outra pessoa pegou o horário milissegundos antes, a transação aborta aqui
        # e o banco libera o Lock automaticamente sem salvar nada.
        raise HTTPException(status_code=409, detail="Este horário acabou de ser reservado por outra pessoa.")

    # 3. Se passou pelo bloqueio, o caminho está livre. Preparamos os dados.
    novo_agendamento = models.Agendamento(
        barbearia_slug=tenant_slug,
        cliente_nome=dados.cliente_nome,
        servico=dados.servico,
        horario=dados.horario,
        valor=dados.valor,
        profissional=dados.profissional,
        telefone_cliente=dados.telefone_cliente
    )

    # 4. Salva no banco (o db.commit dentro dessa função é o que solta o Lock!)
    return agendamento_repository.salvar_agendamento(db, novo_agendamento)


#horarios disponiveis

def obter_horarios_disponiveis(db: Session, tenant_slug: str, duracao_minutos: int, profissional: str):
    # 1. Busca configurações da barbearia (Abertura e Fechamento)
    config = db.query(models.ConfiguracaoAgenda).filter(
        models.ConfiguracaoAgenda.barbearia_slug == tenant_slug
    ).first()
    
    abertura = config.hora_abertura if config else 9
    fechamento = config.hora_fechamento if config else 18

    # 2. Busca os agendamentos já existentes para aquele profissional
    agendamentos = db.query(models.Agendamento).filter(
        models.Agendamento.barbearia_slug == tenant_slug,
        models.Agendamento.profissional == profissional
    ).all()
    
    # 3. Calcula os intervalos já ocupados
    intervalos_ocupados = []
    for agendamento in agendamentos:
        servico = db.query(models.ServicoBarbearia).filter(
            models.ServicoBarbearia.barbearia_slug == tenant_slug, 
            models.ServicoBarbearia.nome == agendamento.servico
        ).first()
        
        duracao_ocupada = servico.duracao if servico else 30 
        inicio_existente = datetime.strptime(agendamento.horario, "%H:%M")
        fim_existente = inicio_existente + timedelta(minutes=duracao_ocupada)
        intervalos_ocupados.append((inicio_existente, fim_existente))

    # 4. Motor de Fatiamento (Lógica central)
    hora_atual = datetime.strptime(f"{abertura}:00", "%H:%M")
    hora_fim = datetime.strptime(f"{fechamento}:00", "%H:%M")
    passo_grade = timedelta(minutes=duracao_minutos)
    horarios_livres = []
    
    while (hora_atual + timedelta(minutes=duracao_minutos)) <= hora_fim:
        inicio_proposto = hora_atual
        fim_proposto = hora_atual + timedelta(minutes=duracao_minutos)
        colisao = False
        
        for inicio_existente, fim_existente in intervalos_ocupados:
            # Verifica se os períodos se sobrepõem
            if max(inicio_proposto, inicio_existente) < min(fim_proposto, fim_existente):
                colisao = True
                break
                
        if not colisao: 
            horarios_livres.append(hora_atual.strftime("%H:%M"))
            
        hora_atual += passo_grade
        
    return {"horarios_disponiveis": horarios_livres}
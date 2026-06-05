from sqlalchemy.orm import Session
import models

def verificar_disponibilidade_e_bloquear(db: Session, tenant_slug: str, profissional_nome: str, horario: str):
    """
    Tenta encontrar um agendamento existente para aquele profissional no mesmo horário.
    A cláusula .with_for_update() avisa ao PostgreSQL para colocar um 'cadeado' (Lock) 
    nessas linhas até que a transação atual faça o db.commit().
    """
    # Buscamos se já existe alguém agendado nesse exato horário para esse profissional
    conflito = db.query(models.Agendamento).filter(
        models.Agendamento.barbearia_slug == tenant_slug,
        models.Agendamento.profissional == profissional_nome,
        models.Agendamento.horario == horario
    ).with_for_update().first() 
    
    return conflito

def salvar_agendamento(db: Session, agendamento: models.Agendamento):
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento) # Atualiza o objeto com o ID gerado pelo banco
    return agendamento
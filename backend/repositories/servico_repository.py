from sqlalchemy.orm import Session
import models

def criar_servico(db: Session, servico: models.ServicoBarbearia):
    db.add(servico)
    db.commit()
    db.refresh(servico)
    return servico

def buscar_servicos_por_tenant(db: Session, tenant_slug: str):
    return db.query(models.ServicoBarbearia).filter(
        models.ServicoBarbearia.barbearia_slug == tenant_slug
    ).all()

def remover_servico(db: Session, servico_id: int, tenant_slug: str):
    alvo = db.query(models.ServicoBarbearia).filter(
        models.ServicoBarbearia.id == servico_id, 
        models.ServicoBarbearia.barbearia_slug == tenant_slug
    ).first()
    
    if alvo:
        db.delete(alvo)
        db.commit()
        return True
    return False
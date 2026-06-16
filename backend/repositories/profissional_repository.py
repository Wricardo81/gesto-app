from sqlalchemy.orm import Session
import models

def buscar_profissionais_por_tenant(db: Session, tenant_slug: str):
    """Apenas executa a query no banco e retorna os dados brutos."""
    return db.query(models.Profissional).filter(
        models.Profissional.barbearia_slug == tenant_slug
    ).all()

    # Adicione no final do arquivo existente:

def criar_profissional(db: Session, profissional: models.Profissional):
    db.add(profissional)
    db.commit()
    db.refresh(profissional)
    return profissional

def remover_profissional(db: Session, prof_id: int, tenant_slug: str):
    alvo = db.query(models.Profissional).filter(
        models.Profissional.id == prof_id, 
        models.Profissional.barbearia_slug == tenant_slug
    ).first()
    
    if alvo:
        db.delete(alvo)
        db.commit()
        return True
    return False
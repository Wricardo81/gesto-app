from sqlalchemy.orm import Session
import models

def obter_configuracao(db: Session, tenant_slug: str):
    return db.query(models.ConfiguracaoAgenda).filter(
        models.ConfiguracaoAgenda.barbearia_slug == tenant_slug
    ).first()

def salvar_configuracao(db: Session, configuracao: models.ConfiguracaoAgenda):
    db.add(configuracao)
    db.commit()
    db.refresh(configuracao)
    return configuracao
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessaoLocal
import models
from security import verificar_senha, criar_token_acesso

router = APIRouter()

def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()

class RequisicaoLogin(BaseModel):
    email: str
    senha: str

@router.post("/api/auth/login")
def fazer_login(
    credenciais: RequisicaoLogin,
    db: Session = Depends(get_db),
):
    usuario = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.email == credenciais.email)
        .first()
    )

    if (
        not usuario
        or not usuario.senha_hash
        or not verificar_senha(credenciais.senha, usuario.senha_hash)
    ):
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha incorretos.",
        )

    token = criar_token_acesso(
    {
        "sub": usuario.slug,
        "role": "tenant_admin",
    }
)

    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_slug": usuario.slug,
    }
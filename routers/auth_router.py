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
def fazer_login(credenciais: RequisicaoLogin, db: Session = Depends(get_db)):
    print("\n====== RAIO-X DO BANCO DE DADOS ======")
    usuario = db.query(models.Barbearia).filter(models.Barbearia.email == credenciais.email).first()
    
    if not usuario:
        print("DIAGNÓSTICO: O e-mail não existe no banco de dados atual!")
        print("======================================\n")
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
        
    print(f"Usuário encontrado: {usuario.nome} (Slug: {usuario.slug})")
    print(f"Senha que está salva no banco: {usuario.senha_hash}")
    
    # Tentamos validar, e se o hash estiver quebrado, capturamos o erro
    try:
        senha_valida = verificar_senha(credenciais.senha, usuario.senha_hash)
        print(f"A matemática do Bcrypt aprovou a senha? {senha_valida}")
    except Exception as e:
        print(f"ERRO CRÍTICO NO BCRYPT: {str(e)}")
        senha_valida = False

    print("======================================\n")

    if not senha_valida:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
        
    token = criar_token_acesso({"sub": usuario.slug})
    
    return {
        "access_token": token, 
        "token_type": "bearer",
        "tenant_slug": usuario.slug
    }
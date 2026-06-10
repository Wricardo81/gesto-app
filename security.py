from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# A chave mestra do seu backend.
SECRET_KEY = "chave_super_secreta_engenharia_de_bits"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # O token dura 7 dias

# Configuração do motor de Hash (Bcrypt)
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__ident="2b" # ISSO AQUI RESOLVE O BUG DAS 72 BYTES!
)

def gerar_hash_senha(senha: str) -> str:
    """Recebe 'senha123' e devolve um código criptografado ilegível."""
    return pwd_context.hash(senha)

def verificar_senha(senha_plana: str, senha_hasheada: str) -> bool:
    """Compara a senha digitada com o hash salvo no banco."""
    return pwd_context.verify(senha_plana, senha_hasheada)

def criar_token_acesso(dados: dict):
    """Cria o crachá VIP (JWT) com os dados do usuário e data de validade."""
    a_criptografar = dados.copy()
    expiracao = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    a_criptografar.update({"exp": expiracao})
    
    # Gera a string final do Token
    token_jwt = jwt.encode(a_criptografar, SECRET_KEY, algorithm=ALGORITHM)
    return token_jwt

# ==========================================
# O SEGURANÇA DA PORTA
# ==========================================
esquema_seguranca = HTTPBearer()

def obter_usuario_logado(credenciais: HTTPAuthorizationCredentials = Depends(esquema_seguranca)):
    """
    Ele intercepta a requisição, pega o Token,
    tenta abrir com a SECRET_KEY e devolve quem é o dono.
    """
    token = credenciais.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_slug: str = payload.get("sub")
        if tenant_slug is None:
            raise HTTPException(status_code=401, detail="Token inválido. Refaça o login.")
        return tenant_slug
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Seu acesso expirou. Refaça o login.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token fraudulento ou inválido.")
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

# A chave mestra do seu backend. Em produção, isso DEVE vir do os.getenv() (como a chave do Stripe)
# Para testes locais, vamos usar uma string fixa.
SECRET_KEY = "chave_super_secreta_engenharia_de_bits"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # O token dura 7 dias

# Configuração do motor de Hash (Bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
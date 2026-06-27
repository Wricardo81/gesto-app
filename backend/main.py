from fastapi import FastAPI, HTTPException, Request
from database import engine, Base, SessaoLocal
import models
from fastapi.middleware.cors import CORSMiddleware
import os
import stripe
from settings import settings
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from routers import aviso_router

# Importando os roteadores refatorados
from routers import profissional_router
from routers import agendamento_router
from routers import servico_router
from routers import configuracao_router
from routers import auth_router
from routers import saas_router
from routers import upload_router
from routers import cliente_router
from routers import bloqueio_router
from routers import agenda_router
from routers import suporte_router
from routers import assinatura_stripe_router
from routers import mercado_pago_router

app = FastAPI()


origins_permitidas = [
    origem.strip()
    for origem in settings.cors_origins.split(",")
    if origem.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_permitidas,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"

UPLOADS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIR)),
    name="uploads",
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "Gesto App",
        "environment": settings.app_env,
    }


# Configuração do Stripe puxando do cofre seguro
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Registrando as rotas isoladas
app.include_router(profissional_router.router)
app.include_router(agendamento_router.router)
app.include_router(servico_router.router)
app.include_router(configuracao_router.router)
app.include_router(auth_router.router)
app.include_router(saas_router.router)
app.include_router(upload_router.router)
app.include_router(cliente_router.router)
app.include_router(bloqueio_router.router)
app.include_router(agenda_router.router)
app.include_router(aviso_router.router)
app.include_router(suporte_router.router)
app.include_router(assinatura_stripe_router.router)
app.include_router(mercado_pago_router.router)

# ==========================================
# MÓDULO MESTRE: PAINEL SAAS & STRIPE
# ==========================================

@app.post("/api/saas/{tenant_slug}/criar-checkout")
def criar_checkout_stripe(tenant_slug: str):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': f'Assinatura Mensal Gesto — Sistema de Agendamento',
                    },
                    'unit_amount': 9900, 
                },
                'quantity': 1,
            }],
            mode='payment', 
            success_url=f"https://gesto-app.netlify.app/admin.html?tenant={tenant_slug}",
            cancel_url=f"https://gesto-app.netlify.app/admin.html?tenant={tenant_slug}",
            metadata={"tenant_slug": tenant_slug}
        )
        return {"checkout_url": session.url}
    except Exception as e:
        print(f"Erro no Stripe: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# MÓDULO DE SEGURANÇA
# ==========================================
@app.get("/api/{tenant_slug}/verificar-acesso")
def verificar_status_inquilino(tenant_slug: str):
    db = SessaoLocal()
    cliente = db.query(models.Barbearia).filter(models.Barbearia.slug == tenant_slug).first()
    db.close()
    
    if not cliente: 
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")
        
    if not cliente.plano_ativo: 
        raise HTTPException(status_code=403, detail="Assinatura suspensa")
        
    return {"status": "Liberado"}
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from database import engine, Base, SessaoLocal
import models
from fastapi.middleware.cors import CORSMiddleware
import os
import stripe

# Importando os roteadores refatorados
from routers import profissional_router
from routers import agendamento_router
from routers import servico_router
from routers import configuracao_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Configuração do Stripe puxando do cofre seguro
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Registrando as rotas isoladas
app.include_router(profissional_router.router)
app.include_router(agendamento_router.router)
app.include_router(servico_router.router)
app.include_router(configuracao_router.router)

# ==========================================
# MÓDULO MESTRE: PAINEL SAAS & STRIPE
# ==========================================
class NovaBarbearia(BaseModel):
    nome: str
    slug: str

@app.post("/api/saas/barbearias")
def registrar_nova_barbearia(dados: NovaBarbearia):
    db = SessaoLocal()
    existe = db.query(models.Barbearia).filter(models.Barbearia.slug == dados.slug).first()
    if existe:
        db.close()
        raise HTTPException(status_code=400, detail="Esse link já está em uso por outro cliente.")
        
    nova = models.Barbearia(nome=dados.nome, slug=dados.slug)
    db.add(nova)
    db.commit()
    db.close()
    return {"status": "Sucesso", "mensagem": f"Inquilino {dados.nome} ativado!"}

@app.get("/api/saas/barbearias")
def listar_clientes_do_software():
    db = SessaoLocal()
    clientes = db.query(models.Barbearia).all()
    db.close()
    return clientes

@app.put("/api/saas/barbearias/{barbearia_id}/status")
def alterar_status_assinatura(barbearia_id: int):
    db = SessaoLocal()
    cliente = db.query(models.Barbearia).filter(models.Barbearia.id == barbearia_id).first()
    if cliente:
        cliente.plano_ativo = not cliente.plano_ativo 
        db.commit()
        status_atual = "Ativo" if cliente.plano_ativo else "Bloqueado"
        db.close()
        return {"mensagem": f"Plano do cliente alterado para: {status_atual}"}
    db.close()
    return {"mensagem": "Cliente não encontrado."}

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

@app.post("/api/webhooks/stripe")
async def webhook_stripe(request: Request):
    try:
        payload = await request.json()
        
        if payload.get("type") == "checkout.session.completed":
            session = payload["data"]["object"]
            tenant_slug = session.get("metadata", {}).get("tenant_slug")
            
            if tenant_slug:
                db = SessaoLocal()
                cliente = db.query(models.Barbearia).filter(models.Barbearia.slug == tenant_slug).first()
                if cliente:
                    cliente.plano_ativo = True
                    db.commit()
                db.close()
                print(f"SUCESSO: Inquilino {tenant_slug} desbloqueado pelo Webhook!")

        return {"status": "recebido com sucesso"}
    
    except Exception as e:
        print(f"ERRO NO WEBHOOK: {str(e)}")
        raise HTTPException(status_code=400, detail="Erro ao processar webhook")

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
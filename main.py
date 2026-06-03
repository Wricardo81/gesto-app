from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from database import engine, Base, SessaoLocal
import models
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
import os
import stripe

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Configuração do Stripe puxando do cofre seguro do Render
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

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

# NOVO: ROTA QUE CRIA O LINK DE PAGAMENTO DA ASSINATURA
# NOVO: ROTA QUE CRIA O LINK DE PAGAMENTO DA ASSINATURA
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
                    'unit_amount': 9900, # R$ 99,00
                },
                'quantity': 1,
            }],
            mode='payment', 
            # CORREÇÃO: Usando o SEU link real da Netlify!
            success_url=f"https://gesto-app.netlify.app/admin.html?tenant={tenant_slug}",
            cancel_url=f"https://gesto-app.netlify.app/admin.html?tenant={tenant_slug}",
            metadata={"tenant_slug": tenant_slug}
        )
        return {"checkout_url": session.url}
    except Exception as e:
        print(f"Erro no Stripe: {str(e)}") # Vai ajudar a debugar se der erro
        raise HTTPException(status_code=500, detail=str(e))

# NOVO: O WEBHOOK (O OUVINTE SILENCIOSO QUE RECEBE O AVISO DE PAGAMENTO DO STRIPE)
# NOVO: O WEBHOOK BLINDADO (LEITURA DIRETA DE JSON)
@app.post("/api/webhooks/stripe")
async def webhook_stripe(request: Request):
    try:
        # Lemos a mensagem da Stripe de forma direta e simples
        payload = await request.json()
        
        # Se a Stripe gritar "O Checkout foi concluído!"
        if payload.get("type") == "checkout.session.completed":
            session = payload["data"]["object"]
            # Pegamos o slug que escondemos lá na criação do link
            tenant_slug = session.get("metadata", {}).get("tenant_slug")
            
            if tenant_slug:
                # O Python abre o banco e libera o cliente
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
# MÓDULO DE AGENDAMENTOS (ISOLADO POR INQUILINO)
# ==========================================
class FichaAgendamento(BaseModel):
    cliente_nome: str
    servico: str
    horario: str
    valor: float
    profissional: str 
    telefone_cliente: str # NOVO CAMPO OBRIGATÓRIO

@app.post("/api/{tenant_slug}/agendar")
def criar_agendamento(tenant_slug: str, dados_recebidos: FichaAgendamento):
    db = SessaoLocal()
    empresa = db.query(models.Barbearia).filter(models.Barbearia.slug == tenant_slug).first()
    if empresa and not empresa.plano_ativo:
        db.close()
        raise HTTPException(status_code=403, detail="Agenda temporariamente indisponível.")

    novo_agendamento = models.Agendamento(
        barbearia_slug=tenant_slug,
        cliente_nome=dados_recebidos.cliente_nome,
        servico=dados_recebidos.servico,
        horario=dados_recebidos.horario,
        valor=dados_recebidos.valor,
        profissional=dados_recebidos.profissional,
        telefone_cliente=dados_recebidos.telefone_cliente # SALVANDO O NÚMERO AQUI!
    )
    db.add(novo_agendamento)
    db.commit()
    db.close()
    return {"status": "Sucesso", "mensagem": f"Agendamento confirmado!"}

@app.get("/api/{tenant_slug}/agendamentos")
def listar_agendamentos_da_empresa(tenant_slug: str):
    db = SessaoLocal()
    agendamentos = db.query(models.Agendamento).filter(models.Agendamento.barbearia_slug == tenant_slug).all()
    db.close()
    return agendamentos

@app.delete("/api/{tenant_slug}/agendamentos/{agendamento_id}")
def cancelar_agendamento(tenant_slug: str, agendamento_id: int):
    db = SessaoLocal()
    alvo = db.query(models.Agendamento).filter(
        models.Agendamento.id == agendamento_id,
        models.Agendamento.barbearia_slug == tenant_slug
    ).first()
    if alvo is not None:
        db.delete(alvo)
        db.commit() 
        db.close()
        return {"mensagem": "Agendamento cancelado!"}
    db.close()
    return {"mensagem": "Erro: Agendamento não encontrado."}

@app.get("/api/{tenant_slug}/horarios/{duracao_minutos}/{profissional}")
def obter_horarios_fatiados(tenant_slug: str, duracao_minutos: int, profissional: str): # Correção do 'ss' aqui!
    db = SessaoLocal()
    config = db.query(models.ConfiguracaoAgenda).filter(models.ConfiguracaoAgenda.barbearia_slug == tenant_slug).first()
    abertura = 9; fechamento = 18
    if config is not None:
        abertura = config.hora_abertura; fechamento = config.hora_fechamento

    agendamentos_do_barbeiro = db.query(models.Agendamento).filter(
        models.Agendamento.barbearia_slug == tenant_slug,
        models.Agendamento.profissional == profissional # Correção do 'ss' aqui também!
    ).all()
    
    intervalos_ocupados = []
    for agendamento in agendamentos_do_barbeiro:
        servico = db.query(models.ServicoBarbearia).filter(models.ServicoBarbearia.barbearia_slug == tenant_slug, models.ServicoBarbearia.nome == agendamento.servico).first()
        duracao_ocupada = servico.duracao if servico else 30 
        inicio_existente = datetime.strptime(agendamento.horario, "%H:%M")
        fim_existente = inicio_existente + timedelta(minutes=duracao_ocupada)
        intervalos_ocupados.append((inicio_existente, fim_existente))
    db.close()

    hora_atual = datetime.strptime(f"{abertura}:00", "%H:%M")
    hora_fim = datetime.strptime(f"{fechamento}:00", "%H:%M")
    passo_grade = timedelta(minutes=duracao_minutos)
    horarios_livres = []
    while (hora_atual + timedelta(minutes=duracao_minutos)) <= hora_fim:
        inicio_proposto = hora_atual; fim_proposto = hora_atual + timedelta(minutes=duracao_minutos)
        colisao = False
        for inicio_existente, fim_existente in intervalos_ocupados:
            if max(inicio_proposto, inicio_existente) < min(fim_proposto, fim_existente):
                colisao = True; break
        if not colisao: horarios_livres.append(hora_atual.strftime("%H:%M"))
        hora_atual += passo_grade
    return {"horarios_disponiveis": horarios_livres}

# ==========================================
# MÓDULO DE SERVIÇOS
# ==========================================
class NovoServico(BaseModel):
    nome: str
    preco: float
    duracao: int 

@app.post("/api/{tenant_slug}/servicos")
def cadastrar_servico(tenant_slug: str, dados: NovoServico):
    db = SessaoLocal()
    novo_servico = models.ServicoBarbearia(barbearia_slug=tenant_slug, nome=dados.nome, preco=dados.preco, duracao=dados.duracao)
    db.add(novo_servico)
    db.commit()
    db.close()
    return {"mensagem": "Serviço cadastrado!"}

@app.get("/api/{tenant_slug}/servicos")
def listar_servicos(tenant_slug: str):
    db = SessaoLocal()
    servicos = db.query(models.ServicoBarbearia).filter(models.ServicoBarbearia.barbearia_slug == tenant_slug).all()
    db.close()
    return servicos

@app.delete("/api/{tenant_slug}/servicos/{servico_id}")
def remover_servico(tenant_slug: str, servico_id: int):
    db = SessaoLocal()
    alvo = db.query(models.ServicoBarbearia).filter(models.ServicoBarbearia.id == servico_id, models.ServicoBarbearia.barbearia_slug == tenant_slug).first()
    if alvo is not None:
        db.delete(alvo)
        db.commit()
    db.close()
    return {"mensagem": "Serviço removido!"}

# ==========================================
# MÓDULO DE CONFIGURAÇÃO 
# ==========================================
class NovaConfiguracao(BaseModel):
    abertura: int; fechamento: int; cor_tema: str; 
    cor_fundo: str; endereco: str; logo_url: str; instrucoes: str

@app.post("/api/{tenant_slug}/configuracoes")
def salvar_configuracoes(tenant_slug: str, dados: NovaConfiguracao):
    db = SessaoLocal()
    config_atual = db.query(models.ConfiguracaoAgenda).filter(models.ConfiguracaoAgenda.barbearia_slug == tenant_slug).first()
    
    if config_atual is None:
        nova = models.ConfiguracaoAgenda(
            barbearia_slug=tenant_slug, hora_abertura=dados.abertura, hora_fechamento=dados.fechamento, 
            cor_tema=dados.cor_tema, cor_fundo=dados.cor_fundo, endereco=dados.endereco, 
            logo_url=dados.logo_url, instrucoes=dados.instrucoes
        )
        db.add(nova)
    else:
        config_atual.hora_abertura = dados.abertura; config_atual.hora_fechamento = dados.fechamento; 
        config_atual.cor_tema = dados.cor_tema; config_atual.cor_fundo = dados.cor_fundo;
        config_atual.endereco = dados.endereco; config_atual.logo_url = dados.logo_url;
        config_atual.instrucoes = dados.instrucoes
    db.commit(); db.close()
    return {"mensagem": "Configurações atualizadas!"}

@app.get("/api/{tenant_slug}/configuracoes")
def ler_configuracoes(tenant_slug: str):
    db = SessaoLocal()
    config_atual = db.query(models.ConfiguracaoAgenda).filter(models.ConfiguracaoAgenda.barbearia_slug == tenant_slug).first()
    db.close()
    if config_atual is None: 
        return {"abertura": 9, "fechamento": 18, "cor_tema": "#f59e0b", "cor_fundo": "#0f172a", "endereco": "", "logo_url": "", "instrucoes": ""}
    return {
        "abertura": config_atual.hora_abertura, "fechamento": config_atual.hora_fechamento, 
        "cor_tema": config_atual.cor_tema, "cor_fundo": config_atual.cor_fundo,
        "endereco": config_atual.endereco, "logo_url": config_atual.logo_url,
        "instrucoes": config_atual.instrucoes
    }

# ==========================================
# MÓDULO DE PROFISSIONAIS (EQUIPE)
# ==========================================
class NovoProfissional(BaseModel):
    nome: str

@app.post("/api/{tenant_slug}/profissionais")
def cadastrar_profissional(tenant_slug: str, dados: NovoProfissional):
    db = SessaoLocal()
    novo_prof = models.Profissional(barbearia_slug=tenant_slug, nome=dados.nome)
    db.add(novo_prof)
    db.commit(); db.close()
    return {"mensagem": "Profissional adicionado!"}

@app.get("/api/{tenant_slug}/profissionais")
def listar_profissionais(tenant_slug: str):
    db = SessaoLocal()
    equipe = db.query(models.Profissional).filter(models.Profissional.barbearia_slug == tenant_slug).all()
    db.close()
    return equipe

@app.delete("/api/{tenant_slug}/profissionais/{prof_id}")
def remover_profissional(tenant_slug: str, prof_id: int):
    db = SessaoLocal()
    alvo = db.query(models.Profissional).filter(models.Profissional.id == prof_id, models.Profissional.barbearia_slug == tenant_slug).first()
    if alvo is not None:
        db.delete(alvo)
        db.commit()
    db.close()
    return {"mensagem": "Profissional removido."}

# ==========================================
# MÓDULO DE SEGURANÇA (VERIFICAÇÃO DE ASSINATURA)
# ==========================================
@app.get("/api/{tenant_slug}/verificar-acesso")
def verificar_status_inquilino(tenant_slug: str):
    db = SessaoLocal()
    cliente = db.query(models.Barbearia).filter(models.Barbearia.slug == tenant_slug).first()
    db.close()
    
    if not cliente: 
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")
        
    # CORREÇÃO CRUCIAL AQUI: plano_ativo
    if not cliente.plano_ativo: 
        raise HTTPException(status_code=403, detail="Assinatura suspensa")
        
    return {"status": "Liberado"}
    # Patch de reinicialização para forçar a recriação das tabelas no PostgreSQL
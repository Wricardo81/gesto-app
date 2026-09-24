# Executor da Outbox WhatsApp no Render

## Objetivo

Executar periodicamente a fila duravel de mensagens WhatsApp sem
acoplar retries ao processo HTTP do FastAPI.

## Arquitetura

Webhook Meta -> Booking Assistant -> Outbox PostgreSQL

Render Cron Job -> executar_outbox_whatsapp.py -> Outbox PostgreSQL

## Configuracao

Servico: gesto-app-whatsapp-outbox
Tipo: Render Cron Job
Runtime: Python
Diretorio raiz: backend

Build:
pip install -r requirements.txt

Comando:
python scripts/executar_outbox_whatsapp.py --limite 50

Frequencia:
uma vez por minuto

Expressao cron:
* * * * *

## Contrato operacional

healthy:
- exit code 0
- lote vazio ou lote processado sem falhas

partial:
- exit code 0
- uma ou mais mensagens falharam
- retry e backoff permanecem sob responsabilidade da Outbox

fatal:
- exit code 2
- configuracao invalida
- falha estrutural
- falha fatal de infraestrutura

## Banco

O Cron Job precisa receber DATABASE_URL pelo ambiente do Render.

O valor de DATABASE_URL nao deve ser salvo no Git.

## Transporte atual

WHATSAPP_TRANSPORT_MODE=fake

Nenhum access token Meta deve ser configurado nesta fase.

## Concorrencia

A Outbox usa claim PostgreSQL com FOR UPDATE SKIP LOCKED.

Claims abandonados podem ser recuperados depois da expiracao.

Isso nao garante exactly-once absoluto no provedor remoto.

## Backoff

Tentativa 1: 30 segundos
Tentativa 2: 120 segundos
Tentativa 3: 300 segundos
Tentativa 4: 900 segundos
Tentativa 5: 3600 segundos

Com execucao uma vez por minuto, uma mensagem volta a ser considerada
no primeiro ciclo posterior a proxima_tentativa_em.

## Ainda nao ativar

- Cron Job real no Render
- access token Meta
- APP_SECRET real
- WHATSAPP_TRANSPORT_MODE=meta
- envio WhatsApp real

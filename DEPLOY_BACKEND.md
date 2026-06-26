# Deploy do Backend — Gesto App

## Serviço

Backend FastAPI.

## Diretório raiz do backend

backend

## Comando de instalação

pip install -r requirements.txt

## Comando de start em produção

uvicorn main:app --host 0.0.0.0 --port $PORT

## Health check

/health

## Variáveis de ambiente obrigatórias

DATABASE_URL=
JWT_SECRET_KEY=
CORS_ORIGINS=
BACKEND_PUBLIC_URL=
FRONTEND_PUBLIC_URL=
APP_ENV=production

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

MERCADO_PAGO_ACCESS_TOKEN=
MERCADO_PAGO_WEBHOOK_SECRET=
MERCADO_PAGO_NOTIFICATION_URL=

TRIAL_DIAS_PADRAO=7
TRIAL_LIMITE_AGENDAMENTOS=30

## Observações

- Nunca enviar backend/.env para o GitHub.
- Em produção, usar HTTPS.
- Em produção, CORS_ORIGINS deve apontar para a URL real do frontend.
- Em produção, BACKEND_PUBLIC_URL deve apontar para a URL pública da API.
- Em produção, FRONTEND_PUBLIC_URL deve apontar para a URL pública do frontend.
- Webhooks de Stripe e Mercado Pago devem apontar para a URL pública do backend.

## CORS em produção

Quando o frontend estiver publicado, atualizar CORS_ORIGINS no backend.

Exemplo:

CORS_ORIGINS=https://app.seudominio.com,https://seudominio.com

Se usar subdomínio para API:

BACKEND_PUBLIC_URL=https://api.seudominio.com
FRONTEND_PUBLIC_URL=https://app.seudominio.com
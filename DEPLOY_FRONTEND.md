# Deploy do Frontend — Gesto App

## Tipo de frontend

Frontend estático com HTML, CSS e JavaScript puro.

## Pasta pública

frontend

## Arquivo principal

index.html

## Páginas principais

- index.html
- saas.html
- admin.html
- agendamento.html
- meus-agendamentos.html

## Configuração da API

A URL da API é definida em:

frontend/js/config.js

Local:

API_BASE_URL=http://127.0.0.1:8000

Produção:

API_BASE_URL=https://api.seudominio.com

## Antes do deploy

Atualizar em frontend/js/config.js:

API_BASE_URL=https://api.seudominio.com
FRONTEND_BASE_URL=https://app.seudominio.com
AMBIENTE=production

## Hospedagem recomendada

Pode ser publicado em:

- Netlify
- Vercel
- Render Static Site
- Cloudflare Pages
- Hospedagem comum com arquivos estáticos

## Atenção

- Não colocar chaves secretas no frontend.
- Stripe Secret Key e Mercado Pago Access Token ficam somente no backend.
- O frontend pode conter apenas URLs públicas.
- O backend precisa liberar o domínio do frontend em CORS_ORIGINS.

## URL pública atual do frontend

https://pontocomum.netlify.app
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


## Interlock de seguranca do executor

O executor possui uma barreira adicional contra ativacao acidental
do transporte real da Meta.

Comportamento:

- `WHATSAPP_TRANSPORT_MODE=fake`: execucao permitida normalmente.
- `WHATSAPP_TRANSPORT_MODE=meta`: execucao bloqueada por padrao.
- `WHATSAPP_TRANSPORT_MODE=meta` com `--permitir-meta`: somente esta
  combinacao permite que o executor tente usar o transporte Meta.

O `render.yaml` NAO deve conter `--permitir-meta` enquanto a integracao
real nao estiver formalmente ativada.

A troca isolada da variavel para `meta` nao deve ser suficiente para
habilitar envios reais.

## Contrato protegido por testes

A suite automatizada valida que o `render.yaml`:

- continua declarando o Cron `gesto-app-whatsapp-outbox`;
- usa `backend` como rootDir;
- aponta para `scripts/executar_outbox_whatsapp.py`;
- continua com `WHATSAPP_TRANSPORT_MODE=fake`;
- nao contem `--permitir-meta`;
- nao contem access token, app secret ou verify token Meta;
- mantem `DATABASE_URL` como valor externo (`sync: false`);
- continua agendado para uma execucao por minuto.

Essas validacoes protegem o repositorio contra ativacao real acidental.

## Checklist futuro para ativacao real

NAO executar este checklist agora.

Quando a ativacao Meta for deliberadamente aprovada:

1. Confirmar dominio, webhook e configuracao oficial da Meta.
2. Confirmar `phone_number_id` de cada tenant.
3. Configurar segredos Meta somente no ambiente do Render.
4. Nunca commitar access token, app secret ou verify token.
5. Confirmar banco PostgreSQL e migration head em producao.
6. Executar suite completa antes da alteracao.
7. Validar primeiro com um tenant e numero de teste controlado.
8. Alterar `WHATSAPP_TRANSPORT_MODE` para `meta`.
9. Somente depois adicionar `--permitir-meta` ao executor operacional.
10. Fazer um envio controlado e conferir logs por `execucao_id`.
11. Confirmar Outbox como `enviada` e `provider_message_id`.
12. Confirmar que retries/backoff nao produziram duplicidade inesperada.
13. Monitorar `healthy`, `partial`, `fatal` e `entrega_incerta`.
14. Ter rollback imediato para `WHATSAPP_TRANSPORT_MODE=fake`.

## Rollback operacional

Se qualquer comportamento inesperado aparecer durante a futura
ativacao real:

1. remover `--permitir-meta`;
2. restaurar `WHATSAPP_TRANSPORT_MODE=fake`;
3. interromper o Cron se necessario;
4. preservar registros da Outbox para diagnostico;
5. nao apagar manualmente mensagens com estado incerto;
6. correlacionar logs usando `execucao_id` e `provider_message_id`.

## Estado atual

O estado esperado nesta fase continua sendo:

- Cron real ainda nao criado/sincronizado no Render;
- transporte configurado como `fake`;
- `--permitir-meta` ausente do `render.yaml`;
- nenhum segredo Meta no Blueprint;
- nenhum envio real habilitado.

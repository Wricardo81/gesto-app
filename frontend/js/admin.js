let tenantSlugLogado = "";
let configuracaoAtual = {};
let listenersDePreviewRegistrados = false;
let listenersCRMRegistrados = false;
let listenersBloqueiosRegistrados = false;
let listenersAgendaVisualRegistrados = false;
let listenersNavegacaoAdminRegistrados = false;

const secoesAdminCarregadas = new Set();
const secoesAdminCarregando = new Set();
let timeoutAtualizacaoAgendaVisual = null;
const WHATSAPP_SUPORTE_ADMIN = "5581988996085";

let agendaVisualEmCarregamento = false;
let agendaVisualRecarregarDepois = false;
let avisosAdminCache = [];
let chamadosAdminCache = [];
let agendamentosAdminCache = [];
let configuracoesAdminCache = {};
let monitorNovosAgendamentosTimer = null;
let painelAdminAtualizando = false;
let intervaloNovosAgendamentosAdmin = null;
let ultimoCarregamentoConfiguracaoAdmin = 0;
let ultimoCarregamentoAvisosAdmin = 0;
let ultimoCarregamentoAgendamentosAdmin = 0;
let ultimoCarregamentoServicosAdmin = 0;
let ultimoCarregamentoProfissionaisAdmin = 0;

const TEMPO_CACHE_CURTO_ADMIN_MS = 10000;
const TEMPO_CACHE_AGENDAMENTOS_ADMIN_MS = 15000;

let carregandoConfiguracaoAdmin = false;
let carregandoAvisosAdmin = false;
let carregandoAgendamentosAdmin = false;
let carregandoServicosAdmin = false;
let carregandoProfissionaisAdmin = false;

let onboardingAdminCarregando = false;
let ultimoCarregamentoOnboardingAdmin = 0;
const TEMPO_CACHE_ONBOARDING_ADMIN_MS = 12000;



/* =========================================================
   UTILITÁRIOS
========================================================= */

function renderizarEstadoVazioEmElementoAdmin(elementoId, htmlEstadoVazio) {
  const elemento = document.getElementById(elementoId);

  if (!elemento) {
    console.warn(`Elemento não encontrado para estado vazio: ${elementoId}`);
    return;
  }

  elemento.innerHTML = htmlEstadoVazio;
}

function renderizarEstadoVazioEmTabelaAdmin(
  tabelaId,
  htmlEstadoVazio,
  colspan = 8,
) {
  const tabela = document.getElementById(tabelaId);

  if (!tabela) {
    console.warn(`Tabela não encontrada para estado vazio: ${tabelaId}`);
    return;
  }

  tabela.innerHTML = `
        <tr>
            <td colspan="${colspan}">
                ${htmlEstadoVazio}
            </td>
        </tr>
    `;
}

function criarEstadoVazioAgendamentosAdmin() {
  return `
        <div class="estado-vazio-inteligente-admin">
            <div class="estado-vazio-inteligente-icone">◴</div>

            <div>
                <h3>Nenhum agendamento recebido ainda</h3>
                <p>Copie o link público e envie para seus clientes pelo WhatsApp, Instagram ou site.</p>

                <button
                    type="button"
                    class="btn-primary estado-vazio-admin-botao"
                    onclick="copiarLinkPublicoAdmin()"
                >
                    Copiar link público
                </button>
            </div>
        </div>
    `;
}


function criarEstadoVazioAdmin({
  icone = "◇",
  titulo = "Nenhum registro encontrado",
  descricao = "Cadastre o primeiro item para começar.",
  textoBotao = "",
  secaoDestino = "",
}) {
  const botao =
    textoBotao && secaoDestino
      ? `
            <button
                type="button"
                class="btn-primary estado-vazio-admin-botao"
                onclick="mostrarSecaoAdmin('${secaoDestino}')"
            >
                ${textoBotao}
            </button>
        `
      : "";

  return `
        <div class="estado-vazio-inteligente-admin">
            <div class="estado-vazio-inteligente-icone">${icone}</div>

            <div>
                <h3>${titulo}</h3>
                <p>${descricao}</p>
                ${botao}
            </div>
        </div>
    `;
}


function limparCachesAdminEmMemoria() {
    avisosAdminCache = [];
    chamadosAdminCache = [];
    agendamentosAdminCache = [];
    configuracoesAdminCache = {};

    ultimoCarregamentoConfiguracaoAdmin = 0;
    ultimoCarregamentoAvisosAdmin = 0;
    ultimoCarregamentoAgendamentosAdmin = 0;
    ultimoCarregamentoServicosAdmin = 0;
    ultimoCarregamentoProfissionaisAdmin = 0;

    if (typeof ultimoCarregamentoOnboardingAdmin !== "undefined") {
        ultimoCarregamentoOnboardingAdmin = 0;
    }

    secoesAdminCarregadas.clear();
    secoesAdminCarregando.clear();
}


function decodificarTokenAdmin(token) {
  if (!token || !token.includes(".")) {
    return null;
  }

  try {
    return JSON.parse(
      atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")),
    );
  } catch (erro) {
    console.warn("Não foi possível decodificar token admin:", erro);
    return null;
  }
}


function obterTenantDoTokenAdmin() {
  const token = localStorage.getItem("gesto_token");
  const payload = decodificarTokenAdmin(token);

  return (
    payload?.sub ||
    payload?.tenant_slug ||
    payload?.barbearia_slug ||
    payload?.tenant ||
    payload?.slug ||
    ""
  );
}


function atualizarUrlTenantAdmin() {
  if (!tenantSlugLogado) {
    return;
  }

  const parametros = new URLSearchParams(window.location.search);
  const tenantUrl = parametros.get("tenant");

  if (tenantUrl === tenantSlugLogado) {
    return;
  }

  const novaUrl = `${window.location.origin}${window.location.pathname}?tenant=${encodeURIComponent(tenantSlugLogado)}`;

  window.history.replaceState({}, document.title, novaUrl);
}


function sincronizarTenantAdminComToken() {
  const tenantToken = obterTenantDoTokenAdmin();

  if (!tenantToken) {
    return "";
  }

  localStorage.setItem("gesto_tenant", tenantToken);

  const parametros = new URLSearchParams(window.location.search);
  const tenantUrl = parametros.get("tenant");

  if (tenantUrl !== tenantToken) {
    const novaUrl = `${window.location.origin}${window.location.pathname}?tenant=${encodeURIComponent(tenantToken)}`;

    window.history.replaceState({}, document.title, novaUrl);
  }

  return tenantToken;
}

function cacheAdminAindaValido(ultimoCarregamento, tempoMaximo) {
    if (!ultimoCarregamento) {
        return false;
    }

    return Date.now() - ultimoCarregamento < tempoMaximo;
}


function exibirMensagemAdmin(mensagem, tipo = "sucesso") {
    const toast = document.getElementById("toast-admin");
    const texto = document.getElementById("toast-admin-texto");

    if (!toast || !texto) {
        console.log(mensagem);
        return;
    }

    texto.innerText = mensagem;

    toast.classList.remove(
        "sucesso",
        "erro",
        "aviso"
    );

    toast.classList.add(tipo);
    toast.style.display = "flex";

    window.clearTimeout(window.toastAdminTimeout);

    window.toastAdminTimeout = window.setTimeout(() => {
        toast.style.display = "none";
    }, 4200);
}


function tratarErroAdmin(erro) {
  tratarErro(erro);
}


function obterChaveUltimoAgendamentoVisto() {
    return `gesto_ultimo_agendamento_visto_${tenantSlugLogado || "sem_tenant"}`;
}


function obterUltimoAgendamentoVisto() {
    return Number(
        localStorage.getItem(obterChaveUltimoAgendamentoVisto()) || 0
    );
}


function salvarUltimoAgendamentoVisto(id) {
    localStorage.setItem(
        obterChaveUltimoAgendamentoVisto(),
        String(Number(id) || 0)
    );
}


function obterMaiorIdAgendamento(agendamentos) {
    if (!Array.isArray(agendamentos) || !agendamentos.length) {
        return 0;
    }

    return Math.max(
        ...agendamentos.map((item) => Number(item.id) || 0)
    );
}


function garantirIndicadorNovosAgendamentos() {
    let indicador = document.getElementById("indicador-novos-agendamentos");

    if (indicador) {
        return indicador;
    }

    const secaoAgenda =
        document.getElementById("secao-agenda")
        || document.querySelector(".secao-admin");

    if (!secaoAgenda) {
        return null;
    }

    indicador = document.createElement("div");
    indicador.id = "indicador-novos-agendamentos";
    indicador.className = "indicador-novos-agendamentos";
    indicador.style.display = "none";

    indicador.innerHTML = `
        <div>
            <strong id="texto-novos-agendamentos">
                Novos agendamentos
            </strong>
            <p>
                Existem agendamentos recentes que ainda não foram visualizados.
            </p>
        </div>

        <button
            type="button"
            onclick="marcarAgendamentosComoVistos()"
        >
            Marcar como visualizados
        </button>
    `;

    secaoAgenda.prepend(indicador);

    return indicador;
}


function atualizarIndicadorNovosAgendamentos(agendamentos) {
    const indicador = garantirIndicadorNovosAgendamentos();

    if (!indicador) {
        return;
    }

    const ultimoVisto = obterUltimoAgendamentoVisto();

    const novos = (agendamentos || []).filter((agendamento) => {
        return Number(agendamento.id) > ultimoVisto;
    });

    const texto = document.getElementById("texto-novos-agendamentos");

    if (!novos.length) {
        indicador.style.display = "none";
        return;
    }

    indicador.style.display = "flex";

    if (texto) {
        texto.textContent =
            novos.length === 1
                ? "1 novo agendamento"
                : `${novos.length} novos agendamentos`;
    }
}


function marcarAgendamentosComoVistos() {
    const maiorId = obterMaiorIdAgendamento(
        agendamentosAdminCache || []
    );

    salvarUltimoAgendamentoVisto(maiorId);

    atualizarIndicadorNovosAgendamentos(
        agendamentosAdminCache || []
    );

    document
        .querySelectorAll(".linha-agendamento-novo")
        .forEach((linha) => {
            linha.classList.remove("linha-agendamento-novo");
        });
}


async function verificarNovosAgendamentosAdmin() {
    if (document.hidden) {
        return;
    }

    if (!adminProntoParaRequisicao()) {
        return;
    }

    try {
        await carregarAgendamentos();

    } catch (erro) {
        console.warn(
            "Não foi possível verificar novos agendamentos:",
            erro
        );
    }
}



function iniciarMonitorNovosAgendamentos() {
    if (intervaloNovosAgendamentosAdmin) {
        return;
    }

    intervaloNovosAgendamentosAdmin = window.setInterval(
        verificarNovosAgendamentosAdmin,
        60000
    );
}


function normalizarTelefoneWhatsApp(numero) {
    const apenasNumeros = String(numero || "").replace(/\D/g, "");

    if (!apenasNumeros) {
        return "";
    }

    if (apenasNumeros.startsWith("55")) {
        return apenasNumeros;
    }

    return `55${apenasNumeros}`;
}


function formatarDataMensagemWhatsApp(data) {
    if (!data) {
        return "";
    }

    const partes = String(data).split("-");

    if (partes.length !== 3) {
        return data;
    }

    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}


function montarMensagemWhatsAppAgendamento(agendamento, tipo = "confirmacao") {
    const nomeCliente = agendamento?.cliente_nome || "cliente";
    const servico = agendamento?.servico || "seu atendimento";
    const profissional = agendamento?.profissional || "nossa equipe";
    const data = formatarDataMensagemWhatsApp(agendamento?.data);
    const horario = agendamento?.horario || "";


    const nomeEmpresa =
        configuracoesAdminCache?.nome_publico
        || configuracoesAdminCache?.nome_empresa
        || tenantSlugLogado
        || "nossa empresa";

    if (tipo === "remarcacao") {
        return (
            `Olá, ${nomeCliente}! Aqui é da ${nomeEmpresa}. ` +
            `Precisamos falar sobre seu agendamento de ${servico}, marcado para ${data} às ${horario} com ${profissional}. ` +
            `Podemos combinar um novo horário?`
        );
    }

    if (tipo === "agradecimento") {
        return (
            `Olá, ${nomeCliente}! Aqui é da ${nomeEmpresa}. ` +
            `Passando para agradecer pela sua visita. Foi um prazer atender você! ` +
            `Quando quiser agendar novamente, estamos à disposição.`
        );
    }

    return (
        `Olá, ${nomeCliente}! Aqui é da ${nomeEmpresa}. ` +
        `Confirmando seu agendamento de ${servico} para ${data} às ${horario} com ${profissional}. ` +
        `Qualquer dúvida, estamos à disposição.`
    );
}


function abrirWhatsAppAgendamento(agendamentoId, tipo = "confirmacao") {
    const agendamento = agendamentosAdminCache.find(
        (item) => Number(item.id) === Number(agendamentoId)
    );

    if (!agendamento) {
        exibirMensagemAdmin("Agendamento não encontrado.");
        return;
    }

    const telefone = normalizarTelefoneWhatsApp(
        agendamento.telefone_cliente
    );

    if (!telefone) {
        exibirMensagemAdmin("Este cliente não possui telefone cadastrado.");
        return;
    }

    const mensagem = montarMensagemWhatsAppAgendamento(
        agendamento,
        tipo
    );

    const url = `https://wa.me/${telefone}?text=${encodeURIComponent(mensagem)}`;

    window.open(
        url,
        "_blank",
        "noopener,noreferrer"
    );
}


function traduzirStatusAssinaturaAdmin(status) {
    const mapa = {
        trial: "Teste gratuito",
        checkout_criado: "Checkout criado",
        checkout_concluido: "Checkout concluído",
        active: "Ativa",
        trialing: "Teste ativo",
        past_due: "Pagamento atrasado",
        unpaid: "Não pago",
        canceled: "Cancelada",
        mercado_pago_aprovado: "Ativa via pagamento online",
        mercado_pago_pendente: "Pagamento pendente",
    };

    return mapa[status] || status || "Não definida";
}


function traduzirStatusPagamento(status) {
    const mapa = {
        em_dia: "Em dia",
        pendente: "Pendente",
        vencido: "Vencido",
        cancelado: "Cancelado",
        teste: "Teste gratuito",
    };

    return mapa[status] || status || "Não definido";
}


function assinaturaAdminEstaAtiva(config) {
    const statusPagamento = String(
        config?.status_pagamento || ""
    )
        .trim()
        .toLowerCase();

    const statusAssinatura = String(
        config?.status_assinatura || ""
    )
        .trim()
        .toLowerCase();

    const gatewayPagamento = String(
        config?.gateway_pagamento || ""
    )
        .trim()
        .toLowerCase();

    const planoCodigo = String(
        config?.plano_codigo || ""
    )
        .trim()
        .toLowerCase();

    if (config?.assinatura_ativa === true) {
        return true;
    }

    if (statusPagamento === "em_dia") {
        return true;
    }

    if (
        [
            "active",
            "checkout_concluido",
            "mercado_pago_aprovado",
        ].includes(statusAssinatura)
    ) {
        return true;
    }

    if (
        gatewayPagamento
        && planoCodigo
        && statusPagamento !== "teste"
        && statusPagamento !== "trial"
        && statusPagamento !== "pendente"
        && statusPagamento !== "vencido"
        && statusPagamento !== "cancelado"
    ) {
        return true;
    }

    return false;
}

function renderizarCardTrialAdmin(config = {}) {
  const card = document.getElementById("card-trial-admin");
  const titulo = document.getElementById("trial-admin-titulo");
  const descricao = document.getElementById("trial-admin-descricao");
  const dias = document.getElementById("trial-admin-dias");
  const agendamentos = document.getElementById("trial-admin-agendamentos");

  if (!card || !titulo || !descricao || !dias || !agendamentos) {
    return;
  }

  const statusAssinatura = String(config.status_assinatura || "").toLowerCase();

  const statusPagamento = String(config.status_pagamento || "").toLowerCase();

  const trialAtivo =
    statusAssinatura === "trial" || statusPagamento === "trial";

  const trialExpirado = Boolean(config.trial_expirado);
  const acessoLiberado = Boolean(config.acesso_liberado);

  if (!trialAtivo && !trialExpirado) {
    card.style.display = "none";
    return;
  }

  card.style.display = "grid";

  const diasRestantes = Number(config.trial_dias_restantes || 0);
  const agendamentosRestantes = Number(
    config.trial_agendamentos_restantes || 0,
  );

  dias.textContent = diasRestantes;
  agendamentos.textContent = agendamentosRestantes;

  card.classList.remove("trial-admin-card-alerta", "trial-admin-card-expirado");

  if (trialExpirado || !acessoLiberado) {
    card.classList.add("trial-admin-card-expirado");

    titulo.textContent = "Teste grátis encerrado";

    descricao.textContent =
      "Seu período gratuito terminou. Ative uma assinatura para continuar recebendo agendamentos.";

    dias.textContent = "0";
    agendamentos.textContent = "0";

    return;
  }

  if (diasRestantes <= 2 || agendamentosRestantes <= 5) {
    card.classList.add("trial-admin-card-alerta");

    titulo.textContent = "Seu teste grátis está quase acabando";

    descricao.textContent =
      `Restam ${diasRestantes} dia(s) ou ${agendamentosRestantes} agendamento(s). ` +
      "Quando um dos limites acabar, será necessário ativar uma assinatura.";

    return;
  }

  titulo.textContent = "Teste grátis ativo";

  descricao.textContent =
    `Você ainda tem ${diasRestantes} dia(s) ou ${agendamentosRestantes} ` +
    "agendamento(s) disponíveis no teste grátis.";
}


function renderizarAssinaturaAdmin(config) {
    renderizarCardTrialAdmin(config);
    const card = document.getElementById("card-assinatura-admin");
    const planos = document.getElementById("planos-assinatura-admin");

    if (!card) {
        return;
    }

    const ativa = assinaturaAdminEstaAtiva(config);

    const trialDiasRestantes = Number(
        config?.trial_dias_restantes ?? 0
    );

    const trialLimiteAgendamentos = Number(
        config?.trial_limite_agendamentos ?? 0
    );

    const trialTotalAgendamentos = Number(
        config?.trial_total_agendamentos ?? 0
    );

    const trialAgendamentosRestantes = Number(
        config?.trial_agendamentos_restantes ?? 0
    );

    const trialExpirado = Boolean(
        config?.trial_expirado
    );

    if (ativa) {
        document.body.classList.add("assinatura-ativa-admin");

        if (planos) {
            planos.style.display = "none";
        }

    } else {
        document.body.classList.remove("assinatura-ativa-admin");

        if (planos) {
            planos.style.display = "grid";
        }
    }

    let titulo = "Teste grátis ativo";
    let descricao =
      "Você pode usar o sistema gratuitamente por 7 dias ou até 30 agendamentos. Depois disso, será necessário ativar uma assinatura para continuar recebendo novos agendamentos.";

    if (ativa) {
      titulo = "Sua assinatura está ativa";
      descricao =
        "Seu acesso está liberado. Os banners de assinatura não serão exibidos enquanto o pagamento estiver em dia.";
    } else if (trialExpirado) {
      titulo = "Seu teste gratuito terminou";

      if (config?.trial_expirado_por_agendamentos) {
        descricao =
          "O limite de 30 agendamentos gratuitos foi atingido. Para continuar recebendo novos agendamentos, escolha um plano.";
      } else {
        descricao =
          "O período gratuito de 7 dias terminou. Para continuar recebendo novos agendamentos, escolha um plano.";
      }
    } else {
      titulo = "Você está no teste gratuito";
      descricao = `Restam ${trialDiasRestantes} dia(s) ou ${trialAgendamentosRestantes} agendamento(s) grátis.`;
    }

    card.innerHTML = `
        <h3>${titulo}</h3>

        <p>${descricao}</p>

        <div class="assinatura-admin-meta">
            <span>Status: ${traduzirStatusAssinaturaAdmin(config?.status_assinatura)}</span>
            <span>Pagamento: ${traduzirStatusPagamento(config?.status_pagamento)}</span>
            <span>Plano: ${config?.plano_codigo || config?.plano_nome || "Não definido"}</span>
            <span>Gateway: ${config?.gateway_pagamento || "Não definido"}</span>
            <span>Vencimento: ${formatarDataBR(config?.vencimento_plano)}</span>
        </div>

        ${
            !ativa
                ? `
                    <div class="trial-admin-box">
                        <div>
                            <span>Dias restantes</span>
                            <strong>${trialDiasRestantes}</strong>
                        </div>

                        <div>
                            <span>Agendamentos usados</span>
                            <strong>${trialTotalAgendamentos}/${trialLimiteAgendamentos}</strong>
                        </div>

                        <div>
                            <span>Agendamentos restantes</span>
                            <strong>${trialAgendamentosRestantes}</strong>
                        </div>
                    </div>
                `
                : ""
        }
    `;
}


async function carregarAssinaturaAdmin() {
    const card = document.getElementById("card-assinatura-admin");

    if (!tenantSlugLogado) {
        if (card) {
            card.innerHTML = `
                <h3>Empresa não identificada</h3>
                <p>Faça login novamente para carregar os dados da assinatura.</p>
            `;
        }

        return;
    }

    if (card) {
        card.innerHTML = "Carregando informações da assinatura...";
    }

    try {
        const config = await apiRequest(
            `/api/${tenantSlugLogado}/configuracoes`,
            {
                auth: true,
            }
        );

        renderizarAssinaturaAdmin(config);
        exibirBannerFuncionalidadesAdmin(config);

    } catch (erro) {
        console.error("Erro ao carregar assinatura admin:", erro);

        if (card) {
            card.innerHTML = `
                <h3>Não foi possível carregar a assinatura</h3>
                <p>${montarMensagemErroComDiagnostico(
                  erro.message || "Erro ao buscar dados do plano.",
                  erro,
                ).replace(/\n/g, "<br>")}</p>
            `;
        }
    }
}


async function assinarPlanoAdmin(planoCodigo) {
    const confirmar = window.confirm(
        `Deseja assinar o plano ${planoCodigo.toUpperCase()}?`
    );

    if (!confirmar) {
        return;
    }

    if (!tenantSlugLogado) {
        exibirMensagemAdmin("Tenant não identificado. Faça login novamente.");
        return;
    }

    const token = obterToken();

    if (!token) {
        exibirMensagemAdmin("Sessão expirada. Faça login novamente.");
        fazerLogout();
        return;
    }

    try {
        const respostaHttp = await fetch(
            `${API_BASE_URL}/api/${tenantSlugLogado}/admin/assinaturas/stripe/checkout`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    barbearia_id: 0,
                    plano_codigo: planoCodigo,
                }),
            }
        );

        const dados = await respostaHttp.json();

        if (!respostaHttp.ok) {
            throw new Error(
                dados.detail
                || "Não foi possível gerar o checkout."
            );
        }

        console.log(
            "Resposta pagamento seguro:",
            dados
        );

        if (!dados.checkout_url) {
            exibirMensagemAdmin("Pagamento iniciado, mas não foi possível abrir a página de pagamento.");
            return;
        }

        window.location.href = dados.checkout_url;

    } catch (erro) {
        console.error("Erro no checkout admin:", erro);

       exibirMensagemAdmin(
         montarMensagemErroComDiagnostico(
           erro.message || "Erro ao carregar dados.",
           erro,
         ),
       );
    }
}


async function assinarPlanoMercadoPagoAdmin(planoCodigo) {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const confirmar = window.confirm(
        `Deseja assinar o plano ${planoCodigo.toUpperCase()} por pagamento online?`
    );

    if (!confirmar) {
        return;
    }

    try {
        const token = localStorage.getItem("gesto_token");

        const resposta = await fetch(
            `${API_BASE_URL}/api/${tenantSlugLogado}/admin/assinaturas/mercado-pago/checkout`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    plano_codigo: planoCodigo,
                }),
            }
        );

        const dados = await resposta.json();

        if (!resposta.ok) {
            throw new Error(
                dados.detail
                || "Não foi possível iniciar o pagamento online."
            );
        }

        if (!dados.checkout_url) {
            throw new Error(
                "Pagamento iniciado, mas não foi possível abrir a página de pagamento."
            );
        }

        window.location.href = dados.checkout_url;

    } catch (erro) {
        exibirMensagemAdmin(
          montarMensagemErroComDiagnostico(
            erro.message || "Erro ao carregar dados.",
            erro,
          ),
        );
    }
}


function tratarRetornoCadastroAdmin() {
  const parametros = new URLSearchParams(window.location.search);

  const cadastroStatus = parametros.get("cadastro");
  const pagamentoStatus = parametros.get("pagamento");

  if (cadastroStatus === "sucesso") {
    exibirMensagemAdmin(
      "Conta criada com sucesso. Seu teste grátis de 7 dias ou 30 agendamentos já começou. Configure seus serviços, profissionais e horários para começar a receber agendamentos.",
    );
  }

  if (pagamentoStatus === "pendente") {
    exibirMensagemAdmin(
      "Sua conta foi criada, mas o pagamento ainda não foi concluído. Você pode continuar usando o teste grátis por 7 dias ou até 30 agendamentos.",
    );
  }

  if (!cadastroStatus && !pagamentoStatus) {
    return;
  }

  const urlLimpa = `${window.location.origin}${window.location.pathname}?tenant=${tenantSlugLogado}`;

  window.history.replaceState({}, document.title, urlLimpa);
}


async function tratarRetornoPagamentoAdmin() {
    const parametros = new URLSearchParams(
        window.location.search
    );

    const statusStripe = parametros.get("stripe");

    if (!statusStripe) {
        return;
    }

    localStorage.setItem(
        "gesto_admin_secao_ativa",
        "secao-admin-assinatura"
    );

    if (statusStripe === "sucesso") {
        exibirMensagemAdmin(
            "Pagamento recebido. Sua assinatura será atualizada automaticamente."
        );
    }

    if (statusStripe === "cancelado") {
        exibirMensagemAdmin(
            "Checkout cancelado. Nenhuma alteração foi feita."
        );
    }

    await carregarAssinaturaAdmin();
    carregarAssinaturaAdmin();
    iniciarMonitorNovosAgendamentos();

    const urlLimpa =
        `${window.location.origin}${window.location.pathname}?tenant=${tenantSlugLogado}`;

    window.history.replaceState(
        {},
        document.title,
        urlLimpa
    );
}


window.assinarPlanoAdmin = assinarPlanoAdmin;

const BANNER_FUNCIONALIDADES_ADMIN_KEY =
    "gesto_banner_funcionalidades_admin_dispensado";


    function exibirBannerFuncionalidadesAdmin(config = null) {
        const banner = document.getElementById(
            "banner-funcionalidades-admin"
        );

        if (!banner) {
            return;
        }

        if (
            config
            && assinaturaAdminEstaAtiva(config)
        ) {
            banner.classList.remove("visivel");
            return;
        }

        const dispensado = localStorage.getItem(
            BANNER_FUNCIONALIDADES_ADMIN_KEY
        );

        if (dispensado === "true") {
            banner.classList.remove("visivel");
            return;
        }

        banner.classList.add("visivel");
    }


function dispensarBannerFuncionalidadesAdmin() {
    localStorage.setItem(
        BANNER_FUNCIONALIDADES_ADMIN_KEY,
        "true"
    );

    const banner = document.getElementById(
        "banner-funcionalidades-admin"
    );

    if (banner) {
        banner.classList.remove("visivel");
    }
}


window.dispensarBannerFuncionalidadesAdmin =
    dispensarBannerFuncionalidadesAdmin;


function formatarMoeda(valor) {
    return Number(valor || 0).toLocaleString(
        "pt-BR",
        {
            style: "currency",
            currency: "BRL"
        }
    );
}


function formatarDataBR(dataISO) {
    if (!dataISO) {
        return "-";
    }

    const partes = String(dataISO).split("-");

    if (partes.length !== 3) {
        return dataISO;
    }

    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

function formatarDataHoraBR(dataHoraISO) {
    if (!dataHoraISO) {
        return "-";
    }

    const data = new Date(dataHoraISO);

    if (Number.isNaN(data.getTime())) {
        return dataHoraISO;
    }

    return data.toLocaleString("pt-BR");
}


function normalizarTelefoneCliente(telefone) {
    return String(telefone || "").replace(/\D/g, "");
}


function valorCampo(id, padrao = "") {
    const elemento = document.getElementById(id);

    if (!elemento) {
        return padrao;
    }

    return elemento.value?.trim?.() ?? padrao;
}

function traduzirStatusAgendamento(status) {
    const mapa = {
        confirmado: "Confirmado",
        concluido: "Concluído",
        cancelado: "Cancelado",
        faltou: "Faltou",
    };

    return mapa[status] || "Confirmado";
}


function classeStatusAgendamento(status) {
    const mapa = {
        confirmado: "status-confirmado",
        concluido: "status-concluido",
        cancelado: "status-cancelado",
        faltou: "status-faltou",
    };

    return mapa[status] || "status-confirmado";
}


function marcarCheckbox(id, valor) {
    const elemento = document.getElementById(id);

    if (elemento) {
        elemento.checked = Boolean(valor);
    }
}


function checkboxMarcado(id) {
    const elemento = document.getElementById(id);

    return Boolean(elemento && elemento.checked);
}


function exibirMensagemPainel(mensagem, tipo = "sucesso") {
    const area = document.getElementById("mensagem-painel");

    if (!area) {
        return;
    }

    area.textContent = mensagem;
    area.style.display = "block";

    if (tipo === "erro") {
        area.style.color = "var(--cor-perigo)";
        area.style.background = "rgba(239, 68, 68, 0.12)";
    } else {
        area.style.color = "var(--cor-sucesso)";
        area.style.background = "rgba(16, 185, 129, 0.12)";
    }

    setTimeout(() => {
        area.style.display = "none";
    }, 3500);
}


function atualizarPreviewMarca() {
    const nome = valorCampo("nome-publico", "Nome da empresa");
    const endereco = valorCampo("endereco", "Endereço ainda não informado.");
    const logoUrl = valorCampo("logo-url", "");

    const previewNome = document.getElementById("preview-nome-publico");
    const previewEndereco = document.getElementById("preview-endereco");
    const previewLogoBox = document.getElementById("preview-logo-box");

    if (previewNome) {
        previewNome.textContent = nome || "Nome da empresa";
    }

    if (previewEndereco) {
        previewEndereco.textContent = endereco || "Endereço ainda não informado.";
    }

    if (previewLogoBox) {
        if (logoUrl) {
            previewLogoBox.innerHTML = `
                <img
                    src="${logoUrl}"
                    alt="Logo da empresa"
                    onerror="this.parentElement.textContent='Logo inválida';"
                >
            `;
        } else {
            previewLogoBox.textContent = "Logo";
        }
    }
}

async function uploadImagemMarca(
    campoArquivoId,
    campoUrlId,
    tipo
) {
    const inputArquivo = document
        .getElementById(campoArquivoId);

    const campoUrl = document
        .getElementById(campoUrlId);

    const arquivo = inputArquivo
        ?.files
        ?.[0];

    if (!arquivo) {
        return;
    }

    if (!arquivo.type.startsWith("image/")) {
        exibirMensagemAdmin("Selecione um arquivo de imagem.");
        inputArquivo.value = "";
        return;
    }

    const tamanhoMaximo = 5 * 1024 * 1024;

    if (arquivo.size > tamanhoMaximo) {
        exibirMensagemAdmin("A imagem deve ter no máximo 5MB.");
        inputArquivo.value = "";
        return;
    }

    const formData = new FormData();

    formData.append("arquivo", arquivo);
    formData.append("tipo", tipo);

    try {
        const resposta = await fetch(
            `${API_BASE_URL}/api/${tenantSlugLogado}/admin/uploads/branding`,
            {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${obterToken()}`
                },
                body: formData,
            }
        );

        const dados = await resposta.json();

        if (!resposta.ok) {
            throw new Error(
                dados.detail
                || "Não foi possível enviar a imagem."
            );
        }

        campoUrl.value = dados.url;

        await salvarConfiguracao({
            silencioso: true,
        });

        atualizarPreviewMarca();

        exibirMensagemPainel(
            "Imagem enviada e configuração salva com sucesso."
        );

    } catch (erro) {
        console.error(erro);
        exibirMensagemAdmin(
          montarMensagemErroComDiagnostico(
            erro.message || "Erro ao carregar dados.",
            erro,
          ),
        );

    } finally {
        inputArquivo.value = "";
    }
}


function atualizarLinkPublico() {
    const link = document.getElementById("link-pagina-publica");

    if (!link || !tenantSlugLogado) {
        return;
    }

    link.href = `./agendamento.html?tenant=${tenantSlugLogado}`;
}

function adminProntoParaRequisicao() {
    return Boolean(tenantSlugLogado && tenantSlugLogado.trim());
}


/* =========================================================
   TRATAMENTO CENTRALIZADO DE ERROS
========================================================= */

function tratarErro(erro) {
  console.error(erro);

  if (erro.status === 401) {
    exibirMensagemAdmin(
      montarMensagemErroComDiagnostico(
        "Sua sessão expirou ou é inválida. Faça login novamente.",
        erro,
      ),
      "erro",
    );

    fazerLogout();
    return;
  }

  if (erro.status === 403) {
    exibirMensagemAdmin(
      montarMensagemErroComDiagnostico(
        "Você não possui permissão para executar esta ação.",
        erro,
      ),
      "erro",
    );

    return;
  }

  exibirMensagemAdmin(
    montarMensagemErroComDiagnostico(
      erro.message || "Erro ao carregar dados.",
      erro,
    ),
    "erro",
  );
}


/* =========================================================
   LOGIN E INICIALIZAÇÃO
========================================================= */

async function realizarLogin(event) {
    event.preventDefault();

    const email = document
        .getElementById("login-email")
        .value
        .trim();

    const senha = document
        .getElementById("login-senha")
        .value;

    const botao = document.getElementById("btn-submit-login");
    const mensagem = document.getElementById("msg-erro-login");

    botao.disabled = true;
    botao.innerText = "Entrando...";
    mensagem.style.display = "none";

    try {
        await autenticar(email, senha);

        limparCachesAdminEmMemoria();

        tenantSlugLogado = sincronizarTenantAdminComToken();

        if (tenantSlugLogado) {
          localStorage.setItem("gesto_tenant", tenantSlugLogado);
          atualizarUrlTenantAdmin();
        }

        iniciarPainel();

    } catch (erro) {
        console.error(erro);

        mensagem.innerText = montarMensagemErroComDiagnostico(
          erro.message || "Erro ao fazer login.",
          erro,
        );
        mensagem.style.display = "block";

    } finally {
        botao.disabled = false;
        botao.innerText = "Entrar no Sistema";
    }
}

function alternarMenuAdmin() {
    const menu = document.getElementById("admin-tabs");

    if (!menu) {
        return;
    }

    menu.classList.toggle("aberto");
}


function mostrarSecaoAdmin(secaoId) {
    const secoes = document.querySelectorAll(".secao-admin");
    const botoes = document.querySelectorAll(".admin-tab");

    secoes.forEach((secao) => {
        secao.classList.toggle(
            "ativa",
            secao.id === secaoId
        );
    });

    botoes.forEach((botao) => {
        botao.classList.toggle(
            "ativa",
            botao.dataset.secao === secaoId
        );
    });

    localStorage.setItem(
        "gesto_admin_secao_ativa",
        secaoId
    );

    const menu = document.getElementById("admin-tabs");

    if (menu) {
        menu.classList.remove("aberto");
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });

    carregarDadosDaSecaoAdmin(secaoId);

}


function inicializarNavegacaoAdmin() {
    const botoes = document.querySelectorAll(".admin-tab");

    if (!listenersNavegacaoAdminRegistrados) {
        botoes.forEach((botao) => {
            botao.addEventListener("click", () => {
                mostrarSecaoAdmin(botao.dataset.secao);
            });
        });

        listenersNavegacaoAdminRegistrados = true;
    }

    const secaoSalva = localStorage.getItem(
        "gesto_admin_secao_ativa"
    );

    mostrarSecaoAdmin(
        secaoSalva || "secao-dashboard"
    );
}


window.alternarMenuAdmin = alternarMenuAdmin;

function alternarCaixaSuporteAdmin() {
    const caixa = document.getElementById("suporte-admin-caixa");

    if (!caixa) {
        return;
    }

    caixa.style.display =
        caixa.style.display === "none" || !caixa.style.display
            ? "block"
            : "none";
}


function obterTextoTipoSuporteAdmin(tipo) {
    const mapa = {
        erro: "Erro",
        bug: "Bug",
        sugestao: "Sugestão",
        elogio: "Elogio",
    };

    return mapa[tipo] || "Suporte";
}


function montarMensagemWhatsAppAgendamento(agendamento, tipo = "confirmacao") {
    const nomeCliente = agendamento?.cliente_nome || "cliente";
    const servico = agendamento?.servico || "seu atendimento";
    const profissional = agendamento?.profissional || "nossa equipe";
    const data = formatarDataMensagemWhatsApp(agendamento?.data);
    const horario = agendamento?.horario || "";

    const nomeEmpresa =
        configuracoesAdminCache?.nome_publico
        || configuracoesAdminCache?.nome_empresa
        || tenantSlugLogado
        || "nossa empresa";

    const linkAgenda =
        `${window.location.origin}/frontend/agendamento.html?tenant=${encodeURIComponent(tenantSlugLogado)}`;

    if (tipo === "remarcacao") {
        return (
            `Olá, ${nomeCliente}! Aqui é da ${nomeEmpresa}.\n\n` +
            `Precisamos falar sobre seu agendamento de ${servico}, marcado para ${data} às ${horario} com ${profissional}.\n\n` +
            `Podemos combinar um novo horário?\n\n` +
            `Você também pode acessar nossa agenda online:\n${linkAgenda}`
        );
    }

    if (tipo === "agradecimento") {
        return (
            `Olá, ${nomeCliente}! Aqui é da ${nomeEmpresa}.\n\n` +
            `Passando para agradecer pela sua visita. Foi um prazer atender você!\n\n` +
            `Quando quiser agendar novamente, acesse nossa agenda online:\n${linkAgenda}`
        );
    }

    return (
        `Olá, ${nomeCliente}! Aqui é da ${nomeEmpresa}.\n\n` +
        `Confirmando seu agendamento de ${servico} para ${data} às ${horario} com ${profissional}.\n\n` +
        `Qualquer dúvida, estamos à disposição.\n\n` +
        `Para consultar ou fazer novos agendamentos, acesse:\n${linkAgenda}`
    );
}


function montarMensagemSuporteAdmin(tipo = "erro") {
  const tipoTexto = {
    erro: "erro",
    bug: "bug",
    sugestao: "sugestão",
    elogio: "elogio",
    outro: "mensagem",
  };

  const tenant =
    tenantSlugLogado ||
    localStorage.getItem("gesto_tenant") ||
    "não identificado";
  const pagina = window.location.href;
  const tipoFormatado = tipoTexto[tipo] || tipoTexto.outro;

  return (
    `Olá, Engenharia de Bits!\n\n` +
    `Quero enviar um(a) ${tipoFormatado} sobre o BitsAgenda OS.\n\n` +
    `Tenant: ${tenant}\n` +
    `Página: ${pagina}\n\n` +
    `Descrição:\n`
  );
}


function abrirSuporteWhatsAppAdmin(tipo) {
  const mensagem = montarMensagemSuporteAdmin(tipo);

  const url =
    `https://wa.me/${WHATSAPP_SUPORTE_ADMIN}` +
    `?text=${encodeURIComponent(mensagem)}`;

  window.open(url, "_blank", "noopener,noreferrer");
}


window.alternarCaixaSuporteAdmin = alternarCaixaSuporteAdmin;
window.abrirSuporteWhatsAppAdmin = abrirSuporteWhatsAppAdmin;


function renderizarCardAvisoAdmin(aviso) {
    return `
        <article class="aviso-admin-card tipo-${aviso.tipo}">
            <div class="aviso-admin-card-topo">
                <div>
                    <strong>${aviso.titulo}</strong>
                    <p>${aviso.mensagem}</p>
                </div>

                ${
                    aviso.dispensavel
                        ? `
                            <button
                                type="button"
                                class="btn-dispensar-aviso"
                                onclick="dispensarAvisoAdmin(${aviso.id})"
                                title="Fechar aviso"
                            >
                                ×
                            </button>
                        `
                        : ""
                }
            </div>
        </article>
    `;
}


function alternarCaixaAvisosAdmin() {
    const caixa = document.getElementById("avisos-admin-caixa");

    if (!caixa) {
        return;
    }

    caixa.style.display =
        caixa.style.display === "none" || !caixa.style.display
            ? "block"
            : "none";
}


function renderizarAvisosAdmin(avisos) {
    avisosAdminCache = avisos;

    const flutuante = document.getElementById("avisos-admin-flutuante");
    const contador = document.getElementById("avisos-admin-contador");
    const lista = document.getElementById("avisos-admin-lista");
    const banner = document.getElementById("avisos-admin-banner");

    if (
        !flutuante
        || !contador
        || !lista
        || !banner
    ) {
        return;
    }

    if (!avisos.length) {
        flutuante.style.display = "none";
        banner.style.display = "none";
        return;
    }

    const avisosFixados = avisos.filter(
        (aviso) => Boolean(aviso.fixado)
    );

    const avisosComuns = avisos.filter(
        (aviso) => !aviso.fixado
    );

    contador.textContent = String(avisos.length);

    flutuante.style.display = "block";

    lista.innerHTML = avisos
        .map(renderizarCardAvisoAdmin)
        .join("");

    if (avisosFixados.length) {
        banner.style.display = "grid";
        banner.innerHTML = avisosFixados
            .map(renderizarCardAvisoAdmin)
            .join("");
    } else {
        banner.style.display = "none";
        banner.innerHTML = "";
    }
}


async function carregarAvisosAdmin() {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const forcar = arguments[0]?.forcar === true;

    if (
        !forcar
        && cacheAdminAindaValido(
            ultimoCarregamentoAvisosAdmin,
            TEMPO_CACHE_CURTO_ADMIN_MS
        )
    ) {
        return;
    }

    if (carregandoAvisosAdmin) {
        return;
    }

    carregandoAvisosAdmin = true;

    try {
        const avisos = await apiRequest(
            `/api/${tenantSlugLogado}/admin/avisos`,
            {
                auth: true,
            }
        );

        renderizarAvisosAdmin(avisos);

        ultimoCarregamentoAvisosAdmin = Date.now();

    } catch (erro) {
        console.error(
            "Erro ao carregar avisos da plataforma:",
            erro
        );

    } finally {
        carregandoAvisosAdmin = false;
    }
}


window.alternarCaixaAvisosAdmin = alternarCaixaAvisosAdmin;


async function dispensarAvisoAdmin(avisoId) {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/admin/avisos/${avisoId}/dispensar`,
            {
                method: "POST",
                auth: true,
            }
        );

        await carregarAvisosAdmin();

    } catch (erro) {
        console.error(
            "Erro ao dispensar aviso:",
            erro
        );
    }
}


window.dispensarAvisoAdmin = dispensarAvisoAdmin;

function traduzirTipoChamadoAdmin(tipo) {
    const mapa = {
        erro: "Erro",
        bug: "Bug",
        sugestao: "Sugestão",
        elogio: "Elogio",
        outro: "Outro",
    };

    return mapa[tipo] || "Erro";
}


function traduzirStatusChamadoAdmin(status) {
    const mapa = {
        aberto: "Aberto",
        em_analise: "Em análise",
        resolvido: "Resolvido",
        fechado: "Fechado",
    };

    return mapa[status] || "Aberto";
}


async function abrirModalHistoricoChamadosAdmin() {
    const modal = document.getElementById("modal-historico-chamados-admin");

    if (!modal) {
        return;
    }

    modal.style.display = "flex";

    await carregarChamadosAdmin();
}

function abrirModalChamadoAdmin(tipo = "erro") {
    const modal = document.getElementById("modal-chamado-admin");

    if (!modal) {
        exibirMensagemAdmin("Modal de chamado não encontrado no HTML.");
        return;
    }

    const campoTipo = document.getElementById("chamado-tipo");
    const campoTitulo = document.getElementById("chamado-titulo");
    const campoDescricao = document.getElementById("chamado-descricao");
    const campoContatoNome = document.getElementById("chamado-contato-nome");
    const campoContatoEmail = document.getElementById("chamado-contato-email");

    if (campoTipo) {
        campoTipo.value = tipo;
    }

    if (campoTitulo) {
        campoTitulo.value = "";
    }

    if (campoDescricao) {
        campoDescricao.value = "";
    }

    if (campoContatoNome) {
        campoContatoNome.value = "";
    }

    if (campoContatoEmail) {
        campoContatoEmail.value = "";
    }

    modal.style.display = "flex";
}


function fecharModalChamadoAdmin() {
    const modal = document.getElementById("modal-chamado-admin");

    if (modal) {
        modal.style.display = "none";
    }
}


async function criarChamadoAdmin(event) {
    event.preventDefault();

    if (!adminProntoParaRequisicao()) {
        return;
    }

    const tipo = document.getElementById("chamado-tipo").value;

    const titulo = document
        .getElementById("chamado-titulo")
        .value
        .trim();

    const descricao = document
        .getElementById("chamado-descricao")
        .value
        .trim();

    const contatoNome = document
        .getElementById("chamado-contato-nome")
        .value
        .trim();

    const contatoEmail = document
        .getElementById("chamado-contato-email")
        .value
        .trim();

    if (
        !titulo
        || titulo.length < 3
        || !descricao
        || descricao.length < 5
    ) {
        exibirMensagemAdmin("Informe título e descrição do chamado.");
        return;
    }

    const botao = document.getElementById("btn-criar-chamado-admin");

    botao.disabled = true;
    botao.textContent = "Enviando...";

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/admin/suporte/chamados`,
            {
                method: "POST",
                auth: true,
                body: {
                    tipo,
                    titulo,
                    descricao,
                    pagina_origem: window.location.href,
                    contato_nome: contatoNome || null,
                    contato_email: contatoEmail || null,
                },
            }
        );

        fecharModalChamadoAdmin();

        await carregarChamadosAdmin();

        exibirMensagemAdmin(
            "Operação realizada com sucesso.",
            "sucesso"
        );

    } catch (erro) {
        console.error(erro);

        exibirMensagemAdmin(
          montarMensagemErroComDiagnostico(
            erro.message || "Erro ao carregar dados.",
            erro,
          ),
        );

    } finally {
        botao.disabled = false;
        botao.textContent = "Enviar chamado";
    }
}


function formatarDataHoraChamadoAdmin(valor) {
    if (!valor) {
        return "-";
    }

    const data = new Date(valor);

    if (Number.isNaN(data.getTime())) {
        return String(valor);
    }

    return data.toLocaleString("pt-BR");
}


function escaparHtmlAdmin(valor) {
    return String(valor ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function renderizarChamadosAdmin(chamados) {
    const container = document.getElementById("lista-chamados-admin");

    if (!container) {
        return;
    }

    chamadosAdminCache = Array.isArray(chamados)
        ? chamados
        : [];

    if (!chamadosAdminCache.length) {

        container.innerHTML = criarEstadoVazioAdmin({
          icone: "◇",
          titulo: "Nenhum chamado aberto ainda",
          descricao:
            "Quando você abrir um chamado de suporte, ele aparecerá aqui.",
          textoBotao: "",
          secaoDestino: "",
        });

        return;
    }

    container.innerHTML = chamadosAdminCache
        .map((chamado) => {
            const resposta = chamado.resposta_suporte
                ? `
                    <div class="resposta-suporte-admin">
                        <strong>Resposta do suporte:</strong><br>
                        ${escaparHtmlAdmin(chamado.resposta_suporte)}
                    </div>
                `
                : `
                    <div class="resposta-suporte-admin">
                        <strong>Resposta do suporte:</strong><br>
                        Ainda sem resposta da Engenharia de Bits.
                    </div>
                `;

            return `
                <article class="chamado-admin-card">
                    <div class="chamado-admin-card-topo">
                        <div>
                            <h3>
                                #${chamado.id} — ${escaparHtmlAdmin(chamado.titulo)}
                            </h3>

                            <span class="badge-chamado status-${chamado.status}">
                                ${traduzirStatusChamadoAdmin(chamado.status)}
                            </span>
                        </div>

                        <span class="badge-chamado">
                            ${traduzirTipoChamadoAdmin(chamado.tipo)}
                        </span>
                    </div>

                    <p>${escaparHtmlAdmin(chamado.descricao)}</p>

                    ${resposta}

                    <div class="chamado-meta">
                        <span>Tenant: ${escaparHtmlAdmin(chamado.tenant_slug)}</span>
                        <span>Status: ${traduzirStatusChamadoAdmin(chamado.status)}</span>
                        <span>Criado em: ${formatarDataHoraChamadoAdmin(chamado.criado_em)}</span>
                        <span>Atualizado em: ${formatarDataHoraChamadoAdmin(chamado.atualizado_em)}</span>
                    </div>
                </article>
            `;
        })
        .join("");
}


function definirLoadingAgendamentosAdmin(ativo) {
    const tabela = document.getElementById("lista-agendamentos-admin");

    if (!tabela) {
        return;
    }

    if (ativo) {
        tabela.innerHTML = `
            <tr>
                <td colspan="8" class="estado-vazio-admin carregando">
                    Carregando agendamentos
                </td>
            </tr>
        `;
    }
}


async function carregarChamadosAdmin() {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const container = document.getElementById("lista-chamados-admin");

    if (container) {
        container.innerHTML = `
            <p class="horarios-vazios">
                Carregando chamados...
            </p>
        `;
    }

    try {
        const chamados = await apiRequest(
            `/api/${tenantSlugLogado}/admin/suporte/chamados`,
            {
                auth: true,
            }
        );

        renderizarChamadosAdmin(chamados);

    } catch (erro) {
        console.error(
            "Erro ao carregar chamados:",
            erro
        );

        if (container) {
            container.innerHTML = criarEstadoVazioAdmin({
              icone: "!",
              titulo: "Não foi possível carregar os chamados",
              descricao: "Tente novamente em alguns instantes.",
              textoBotao: "",
              secaoDestino: "",
            });
        }
    }
}


async function abrirModalHistoricoChamadosAdmin() {
    const modal = document.getElementById("modal-historico-chamados-admin");

    if (!modal) {
        return;
    }

    modal.style.display = "flex";

    await carregarChamadosAdmin();
}


function fecharModalHistoricoChamadosAdmin() {
    const modal = document.getElementById("modal-historico-chamados-admin");

    if (modal) {
        modal.style.display = "none";
    }
}


window.abrirModalChamadoAdmin = abrirModalChamadoAdmin;
window.fecharModalChamadoAdmin = fecharModalChamadoAdmin;
window.criarChamadoAdmin = criarChamadoAdmin;
window.carregarChamadosAdmin = carregarChamadosAdmin;
window.abrirModalHistoricoChamadosAdmin = abrirModalHistoricoChamadosAdmin;
window.fecharModalHistoricoChamadosAdmin = fecharModalHistoricoChamadosAdmin;


function obterUrlPublicaTenantAdmin() {
  const origem = window.location.origin;
  const caminhoBase = window.location.pathname.replace("admin.html", "");

  return `${origem}${caminhoBase}agendamento.html?tenant=${encodeURIComponent(tenantSlugLogado)}`;
}

function copiarLinkPublicoAdmin() {
  const link = obterUrlPublicaTenantAdmin();

  navigator.clipboard
    .writeText(link)
    .then(function () {
      exibirMensagemAdmin(
        "Link público copiado. Agora você pode enviar para seus clientes.",
      );
    })
    .catch(function () {
      exibirMensagemAdmin(`Seu link público é: ${link}`);
    });
}

window.copiarLinkPublicoAdmin = copiarLinkPublicoAdmin;

function irParaSecaoAdminOnboarding(secaoId) {
  if (typeof mostrarSecaoAdmin === "function") {
    mostrarSecaoAdmin(secaoId);

    setTimeout(function () {
      ultimoCarregamentoOnboardingAdmin = 0;
      carregarOnboardingAdmin();
    }, 700);

    return;
  }

  const elemento = document.getElementById(secaoId);

  if (elemento) {
    elemento.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  setTimeout(function () {
    ultimoCarregamentoOnboardingAdmin = 0;
    carregarOnboardingAdmin();
  }, 700);
}



async function carregarResumoOnboardingAdmin() {
  if (!tenantSlugLogado) {
    return null;
  }

  const [
    resultadoConfig,
    resultadoServicos,
    resultadoProfissionais,
    resultadoAgendamentos,
  ] = await Promise.allSettled([
    apiRequest(`/api/${tenantSlugLogado}/configuracoes`, {
      method: "GET",
      auth: true,
    }),
    apiRequest(`/api/${tenantSlugLogado}/servicos`, {
      method: "GET",
      auth: true,
    }),
    apiRequest(`/api/${tenantSlugLogado}/profissionais`, {
      method: "GET",
      auth: true,
    }),
    apiRequest(`/api/${tenantSlugLogado}/admin/agendamentos`, {
      method: "GET",
      auth: true,
    }),
  ]);

  const config =
    resultadoConfig.status === "fulfilled" ? resultadoConfig.value : null;

  const servicosResposta =
    resultadoServicos.status === "fulfilled" ? resultadoServicos.value : [];

  const profissionaisResposta =
    resultadoProfissionais.status === "fulfilled"
      ? resultadoProfissionais.value
      : [];

  const agendamentosResposta =
    resultadoAgendamentos.status === "fulfilled"
      ? resultadoAgendamentos.value
      : [];

  const servicos = Array.isArray(servicosResposta)
    ? servicosResposta
    : servicosResposta?.servicos || [];

  const profissionais = Array.isArray(profissionaisResposta)
    ? profissionaisResposta
    : profissionaisResposta?.profissionais || [];

  const agendamentos = Array.isArray(agendamentosResposta)
    ? agendamentosResposta
    : agendamentosResposta?.agendamentos || [];

  return {
    config,
    totalServicos: servicos.length,
    totalProfissionais: profissionais.length,
    totalAgendamentos: agendamentos.length,
  };
}

function montarChecklistOnboardingAdmin(resumo) {
  const config = resumo?.config || {};

  const possuiDadosBasicos = Boolean(
    String(
      config?.nome_publico ||
        config?.nome_empresa ||
        config?.nome ||
        config?.nome_estabelecimento ||
        "",
    ).trim(),
  );

  const possuiServicos = Number(resumo?.totalServicos || 0) > 0;
  const possuiProfissionais = Number(resumo?.totalProfissionais || 0) > 0;
  const possuiAgendamentos = Number(resumo?.totalAgendamentos || 0) > 0;

  const possuiConfiguracoes = Boolean(
        config &&
        Number(config?.abertura || 0) >= 0 &&
        Number(config?.fechamento || 0) > 0,
    );

  return [
    {
      id: "horarios",
      titulo: "Conferir horários de atendimento",
      descricao:
        "Garanta que os horários estão corretos antes de divulgar o link.",
      concluido: possuiDadosBasicos && possuiConfiguracoes,
      acaoTexto: "Conferir horários",
      acao: function () {
        irParaSecaoAdminOnboarding("secao-configuracoes");
      },
    },
    {
      id: "servicos",
      titulo: "Cadastrar serviços",
      descricao:
        "Adicione serviços com duração e preço para liberar a agenda pública.",
      concluido: possuiServicos,
      acaoTexto: "Cadastrar serviços",
      acao: function () {
        irParaSecaoAdminOnboarding("secao-servicos");
      },
    },
    {
      id: "profissionais",
      titulo: "Cadastrar profissionais",
      descricao: "Inclua os profissionais que atenderão os clientes.",
      concluido: possuiProfissionais,
      acaoTexto: "Cadastrar profissionais",
      acao: function () {
        irParaSecaoAdminOnboarding("secao-profissionais");
      },
    },
    {
      id: "horarios",
      titulo: "Conferir horários de atendimento",
      descricao:
        "Garanta que os horários estão corretos antes de divulgar o link.",
      concluido: possuiConfiguracoes,
      acaoTexto: "Conferir horários",
      acao: function () {
        irParaSecaoAdminOnboarding("secao-configuracoes");
      },
    },
    {
      id: "link",
      titulo: "Copiar link público de agendamento",
      descricao: "Envie o link para clientes pelo WhatsApp, Instagram ou site.",
      concluido: Boolean(tenantSlugLogado && tenantSlugLogado.trim()),
      acaoTexto: "Copiar link",
      acao: copiarLinkPublicoAdmin,
    },
    {
      id: "primeiro-agendamento",
      titulo: "Receber o primeiro agendamento",
      descricao:
        "Quando o primeiro cliente agendar, este passo será concluído automaticamente.",
      concluido: possuiAgendamentos,
      acaoTexto: "Abrir agenda pública",
      acao: function () {
        window.open(obterUrlPublicaTenantAdmin(), "_blank");
      },
    },
  ];
}

function obterChaveOnboardingDispensadoAdmin() {
  return `bitsagenda_onboarding_dispensado_${tenantSlugLogado || "sem_tenant"}`;
}

function dispensarOnboardingAdmin() {
  localStorage.setItem(obterChaveOnboardingDispensadoAdmin(), "sim");

  const card = document.getElementById("card-onboarding-admin");

  if (card) {
    card.style.display = "none";
  }

  exibirMensagemAdmin("Checklist de primeiros passos dispensado.");
}

function renderizarOnboardingAdminComResumo(resumo) {
  const card = document.getElementById("card-onboarding-admin");
  const lista = document.getElementById("onboarding-admin-lista");
  const progresso = document.getElementById("onboarding-admin-progresso");

  if (!card || !lista || !progresso || !tenantSlugLogado) {
    return;
  }

//   const dispensado = localStorage.getItem(
//     obterChaveOnboardingDispensadoAdmin(),
//   );

//   if (dispensado === "sim") {
//     card.style.display = "none";
//     return;
//   }

  const itens = montarChecklistOnboardingAdmin(resumo);

  const totalConcluido = itens.filter(function (item) {
    return item.concluido;
  }).length;

  const itensPendentes = itens.filter(function (item) {
    return !item.concluido;
  });

  if (!itensPendentes.length) {
    card.style.display = "none";
    return;
  }

  card.style.display = "block";

  progresso.textContent =
    totalConcluido === 1
      ? `${totalConcluido}/${itens.length} concluído`
      : `${totalConcluido}/${itens.length} concluídos`;

  const proximoItem = itensPendentes[0];

  lista.innerHTML = `
        <div class="onboarding-admin-compacto">
            <div class="onboarding-admin-compacto-info">
                <span class="onboarding-admin-status">${totalConcluido + 1}</span>

                <div>
                    <strong>Próximo passo: ${proximoItem.titulo}</strong>
                    <p>${proximoItem.descricao}</p>
                </div>
            </div>

            <div class="onboarding-admin-compacto-acoes">
                <button
                    type="button"
                    class="btn-secondary btn-onboarding-admin"
                    data-onboarding-id="${proximoItem.id}"
                >
                    ${proximoItem.acaoTexto}
                </button>


            </div>
        </div>
    `;

  document.querySelectorAll("[data-onboarding-id]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      const id = botao.getAttribute("data-onboarding-id");

      const item = itens.find(function (checklistItem) {
        return checklistItem.id === id;
      });

      if (item && typeof item.acao === "function") {
        item.acao();
      }
    });
  });
}

async function carregarOnboardingAdmin() {
  if (onboardingAdminCarregando || !tenantSlugLogado) {
    return;
  }

//   if (
//     Date.now() - ultimoCarregamentoOnboardingAdmin <
//     TEMPO_CACHE_ONBOARDING_ADMIN_MS
//   ) {
//     return;
//   }

  onboardingAdminCarregando = true;

  const lista = document.getElementById("onboarding-admin-lista");

  if (lista) {
    lista.innerHTML = "Carregando checklist...";
  }

  try {
    const resumo = await carregarResumoOnboardingAdmin();

    renderizarOnboardingAdminComResumo(resumo);

    ultimoCarregamentoOnboardingAdmin = Date.now();
  } catch (erro) {
    console.error("Erro ao carregar onboarding admin:", erro);

    if (lista) {
      lista.innerHTML = `
                <div class="onboarding-admin-item">
                    <div class="onboarding-admin-item-info">
                        <span class="onboarding-admin-status">!</span>
                        <div>
                            <h4>Não foi possível carregar o checklist</h4>
                            <p>Atualize a página ou tente novamente em alguns instantes.</p>
                        </div>
                    </div>
                </div>
            `;
    }
  } finally {
    onboardingAdminCarregando = false;
  }
}

window.carregarOnboardingAdmin = carregarOnboardingAdmin;


function iniciarPainel() {
  if (!existeSessaoLocal()) {
    document.getElementById("tela-login").style.display = "flex";

    document.getElementById("painel-principal").style.display = "none";

    return;
  }

  tenantSlugLogado = sincronizarTenantAdminComToken();

  if (!tenantSlugLogado) {
    tenantSlugLogado = obterTenantLogado();
  }

  if (tenantSlugLogado) {
    localStorage.setItem("gesto_tenant", tenantSlugLogado);
  }

  atualizarUrlTenantAdmin();

  if (!tenantSlugLogado) {
    exibirMensagemAdmin("Sessão inválida. Faça login novamente.");
    fazerLogout();
    return;
  }

  document.getElementById("tela-login").style.display = "none";

  document.getElementById("painel-principal").style.display = "block";

  document.getElementById("tag-tenant").innerText = `@${tenantSlugLogado}`;

  atualizarLinkPublico();
  registrarListenersDePreview();
  registrarListenersCRM();
  registrarListenersBloqueiosAgenda();
  registrarListenersAgendaVisual();
  inicializarNavegacaoAdmin();

  carregarAvisosAdmin();
  tratarRetornoCadastroAdmin();
  tratarRetornoPagamentoAdmin();
  carregarAssinaturaAdmin();
  carregarOnboardingAdmin();
  iniciarMonitorNovosAgendamentos();
}

    async function atualizarStatusAgendamento(id, status) {
        const confirmarAlteracao = confirm(
            `Deseja marcar este agendamento como "${traduzirStatusAgendamento(status)}"?`
        );

        if (!confirmarAlteracao) {
            return;
        }

        try {
            await apiRequest(
                `/api/${tenantSlugLogado}/admin/agendamentos/${id}/status`,
                {
                    method: "PUT",
                    auth: true,
                    body: {
                        status,
                    },
                }
            );

            exibirMensagemPainel(
                "Status do agendamento atualizado com sucesso."
            );

            await carregarAgendamentos();
            await carregarAgendaVisualDia({
                forcar: true,
            });

            invalidarSecoesAdmin([
                "secao-dashboard",
                "secao-agenda",
                "secao-clientes-crm",
            ]);

        } catch (erro) {
            tratarErro(erro);
        }
    }


    window.atualizarStatusAgendamento = atualizarStatusAgendamento;



function registrarListenersDePreview() {
    if (listenersDePreviewRegistrados) {
        return;
    }

    listenersDePreviewRegistrados = true;

    [
        "nome-publico",
        "endereco",
        "logo-url",
        "logomarca-url",
    ].forEach((id) => {
        const elemento = document.getElementById(id);

        if (elemento) {
            elemento.addEventListener(
                "input",
                atualizarPreviewMarca
            );
        }
    });

    const inputLogoArquivo = document
        .getElementById("logo-arquivo");

    if (inputLogoArquivo) {
        inputLogoArquivo.addEventListener(
            "change",
            () => uploadImagemMarca(
                "logo-arquivo",
                "logo-url",
                "logo"
            )
        );
    }

    const inputLogomarcaArquivo = document
        .getElementById("logomarca-arquivo");

    if (inputLogomarcaArquivo) {
        inputLogomarcaArquivo.addEventListener(
            "change",
            () => uploadImagemMarca(
                "logomarca-arquivo",
                "logomarca-url",
                "logomarca"
            )
        );
    }
}


/* =========================================================
   CONFIGURAÇÕES
========================================================= */

async function carregarStatusAssinaturaAdmin() {
    await carregarConfiguracaoAtual();
}


function empresaAdminEstaBloqueadaManualmente(config) {
    if (!config) {
        return false;
    }

    const statusAssinatura = String(
        config.status_assinatura || ""
    ).trim().toLowerCase();

    return (
        config.empresa_desativada === true
        || statusAssinatura === "desativada"
    );
}


function obterMensagemBloqueioAdmin(config) {
    const statusAssinatura = String(
        config?.status_assinatura || ""
    ).trim().toLowerCase();

    if (
        config?.empresa_desativada === true
        || statusAssinatura === "desativada"
    ) {
        return (
            "Esta empresa foi desativada manualmente pela administração da plataforma. " +
            "A agenda pública está bloqueada e pagamentos não reativam a conta. " +
            "Somente o Painel Mestre SaaS pode reativar o acesso."
        );
    }

    if (config?.acesso_liberado === false) {
        return (
            "O acesso público desta empresa está temporariamente bloqueado. " +
            "Verifique o status do plano ou entre em contato com o suporte da plataforma."
        );
    }

    return "";
}


function atualizarAvisoBloqueioAdmin(config) {
    const aviso = document.getElementById("aviso-bloqueio-admin");
    const texto = document.getElementById("texto-aviso-bloqueio-admin");

    if (!aviso || !texto) {
        return;
    }

    const bloqueada = empresaAdminEstaBloqueadaManualmente(config);

    if (!bloqueada) {
        aviso.style.display = "none";
        texto.innerText = "";
        atualizarBotoesPagamentoAdminBloqueio(false);
        return;
    }

    texto.innerText = obterMensagemBloqueioAdmin(config);
    aviso.style.display = "block";

    atualizarBotoesPagamentoAdminBloqueio(true);
}


function atualizarBotoesPagamentoAdminBloqueio(bloquear) {
    const cards = document.querySelectorAll(".plano-admin-card");

    cards.forEach((card) => {
        card.classList.toggle(
            "bloqueado-pagamento-admin",
            bloquear
        );

        const botoes = card.querySelectorAll("button");

        botoes.forEach((botao) => {
            botao.disabled = bloquear;

            if (bloquear) {
                botao.title = (
                    "Conta bloqueada manualmente. " +
                    "Somente o Painel Mestre SaaS pode reativar."
                );
            } else {
                botao.removeAttribute("title");
            }
        });
    });
}

async function carregarConfiguracaoAtual() {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const forcar = arguments[0]?.forcar === true;

    if (
        !forcar
        && configuracoesAdminCache
        && Object.keys(configuracoesAdminCache).length > 0
        && cacheAdminAindaValido(
            ultimoCarregamentoConfiguracaoAdmin,
            TEMPO_CACHE_CURTO_ADMIN_MS
        )
    ) {
        atualizarAvisoBloqueioAdmin(configuracoesAdminCache);
        return configuracoesAdminCache;
    }

    if (carregandoConfiguracaoAdmin) {
        return configuracoesAdminCache;
    }

    carregandoConfiguracaoAdmin = true;



    try {
        const config = await apiRequest(
            `/api/${tenantSlugLogado}/configuracoes`,
            {
                auth: true
            }
        );

        configuracoesAdminCache = config || {};

        atualizarAvisoBloqueioAdmin(configuracoesAdminCache);

        const campoAbertura = document.getElementById("hora-abertura");
        const campoFechamento = document.getElementById("hora-fechamento");
        const campoCorTema = document.getElementById("cor-tema");
        const campoCorFundo = document.getElementById("cor-fundo");
        const campoTelefone = document.getElementById("telefone-barbearia");
        const campoNomePublico = document.getElementById("nome-publico");
        const campoLogoUrl = document.getElementById("logo-url");
        const campoLogomarcaUrl = document.getElementById("logomarca-url");
        const campoWhatsapp = document.getElementById("whatsapp-comercial");
        const campoEndereco = document.getElementById("endereco");
        const campoGoogleMaps = document.getElementById("google-maps-url");
        const campoMensagemPublica = document.getElementById("mensagem-publica");
        const campoInstrucoes = document.getElementById("instrucoes");
        const campoInstagram = document.getElementById("instagram-url");
        const campoFacebook = document.getElementById("facebook-url");
        const campoTiktok = document.getElementById("tiktok-url");
        const campoSite = document.getElementById("site-url");
        const campoLimiteCancelamento = document.getElementById(
            "limite-cancelamento-horas"
        );

        if (campoAbertura) campoAbertura.value = config.abertura ?? 9;
        if (campoFechamento) campoFechamento.value = config.fechamento ?? 18;
        if (campoCorTema) campoCorTema.value = config.cor_tema || "#f59e0b";
        if (campoCorFundo) campoCorFundo.value = config.cor_fundo || "#0f172a";
        if (campoTelefone) campoTelefone.value = config.telefone || "";

        if (campoNomePublico) campoNomePublico.value = config.nome_publico || "";
        if (campoLogoUrl) campoLogoUrl.value = config.logo_url || "";
        if (campoLogomarcaUrl) campoLogomarcaUrl.value = config.logomarca_url || "";

        if (campoWhatsapp) {
            campoWhatsapp.value = config.whatsapp_comercial || config.telefone || "";
        }

        if (campoEndereco) campoEndereco.value = config.endereco || "";
        if (campoGoogleMaps) campoGoogleMaps.value = config.google_maps_url || "";
        if (campoMensagemPublica) campoMensagemPublica.value = config.mensagem_publica || "";
        if (campoInstrucoes) campoInstrucoes.value = config.instrucoes || "";
        if (campoInstagram) campoInstagram.value = config.instagram_url || "";
        if (campoFacebook) campoFacebook.value = config.facebook_url || "";
        if (campoTiktok) campoTiktok.value = config.tiktok_url || "";
        if (campoSite) campoSite.value = config.site_url || "";
        if (campoLimiteCancelamento) {
            campoLimiteCancelamento.value =
                config.limite_cancelamento_horas ?? 3;
        }

        marcarCheckbox(
            "captar-whatsapp-lembretes",
            config.captar_whatsapp_lembretes ?? true
        );

        marcarCheckbox(
            "captar-whatsapp-promocoes",
            config.captar_whatsapp_promocoes ?? false
        );

        atualizarPreviewMarca();

        ultimoCarregamentoConfiguracaoAdmin = Date.now();

        return configuracoesAdminCache;

    } catch (erro) {
        console.warn(
            "Configurações ainda não cadastradas:",
            erro
        );

        tratarErroAdmin(erro);

    } finally {
        carregandoConfiguracaoAdmin = false;
    }
}


async function salvarConfiguracao(opcoes = {}) {
    const abertura = Number(
        document.getElementById("hora-abertura").value || 9
    );

    const fechamento = Number(
        document.getElementById("hora-fechamento").value || 18
    );

    const whatsappComercial = valorCampo("whatsapp-comercial", "");
    const telefone = valorCampo("telefone-barbearia", whatsappComercial);

    try {
        const payload = {
            abertura,
            fechamento,
            limite_cancelamento_horas: Number(
                valorCampo("limite-cancelamento-horas", 3)
            ),
            cor_tema: valorCampo("cor-tema", "#f59e0b"),
            cor_fundo: valorCampo("cor-fundo", "#0f172a"),
            endereco: valorCampo(
                "endereco",
                configuracaoAtual.endereco || ""
            ),
            logo_url: valorCampo(
                "logo-url",
                configuracaoAtual.logo_url || ""
            ),
            instrucoes: valorCampo(
                "instrucoes",
                configuracaoAtual.instrucoes || ""
            ),
            telefone,

            nome_publico: valorCampo(
                "nome-publico",
                configuracaoAtual.nome_publico || ""
            ),
            logomarca_url: valorCampo(
                "logomarca-url",
                configuracaoAtual.logomarca_url || ""
            ),

            whatsapp_comercial: whatsappComercial,
            instagram_url: valorCampo(
                "instagram-url",
                configuracaoAtual.instagram_url || ""
            ),
            facebook_url: valorCampo(
                "facebook-url",
                configuracaoAtual.facebook_url || ""
            ),
            tiktok_url: valorCampo(
                "tiktok-url",
                configuracaoAtual.tiktok_url || ""
            ),
            site_url: valorCampo(
                "site-url",
                configuracaoAtual.site_url || ""
            ),
            google_maps_url: valorCampo(
                "google-maps-url",
                configuracaoAtual.google_maps_url || ""
            ),

            mensagem_publica: valorCampo(
                "mensagem-publica",
                configuracaoAtual.mensagem_publica || ""
            ),
            captar_whatsapp_lembretes: checkboxMarcado(
                "captar-whatsapp-lembretes"
            ),
            captar_whatsapp_promocoes: checkboxMarcado(
                "captar-whatsapp-promocoes"
            ),
        };

        await apiRequest(
            `/api/${tenantSlugLogado}/configuracoes`,
            {
                method: "POST",
                auth: true,
                body: payload,
            }
        );

        configuracaoAtual = {
            ...configuracaoAtual,
            ...payload,
        };

        atualizarPreviewMarca();

        if (!opcoes.silencioso) {
            exibirMensagemPainel("Configurações salvas com sucesso.");

            ultimoCarregamentoOnboardingAdmin = 0;
            await carregarOnboardingAdmin();
        }

    } catch (erro) {
        tratarErro(erro);
    }
}


  /* =========================================================
   PROFISSIONAIS
========================================================= */

async function carregarEquipe() {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const area = document.getElementById("lista-equipe");

    try {
        const equipe = await apiRequest(
            `/api/${tenantSlugLogado}/profissionais`
        );

        area.innerHTML = "";

        if (!equipe.length) {
            area.innerHTML = criarEstadoVazioAdmin({
              icone: "◎",
              titulo: "Nenhum profissional cadastrado ainda",
              descricao:
                "Adicione pelo menos um profissional para que os clientes possam escolher quem irá atender.",
              textoBotao: "Cadastrar profissional",
              secaoDestino: "secao-profissionais",
            });

            return;
        }

        for (const profissional of equipe) {
            const div = document.createElement("div");

            div.className = "item-lista";

            div.innerHTML = `
                <span>${profissional.nome}</span>

                <button
                    class="btn-del-mini"
                    onclick="deletarProfissional(${profissional.id})"
                >
                    Remover
                </button>
            `;

            area.appendChild(div);
        }

    } catch (erro) {
        tratarErro(erro);
    }
}


async function salvarProfissional() {
    const input = document.getElementById("novo-prof-nome");
    const nome = input.value.trim();

    if (!nome) {
        exibirMensagemAdmin("Informe o nome do profissional.");
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/profissionais`,
            {
                method: "POST",
                auth: true,
                body: { nome }
            }
        );

        input.value = "";

        await carregarEquipe();
        ultimoCarregamentoOnboardingAdmin = 0;
        await carregarOnboardingAdmin();

        invalidarSecoesAdmin([
            "secao-dashboard",
            "secao-configuracoes",
            "secao-agenda",
            "secao-bloqueios-agenda",
        ]);

        exibirMensagemPainel(
            "Profissional adicionado com sucesso."
        );

    } catch (erro) {
        tratarErro(erro);
    }
}


async function deletarProfissional(id) {
    if (!confirm("Deseja remover este profissional?")) {
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/profissionais/${id}`,
            {
                method: "DELETE",
                auth: true
            }
        );

        await carregarEquipe();

        exibirMensagemPainel(
            "Profissional removido com sucesso."
        );

    } catch (erro) {
        tratarErro(erro);
    }
}


/* =========================================================
   SERVIÇOS
========================================================= */

async function carregarServicos() {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const area = document.getElementById("lista-cardapio");

    try {
        const servicos = await apiRequest(
            `/api/${tenantSlugLogado}/servicos`
        );

        area.innerHTML = "";

        if (!servicos.length) {
            area.innerHTML = criarEstadoVazioAdmin({
              icone: "✦",
              titulo: "Nenhum serviço cadastrado ainda",
              descricao:
                "Cadastre serviços com preço e duração para liberar sua agenda pública.",
              textoBotao: "Cadastrar primeiro serviço",
              secaoDestino: "secao-servicos",
            });

            return;
        }

        for (const servico of servicos) {
            const div = document.createElement("div");

            div.className = "item-lista";

            const valorFormatado = formatarMoeda(
                servico.preco
            );

            div.innerHTML = `
                <span>
                    <strong>${servico.nome}</strong>
                    <br>
                    <small style="color: var(--texto-secundario);">
                        ${servico.duracao} min
                    </small>
                </span>

                <div>
                    <span
                        style="
                            color: var(--cor-sucesso);
                            margin-right: 15px;
                            font-weight: 800;
                        "
                    >
                        ${valorFormatado}
                    </span>

                    <button
                        class="btn-del-mini"
                        onclick="deletarServico(${servico.id})"
                    >
                        Remover
                    </button>
                </div>
            `;

            area.appendChild(div);
        }

    } catch (erro) {
        tratarErro(erro);
    }
}


async function salvarServico() {
    const inputNome = document.getElementById("novo-servico-nome");
    const inputPreco = document.getElementById("novo-servico-preco");
    const inputDuracao = document.getElementById("novo-servico-duracao");

    const nome = inputNome.value.trim();

    const preco = Number(
        inputPreco.value.replace(",", ".")
    );

    const duracao = Number(
        inputDuracao.value
    );

    if (!nome || preco <= 0 || duracao <= 0) {
        exibirMensagemAdmin(
            "Informe um serviço, um preço positivo e uma duração válida."
        );

        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/servicos`,
            {
                method: "POST",
                auth: true,
                body: {
                    nome,
                    preco,
                    duracao
                }
            }
        );

        inputNome.value = "";
        inputPreco.value = "";
        inputDuracao.value = "";

        await carregarServicos();
        ultimoCarregamentoOnboardingAdmin = 0;
        await carregarOnboardingAdmin();

        invalidarSecoesAdmin([
            "secao-dashboard",
            "secao-configuracoes",
            "secao-agenda",
            "secao-bloqueios-agenda",
        ]);

        exibirMensagemPainel(
            "Serviço adicionado com sucesso."
        );

    } catch (erro) {
        tratarErro(erro);
    }
}


async function deletarServico(id) {
    if (!confirm("Deseja remover este serviço?")) {
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/servicos/${id}`,
            {
                method: "DELETE",
                auth: true
            }
        );

        await carregarServicos();

        exibirMensagemPainel(
            "Serviço removido com sucesso."
        );

    } catch (erro) {
        tratarErro(erro);
    }
}


/* =========================================================
   AGENDA E FATURAMENTO
========================================================= */

async function carregarAgendamentos() {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const forcar = arguments[0]?.forcar === true;

    if (
        !forcar
        && cacheAdminAindaValido(
            ultimoCarregamentoAgendamentosAdmin,
            TEMPO_CACHE_AGENDAMENTOS_ADMIN_MS
        )
    ) {
        return;
    }

    if (carregandoAgendamentosAdmin) {
        return;
    }

    carregandoAgendamentosAdmin = true;

    definirLoadingAgendamentosAdmin(true);

    const tbody = document.getElementById("lista-agendamentos");

    const dataInicio = valorCampo("filtro-data-inicio", "");
    const dataFim = valorCampo("filtro-data-fim", "");

    const parametros = new URLSearchParams();

    if (dataInicio) {
        parametros.set("data_inicio", dataInicio);
    }

    if (dataFim) {
        parametros.set("data_fim", dataFim);
    }

    const query = parametros.toString();

    const endpoint = query
        ? `/api/${tenantSlugLogado}/admin/agendamentos?${query}`
        : `/api/${tenantSlugLogado}/admin/agendamentos`;

    try {
        const dados = await apiRequest(
            endpoint,
            {
                auth: true
            }
        );

        const total = dados.total_agendamentos || 0;
        const faturamento = Number(
            dados.faturamento_previsto || 0
        );

        const ticketMedio = total > 0
            ? faturamento / total
            : 0;

        document.getElementById("visor-total-agendamentos").textContent =
            total;

        document.getElementById("visor-faturamento").textContent =
            formatarMoeda(faturamento);

        document.getElementById("visor-ticket-medio").textContent =
            formatarMoeda(ticketMedio);

        tbody.innerHTML = "";

        if (!dados.agendamentos || !dados.agendamentos.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8">
                        ${criarEstadoVazioAdmin({
                        icone: "◴",
                        titulo: "Nenhum agendamento recebido ainda",
                        descricao:
                            "Copie o link público e envie para seus clientes começarem a agendar.",
                        textoBotao: "Copiar link público",
                        secaoDestino: "secao-dashboard",
                        })}
                    </td>
                </tr>
            `;

            // tbody.innerHTML = `
            //     <tr>
            //         <td colspan="7" class="mensagem-tabela">
            //             Nenhum agendamento encontrado.
            //         </td>
            //     </tr>
            // `;

            return;
        }

        for (const agendamento of dados.agendamentos) {
            const tr = document.createElement("tr");

            const ultimoVisto = obterUltimoAgendamentoVisto();

            if (Number(agendamento.id) > ultimoVisto) {
                tr.classList.add("linha-agendamento-novo");
            }

            const colunas = [
                formatarDataBR(agendamento.data),
                agendamento.horario,
                agendamento.cliente_nome,
                agendamento.telefone_cliente || "-",
                agendamento.servico,
                agendamento.profissional,
                formatarMoeda(agendamento.valor),
            ];

            for (const valor of colunas) {
                const td = document.createElement("td");
                td.textContent = valor || "-";
                tr.appendChild(td);
            }

            const status = agendamento.status || "confirmado";

            const tdStatus = document.createElement("td");
            tdStatus.innerHTML = `
                <span class="badge-status ${classeStatusAgendamento(status)}">
                    ${traduzirStatusAgendamento(status)}
                </span>
            `;
            tr.appendChild(tdStatus);

            const tdAcoes = document.createElement("td");
            const observacaoEscapada = String(
                agendamento.observacao_interna || ""
            ).replace(/'/g, "\\'");

            tdAcoes.innerHTML = `
                <div class="acoes-agendamento">
                    <button type="button" onclick="atualizarStatusAgendamento(${agendamento.id}, 'confirmado')">
                        Confirmar
                    </button>

                    <button type="button" onclick="atualizarStatusAgendamento(${agendamento.id}, 'concluido')">
                        Concluir
                    </button>

                    <button type="button" onclick="cancelarAgendamentoComMotivo(${agendamento.id})">
                        Cancelar
                    </button>

                    <button type="button" onclick="atualizarStatusAgendamento(${agendamento.id}, 'faltou')">
                        Faltou
                    </button>

                    <button type="button" onclick="abrirHistoricoCliente('${agendamento.telefone_cliente || ""}')">
                        Histórico
                    </button>

                    <button type="button" onclick="atualizarObservacaoAgendamento(${agendamento.id}, '${observacaoEscapada}')">
                        Obs.
                    </button>

                    <div class="acoes-whatsapp-agendamento">
                        <button
                            type="button"
                            class="btn-whatsapp-agendamento"
                            onclick="abrirWhatsAppAgendamento(${agendamento.id}, 'confirmacao')"
                        >
                            Confirmar no WhatsApp
                        </button>

                        <button
                            type="button"
                            class="btn-whatsapp-secundario"
                            onclick="abrirWhatsAppAgendamento(${agendamento.id}, 'remarcacao')"
                        >
                            Remarcar
                        </button>

                        <button
                            type="button"
                            class="btn-whatsapp-secundario"
                            onclick="abrirWhatsAppAgendamento(${agendamento.id}, 'agradecimento')"
                        >
                            Agradecer
                        </button>
                    </div>
                </div>
            `;

            tr.appendChild(tdAcoes);

            tbody.appendChild(tr);

            if (agendamento.motivo_cancelamento || agendamento.observacao_interna) {
                const trDetalhes = document.createElement("tr");

                trDetalhes.innerHTML = `
                    <td colspan="9" class="linha-detalhes-agendamento">
                        ${
                            agendamento.motivo_cancelamento
                                ? `<strong>Cancelamento:</strong> ${agendamento.motivo_cancelamento}`
                                : ""
                        }

                        ${
                            agendamento.observacao_interna
                                ? `<br><strong>Observação interna:</strong> ${agendamento.observacao_interna}`
                                : ""
                        }
                    </td>
                `;

                tbody.appendChild(trDetalhes);
            }


            const ticketMedio = total > 0
            ? faturamento / total
            : 0;

            agendamentosAdminCache = dados.agendamentos || [];


            atualizarIndicadorNovosAgendamentos(agendamentosAdminCache);

            document.getElementById("visor-total-agendamentos").textContent =
                total;
        }

        ultimoCarregamentoAgendamentosAdmin = Date.now();

    } catch (erro) {
        if (erro.status === 404) {
            console.warn(
                "Rota administrativa de agendamentos ainda não foi criada."
            );

            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="mensagem-tabela">
                        A rota de agenda administrativa ainda não está disponível.
                    </td>
                </tr>
            `;

            return;
        }

        tratarErroAdmin(erro);
    }

    finally {
        carregandoAgendamentosAdmin = false;
    }
}

async function atualizarStatusAgendamento(id, status) {
    const confirmarAlteracao = confirm(
        `Deseja marcar este agendamento como "${traduzirStatusAgendamento(status)}"?`
    );

    if (!confirmarAlteracao) {
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/admin/agendamentos/${id}/status`,
            {
                method: "PUT",
                auth: true,
                body: {
                    status,
                },
            }
        );

        exibirMensagemPainel(
            "Status do agendamento atualizado com sucesso."
        );

        invalidarSecoesAdmin([
            "secao-dashboard",
            "secao-agenda",
            "secao-clientes-crm",
        ]);

        await carregarAgendamentos();
        await carregarAgendaVisualDia();

    } catch (erro) {
        tratarErro(erro);
    }
}


window.atualizarStatusAgendamento = atualizarStatusAgendamento;


/* =========================================================
   CARREGAMENTO INICIAL
========================================================= */

async function cancelarAgendamentoComMotivo(id) {
    const motivo = prompt(
        "Informe o motivo do cancelamento:"
    );

    if (motivo === null) {
        return;
    }

    const motivoTratado = motivo.trim();

    if (!motivoTratado) {
        exibirMensagemAdmin("O motivo do cancelamento é obrigatório.");
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/admin/agendamentos/${id}/cancelar`,
            {
                method: "PUT",
                auth: true,
                body: {
                    motivo_cancelamento: motivoTratado,
                },
            }
        );

        exibirMensagemPainel(
            "Agendamento cancelado com sucesso."
        );

        await carregarAgendamentos();
        await carregarAgendaVisualDia({
            forcar: true,
        });

        invalidarSecoesAdmin([
            "secao-dashboard",
            "secao-agenda",
            "secao-clientes-crm",
        ]);

    } catch (erro) {
        tratarErro(erro);
    }
}


async function atualizarObservacaoAgendamento(id, observacaoAtual = "") {
    const observacao = prompt(
        "Observação interna deste agendamento:",
        observacaoAtual || ""
    );

    if (observacao === null) {
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/admin/agendamentos/${id}/observacao`,
            {
                method: "PUT",
                auth: true,
                body: {
                    observacao_interna: observacao.trim(),
                },
            }
        );

        exibirMensagemPainel(
            "Observação interna atualizada com sucesso."
        );

        await carregarAgendamentos();

    } catch (erro) {
        tratarErro(erro);
    }
}


window.cancelarAgendamentoComMotivo = cancelarAgendamentoComMotivo;
window.atualizarObservacaoAgendamento = atualizarObservacaoAgendamento;


function garantirModalHistoricoCliente() {
    let modal = document.getElementById("modal-historico-cliente");

    if (modal) {
        return modal;
    }

    modal = document.createElement("div");
    modal.id = "modal-historico-cliente";
    modal.className = "modal-historico-cliente";
    modal.style.display = "none";

    modal.innerHTML = `
        <div class="modal-historico-overlay" onclick="fecharHistoricoCliente()"></div>

        <div class="modal-historico-card">
            <div class="modal-historico-header">
                <div>
                    <h2>Histórico do Cliente</h2>
                    <p id="historico-cliente-resumo">
                        Carregando informações...
                    </p>
                </div>

                <button
                    type="button"
                    class="btn-fechar-modal"
                    onclick="fecharHistoricoCliente()"
                >
                    ×
                </button>
            </div>

            <div id="historico-cliente-conteudo" class="historico-cliente-conteudo">
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    return modal;
}


function fecharHistoricoCliente() {
    const modal = document.getElementById("modal-historico-cliente");

    if (modal) {
        modal.style.display = "none";
    }
}


async function abrirHistoricoCliente(telefone) {
    const telefoneNormalizado = normalizarTelefoneCliente(telefone);

    if (!telefoneNormalizado) {
        exibirMensagemAdmin("Este agendamento não possui telefone válido.");
        return;
    }

    const modal = garantirModalHistoricoCliente();
    const resumo = document.getElementById("historico-cliente-resumo");
    const conteudo = document.getElementById("historico-cliente-conteudo");

    modal.style.display = "flex";
    resumo.textContent = "Carregando histórico...";
    conteudo.innerHTML = "";

    try {
        const dados = await apiRequest(
            `/api/${tenantSlugLogado}/admin/clientes/historico?telefone=${telefoneNormalizado}`,
            {
                auth: true,
            }
        );

        resumo.textContent = `
            Telefone: ${dados.telefone}
            • ${dados.total_agendamentos} agendamento(s)
            • ${dados.total_cancelamentos} cancelamento(s)
            • ${formatarMoeda(dados.faturamento_total_concluido)} concluído(s)
        `;

        if (!dados.agendamentos || !dados.agendamentos.length) {
            conteudo.innerHTML = `
                <p class="mensagem-vazia">
                    Nenhum histórico encontrado para este cliente.
                </p>
            `;
            return;
        }

        conteudo.innerHTML = dados.agendamentos
            .map((agendamento) => {
                const status = agendamento.status || "confirmado";

                return `
                    <div class="card-historico-cliente">
                        <div class="card-historico-topo">
                            <strong>${agendamento.servico || "-"}</strong>

                            <span class="badge-status ${classeStatusAgendamento(status)}">
                                ${traduzirStatusAgendamento(status)}
                            </span>
                        </div>

                        <p>
                            <strong>Data:</strong>
                            ${formatarDataBR(agendamento.data)}
                            às ${agendamento.horario || "-"}
                        </p>

                        <p>
                            <strong>Profissional:</strong>
                            ${agendamento.profissional || "-"}
                        </p>

                        <p>
                            <strong>Valor:</strong>
                            ${formatarMoeda(agendamento.valor)}
                        </p>

                        ${
                            agendamento.motivo_cancelamento
                                ? `<p><strong>Motivo do cancelamento:</strong> ${agendamento.motivo_cancelamento}</p>`
                                : ""
                        }

                        ${
                            agendamento.cancelado_em
                                ? `<p><strong>Cancelado em:</strong> ${formatarDataHoraBR(agendamento.cancelado_em)}</p>`
                                : ""
                        }

                        ${
                            agendamento.observacao_interna
                                ? `<p><strong>Observação interna:</strong> ${agendamento.observacao_interna}</p>`
                                : ""
                        }
                    </div>
                `;
            })
            .join("");

    } catch (erro) {
        tratarErro(erro);
        fecharHistoricoCliente();
    }
}


window.abrirHistoricoCliente = abrirHistoricoCliente;
window.fecharHistoricoCliente = fecharHistoricoCliente;

function registrarListenersCRM() {
    if (listenersCRMRegistrados) {
        return;
    }

    listenersCRMRegistrados = true;

    const inputBusca = document.getElementById("busca-clientes-crm");
    const botaoBuscar = document.getElementById("btn-buscar-clientes-crm");
    const botaoLimpar = document.getElementById("btn-limpar-busca-clientes-crm");

    if (botaoBuscar) {
        botaoBuscar.addEventListener("click", () => {
            carregarClientesCRM(
                inputBusca?.value || ""
            );
        });
    }

    if (botaoLimpar) {
        botaoLimpar.addEventListener("click", () => {
            if (inputBusca) {
                inputBusca.value = "";
            }

            carregarClientesCRM();
        });
    }

    if (inputBusca) {
        inputBusca.addEventListener("keydown", (evento) => {
            if (evento.key === "Enter") {
                evento.preventDefault();

                carregarClientesCRM(
                    inputBusca.value || ""
                );
            }
        });
    }
}


async function carregarClientesCRM(busca = "") {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const tbody = document.getElementById("lista-clientes-crm");

    if (!tbody) {
        return;
    }

    const parametros = new URLSearchParams();

    if (busca.trim()) {
        parametros.set("busca", busca.trim());
    }

    const query = parametros.toString();

    const endpoint = query
        ? `/api/${tenantSlugLogado}/admin/clientes?${query}`
        : `/api/${tenantSlugLogado}/admin/clientes`;

    try {
        const dados = await apiRequest(
            endpoint,
            {
                auth: true,
            }
        );

        document.getElementById("visor-total-clientes").textContent =
            dados.total_clientes || 0;

        document.getElementById("visor-clientes-recorrentes").textContent =
            dados.clientes_recorrentes || 0;

        document.getElementById("visor-faturamento-crm").textContent =
            formatarMoeda(dados.faturamento_total_concluido || 0);

        document.getElementById("visor-ticket-medio-crm").textContent =
            formatarMoeda(dados.ticket_medio_geral || 0);

        tbody.innerHTML = "";

        if (!dados.clientes || !dados.clientes.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" class="mensagem-tabela">
                        Nenhum cliente encontrado.
                    </td>
                </tr>
            `;

            return;
        }

        for (const cliente of dados.clientes) {
            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>
                    <span class="cliente-nome-crm">
                        ${cliente.nome || "Cliente"}
                    </span>

                    <span class="cliente-detalhe-crm">
                        Último serviço:
                        ${cliente.ultimo_servico || "-"}
                    </span>
                </td>

                <td>${cliente.telefone || "-"}</td>
                <td>${cliente.total_agendamentos || 0}</td>
                <td>${cliente.total_concluidos || 0}</td>
                <td>${cliente.total_cancelados || 0}</td>
                <td>${cliente.total_faltas || 0}</td>
                <td>${formatarMoeda(cliente.faturamento_total_concluido || 0)}</td>
                <td>${formatarMoeda(cliente.ticket_medio || 0)}</td>
                <td>${formatarDataBR(cliente.ultima_visita)}</td>
                <td>${formatarDataBR(cliente.proximo_agendamento)}</td>
                <td>
                    <button
                        type="button"
                        class="btn-mini-crm"
                        onclick="abrirHistoricoCliente('${cliente.telefone}')"
                    >
                        Histórico
                    </button>
                </td>
            `;

            tbody.appendChild(tr);
        }

    } catch (erro) {
        tratarErro(erro);
    }
}

function obterValorCampo(id, padrao = "") {
    const campo = document.getElementById(id);

    if (!campo) {
        return padrao;
    }

    return campo.value || padrao;
}


function configurarDiaInteiroBloqueio() {
    const campoDiaInteiro = document.getElementById("bloqueio-dia-inteiro");
    const campoInicio = document.getElementById("bloqueio-horario-inicio");
    const campoFim = document.getElementById("bloqueio-horario-fim");

    if (!campoDiaInteiro || !campoInicio || !campoFim) {
        return;
    }

    const diaInteiro = campoDiaInteiro.value === "true";

    campoInicio.disabled = diaInteiro;
    campoFim.disabled = diaInteiro;

    if (diaInteiro) {
        campoInicio.value = "";
        campoFim.value = "";
    }
}


function registrarListenersBloqueiosAgenda() {
    if (listenersBloqueiosRegistrados) {
        return;
    }

    listenersBloqueiosRegistrados = true;

    const form = document.getElementById("form-bloqueio-agenda");
    const campoDiaInteiro = document.getElementById("bloqueio-dia-inteiro");

    if (form) {
        form.addEventListener("submit", criarBloqueioAgenda);
    }

    if (campoDiaInteiro) {
        campoDiaInteiro.addEventListener(
            "change",
            configurarDiaInteiroBloqueio
        );
    }

    configurarDiaInteiroBloqueio();
}


async function carregarProfissionaisBloqueio() {
    if (!adminProntoParaRequisicao()) {
        return;
    }
    const select = document.getElementById("bloqueio-profissional");

    if (!select) {
        return;
    }

    select.innerHTML = `
        <option value="">Todos os profissionais</option>
    `;

    try {
        const profissionais = await apiRequest(
            `/api/${tenantSlugLogado}/profissionais`
        );

        for (const profissional of profissionais) {
            const option = document.createElement("option");

            option.value = profissional.nome;
            option.textContent = profissional.nome;

            select.appendChild(option);
        }

    } catch (erro) {
        console.error("Erro ao carregar profissionais para bloqueio:", erro);
    }
}


async function carregarBloqueiosAgenda() {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const tbody = document.getElementById("lista-bloqueios-agenda");

    if (!tbody) {
        return;
    }

    const dataFiltro = obterValorCampo("filtro-data-bloqueios", "");
    const params = new URLSearchParams();

    if (dataFiltro) {
        params.set("data", dataFiltro);
    }

    const query = params.toString();

    const endpoint = query
        ? `/api/${tenantSlugLogado}/admin/bloqueios?${query}`
        : `/api/${tenantSlugLogado}/admin/bloqueios`;

    tbody.innerHTML = `
        <tr>
            <td colspan="6" class="mensagem-tabela">
                Carregando bloqueios...
            </td>
        </tr>
    `;

    try {
        const bloqueios = await apiRequest(
            endpoint,
            {
                auth: true,
            }
        );

        tbody.innerHTML = "";

        if (!bloqueios.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="mensagem-tabela">
                        Nenhum bloqueio encontrado.
                    </td>
                </tr>
            `;

            return;
        }

        for (const bloqueio of bloqueios) {
            const tr = document.createElement("tr");

            const profissional = bloqueio.profissional || "Todos";
            const tipo = bloqueio.dia_inteiro ? "Dia inteiro" : "Intervalo";
            const intervalo = bloqueio.dia_inteiro
                ? "Dia todo"
                : `${bloqueio.horario_inicio || "-"} até ${bloqueio.horario_fim || "-"}`;

            tr.innerHTML = `
                <td>${formatarDataBR(bloqueio.data)}</td>
                <td>${profissional}</td>
                <td>${tipo}</td>
                <td>${intervalo}</td>
                <td>${bloqueio.motivo || "-"}</td>
                <td>
                    <button
                        type="button"
                        class="btn-del-mini"
                        onclick="removerBloqueioAgenda(${bloqueio.id})"
                    >
                        Remover
                    </button>
                </td>
            `;

            tbody.appendChild(tr);
        }

    } catch (erro) {
        tratarErro(erro);
    }
}


async function criarBloqueioAgenda(event) {
    event.preventDefault();

    const profissional = obterValorCampo("bloqueio-profissional", "");
    const data = obterValorCampo("bloqueio-data", "");
    const diaInteiro = obterValorCampo("bloqueio-dia-inteiro", "false") === "true";
    const horarioInicio = obterValorCampo("bloqueio-horario-inicio", "");
    const horarioFim = obterValorCampo("bloqueio-horario-fim", "");
    const motivo = obterValorCampo("bloqueio-motivo", "");

    if (!data) {
        exibirMensagemAdmin("Informe a data do bloqueio.");
        return;
    }

    if (!diaInteiro && (!horarioInicio || !horarioFim)) {
        exibirMensagemAdmin("Informe horário inicial e final para bloqueio parcial.");
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/admin/bloqueios`,
            {
                method: "POST",
                auth: true,
                body: {
                    profissional: profissional || null,
                    data,
                    horario_inicio: diaInteiro ? null : horarioInicio,
                    horario_fim: diaInteiro ? null : horarioFim,
                    dia_inteiro: diaInteiro,
                    motivo: motivo || null,
                },
            }
        );

        document.getElementById("form-bloqueio-agenda").reset();

        configurarDiaInteiroBloqueio();

        await carregarBloqueiosAgenda();
        await carregarAgendamentos();
        await carregarAgendaVisualDia({
            forcar: true,
        });

        invalidarSecoesAdmin([
            "secao-agenda",
            "secao-bloqueios-agenda",
        ]);

        exibirMensagemAdmin(
            "Operação realizada com sucesso.",
            "sucesso"
        );

    } catch (erro) {
        tratarErro(erro);
    }
}


async function removerBloqueioAgenda(bloqueioId) {
    const confirmar = window.confirm(
        "Deseja remover este bloqueio de agenda?"
    );

    if (!confirmar) {
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/admin/bloqueios/${bloqueioId}`,
            {
                method: "DELETE",
                auth: true,
            }
        );

        await carregarBloqueiosAgenda();
        await carregarAgendaVisualDia({
            forcar: true,
        });

        invalidarSecoesAdmin([
            "secao-agenda",
            "secao-bloqueios-agenda",
        ]);

        exibirMensagemAdmin(
            "Operação realizada com sucesso.",
            "sucesso"
        );

    } catch (erro) {
        tratarErro(erro);
    }
}


function limparFiltroBloqueiosAgenda() {
    const filtro = document.getElementById("filtro-data-bloqueios");

    if (filtro) {
        filtro.value = "";
    }

    carregarBloqueiosAgenda();
}


window.carregarBloqueiosAgenda = carregarBloqueiosAgenda;
window.removerBloqueioAgenda = removerBloqueioAgenda;
window.limparFiltroBloqueiosAgenda = limparFiltroBloqueiosAgenda;


function obterDataLocalAdmin() {
    const hoje = new Date();

    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, "0");
    const dia = String(hoje.getDate()).padStart(2, "0");

    return `${ano}-${mes}-${dia}`;
}


function formatarHorarioAtualizacao() {
    return new Date().toLocaleTimeString(
        "pt-BR",
        {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        }
    );
}


function atualizarTextoUltimaAtualizacaoAgenda() {
    const elemento = document.getElementById("agenda-dia-atualizacao");

    if (!elemento) {
        return;
    }

    elemento.textContent = `Última atualização: ${formatarHorarioAtualizacao()}`;
}


function horarioParaMinutos(horario) {
    const partes = String(horario || "").split(":");

    if (partes.length < 2) {
        return null;
    }

    const horas = Number(partes[0]);
    const minutos = Number(partes[1]);

    if (
        Number.isNaN(horas)
        || Number.isNaN(minutos)
    ) {
        return null;
    }

    return horas * 60 + minutos;
}


function slotEstaNoPeriodoAtual(horario, dataAgenda) {
    if (dataAgenda !== obterDataLocalAdmin()) {
        return false;
    }

    const inicioSlot = horarioParaMinutos(horario);

    if (inicioSlot === null) {
        return false;
    }

    const agora = new Date();
    const minutosAgora = agora.getHours() * 60 + agora.getMinutes();

    return (
        minutosAgora >= inicioSlot
        && minutosAgora < inicioSlot + 30
    );
}


function agendarAtualizacaoAgendaVisual() {
    clearTimeout(timeoutAtualizacaoAgendaVisual);

    timeoutAtualizacaoAgendaVisual = setTimeout(() => {
        carregarAgendaVisualDia({
            forcar: true,
        });
    }, 350);
}


function registrarListenersAgendaVisual() {
    if (listenersAgendaVisualRegistrados) {
        return;
    }

    listenersAgendaVisualRegistrados = true;

    const campoData = document.getElementById("agenda-visual-data");
    const campoProfissional = document.getElementById("agenda-visual-profissional");

    if (campoData && !campoData.value) {
        campoData.value = obterDataLocalAdmin();
    }

    if (campoData) {
        campoData.addEventListener("change", agendarAtualizacaoAgendaVisual);
    }

    if (campoProfissional) {
        campoProfissional.addEventListener("change", agendarAtualizacaoAgendaVisual);
    }
}


function preencherProfissionaisAgendaVisual(profissionais) {
    const select = document.getElementById("agenda-visual-profissional");

    if (!select) {
        return;
    }

    const valorAtual = select.value;

    select.innerHTML = `
        <option value="">Todos os profissionais</option>
    `;

    for (const profissional of profissionais || []) {
        const option = document.createElement("option");

        option.value = profissional.nome;
        option.textContent = profissional.nome;

        select.appendChild(option);
    }

    if (valorAtual) {
        select.value = valorAtual;
    }
}


function eventoPertenceAoHorario(evento, horario) {
    const inicio = String(
        evento.horario
        || evento.horario_inicio
        || ""
    );

    return inicio === horario;
}


function renderizarAcoesAgendaVisual(evento) {
    if (evento.tipo === "bloqueio") {
        return `
            <div class="agenda-evento-acoes">
                <button
                    type="button"
                    onclick="removerBloqueioAgenda(${evento.id})"
                >
                    Remover bloqueio
                </button>
            </div>
        `;
    }

    const status = evento.status || "confirmado";

    if (status === "cancelado") {
        return "";
    }

    return `
        <div class="agenda-evento-acoes">
            <button
                type="button"
                onclick="atualizarStatusAgendamento(${evento.id}, 'confirmado')"
            >
                Confirmar
            </button>

            <button
                type="button"
                onclick="atualizarStatusAgendamento(${evento.id}, 'concluido')"
            >
                Concluir
            </button>

            <button
                type="button"
                onclick="cancelarAgendamentoComMotivo(${evento.id})"
            >
                Cancelar
            </button>

            <button
                type="button"
                onclick="atualizarStatusAgendamento(${evento.id}, 'faltou')"
            >
                Faltou
            </button>

            <button
                type="button"
                onclick="abrirHistoricoCliente('${evento.telefone_cliente || ""}')"
            >
                Histórico
            </button>
        </div>
    `;
}


function renderizarEventoAgendaVisual(evento) {
    if (evento.tipo === "bloqueio") {
        return `
            <article class="agenda-evento-card bloqueio">
                <div class="agenda-evento-topo">
                    <div>
                        <strong>Bloqueio de agenda</strong>
                        <br>
                        <small>
                            ${evento.horario_inicio || "-"}
                            até
                            ${evento.horario_fim || "-"}
                        </small>
                    </div>

                    <span class="badge-status status-cancelado">
                        Bloqueado
                    </span>
                </div>

                <div class="agenda-evento-info">
                    <span>
                        Profissional:
                        ${evento.profissional_label || evento.profissional || "Todos"}
                    </span>

                    <span>
                        Tipo:
                        ${evento.dia_inteiro ? "Dia inteiro" : "Intervalo"}
                    </span>

                    <span>
                        Motivo:
                        ${evento.motivo || "-"}
                    </span>
                </div>

                ${renderizarAcoesAgendaVisual(evento)}
            </article>
        `;
    }

    const status = evento.status || "confirmado";

    return `
        <article class="agenda-evento-card agendamento">
            <div class="agenda-evento-topo">
                <div>
                    <strong>
                        ${evento.horario || "-"} — ${evento.cliente_nome || "Cliente"}
                    </strong>
                    <br>
                    <small>
                        ${evento.servico || "-"}
                        •
                        ${evento.profissional || "-"}
                    </small>
                </div>

                <span class="badge-status ${classeStatusAgendamento(status)}">
                    ${traduzirStatusAgendamento(status)}
                </span>
            </div>

            <div class="agenda-evento-info">
                <span>
                    Telefone:
                    ${evento.telefone_cliente || "-"}
                </span>

                <span>
                    Valor:
                    ${formatarMoeda(evento.valor || 0)}
                </span>

                <span>
                    Duração:
                    ${evento.duracao_minutos || 30} min
                </span>

                ${
                    evento.observacao_interna
                        ? `<span>Obs.: ${evento.observacao_interna}</span>`
                        : ""
                }
            </div>

            ${renderizarAcoesAgendaVisual(evento)}
        </article>
    `;
}


function renderizarAgendaVisualDia(dados) {
    const container = document.getElementById("agenda-visual-lista");

    if (!container) {
        return;
    }

    preencherProfissionaisAgendaVisual(dados.profissionais || []);

    const resumo = dados.resumo || {};

    document.getElementById("agenda-dia-total").textContent =
        resumo.total_agendamentos || 0;

    document.getElementById("agenda-dia-confirmados").textContent =
        resumo.confirmados || 0;

    document.getElementById("agenda-dia-concluidos").textContent =
        resumo.concluidos || 0;

    document.getElementById("agenda-dia-cancelados").textContent =
        resumo.cancelados || 0;

    document.getElementById("agenda-dia-faltas").textContent =
        resumo.faltas || 0;

    document.getElementById("agenda-dia-previsto").textContent =
        formatarMoeda(resumo.faturamento_previsto || 0);

    document.getElementById("agenda-dia-faturado").textContent =
        formatarMoeda(resumo.faturamento_concluido || 0);

    const linhaDoTempo = dados.linha_do_tempo || [];
    const eventos = dados.eventos || [];

    container.innerHTML = `
        <div class="mensagem-vazia">
            Carregando agenda visual...
        </div>
    `;

    if (!linhaDoTempo.length) {
        container.innerHTML = `
            <tr>
                <td colspan="8">
                    ${criarEstadoVazioAdmin({
                        icone: "◴",
                        titulo: "Nenhum agendamento recebido ainda",
                        descricao:
                            "Copie o link público e envie para seus clientes começarem a agendar.",
                        textoBotao: "Copiar link público",
                        secaoDestino: "secao-dashboard",
                        })}
                    </td>
                </tr>
            `;

        return;
    }

    const horariosDaGrade = new Set(
        linhaDoTempo.map((slot) => slot.horario)
    );

    for (const slot of linhaDoTempo) {
        const eventosDoHorario = eventos.filter((evento) => {
            return eventoPertenceAoHorario(
                evento,
                slot.horario
            );
        });

        const horarioAtual = slotEstaNoPeriodoAtual(
            slot.horario,
            dados.data
        );

        const linha = document.createElement("div");

        linha.className = horarioAtual
            ? "agenda-linha-horario horario-atual"
            : "agenda-linha-horario";

        linha.innerHTML = `
            <div class="agenda-horario-label ${horarioAtual ? "agora" : ""}">
                ${slot.horario}
            </div>

            <div class="agenda-eventos-slot">
                ${
                    eventosDoHorario.length
                        ? eventosDoHorario
                            .map(renderizarEventoAgendaVisual)
                            .join("")
                        : `<div class="agenda-slot-vazio">Livre</div>`
                }
            </div>
        `;

        container.appendChild(linha);
    }

    const eventosForaDaGrade = eventos.filter((evento) => {
        const horarioEvento = String(
            evento.horario
            || evento.horario_inicio
            || ""
        );

        return (
            horarioEvento
            && !horariosDaGrade.has(horarioEvento)
        );
    });

    if (eventosForaDaGrade.length) {
        const blocoForaDaGrade = document.createElement("div");

        blocoForaDaGrade.className = "agenda-eventos-fora-grade";

        blocoForaDaGrade.innerHTML = `
            <h4>Eventos fora da grade de horários</h4>

            ${
                eventosForaDaGrade
                    .map(renderizarEventoAgendaVisual)
                    .join("")
            }
        `;

        container.appendChild(blocoForaDaGrade);
    }

    atualizarTextoUltimaAtualizacaoAgenda();
}


async function carregarAgendaVisualDia(opcoes = {}) {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    if (agendaVisualEmCarregamento) {
        agendaVisualRecarregarDepois = true;
        return;
    }

    agendaVisualEmCarregamento = true;

    const container = document.getElementById("agenda-visual-lista");

    if (!container) {
        return;
    }

    const data = obterValorCampo(
        "agenda-visual-data",
        obterDataLocalAdmin()
    );

    const profissional = obterValorCampo(
        "agenda-visual-profissional",
        ""
    );

    const params = new URLSearchParams();

    params.set("data", data);

    if (profissional) {
        params.set("profissional", profissional);
    }

    const containerAgendaVisual = document.getElementById(
      "agenda-visual-lista",
    );

    if (containerAgendaVisual) {
      containerAgendaVisual.innerHTML = criarEstadoVazioAdmin({
        icone: "◴",
        titulo: "Nenhum horário encontrado",
        descricao:
          "Não existem horários configurados para esta data ou profissional.",
        textoBotao: "Conferir horários",
        secaoDestino: "secao-configuracoes",
      });
    }

    try {
        const dados = await apiRequest(
            `/api/${tenantSlugLogado}/admin/agenda-dia?${params.toString()}`,
            {
                auth: true,
            }
        );

        renderizarAgendaVisualDia(dados);

    } catch (erro) {
        tratarErro(erro);

    } finally {
        agendaVisualEmCarregamento = false;

        if (agendaVisualRecarregarDepois) {
            agendaVisualRecarregarDepois = false;

            carregarAgendaVisualDia({
                forcar: true,
            });
        }
    }
}


window.carregarAgendaVisualDia = carregarAgendaVisualDia;

async function carregarDadosDaSecaoAdmin(secaoId, opcoes = {}) {
    const forcar = Boolean(opcoes.forcar);

    if (!secaoId) {
        return;
    }

    if (!tenantSlugLogado) {
        return;
    }

    if (
        secoesAdminCarregando.has(secaoId)
    ) {
        return;
    }

    if (
        secoesAdminCarregadas.has(secaoId)
        && !forcar
    ) {
        return;
    }

    secoesAdminCarregando.add(secaoId);

    try {
        if (secaoId === "secao-dashboard") {
            await Promise.all([
                carregarConfiguracaoAtual(),
                carregarEquipe(),
                carregarServicos(),
                carregarAgendamentos(),
            ]);
        }

        if (secaoId === "secao-configuracoes") {
            await Promise.all([
                carregarConfiguracaoAtual(),
                carregarEquipe(),
                carregarServicos(),
            ]);
        }

        if (secaoId === "secao-servicos") {
          await carregarServicos({
            forcar,
          });
        }

        if (secaoId === "secao-profissionais") {
          await carregarEquipe({
            forcar,
          });
        }

        if (secaoId === "secao-admin-assinatura") {
            await carregarAssinaturaAdmin();
        }

        if (secaoId === "secao-agenda") {
            await Promise.all([
                carregarAgendamentos(),
                carregarAgendaVisualDia(),
            ]);
        }

        if (secaoId === "secao-bloqueios-agenda") {
            await Promise.all([
                carregarProfissionaisBloqueio(),
                carregarBloqueiosAgenda(),
            ]);
        }

        if (secaoId === "secao-clientes-crm") {
            await carregarClientesCRM();
        }

        secoesAdminCarregadas.add(secaoId);

    } catch (erro) {
        console.error(
            "Erro ao carregar seção do admin:",
            secaoId,
            erro
        );

        tratarErro(erro);

    } finally {
        secoesAdminCarregando.delete(secaoId);
    }
}


function invalidarSecaoAdmin(secaoId) {
    secoesAdminCarregadas.delete(secaoId);
}


function invalidarSecoesAdmin(secaoIds = []) {
    secaoIds.forEach((secaoId) => {
        invalidarSecaoAdmin(secaoId);
    });
}


async function carregarTudo(opcoes = {}) {
    const secaoSalva = localStorage.getItem(
        "gesto_admin_secao_ativa"
    );

    const secaoInicial = secaoSalva || "secao-dashboard";

    await carregarDadosDaSecaoAdmin(
        secaoInicial,
        {
            forcar: Boolean(opcoes.forcar),
        }
    );
}




async function atualizarPainelAdmin() {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    if (painelAdminAtualizando) {
        return;
    }

    painelAdminAtualizando = true;

    try {
        const secaoAtual =
            document.querySelector(".secao-admin.ativa")?.id
            || localStorage.getItem("gesto_admin_secao_ativa")
            || "secao-admin-dashboard";

        await carregarDadosDaSecaoAdmin(
            secaoAtual,
            {
                forcar: true,
            }
        );

        await carregarAvisosAdmin({
            forcar: true,
        });

        await carregarConfiguracaoAtual({
            forcar: true,
        });

        exibirMensagemAdmin(
            "Painel atualizado com sucesso.",
            "sucesso"
        );

    } catch (erro) {
        tratarErroAdmin(erro);

    } finally {
        painelAdminAtualizando = false;
    }
}


window.onload = iniciarPainel;
window.dispensarAvisoAdmin = dispensarAvisoAdmin;
window.abrirModalChamadoAdmin = abrirModalChamadoAdmin;
window.fecharModalChamadoAdmin = fecharModalChamadoAdmin;
window.criarChamadoAdmin = criarChamadoAdmin;
window.carregarChamadosAdmin = carregarChamadosAdmin;
window.abrirModalHistoricoChamadosAdmin = abrirModalHistoricoChamadosAdmin;
window.fecharModalHistoricoChamadosAdmin = fecharModalHistoricoChamadosAdmin;
window.carregarTudo = carregarTudo;
window.atualizarPainelAdmin = atualizarPainelAdmin;
window.abrirWhatsAppAgendamento = abrirWhatsAppAgendamento;
window.marcarAgendamentosComoVistos = marcarAgendamentosComoVistos;
window.assinarPlanoMercadoPagoAdmin = assinarPlanoMercadoPagoAdmin;
window.atualizarAvisoBloqueioAdmin = atualizarAvisoBloqueioAdmin;


document.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => {
        exibirBannerFuncionalidadesAdmin();
    }, 700);
});

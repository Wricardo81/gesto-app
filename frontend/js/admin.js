let tenantSlugLogado = "";
let contextoUsuarioAdmin = null;
let catalogoPerfisOperacionaisAdmin = [];
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
let carregandoAcessosEquipeAdmin = false;
let configuracoesAdminCache = {};
let monitorNovosAgendamentosTimer = null;
let painelAdminAtualizando = false;
let intervaloNovosAgendamentosAdmin = null;
let ultimoCarregamentoConfiguracaoAdmin = 0;
let ultimoCarregamentoAvisosAdmin = 0;
let ultimoCarregamentoAgendamentosAdmin = 0;
let ultimoCarregamentoServicosAdmin = 0;
let ultimoCarregamentoProfissionaisAdmin = 0;
let proximoPassoOnboardingAdmin = null;
let atualizandoResumoAdmin = false;

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
    await atualizarResumoAdminAposMudanca();
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

function decodificarTokenAdmin(token) {
  if (!token || typeof token !== "string") {
    return null;
  }

  try {
    const partes = token.split(".");

    if (partes.length < 2) {
      return null;
    }

    const payloadBase64 = partes[1].replace(/-/g, "+").replace(/_/g, "/");

    const payloadJson = decodeURIComponent(
      atob(payloadBase64)
        .split("")
        .map((caractere) => {
          return "%" + ("00" + caractere.charCodeAt(0).toString(16)).slice(-2);
        })
        .join(""),
    );

    return JSON.parse(payloadJson);
  } catch (erro) {
    console.warn("Não foi possível decodificar token do Admin.", erro);
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

function obterTenantDaUrlAdmin() {
  const parametros = new URLSearchParams(window.location.search);

  return parametros.get("tenant") || "";
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

  const novaUrl =
    `${window.location.origin}${window.location.pathname}` +
    `?tenant=${encodeURIComponent(tenantSlugLogado)}`;

  window.history.replaceState({}, document.title, novaUrl);
}


function sincronizarTenantAdminComToken() {
  const tenantToken = obterTenantDoTokenAdmin();
  const tenantUrl = obterTenantDaUrlAdmin();

  if (!tenantToken) {
    return "";
  }

  localStorage.setItem("gesto_tenant", tenantToken);

  if (tenantUrl !== tenantToken) {
    const novaUrl =
      `${window.location.origin}${window.location.pathname}` +
      `?tenant=${encodeURIComponent(tenantToken)}`;

    window.history.replaceState({}, document.title, novaUrl);
  }

  return tenantToken;
}


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
  document.body.classList.toggle("admin-menu-aberto");
}








async function carregarContextoUsuarioAdmin() {
  const token = obterToken();

  if (!token) {
    contextoUsuarioAdmin = null;
    console.warn("Token ausente. Contexto do usuario admin nao foi carregado.");
    return null;
  }

  try {
    const resposta = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!resposta.ok) {
      throw new Error(`Falha ao carregar contexto do usuario: ${resposta.status}`);
    }

    const contexto = await resposta.json();

    contextoUsuarioAdmin = contexto;

    const papel = obterPapelUsuarioAdmin();
    const permissoes = obterPermissoesUsuarioAdmin();

    console.info("Contexto do usuario admin carregado.", {
      papel,
      permissoes,
      tenant: contexto?.tenant?.slug || tenantSlugLogado
    });

    atualizarIndicadorPerfilAdmin();
    aplicarPermissoesInterfaceAdmin();
    atualizarRotuloAgendaPorPerfilAdmin();
    aplicarVisibilidadeFinanceiraOperacionalAdmin();
    aplicarDashboardLimpoPorPerfilAdmin();

    setTimeout(() => {
      if (usuarioAdminEhPrestador()) {
        renderizarResumoProducaoPrestadorAdmin(agendamentosAdminCache || []);
      }
    }, 700);

    return contexto;
  } catch (erro) {
    contextoUsuarioAdmin = null;
    console.warn("Nao foi possivel carregar contexto do usuario admin.", erro);
    return null;
  }
}

function obterPapelUsuarioAdmin() {
  return (
    contextoUsuarioAdmin?.usuario?.papel
    || "gestor"
  );
}

function obterPermissoesUsuarioAdmin() {
  const permissoes = contextoUsuarioAdmin?.usuario?.permissoes;

  if (Array.isArray(permissoes)) {
    return permissoes;
  }

  return [];
}

function usuarioAdminTemPermissao(permissao) {
  const permissoes = obterPermissoesUsuarioAdmin();

  return (
    permissoes.includes("*")
    || permissoes.includes(permissao)
  );
}


const PERMISSOES_SECAO_ADMIN = {
  "secao-dashboard": [
    "ver_dashboard",
    "ver_dashboard_operacional",
    "ver_resumo"
  ],
  "secao-agenda": [
    "gerenciar_agenda",
    "ver_agenda",
    "ver_agenda_propria"
  ],
  "secao-bloqueios-agenda": [
    "gerenciar_bloqueios",
    "gerenciar_agenda"
  ],
  "secao-clientes-crm": [
    "gerenciar_clientes",
    "ver_clientes"
  ],
  "secao-configuracoes": [
    "gerenciar_configuracoes",
    "editar_configuracoes"
  ],
  "secao-admin-assinatura": [
    "gerenciar_assinatura",
    "ver_assinatura",
    "gerenciar_plano"
  ],
  "secao-servicos": [
    "gerenciar_servicos"
  ],
  "secao-profissionais": [
    "gerenciar_equipe",
    "gerenciar_profissionais"
  ],
  "secao-equipe": [
    "gerenciar_equipe",
    "gerenciar_profissionais"
  ]
};

function usuarioPodeAcessarSecaoAdmin(secaoId) {
  if (!secaoId) {
    return true;
  }

  if (!contextoUsuarioAdmin) {
    return true;
  }

  const permissoes = obterPermissoesUsuarioAdmin();

  if (permissoes.includes("*")) {
    return true;
  }

  const permissoesDaSecao = PERMISSOES_SECAO_ADMIN[secaoId];

  if (!Array.isArray(permissoesDaSecao) || !permissoesDaSecao.length) {
    return true;
  }

  return permissoesDaSecao.some((permissao) =>
    usuarioAdminTemPermissao(permissao)
  );
}

function obterPrimeiraSecaoPermitidaAdmin() {
  const botoes = Array.from(document.querySelectorAll(".admin-tab"));

  const botaoPermitido = botoes.find((botao) =>
    usuarioPodeAcessarSecaoAdmin(botao.dataset.secao)
  );

  return botaoPermitido?.dataset?.secao || "secao-dashboard";
}

function aplicarPermissoesInterfaceAdmin() {
  const botoes = document.querySelectorAll(".admin-tab");

  botoes.forEach((botao) => {
    const secaoId = botao.dataset.secao;
    const permitido = usuarioPodeAcessarSecaoAdmin(secaoId);

    botao.hidden = !permitido;
    botao.setAttribute("aria-hidden", String(!permitido));
    botao.disabled = !permitido;
  });

  const secaoAtual = document.querySelector(".secao-admin.ativa")?.id;

  if (secaoAtual && !usuarioPodeAcessarSecaoAdmin(secaoAtual)) {
    mostrarSecaoAdmin(obterPrimeiraSecaoPermitidaAdmin());
  }
}

function avisarPermissaoNegadaAdmin(secaoId) {
  const mensagem = "Seu perfil operacional nao tem permissao para acessar esta area.";

  console.warn("Acesso negado por permissao operacional.", {
    secao: secaoId,
    papel: obterPapelUsuarioAdmin(),
    permissoes: obterPermissoesUsuarioAdmin()
  });

  if (typeof mostrarToast === "function") {
    mostrarToast(mensagem, "erro");
    return;
  }

  if (typeof exibirToast === "function") {
    exibirToast(mensagem, "erro");
    return;
  }

  alert(mensagem);
}







function usuarioAdminEhPrestador() {
  return obterPapelUsuarioAdmin() === "prestador";
}

function normalizarNomeProfissionalAdmin(valor) {
  return String(valor || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function obterProfissionalVinculadoUsuarioAdmin() {
  return (
    contextoUsuarioAdmin?.usuario?.profissional_nome
    || contextoUsuarioAdmin?.usuario?.nome_profissional
    || contextoUsuarioAdmin?.usuario?.profissional
    || contextoUsuarioAdmin?.usuario?.profissionalNome
    || window.__profissionalOperacionalTeste
    || ""
  );
}

function filtrarAgendamentosPorPerfilOperacionalAdmin(agendamentos) {
  const lista = Array.isArray(agendamentos) ? agendamentos : [];

  if (!usuarioAdminEhPrestador()) {
    return lista;
  }

  const profissionalVinculado = normalizarNomeProfissionalAdmin(
    obterProfissionalVinculadoUsuarioAdmin()
  );

  if (!profissionalVinculado) {
    console.warn(
      "Prestador sem profissional vinculado. Agenda propria retornara vazia.",
      {
        contexto: contextoUsuarioAdmin
      }
    );

    return [];
  }

  return lista.filter((agendamento) =>
    normalizarNomeProfissionalAdmin(agendamento?.profissional)
      === profissionalVinculado
  );
}

function atualizarRotuloAgendaPorPerfilAdmin() {
  const tituloAgenda = document.querySelector("#secao-agenda h3");

  if (!tituloAgenda) {
    return;
  }

  if (usuarioAdminEhPrestador()) {
    tituloAgenda.textContent = "Minha agenda";
    return;
  }

  tituloAgenda.textContent = "Agenda e faturamento";
}


async function carregarCatalogoPerfisOperacionaisAdmin() {
  const token = obterToken();

  if (!token) {
    catalogoPerfisOperacionaisAdmin = [];
    console.warn("Token ausente. Catalogo de perfis operacionais nao foi carregado.");
    return [];
  }

  try {
    const resposta = await fetch(`${API_BASE_URL}/api/auth/perfis-operacionais`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!resposta.ok) {
      throw new Error(`Falha ao carregar catalogo de perfis operacionais: ${resposta.status}`);
    }

    const dados = await resposta.json();
    const perfis = Array.isArray(dados?.perfis) ? dados.perfis : [];

    catalogoPerfisOperacionaisAdmin = perfis;

    console.info("Catalogo de perfis operacionais carregado.", {
      total: perfis.length,
      perfis: perfis.map((perfil) => perfil.codigo)
    });

    return perfis;
  } catch (erro) {
    catalogoPerfisOperacionaisAdmin = [];
    console.warn("Nao foi possivel carregar catalogo de perfis operacionais.", erro);
    return [];
  }
}

function obterCatalogoPerfisOperacionaisAdmin() {
  return Array.isArray(catalogoPerfisOperacionaisAdmin)
    ? catalogoPerfisOperacionaisAdmin
    : [];
}

function obterPerfilOperacionalPorCodigoAdmin(codigo) {
  const codigoNormalizado = String(codigo || "").trim().toLowerCase();

  return obterCatalogoPerfisOperacionaisAdmin().find(
    (perfil) => perfil.codigo === codigoNormalizado
  ) || null;
}

function traduzirPapelUsuarioAdmin(papel) {
  const papelNormalizado = String(papel || "gestor").trim().toLowerCase();

  const nomes = {
    gestor: "Gestor",
    recepcao: "Recep\u00e7\u00e3o",
    prestador: "Prestador"
  };

  return nomes[papelNormalizado] || "Gestor";
}

function obterResumoPermissoesUsuarioAdmin() {
  const permissoes = obterPermissoesUsuarioAdmin();

  if (permissoes.includes("*")) {
    return "Acesso total";
  }

  if (!permissoes.length) {
    return "Permiss\u00f5es padr\u00e3o";
  }

  return `${permissoes.length} permiss\u00f5es`;
}

function atualizarIndicadorPerfilAdmin() {
  const indicador = document.getElementById("admin-perfil-operacional");

  if (!indicador) {
    return;
  }

  const papel = traduzirPapelUsuarioAdmin(obterPapelUsuarioAdmin());
  const resumo = obterResumoPermissoesUsuarioAdmin();

  indicador.textContent = `Perfil: ${papel} \u00b7 ${resumo}`;
}

function atualizarInsightDashboardAdmin(totalHoje, receitaHoje, concluidosHoje, proximoHorario) {
    const titulo = document.getElementById("dashboard-insight-titulo");
    const texto = document.getElementById("dashboard-insight-texto");

    if (!titulo || !texto) {
        return;
    }

    if (!totalHoje) {
        titulo.textContent = "Agenda livre hoje.";
        texto.textContent = "Nenhum agendamento para hoje. Divulgue o link p\u00fablico ou use as a\u00e7\u00f5es r\u00e1pidas para movimentar a agenda.";
        return;
    }

    if (concluidosHoje >= totalHoje) {
        titulo.textContent = "Dia praticamente conclu\u00eddo.";
        texto.textContent = "Todos os agendamentos carregados para hoje j\u00e1 aparecem como conclu\u00eddos. Revise o financeiro realizado.";
        return;
    }

    if (receitaHoje > 0 && proximoHorario && proximoHorario !== "--:--") {
        titulo.textContent = "Movimento ativo hoje.";
        texto.textContent = `Pr\u00f3ximo hor\u00e1rio: ${proximoHorario}. Acompanhe os atendimentos e mantenha os status atualizados.`;
        return;
    }

    titulo.textContent = "Agenda com movimento.";
    texto.textContent = "Existem agendamentos para hoje. Revise confirma\u00e7\u00f5es, faltas e pr\u00f3ximos hor\u00e1rios.";
}

function atualizarSaudacaoDashboardAdmin() {
    const kicker = document.getElementById("dashboard-pro-kicker");
    const titulo = document.getElementById("dashboard-pro-titulo");
    const subtitulo = document.getElementById("dashboard-pro-subtitulo");

    if (!kicker || !titulo || !subtitulo) {
        return;
    }

    const horaAtual = new Date().getHours();

    let saudacao = "Boa noite";

    if (horaAtual >= 5 && horaAtual < 12) {
        saudacao = "Bom dia";
    } else if (horaAtual >= 12 && horaAtual < 18) {
        saudacao = "Boa tarde";
    }

    kicker.textContent = "Painel do neg\u00f3cio";
    titulo.textContent = `${saudacao}, acompanhe sua opera\u00e7\u00e3o.`;
    subtitulo.textContent = "Veja o que acontece hoje, acompanhe o financeiro e use atalhos para operar mais r\u00e1pido.";
}

document.addEventListener("DOMContentLoaded", atualizarSaudacaoDashboardAdmin);

function atualizarStatusAcoesRapidasAdmin(mensagem) {
    const status = document.getElementById("dashboard-acoes-status");

    if (!status || !mensagem) {
        return;
    }

    status.textContent = mensagem;
    status.classList.add("dashboard-acoes-status-ativo");

    window.clearTimeout(window.bitsAgendaDashboardAcoesStatusTimeout);

    window.bitsAgendaDashboardAcoesStatusTimeout = window.setTimeout(() => {
        status.classList.remove("dashboard-acoes-status-ativo");
        status.textContent = "Comece as principais tarefas sem procurar no menu.";
    }, 2600);
}

function copiarLinkPublicoDashboardAdmin() {
    copiarLinkPublicoAdmin({ silencioso: true });
    atualizarStatusAcoesRapidasAdmin("Link p\u00fablico copiado.");
}

function abrirAtalhoDashboardAdmin(secaoId, campoId = null, mensagem = null) {
    mostrarSecaoAdmin(secaoId);
    atualizarStatusAcoesRapidasAdmin(mensagem);

    if (!campoId) {
        return;
    }

    setTimeout(() => {
        const campo = document.getElementById(campoId);

        if (!campo) {
            return;
        }

        campo.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

        if (typeof campo.focus === "function") {
            campo.focus();
        }
    }, 180);
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

    if (window.innerWidth <= 900) {
      document.body.classList.remove("admin-menu-aberto");
    }

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
    const linkAgenda = obterUrlPublicaTenantAdmin();

    const nomeEmpresa =
        configuracoesAdminCache?.nome_publico
        || configuracoesAdminCache?.nome_empresa
        || tenantSlugLogado
        || "nossa empresa";


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
    !forcar &&
    cacheAdminAindaValido(
      ultimoCarregamentoAvisosAdmin,
      TEMPO_CACHE_CURTO_ADMIN_MS,
    )
  ) {
    return;
  }

  if (carregandoAvisosAdmin) {
    return;
  }

  carregandoAvisosAdmin = true;

  try {
    const avisos = await apiRequest(`/api/${tenantSlugLogado}/admin/avisos`, {
      auth: true,
    });

    renderizarAvisosAdmin(avisos);

    ultimoCarregamentoAvisosAdmin = Date.now();
  } catch (erro) {
    console.error("Erro ao carregar avisos da plataforma:", erro);
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


function obterBasePublicaFrontendAdmin() {
    const hostname = window.location.hostname;
    const origin = window.location.origin;

    const rodandoLocal =
        hostname === "127.0.0.1" ||
        hostname === "localhost";

    if (rodandoLocal) {
        return `${origin}/frontend`;
    }

    return origin;
}

function obterUrlPublicaTenantAdmin() {
    if (!tenantSlugLogado) {
        return "";
    }

    const baseUrl = obterBasePublicaFrontendAdmin();

    return `${baseUrl}/agendamento.html?tenant=${encodeURIComponent(tenantSlugLogado)}`;
}


function renderizarLinkPublicoAdmin() {
  const elemento = document.getElementById("link-publico-admin-url");

  if (!elemento) {
    return;
  }

  const urlPublica = obterUrlPublicaTenantAdmin();

  elemento.textContent = urlPublica || "Link indisponível no momento.";
}

async function copiarLinkPublicoAdmin(opcoes = {}) {
  const urlPublica = obterUrlPublicaTenantAdmin();

  if (!urlPublica) {
    alert("Não foi possível gerar o link público agora.");
    return;
  }

  try {
    await navigator.clipboard.writeText(urlPublica);
    alert("Link público copiado com sucesso.");
  } catch (erro) {
    console.warn("Erro ao copiar link público.", erro);
    prompt("Copie o link público:", urlPublica);
  }
}

function abrirLinkPublicoAdmin() {
  const urlPublica = obterUrlPublicaTenantAdmin();

  if (!urlPublica) {
    alert("Não foi possível abrir o link público agora.");
    return;
  }

  window.open(urlPublica, "_blank", "noopener,noreferrer");
}

window.copiarLinkPublicoAdmin = copiarLinkPublicoAdmin;
window.abrirLinkPublicoAdmin = abrirLinkPublicoAdmin;


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


function definirProximoPassoOnboardingAdmin(resumo = {}) {
  const config = resumo?.config || {};

  const possuiPerfil = Boolean(
    String(
      config?.nome_publico ||
        config?.nome_empresa ||
        config?.nome ||
        config?.nome_estabelecimento ||
        "",
    ).trim(),
  );

  const possuiServico = Number(resumo?.totalServicos || 0) > 0;
  const possuiProfissional = Number(resumo?.totalProfissionais || 0) > 0;
  const possuiAgendamento = Number(resumo?.totalAgendamentos || 0) > 0;


  if (!possuiPerfil) {
    return {
      chave: "perfil",
      titulo: "Configure o perfil da sua empresa",
      descricao:
        "Adicione nome público, telefone, WhatsApp, cores e informações principais para sua agenda ficar pronta para os clientes.",
      textoBotao: "Configurar perfil",
      secao: "secao-admin-configuracoes",
    };
  }

  if (!possuiServico) {
    return {
      chave: "servico",
      titulo: "Crie seu primeiro serviço",
      descricao:
        "Cadastre o serviço que seus clientes poderão escolher na página pública de agendamento.",
      textoBotao: "Criar serviço",
      secao: "secao-servicos",
    };
  }

  if (!possuiProfissional) {
    return {
      chave: "profissional",
      titulo: "Cadastre um profissional",
      descricao:
        "Adicione quem irá atender os clientes. Depois disso, sua agenda pública já fica pronta para receber horários.",
      textoBotao: "Criar profissional",
      secao: "secao-profissionais",
    };
  }

  if (!possuiAgendamento) {
    return {
      chave: "divulgar",
      titulo: "Divulgue sua agenda pública",
      descricao:
        "Sua configuração inicial está pronta. Compartilhe o link público com seus clientes para receber o primeiro agendamento.",
      textoBotao: "Copiar link público",
      acao: "copiar-link",
    };
  }

  return {
    chave: "concluido",
    titulo: "Sua agenda já está funcionando",
    descricao:
      "Você já configurou a empresa, cadastrou serviço, profissional e recebeu agendamento. Agora acompanhe sua agenda pelo painel.",
    textoBotao: "Ver agenda",
    secao: "secao-agenda",
  };
}

function renderizarProximoPassoOnboardingAdmin(resumo = {}) {
  const card = document.getElementById("onboarding-proximo-passo");
  const titulo = document.getElementById("onboarding-proximo-titulo");
  const descricao = document.getElementById("onboarding-proximo-descricao");
  const botao = document.getElementById("onboarding-proximo-botao");

  if (!card || !titulo || !descricao || !botao) {
    return;
  }

  const proximoPasso = definirProximoPassoOnboardingAdmin(resumo);

  proximoPassoOnboardingAdmin = proximoPasso;

  titulo.textContent = proximoPasso.titulo;
  descricao.textContent = proximoPasso.descricao;
  botao.textContent = proximoPasso.textoBotao;

  card.classList.remove("onboarding-proximo-concluido");

  if (proximoPasso.chave === "concluido") {
    card.classList.add("onboarding-proximo-concluido");
  }
}

function executarProximoPassoOnboardingAdmin() {
  if (!proximoPassoOnboardingAdmin) {
    return;
  }

  if (proximoPassoOnboardingAdmin.acao === "copiar-link") {
    copiarLinkPublicoAdmin();
    return;
  }

  if (proximoPassoOnboardingAdmin.secao) {
    mostrarSecaoAdmin(proximoPassoOnboardingAdmin.secao);
  }
}

window.executarProximoPassoOnboardingAdmin =
  executarProximoPassoOnboardingAdmin;


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



async function atualizarResumoAdminAposMudanca() {
  if (atualizandoResumoAdmin) {
    return;
  }

  atualizandoResumoAdmin = true;

  try {
    if (typeof ultimoCarregamentoOnboardingAdmin !== "undefined") {
      ultimoCarregamentoOnboardingAdmin = 0;
    }

    await carregarAssinaturaAdmin();
    await carregarOnboardingAdmin();
    renderizarLinkPublicoAdmin();
  } catch (erro) {
    console.warn("Não foi possível atualizar resumo do Admin.", erro);
  } finally {
    atualizandoResumoAdmin = false;
  }
}


function renderizarOnboardingAdminComResumo(resumo) {
    renderizarProximoPassoOnboardingAdmin(resumo);
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
    card.hidden = true;
    card.setAttribute("aria-hidden", "true");

    progresso.textContent = `${totalConcluido}/${itens.length} concluídos`;

    lista.innerHTML = `
        <div class="onboarding-admin-compacto onboarding-admin-concluido">
            <div class="onboarding-admin-compacto-info">
                <span class="onboarding-admin-status">✓</span>

                <div>
                    <strong>Sua agenda já está funcionando</strong>
                    <p>
                        Perfil configurado, serviço cadastrado, profissional cadastrado
                        e primeiro agendamento recebido.
                    </p>
                </div>
            </div>

            <div class="onboarding-admin-compacto-acoes">
                <button
                    type="button"
                    class="btn-secondary btn-onboarding-admin"
                    onclick="mostrarSecaoAdmin('secao-agenda')"
                >
                    Ver agenda
                </button>
            </div>
        </div>
    `;

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


async function iniciarPainel() {
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

  if (!tenantSlugLogado) {
    alert(
      "Não foi possível identificar a empresa logada. Faça login novamente.",
    );
    fazerLogout();
    return;
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

  await carregarContextoUsuarioAdmin();
  await carregarCatalogoPerfisOperacionaisAdmin();

  criarEstruturaFilaEsperaAdmin();

  atualizarLinkPublico();
  registrarListenersDePreview();
  registrarListenersCRM();
  registrarListenersBloqueiosAgenda();
  registrarListenersAgendaVisual();
  registrarListenerPapelAcessoEquipeAdmin();
    inicializarNavegacaoAdmin();
    renderizarLinkPublicoAdmin();

  if (usuarioAdminEhGestor()) {
    carregarUsuariosOperacionaisAdmin();
  }

  carregarAvisosAdmin();
  tratarRetornoCadastroAdmin();
  tratarRetornoPagamentoAdmin();
  carregarAssinaturaAdmin();

  if (usuarioAdminEhGestor()) {
    carregarOnboardingAdmin();
  } else {
    ocultarElementoDashboardAdmin("card-onboarding-admin", true);
  }

  aplicarDashboardLimpoPorPerfilAdmin();

  if (usuarioAdminPodeVerFinanceiroGeral()) {
    await carregarResumoComissoesRepassesAdmin();
  }

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

            if (usuarioAdminPodeVerFinanceiroGeral()) {
                await carregarResumoComissoesRepassesAdmin();
            }

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


async function recarregarConfiguracaoAdminAposSalvar() {
  const config = await apiRequest(`/api/${tenantSlugLogado}/configuracoes`, {
    auth: true,
  });

  configuracaoAtual = {
    ...configuracaoAtual,
    ...config,
  };

  configuracoesAdminCache = {
    ...configuracoesAdminCache,
    ...config,
  };

  if (typeof preencherFormularioConfiguracao === "function") {
    preencherFormularioConfiguracao(config);
  }

  if (typeof preencherFormularioConfiguracoes === "function") {
    preencherFormularioConfiguracoes(config);
  }

  atualizarPreviewMarca();

  return config;
}


async function salvarConfiguracao(opcoes = {}) {
  const abertura = Number(document.getElementById("hora-abertura").value || 9);

  const fechamento = Number(
    document.getElementById("hora-fechamento").value || 18,
  );

  const whatsappComercial = valorCampo("whatsapp-comercial", "");
  const telefone = valorCampo("telefone-barbearia", whatsappComercial);

  try {
    const payload = {
      abertura,
      fechamento,
      limite_cancelamento_horas: Number(
        valorCampo("limite-cancelamento-horas", 3),
      ),
      cor_tema: valorCampo("cor-tema", "#f59e0b"),
      cor_fundo: valorCampo("cor-fundo", "#0f172a"),
      endereco: valorCampo("endereco", configuracaoAtual.endereco || ""),
      logo_url: valorCampo("logo-url", configuracaoAtual.logo_url || ""),
      instrucoes: valorCampo("instrucoes", configuracaoAtual.instrucoes || ""),
      telefone,

      nome_publico: valorCampo(
        "nome-publico",
        configuracaoAtual.nome_publico || "",
      ),
      logomarca_url: valorCampo(
        "logomarca-url",
        configuracaoAtual.logomarca_url || "",
      ),

      whatsapp_comercial: whatsappComercial,
      instagram_url: valorCampo(
        "instagram-url",
        configuracaoAtual.instagram_url || "",
      ),
      facebook_url: valorCampo(
        "facebook-url",
        configuracaoAtual.facebook_url || "",
      ),
      tiktok_url: valorCampo("tiktok-url", configuracaoAtual.tiktok_url || ""),
      site_url: valorCampo("site-url", configuracaoAtual.site_url || ""),
      google_maps_url: valorCampo(
        "google-maps-url",
        configuracaoAtual.google_maps_url || "",
      ),

      mensagem_publica: valorCampo(
        "mensagem-publica",
        configuracaoAtual.mensagem_publica || "",
      ),
      captar_whatsapp_lembretes: checkboxMarcado("captar-whatsapp-lembretes"),
      captar_whatsapp_promocoes: checkboxMarcado("captar-whatsapp-promocoes"),
    };

    await apiRequest(`/api/${tenantSlugLogado}/configuracoes`, {
      method: "POST",
      auth: true,
      body: payload,
    });

    await recarregarConfiguracaoAdminAposSalvar();

    configuracaoAtual = {
      ...configuracaoAtual,
      ...payload,
    };

    atualizarPreviewMarca();

    await atualizarResumoAdminAposMudanca();

    if (!opcoes.silencioso) {
      exibirMensagemPainel("Configurações salvas com sucesso.");
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

            const comissaoTipo = profissional.comissao_tipo || "nenhuma";
            const comissaoValor = Number(profissional.comissao_valor || 0);

            div.innerHTML = `
                <div class="profissional-info-admin">
                    <strong>${profissional.nome}</strong>
                    <small>
                        Comissao atual: ${formatarResumoComissaoProfissionalAdmin(
                          comissaoTipo,
                          comissaoValor
                        )}
                    </small>
                </div>

                <div class="profissional-comissao-admin">
                    <select id="comissao-tipo-${profissional.id}">
                        <option value="nenhuma" ${comissaoTipo === "nenhuma" ? "selected" : ""}>
                            Sem comissao
                        </option>
                        <option value="percentual" ${comissaoTipo === "percentual" ? "selected" : ""}>
                            Percentual
                        </option>
                        <option value="valor_fixo" ${comissaoTipo === "valor_fixo" ? "selected" : ""}>
                            Valor fixo
                        </option>
                    </select>

                    <input
                        type="number"
                        min="0"
                        step="0.01"
                        id="comissao-valor-${profissional.id}"
                        value="${comissaoValor}"
                        placeholder="Valor"
                    >

                    <button
                        type="button"
                        class="btn-secundario-mini"
                        onclick="salvarComissaoProfissionalAdmin(${profissional.id})"
                    >
                        Salvar comissao
                    </button>

                    <button
                        type="button"
                        class="btn-del-mini"
                        onclick="deletarProfissional(${profissional.id})"
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




function resumirPermissoesUsuarioOperacionalAdmin(permissoes) {
  const lista = Array.isArray(permissoes) ? permissoes : [];

  if (!lista.length) {
    return "Sem permissoes informadas";
  }

  if (lista.includes("*")) {
    return "Acesso total";
  }

  const mapa = {
    ver_dashboard: "Ver painel",
    ver_dashboard_operacional: "Painel operacional",
    ver_agenda_geral: "Agenda geral",
    ver_agenda_propria: "Agenda propria",
    gerenciar_agenda: "Gerenciar agenda",
    criar_agendamento: "Criar agendamento",
    editar_agendamento: "Editar agendamento",
    cancelar_agendamento: "Cancelar agendamento",
    marcar_falta: "Marcar falta",
    ver_clientes: "Ver clientes",
    gerenciar_clientes: "Gerenciar clientes",
    criar_cliente: "Criar cliente",
    editar_cliente: "Editar cliente",
    ver_servicos: "Ver servicos",
    ver_profissionais: "Ver profissionais",
    gerenciar_bloqueios: "Gerenciar bloqueios",
    concluir_agendamento: "Concluir agendamento",
    ver_financeiro_proprio: "Financeiro proprio",
    ver_comissao_propria: "Comissao propria",
  };

  return lista
    .slice(0, 8)
    .map((permissao) => mapa[permissao] || permissao)
    .join(", ");
}



function atualizarCampoProfissionalPorPapelAcessoAdmin() {
  const selectPapel = document.getElementById("acesso-equipe-papel");
  const selectProfissional = document.getElementById("acesso-equipe-profissional");

  if (!selectPapel || !selectProfissional) {
    return;
  }

  const campo = selectProfissional.closest(".campo");
  const papel = String(selectPapel.value || "prestador").trim().toLowerCase();
  const ehPrestador = papel === "prestador";

  if (campo) {
    campo.hidden = !ehPrestador;
    campo.setAttribute("aria-hidden", String(!ehPrestador));
    campo.style.display = ehPrestador ? "" : "none";
  }

  selectProfissional.required = ehPrestador;

  if (!ehPrestador) {
    selectProfissional.value = "";
  }
}

function registrarListenerPapelAcessoEquipeAdmin() {
  const selectPapel = document.getElementById("acesso-equipe-papel");

  if (!selectPapel || selectPapel.dataset.listenerPapelAcesso === "true") {
    return;
  }

  selectPapel.dataset.listenerPapelAcesso = "true";
  selectPapel.addEventListener("change", atualizarCampoProfissionalPorPapelAcessoAdmin);

  atualizarCampoProfissionalPorPapelAcessoAdmin();
}


function obterLabelPapelOperacionalAdmin(papel) {
  const mapa = {
    gestor: "Gestor",
    recepcao: "Recepcao",
    prestador: "Prestador",
  };

  return mapa[String(papel || "").trim().toLowerCase()] || "Operacional";
}

async function preencherProfissionaisUsuarioOperacionalAdmin() {
  const select = document.getElementById("acesso-equipe-profissional");

  if (!select || !adminProntoParaRequisicao()) {
    return;
  }

  const valorAtual = select.value;

  select.innerHTML = '<option value="">Selecione um profissional</option>';

  try {
    const profissionais = await apiRequest(
      `/api/${tenantSlugLogado}/profissionais`,
      {
        auth: true,
      }
    );

    for (const profissional of profissionais || []) {
      const option = document.createElement("option");
      option.value = profissional.nome;
      option.textContent = profissional.nome;
      select.appendChild(option);
    }

    if (valorAtual) {
      select.value = valorAtual;
    }
  } catch (erro) {
    console.error("Erro ao carregar profissionais para acessos:", erro);
  }
}

function renderizarUsuariosOperacionaisAdmin(usuarios) {
  const area = document.getElementById("lista-usuarios-operacionais");

  if (!area) {
    return;
  }

  const lista = Array.isArray(usuarios) ? usuarios : [];

  if (!lista.length) {
    area.innerHTML = criarEstadoVazioAdmin({
      icone: "?",
      titulo: "Nenhum acesso cadastrado ainda",
      descricao:
        "Crie acessos para recepcao ou prestadores entrarem com login pr?prio.",
      textoBotao: "Criar primeiro acesso",
      secaoDestino: "secao-profissionais",
    });

    return;
  }

  area.innerHTML = "";

  for (const usuario of lista) {
    const item = document.createElement("div");
    item.className = "item-lista";

    const papel = obterLabelPapelOperacionalAdmin(usuario.papel);
    const status = usuario.ativo ? "Ativo" : "Inativo";
    const profissional = usuario.profissional_nome || "Sem vinculo";

    const textoBotaoStatus = usuario.ativo ? "Desativar" : "Reativar";
    const proximoStatus = usuario.ativo ? "false" : "true";

    item.innerHTML = `
      <div>
        <strong>${usuario.nome || "-"}</strong>
        <small>
          ${usuario.email || "-"} - ${papel} - ${profissional} - ${status}
        </small>
      </div>

      <button
        type="button"
        class="btn-del-mini"
        onclick="alternarStatusUsuarioOperacionalAdmin(${usuario.id}, ${proximoStatus})"
      >
        ${textoBotaoStatus}
      </button>
    `;

    area.appendChild(item);
  }
}

async function carregarUsuariosOperacionaisAdmin() {
  if (!adminProntoParaRequisicao()) {
    return;
  }

  if (carregandoAcessosEquipeAdmin) {
    return;
  }

  carregandoAcessosEquipeAdmin = true;

  const area = document.getElementById("lista-usuarios-operacionais");

  if (!area) {
    return;
  }

  area.innerHTML = criarEstadoVazioAdmin({
    icone: "?",
    titulo: "Carregando acessos",
    descricao: "Buscando usu?rios operacionais da equipe.",
  });

  try {
    await preencherProfissionaisUsuarioOperacionalAdmin();

    const resposta = await apiRequest(
      `/api/${tenantSlugLogado}/admin/usuarios-operacionais`,
      {
        auth: true,
      }
    );

    renderizarUsuariosOperacionaisAdmin(resposta.usuarios || []);
  } catch (erro) {
    tratarErro(erro);
  } finally {
    carregandoAcessosEquipeAdmin = false;
  }
}

async function salvarUsuarioOperacionalAdmin() {
  if (!adminProntoParaRequisicao()) {
    return;
  }

  const nome = obterValorCampo("acesso-equipe-nome", "");
  const email = obterValorCampo("acesso-equipe-email", "");
  const senha = obterValorCampo("acesso-equipe-senha", "");
  const papel = obterValorCampo("acesso-equipe-papel", "prestador");
  const profissionalNome = papel === "prestador"
    ? obterValorCampo("acesso-equipe-profissional", "")
    : "";
  const ativo = obterValorCampo("acesso-equipe-ativo", "true") === "true";

  if (!nome || !email || !senha) {
    exibirMensagemAdmin("Informe nome, e-mail e senha do acesso.");
    return;
  }

  if (papel === "prestador" && !profissionalNome) {
    exibirMensagemAdmin("Prestador precisa estar vinculado a um profissional.");
    return;
  }

  try {
    await apiRequest(
      `/api/${tenantSlugLogado}/admin/usuarios-operacionais`,
      {
        method: "POST",
        auth: true,
        body: {
          nome,
          email,
          senha,
          papel,
          profissional_nome: profissionalNome || null,
          ativo,
        },
      }
    );

    document.getElementById("acesso-equipe-nome").value = "";
    document.getElementById("acesso-equipe-email").value = "";
    document.getElementById("acesso-equipe-senha").value = "";
    document.getElementById("acesso-equipe-papel").value = "prestador";
    document.getElementById("acesso-equipe-profissional").value = "";
    document.getElementById("acesso-equipe-ativo").value = "true";
    atualizarCampoProfissionalPorPapelAcessoAdmin();

    await carregarUsuariosOperacionaisAdmin();

    exibirMensagemPainel("Acesso operacional criado com sucesso.");
  } catch (erro) {
    tratarErro(erro);
  }
}


async function alternarStatusUsuarioOperacionalAdmin(usuarioId, ativo) {
  if (!adminProntoParaRequisicao()) {
    return;
  }

  const acao = ativo ? "reativar" : "desativar";

  if (!confirm(`Deseja ${acao} este acesso da equipe?`)) {
    return;
  }

  try {
    await apiRequest(
      `/api/${tenantSlugLogado}/admin/usuarios-operacionais/${usuarioId}`,
      {
        method: "PUT",
        auth: true,
        body: {
          ativo,
        },
      }
    );

    await carregarUsuariosOperacionaisAdmin();

    exibirMensagemPainel(
      ativo
        ? "Acesso reativado com sucesso."
        : "Acesso desativado com sucesso."
    );
  } catch (erro) {
    tratarErro(erro);
  }
}

window.alternarStatusUsuarioOperacionalAdmin =
  alternarStatusUsuarioOperacionalAdmin;


window.carregarUsuariosOperacionaisAdmin = carregarUsuariosOperacionaisAdmin;
window.salvarUsuarioOperacionalAdmin = salvarUsuarioOperacionalAdmin;


function agendarCarregamentoAcessosEquipeAdmin() {
    window.setTimeout(() => {
        const secaoEquipe = document.getElementById("secao-profissionais");
        const listaAcessos = document.getElementById("lista-usuarios-operacionais");

        if (!secaoEquipe || !listaAcessos) {
            return;
        }

        const secaoVisivel =
            secaoEquipe.classList.contains("ativa")
            || secaoEquipe.style.display !== "none";

        if (!secaoVisivel) {
            return;
        }

        carregarUsuariosOperacionaisAdmin();
    }, 250);
}

document.addEventListener("click", (evento) => {
    const alvo = evento.target?.closest?.(
        '[data-secao="secao-profissionais"], [onclick*="secao-profissionais"]'
    );

    if (!alvo) {
        return;
    }

    agendarCarregamentoAcessosEquipeAdmin();
});




function formatarResumoComissaoProfissionalAdmin(tipo, valor) {
    const tipoNormalizado = String(tipo || "nenhuma").trim().toLowerCase();
    const valorNumerico = Number(valor || 0);

    if (tipoNormalizado === "percentual") {
        return `${valorNumerico}% sobre atendimentos concluidos`;
    }

    if (tipoNormalizado === "valor_fixo") {
        return `${formatarMoeda(valorNumerico)} por atendimento concluido`;
    }

    return "sem comissao configurada";
}

async function salvarComissaoProfissionalAdmin(profissionalId) {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const campoTipo = document.getElementById(`comissao-tipo-${profissionalId}`);
    const campoValor = document.getElementById(`comissao-valor-${profissionalId}`);

    if (!campoTipo || !campoValor) {
        exibirMensagemAdmin("Campos de comissao nao encontrados.");
        return;
    }

    const comissaoTipo = campoTipo.value || "nenhuma";
    const comissaoValor = Number(campoValor.value || 0);

    try {
        await apiRequest(
            `/api/${tenantSlugLogado}/profissionais/${profissionalId}/comissao`,
            {
                method: "PUT",
                auth: true,
                body: {
                    comissao_tipo: comissaoTipo,
                    comissao_valor: comissaoValor,
                },
            }
        );

        await carregarEquipe();

        exibirMensagemPainel("Comissao do profissional atualizada com sucesso.");
    } catch (erro) {
        tratarErro(erro);
    }
}

window.salvarComissaoProfissionalAdmin = salvarComissaoProfissionalAdmin;
window.salvarProfissionaisServicoAdmin = salvarProfissionaisServicoAdmin;


async function salvarProfissional() {
  const input = document.getElementById("novo-prof-nome");
  const nome = input.value.trim();

  if (!nome) {
    exibirMensagemAdmin("Informe o nome do profissional.");
    return;
  }

  try {
    await apiRequest(`/api/${tenantSlugLogado}/profissionais`, {
      method: "POST",
      auth: true,
      body: { nome },
    });

    input.value = "";

    await carregarEquipe();
    await atualizarResumoAdminAposMudanca();

    invalidarSecoesAdmin([
      "secao-dashboard",
      "secao-configuracoes",
      "secao-agenda",
      "secao-bloqueios-agenda",
    ]);

      exibirMensagemPainel("Profissional adicionado com sucesso.");

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
        await atualizarResumoAdminAposMudanca();

        exibirMensagemPainel("Profissional removido com sucesso.");

    } catch (erro) {
        tratarErro(erro);
    }
}


/* =========================================================
   SERVIÇOS
========================================================= */


async function obterProfissionaisAptosServicoAdmin(servicoId) {
    try {
        const resposta = await apiRequest(
            `/api/${tenantSlugLogado}/servicos/${servicoId}/profissionais`,
            {
                auth: true,
            }
        );

        return resposta?.profissionais || [];
    } catch (erro) {
        console.warn("Nao foi possivel carregar profissionais aptos do servico.", erro);
        return [];
    }
}

function obterIdsProfissionaisSelecionadosServicoAdmin(servicoId) {
    return Array.from(
        document.querySelectorAll(
            `[data-servico-profissional="${servicoId}"]:checked`
        )
    ).map((checkbox) => Number(checkbox.value)).filter(Boolean);
}

async function salvarProfissionaisServicoAdmin(servicoId) {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const idServico = Number(servicoId);
    const profissionalIds = obterIdsProfissionaisSelecionadosServicoAdmin(idServico);

    console.log("Salvando profissionais aptos do servico.", {
        servicoId: idServico,
        profissionalIds,
    });

    try {
        const resposta = await apiRequest(
            `/api/${tenantSlugLogado}/servicos/${idServico}/profissionais`,
            {
                method: "PUT",
                auth: true,
                body: {
                    profissional_ids: profissionalIds,
                },
            }
        );

        console.log("Profissionais aptos atualizados.", resposta);

        ultimoCarregamentoServicosAdmin = 0;

        await carregarServicos({
            forcar: true,
        });

        exibirMensagemPainel("Profissionais aptos do servico atualizados com sucesso.");
    } catch (erro) {
        console.error("Erro ao salvar profissionais aptos do servico.", erro);
        tratarErro(erro);
    }
}

function renderizarProfissionaisServicoAdmin(servico, profissionais, profissionaisAptos) {
    const aptosIds = new Set(
        (profissionaisAptos || []).map((profissional) => Number(profissional.id))
    );

    if (!profissionais.length) {
        return `
            <div class="servico-profissionais-admin">
                <small>Nenhum profissional cadastrado ainda.</small>
            </div>
        `;
    }

    const nomesAptos = (profissionaisAptos || [])
        .map((profissional) => profissional.nome)
        .filter(Boolean);

    const servicoRestrito = nomesAptos.length > 0;

    const resumoAptos = servicoRestrito
        ? nomesAptos.join(", ")
        : "Todos os profissionais cadastrados podem executar este servico.";

    const selo = servicoRestrito
        ? '<span class="selo-vinculo-servico-admin restrito">Restrito</span>'
        : '<span class="selo-vinculo-servico-admin livre">Todos executam</span>';

    const ajuda = servicoRestrito
        ? "Somente os profissionais marcados aparecem na agenda publica para este servico."
        : "Nenhum profissional especifico foi marcado. Por isso, todos aparecem na agenda publica para este servico.";

    const opcoes = profissionais.map((profissional) => {
        const checked = aptosIds.has(Number(profissional.id)) ? "checked" : "";

        return `
            <label class="opcao-vinculo-servico-admin">
                <input
                    type="checkbox"
                    value="${profissional.id}"
                    data-servico-profissional="${servico.id}"
                    ${checked}
                >
                <span>${profissional.nome}</span>
            </label>
        `;
    }).join("");

    return `
        <div class="servico-profissionais-admin">
            <div class="cabecalho-vinculo-servico-admin">
                ${selo}
                <small><strong>Aptos:</strong> ${resumoAptos}</small>
            </div>

            <small class="ajuda-vinculo-servico-admin">
                ${ajuda}
            </small>

            <div class="grid-vinculos-servico-admin">
                ${opcoes}
            </div>

            <button
                type="button"
                class="btn-secundario"
                onclick="salvarProfissionaisServicoAdmin(${servico.id})"
            >
                Salvar profissionais aptos
            </button>
        </div>
    `;
}


async function carregarServicos(opcoes = {}) {
    if (!adminProntoParaRequisicao()) {
        return;
    }

    const forcar = opcoes?.forcar === true;
    const area = document.getElementById("lista-cardapio");

    if (!area) {
        return;
    }

    if (
        !forcar
        && cacheAdminAindaValido(
            ultimoCarregamentoServicosAdmin,
            TEMPO_CACHE_CURTO_ADMIN_MS
        )
    ) {
        return;
    }

    if (carregandoServicosAdmin) {
        return;
    }

    carregandoServicosAdmin = true;

    area.innerHTML = criarEstadoVazioAdmin({
        icone: "??",
        titulo: "Carregando servicos",
        descricao: "Buscando servicos e profissionais aptos.",
    });

    try {
        const [servicosResposta, profissionaisResposta] = await Promise.all([
            apiRequest(`/api/${tenantSlugLogado}/servicos`, {
                auth: true,
            }),
            apiRequest(`/api/${tenantSlugLogado}/profissionais`, {
                auth: true,
            }),
        ]);

        const servicos = Array.isArray(servicosResposta)
            ? servicosResposta
            : servicosResposta?.servicos || [];

        const profissionais = Array.isArray(profissionaisResposta)
            ? profissionaisResposta
            : profissionaisResposta?.profissionais || [];

        if (!servicos.length) {
            area.innerHTML = criarEstadoVazioAdmin({
                icone: "??",
                titulo: "Nenhum servico cadastrado ainda",
                descricao: "Cadastre os servicos para que os clientes possam agendar.",
                textoBotao: "Cadastrar servico",
                secaoDestino: "secao-servicos",
            });

            ultimoCarregamentoServicosAdmin = Date.now();
            return;
        }

        const vinculosPorServico = await Promise.all(
            servicos.map(async (servico) => ({
                servicoId: servico.id,
                profissionaisAptos: await obterProfissionaisAptosServicoAdmin(servico.id),
            }))
        );

        const mapaAptos = new Map(
            vinculosPorServico.map((item) => [
                Number(item.servicoId),
                item.profissionaisAptos,
            ])
        );

        area.innerHTML = "";

        for (const servico of servicos) {
            const profissionaisAptos = mapaAptos.get(Number(servico.id)) || [];

            const item = document.createElement("div");
            item.className = "card-servico-admin";
            item.innerHTML = `
                <div>
                    <strong>${servico.nome}</strong>
                    <p>
                        ${formatarMoeda(servico.preco)} - ${servico.duracao} min
                    </p>
                </div>

                ${renderizarProfissionaisServicoAdmin(
                    servico,
                    profissionais,
                    profissionaisAptos
                )}

                <button
                    type="button"
                    onclick="deletarServico(${servico.id})"
                >
                    Remover
                </button>
            `;

            area.appendChild(item);
        }

        ultimoCarregamentoServicosAdmin = Date.now();
    } catch (erro) {
        tratarErro(erro);
    } finally {
        carregandoServicosAdmin = false;
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
        await atualizarResumoAdminAposMudanca();

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
        await atualizarResumoAdminAposMudanca();


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


function usuarioAdminEhGestor() {
  return obterPapelUsuarioAdmin() === "gestor"
    || obterPermissoesUsuarioAdmin().includes("*");
}

function usuarioAdminEhRecepcao() {
  return obterPapelUsuarioAdmin() === "recepcao";
}

function usuarioAdminPodeVerFinanceiroGeral() {
  return usuarioAdminEhGestor();
}

function usuarioAdminPodeVerFinanceiroProprio() {
  return (
    usuarioAdminEhPrestador()
    && (
      usuarioAdminTemPermissao("ver_financeiro_proprio")
      || usuarioAdminTemPermissao("ver_comissao_propria")
    )
  );
}

function usuarioAdminPodeVerAlgumFinanceiro() {
  return (
    usuarioAdminPodeVerFinanceiroGeral()
    || usuarioAdminPodeVerFinanceiroProprio()
  );
}

function obterContainerFinanceiroAdmin(elemento) {
  if (!elemento) {
    return null;
  }

  return (
    elemento.closest(".metric-card")
    || elemento.closest(".financeiro-resumo-card")
    || elemento.closest(".agenda-resumo-card")
    || elemento.closest("section")
    || elemento.parentElement
  );
}

function alternarElementoFinanceiroAdmin(id, visivel) {
  const elemento = document.getElementById(id);

  if (!elemento) {
    return;
  }

  const container = obterContainerFinanceiroAdmin(elemento);

  if (container) {
    container.hidden = !visivel;
    container.setAttribute("aria-hidden", String(!visivel));
  }
}

function ajustarColunasFinanceirasTabelaAdmin(containerSelector, termos, visivel) {
  const container = document.querySelector(containerSelector);

  if (!container) {
    return;
  }

  const termosNormalizados = (termos || []).map((termo) =>
    String(termo || "").trim().toLowerCase()
  );

  const tabelas = container.querySelectorAll("table");

  tabelas.forEach((tabela) => {
    const cabecalhos = Array.from(tabela.querySelectorAll("thead th"));

    cabecalhos.forEach((th, indice) => {
      const texto = String(th.textContent || "").trim().toLowerCase();
      const ehFinanceiro = termosNormalizados.some((termo) =>
        texto.includes(termo)
      );

      if (!ehFinanceiro) {
        return;
      }

      th.hidden = !visivel;
      th.setAttribute("aria-hidden", String(!visivel));

      tabela.querySelectorAll("tbody tr").forEach((linha) => {
        const celula = linha.children[indice];

        if (celula) {
          celula.hidden = !visivel;
          celula.setAttribute("aria-hidden", String(!visivel));
        }
      });
    });
  });
}


function ocultarElementoDashboardAdmin(id, ocultar) {
    const elemento = document.getElementById(id);

    if (!elemento) {
        return;
    }

    elemento.hidden = Boolean(ocultar);
    elemento.setAttribute("aria-hidden", String(Boolean(ocultar)));
    elemento.style.display = ocultar ? "none" : "";
}

function aplicarDashboardLimpoPorPerfilAdmin() {
    const ehGestor = usuarioAdminEhGestor();
    const ehRecepcao = usuarioAdminEhRecepcao();
    const ehPrestador = usuarioAdminEhPrestador();

    const ocultarCardsGestao = ehRecepcao || ehPrestador;

    ocultarElementoDashboardAdmin("card-link-publico-admin", ocultarCardsGestao);
    ocultarElementoDashboardAdmin("card-onboarding-admin", ocultarCardsGestao);
    ocultarElementoDashboardAdmin("dashboard-acoes-rapidas", ocultarCardsGestao);
    ocultarElementoDashboardAdmin("dashboard-insight-dia", ehPrestador);

    const kicker = document.getElementById("dashboard-pro-kicker");
    const titulo = document.getElementById("dashboard-pro-titulo");
    const subtitulo = document.getElementById("dashboard-pro-subtitulo");

    if (ehPrestador) {
        if (kicker) kicker.textContent = "Painel do prestador";
        if (titulo) titulo.textContent = "Minha agenda e producao";
        if (subtitulo) {
            subtitulo.textContent =
                "Acompanhe seus atendimentos, conclusoes e comissao estimada.";
        }
    } else if (ehRecepcao) {
        if (kicker) kicker.textContent = "Painel da recepcao";
        if (titulo) titulo.textContent = "Agenda e atendimento";
        if (subtitulo) {
            subtitulo.textContent =
                "Acompanhe a agenda, clientes e operacao do atendimento.";
        }
    } else if (ehGestor) {
        if (kicker) kicker.textContent = "Painel do negocio";
        if (titulo) titulo.textContent = "Resumo inteligente da sua operacao";
    }
}


function aplicarVisibilidadeFinanceiraOperacionalAdmin() {
  const podeVerAlgumFinanceiro = usuarioAdminPodeVerAlgumFinanceiro();
  const podeVerFinanceiroGeral = usuarioAdminPodeVerFinanceiroGeral();

  const idsFinanceiroDashboard = [
    "visor-hoje-receita",
    "visor-faturamento",
    "visor-faturamento-concluido",
    "visor-agendamentos-faturaveis",
    "visor-ticket-medio",
    "visor-cancelamentos-financeiro",
    "visor-financeiro-receita-prevista",
    "visor-financeiro-receita-realizada",
  ];

  idsFinanceiroDashboard.forEach((id) =>
    alternarElementoFinanceiroAdmin(id, podeVerAlgumFinanceiro)
  );

  const resumoFinanceiro = document.getElementById("resumo-financeiro-dashboard");

  if (resumoFinanceiro) {
    resumoFinanceiro.hidden = !podeVerAlgumFinanceiro;
    resumoFinanceiro.setAttribute(
      "aria-hidden",
      String(!podeVerAlgumFinanceiro)
    );
  }

  alternarElementoFinanceiroAdmin(
    "visor-faturamento-crm",
    podeVerFinanceiroGeral
  );

  alternarElementoFinanceiroAdmin(
    "visor-ticket-medio-crm",
    podeVerFinanceiroGeral
  );

  ajustarColunasFinanceirasTabelaAdmin(
    "#secao-agenda",
    ["valor"],
    podeVerAlgumFinanceiro
  );

  ajustarColunasFinanceirasTabelaAdmin(
    "#secao-clientes-crm",
    ["faturamento", "ticket"],
    podeVerFinanceiroGeral
  );

  const subtituloDashboard = document.getElementById("dashboard-pro-subtitulo");

  if (subtituloDashboard) {
    if (usuarioAdminEhRecepcao()) {
      subtituloDashboard.textContent =
        "Acompanhe agenda, clientes e operacao do atendimento.";
    } else if (usuarioAdminEhPrestador()) {
      subtituloDashboard.textContent =
        "Acompanhe sua agenda, seus atendimentos e sua producao.";
    }
  }

  const tituloAgenda = document.querySelector("#secao-agenda h3");
  const descricaoAgenda = document.querySelector("#secao-agenda .descricao-bloco");

  if (tituloAgenda) {
    if (usuarioAdminEhRecepcao()) {
      tituloAgenda.textContent = "Agenda";
    } else if (usuarioAdminEhPrestador()) {
      tituloAgenda.textContent = "Minha agenda e producao";
    } else {
      tituloAgenda.textContent = "Agenda e faturamento";
    }
  }

  if (descricaoAgenda) {
    if (usuarioAdminEhRecepcao()) {
      descricaoAgenda.textContent =
        "Consulte e acompanhe os agendamentos recebidos.";
    } else if (usuarioAdminEhPrestador()) {
      descricaoAgenda.textContent =
        "Consulte seus atendimentos e sua producao individual.";
    } else {
      descricaoAgenda.textContent =
        "Consulte os agendamentos recebidos e o faturamento previsto.";
    }
  }
}



function obterAgendamentosConcluidosPrestadorAdmin(agendamentos) {
    const profissionalVinculado = obterProfissionalVinculadoUsuarioAdmin();
    const profissionalNormalizado = normalizarNomeProfissionalAdmin(
        profissionalVinculado
    );

    return (agendamentos || []).filter((agendamento) => {
        const status = String(agendamento?.status || "")
            .trim()
            .toLowerCase();

        const profissionalAgendamento = normalizarNomeProfissionalAdmin(
            agendamento?.profissional
        );

        return (
            status === "concluido"
            && profissionalAgendamento === profissionalNormalizado
        );
    });
}

async function obterComissaoProfissionalLogadoAdmin() {
    const profissionalVinculado = obterProfissionalVinculadoUsuarioAdmin();
    const profissionalNormalizado = normalizarNomeProfissionalAdmin(
        profissionalVinculado
    );

    if (!profissionalNormalizado) {
        return {
            comissao_tipo: "nenhuma",
            comissao_valor: 0,
            profissional_nome: "",
        };
    }

    const profissionais = await apiRequest(
        `/api/${tenantSlugLogado}/profissionais`,
        {
            auth: true,
        }
    );

    const profissional = (profissionais || []).find((item) =>
        normalizarNomeProfissionalAdmin(item?.nome) === profissionalNormalizado
    );

    return {
        comissao_tipo: profissional?.comissao_tipo || "nenhuma",
        comissao_valor: Number(profissional?.comissao_valor || 0),
        profissional_nome: profissional?.nome || profissionalVinculado,
    };
}

function calcularResumoProducaoPrestadorAdmin(agendamentos, comissao) {
    const concluidos = obterAgendamentosConcluidosPrestadorAdmin(agendamentos);

    const valorProduzido = concluidos.reduce(
        (total, agendamento) => total + Number(agendamento?.valor || 0),
        0
    );

    const tipo = String(comissao?.comissao_tipo || "nenhuma")
        .trim()
        .toLowerCase();

    const valorComissao = Number(comissao?.comissao_valor || 0);

    let valorReceber = 0;

    if (tipo === "percentual") {
        valorReceber = valorProduzido * valorComissao / 100;
    }

    if (tipo === "valor_fixo") {
        valorReceber = concluidos.length * valorComissao;
    }

    const servicos = {};

    for (const agendamento of concluidos) {
        const nomeServico = agendamento?.servico || "Servico nao informado";

        if (!servicos[nomeServico]) {
            servicos[nomeServico] = {
                quantidade: 0,
                valor: 0,
            };
        }

        servicos[nomeServico].quantidade += 1;
        servicos[nomeServico].valor += Number(agendamento?.valor || 0);
    }

    return {
        atendimentos: concluidos.length,
        valorProduzido,
        valorReceber,
        tipo,
        valorComissao,
        servicos,
        ultimosAtendimentos: concluidos.slice(0, 5),
    };
}

function formatarTipoComissaoPrestadorAdmin(tipo, valor) {
    if (tipo === "percentual") {
        return `${Number(valor || 0)}% sobre atendimentos concluidos`;
    }

    if (tipo === "valor_fixo") {
        return `${formatarMoeda(valor)} por atendimento concluido`;
    }

    return "Sem comissao configurada";
}


async function obterAgendamentosParaResumoPrestadorAdmin(agendamentos) {
    if (Array.isArray(agendamentos) && agendamentos.length > 0) {
        return agendamentos;
    }

    if (Array.isArray(agendamentosAdminCache) && agendamentosAdminCache.length > 0) {
        return agendamentosAdminCache;
    }

    try {
        const resposta = await apiRequest(
            `/api/${tenantSlugLogado}/admin/agendamentos`,
            {
                auth: true,
            }
        );

        const lista = resposta?.agendamentos || [];

        if (Array.isArray(lista)) {
            agendamentosAdminCache = lista;
            return lista;
        }
    } catch (erro) {
        console.warn("Nao foi possivel buscar agendamentos para resumo do prestador.", erro);
    }

    return [];
}


async function renderizarResumoProducaoPrestadorAdmin(agendamentos) {
    const cardId = "resumo-producao-prestador-admin";
    const cardExistente = document.getElementById(cardId);

    const agendamentosBase = await obterAgendamentosParaResumoPrestadorAdmin(
        agendamentos
    );

    if (!usuarioAdminEhPrestador()) {
        if (cardExistente) {
            cardExistente.remove();
        }

        return;
    }

    const secaoDashboard = document.getElementById("secao-dashboard");

    if (!secaoDashboard) {
        return;
    }

    const comissao = await obterComissaoProfissionalLogadoAdmin();
    const resumo = calcularResumoProducaoPrestadorAdmin(
        agendamentosBase,
        comissao
    );

    let card = cardExistente;

    if (!card) {
        card = document.createElement("section");
        card.id = cardId;
        card.className = "financeiro-resumo-card";

        const referencia = document.getElementById("dashboard-hoje-negocio");

        if (referencia && referencia.parentElement) {
            referencia.insertAdjacentElement("afterend", card);
        } else {
            secaoDashboard.prepend(card);
        }
    }

    const servicosHtml = Object.entries(resumo.servicos)
        .map(([nome, dados]) => `
            <li>
                <strong>${nome}</strong>
                <span>
                    ${dados.quantidade} atendimento(s) -
                    ${formatarMoeda(dados.valor)}
                </span>
            </li>
        `)
        .join("");

    const ultimosHtml = resumo.ultimosAtendimentos
        .map((agendamento) => `
            <li>
                <strong>${agendamento.data || "-"} ${agendamento.horario || ""}</strong>
                <span>
                    ${agendamento.cliente_nome || "-"} -
                    ${agendamento.servico || "-"} -
                    ${formatarMoeda(agendamento.valor || 0)}
                </span>
            </li>
        `)
        .join("");

    card.innerHTML = `
        <div class="financeiro-resumo-topo">
            <div>
                <span>Minha producao</span>
                <h3>Resumo do prestador</h3>
                <p>
                    Acompanhe seus atendimentos concluidos, valor produzido
                    e comissao estimada.
                </p>
            </div>
        </div>

        <div class="financeiro-resumo-grid">
            <div>
                <span>Atendimentos concluidos</span>
                <strong>${resumo.atendimentos}</strong>
            </div>

            <div>
                <span>Valor produzido</span>
                <strong>${formatarMoeda(resumo.valorProduzido)}</strong>
            </div>

            <div>
                <span>A receber estimado</span>
                <strong>${formatarMoeda(resumo.valorReceber)}</strong>
            </div>

            <div>
                <span>Regra de comissao</span>
                <strong>
                    ${formatarTipoComissaoPrestadorAdmin(
                        resumo.tipo,
                        resumo.valorComissao
                    )}
                </strong>
            </div>
        </div>

        <div class="financeiro-resumo-detalhes">
            <h4>Servicos realizados</h4>
            <ul>
                ${servicosHtml || "<li>Nenhum atendimento concluido ainda.</li>"}
            </ul>

            <h4>Ultimos atendimentos concluidos</h4>
            <ul>
                ${ultimosHtml || "<li>Nenhum atendimento concluido ainda.</li>"}
            </ul>
        </div>
    `;
}


window.renderizarResumoProducaoPrestadorAdmin = renderizarResumoProducaoPrestadorAdmin;



async function carregarResumoComissoesRepassesAdmin() {
    const card = document.getElementById(
        "comissoes-repasses-dashboard"
    );

    if (!card) {
        return;
    }

    if (!usuarioAdminPodeVerFinanceiroGeral()) {
        card.hidden = true;
        card.setAttribute("aria-hidden", "true");
        return;
    }

    card.hidden = false;
    card.setAttribute("aria-hidden", "false");

    const visorQuantidadePendentes = document.getElementById(
        "visor-comissoes-pendentes-quantidade"
    );

    const visorTotalPendente = document.getElementById(
        "visor-comissoes-pendentes-total"
    );

    const visorQuantidadeRepasses = document.getElementById(
        "visor-repasses-quantidade"
    );

    const visorTotalRepasses = document.getElementById(
        "visor-repasses-total"
    );

    const listaRepasses = document.getElementById(
        "lista-repasses-recentes-admin"
    );

    try {
        const [
            pendentes,
            historico,
        ] = await Promise.all([
            apiRequest(
                `/api/${tenantSlugLogado}/comissoes/pendentes`,
                {
                    auth: true,
                }
            ),
            apiRequest(
                `/api/${tenantSlugLogado}/repasses`,
                {
                    auth: true,
                }
            ),
        ]);

        if (visorQuantidadePendentes) {
            visorQuantidadePendentes.textContent = String(
                Number(pendentes?.quantidade || 0)
            );
        }

        if (visorTotalPendente) {
            visorTotalPendente.textContent = formatarMoeda(
                pendentes?.total_pendente || 0
            );
        }

        if (visorQuantidadeRepasses) {
            visorQuantidadeRepasses.textContent = String(
                Number(historico?.quantidade || 0)
            );
        }

        if (visorTotalRepasses) {
            visorTotalRepasses.textContent = formatarMoeda(
                historico?.total_pago || 0
            );
        }

        if (!listaRepasses) {
            return;
        }

        const repasses = Array.isArray(historico?.repasses)
            ? historico.repasses
            : [];

        if (!repasses.length) {
            listaRepasses.innerHTML = `
                <li>
                    Nenhum repasse registrado ainda.
                </li>
            `;

            return;
        }

        listaRepasses.innerHTML = repasses
            .slice(0, 5)
            .map((repasse) => {
                const profissional = escaparHtmlAdmin(
                    repasse?.profissional_nome
                    || "Profissional n?o informado"
                );

                const quantidadeComissoes = Number(
                    repasse?.quantidade_comissoes || 0
                );

                const valor = formatarMoeda(
                    repasse?.valor || 0
                );

                const pagoEm = repasse?.pago_em
                    ? formatarDataHoraBR(repasse.pago_em)
                    : "-";

                return `
                    <li>
                        <strong>${profissional}</strong>

                        <span>
                            ${valor}
                            ? ${quantidadeComissoes} comiss?o(?es)
                            ? ${pagoEm}
                        </span>
                    </li>
                `;
            })
            .join("");

    } catch (erro) {
        console.error(
            "Erro ao carregar comissoes e repasses:",
            erro
        );

        if (listaRepasses) {
            listaRepasses.innerHTML = `
                <li>
                    N?o foi poss?vel carregar os dados financeiros.
                </li>
            `;
        }

        tratarErro(erro);
    }
}


window.carregarResumoComissoesRepassesAdmin =
    carregarResumoComissoesRepassesAdmin;


function usuarioPodeConcluirAgendamentoAdmin(agendamento) {
    const status = String(agendamento?.status || "confirmado")
        .trim()
        .toLowerCase();

    if (["concluido", "cancelado", "faltou", "falta"].includes(status)) {
        return false;
    }

    if (usuarioAdminEhGestor()) {
        return true;
    }

    if (!usuarioAdminEhPrestador()) {
        return false;
    }

    const profissionalAgendamento = normalizarNomeProfissionalAdmin(
        agendamento?.profissional
    );

    const profissionalVinculado = normalizarNomeProfissionalAdmin(
        obterProfissionalVinculadoUsuarioAdmin()
    );

    return (
        profissionalAgendamento
        && profissionalVinculado
        && profissionalAgendamento === profissionalVinculado
    );
}

function renderizarBotaoConcluirAgendamentoAdmin(agendamento) {
    if (!usuarioPodeConcluirAgendamentoAdmin(agendamento)) {
        return "";
    }

    return `
        <button
            type="button"
            onclick="atualizarStatusAgendamento(${agendamento.id}, 'concluido')"
        >
            Concluir
        </button>
    `;
}


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

        const agendamentosOriginais = Array.isArray(dados.agendamentos)
            ? dados.agendamentos
            : [];

        const agendamentos = filtrarAgendamentosPorPerfilOperacionalAdmin(
            agendamentosOriginais
        );

        const total = agendamentos.length;

        const normalizarStatusFinanceiro = (valor) =>
            String(valor || "confirmado").trim().toLowerCase();

        const obterValorAgendamento = (agendamento) =>
            Number(agendamento?.valor || 0);

        const agendamentosFaturaveis = agendamentos.filter((agendamento) => {
            const status = normalizarStatusFinanceiro(agendamento.status);
            return ["confirmado", "concluido"].includes(status);
        });

        const agendamentosConcluidos = agendamentos.filter((agendamento) => {
            const status = normalizarStatusFinanceiro(agendamento.status);
            return status === "concluido";
        });

        const agendamentosPerdidos = agendamentos.filter((agendamento) => {
            const status = normalizarStatusFinanceiro(agendamento.status);
            return ["cancelado", "falta"].includes(status);
        });

        const faturamento = agendamentosFaturaveis.reduce(
            (totalFinanceiro, agendamento) =>
                totalFinanceiro + obterValorAgendamento(agendamento),
            0
        );

        const faturamentoConcluido = agendamentosConcluidos.reduce(
            (totalFinanceiro, agendamento) =>
                totalFinanceiro + obterValorAgendamento(agendamento),
            0
        );

        const ticketMedio = agendamentosFaturaveis.length > 0
            ? faturamento / agendamentosFaturaveis.length
            : 0;

        const atualizarMetricaAdmin = (id, valor) => {
            const elemento = document.getElementById(id);

            if (elemento) {
                elemento.textContent = valor;
            }
        };

        atualizarMetricaAdmin(
            "visor-total-agendamentos",
            total
        );

        atualizarMetricaAdmin(
            "visor-faturamento",
            formatarMoeda(faturamento)
        );

        atualizarMetricaAdmin(
            "visor-faturamento-concluido",
            formatarMoeda(faturamentoConcluido)
        );

        atualizarMetricaAdmin(
            "visor-agendamentos-faturaveis",
            agendamentosFaturaveis.length
        );

        atualizarMetricaAdmin(
            "visor-ticket-medio",
            formatarMoeda(ticketMedio)
        );

        atualizarMetricaAdmin(
            "visor-cancelamentos-financeiro",
            agendamentosPerdidos.length
        );

        const totalConfirmados = agendamentos.filter((agendamento) => {
            const status = normalizarStatusFinanceiro(agendamento.status);
            return status === "confirmado";
        }).length;

        const totalConcluidos = agendamentosConcluidos.length;

        const totalCancelados = agendamentos.filter((agendamento) => {
            const status = normalizarStatusFinanceiro(agendamento.status);
            return status === "cancelado";
        }).length;

        const totalFaltas = agendamentos.filter((agendamento) => {
            const status = normalizarStatusFinanceiro(agendamento.status);
            return status === "falta";
        }).length;

        atualizarMetricaAdmin(
            "visor-financeiro-confirmados",
            totalConfirmados
        );

        atualizarMetricaAdmin(
            "visor-financeiro-concluidos",
            totalConcluidos
        );

        atualizarMetricaAdmin(
            "visor-financeiro-cancelados",
            totalCancelados
        );

        atualizarMetricaAdmin(
            "visor-financeiro-faltas",
            totalFaltas
        );

        atualizarMetricaAdmin(
            "visor-financeiro-receita-prevista",
            formatarMoeda(faturamento)
        );

        atualizarMetricaAdmin(
            "visor-financeiro-receita-realizada",
            formatarMoeda(faturamentoConcluido)
        );

        const agoraDashboard = new Date();
        const dataHojeDashboard = [
            agoraDashboard.getFullYear(),
            String(agoraDashboard.getMonth() + 1).padStart(2, "0"),
            String(agoraDashboard.getDate()).padStart(2, "0")
        ].join("-");

        const agendamentosHoje = agendamentos.filter((agendamento) =>
            String(agendamento?.data || "").slice(0, 10) === dataHojeDashboard
        );

        const agendamentosHojeFaturaveis = agendamentosHoje.filter((agendamento) => {
            const status = normalizarStatusFinanceiro(agendamento.status);
            return ["confirmado", "concluido"].includes(status);
        });

        const receitaHoje = agendamentosHojeFaturaveis.reduce(
            (totalFinanceiro, agendamento) =>
                totalFinanceiro + obterValorAgendamento(agendamento),
            0
        );

        const concluidosHoje = agendamentosHoje.filter((agendamento) => {
            const status = normalizarStatusFinanceiro(agendamento.status);
            return status === "concluido";
        }).length;

        const minutosAgoraDashboard =
            agoraDashboard.getHours() * 60 + agoraDashboard.getMinutes();

        const obterMinutosHorarioDashboard = (horario) => {
            const partes = String(horario || "").trim().split(":");

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
        };

        const horariosFuturosHoje = agendamentosHoje
            .filter((agendamento) => {
                const status = normalizarStatusFinanceiro(agendamento.status);
                return !["cancelado", "falta"].includes(status);
            })
            .map((agendamento) => {
                const horario = String(agendamento?.horario || "").trim();

                return {
                    horario,
                    minutos: obterMinutosHorarioDashboard(horario)
                };
            })
            .filter((item) =>
                item.horario
                && item.minutos !== null
                && item.minutos >= minutosAgoraDashboard
            )
            .sort((a, b) => a.minutos - b.minutos);

        atualizarMetricaAdmin(
            "visor-hoje-agendamentos",
            agendamentosHoje.length
        );

        atualizarMetricaAdmin(
            "visor-hoje-receita",
            formatarMoeda(receitaHoje)
        );

        atualizarMetricaAdmin(
            "visor-hoje-concluidos",
            concluidosHoje
        );

        const proximoHorarioHojeDashboard =
            horariosFuturosHoje[0]?.horario || "--:--";

        atualizarMetricaAdmin(
            "visor-hoje-proximo",
            proximoHorarioHojeDashboard
        );

        atualizarInsightDashboardAdmin(
            agendamentosHoje.length,
            receitaHoje,
            concluidosHoje,
            proximoHorarioHojeDashboard
        );

        tbody.innerHTML = "";

        if (!agendamentos.length) {
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

        for (const agendamento of agendamentos) {
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

                    ${renderizarBotaoConcluirAgendamentoAdmin(agendamento)}

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

            agendamentosAdminCache = agendamentos;


            atualizarIndicadorNovosAgendamentos(agendamentosAdminCache);

            document.getElementById("visor-total-agendamentos").textContent =
                total;
        }

        ultimoCarregamentoAgendamentosAdmin = Date.now();

        if (!atualizandoResumoAdmin) {
          await atualizarResumoAdminAposMudanca();
        }

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

            ${renderizarBotaoConcluirAgendamentoAdmin(evento)}

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
          await Promise.all([
            carregarEquipe({
              forcar,
            }),
            carregarUsuariosOperacionaisAdmin(),
          ]);
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


/* Fila de espera - Sprint 4.7B */
let filaEsperaAdminCache = [];

function usuarioAdminPodeVerFilaEspera() {
    if (usuarioAdminEhGestor && usuarioAdminEhGestor()) {
        return true;
    }

    if (usuarioAdminEhRecepcao && usuarioAdminEhRecepcao()) {
        return true;
    }

    return usuarioAdminTemPermissao
        && (
            usuarioAdminTemPermissao("ver_fila_espera")
            || usuarioAdminTemPermissao("gerenciar_fila_espera")
        );
}

function traduzirStatusFilaEsperaAdmin(status) {
    const mapa = {
        aguardando: "Aguardando",
        chamado: "Chamado",
        agendado: "Agendado",
        cancelado: "Cancelado",
        expirado: "Expirado",
    };

    return mapa[String(status || "").toLowerCase()] || status || "Aguardando";
}


function formatarDataFilaEsperaAdmin(data) {
    if (!data) {
        return "-";
    }

    const partes = String(data).split("-");

    if (partes.length === 3) {
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }

    return String(data);
}

function formatarPeriodoFilaEsperaAdmin(periodo) {
    const mapa = {
        manha: "Manha",
        tarde: "Tarde",
        noite: "Noite",
        qualquer: "Qualquer",
    };

    return mapa[String(periodo || "").toLowerCase()] || periodo || "Qualquer";
}

function criarEstruturaFilaEsperaAdmin() {
    if (document.getElementById("secao-fila-espera")) {
        return;
    }

    const podeVer = usuarioAdminPodeVerFilaEspera();

    const referenciaTab = document.querySelector(".admin-tab");
    const containerTabs = referenciaTab ? referenciaTab.parentElement : null;

    if (containerTabs) {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "admin-tab admin-nav-item";
        botao.dataset.secao = "secao-fila-espera";
        botao.innerHTML = `
            <span class="admin-nav-icon">?</span>
            <span>Fila de espera</span>
        `;
        botao.onclick = () => {
            mostrarSecaoAdmin("secao-fila-espera");
            carregarFilaEsperaAdmin();
        };

        if (!podeVer) {
            botao.hidden = true;
            botao.style.display = "none";
        }

        containerTabs.appendChild(botao);
    }

    const referenciaSecao = document.querySelector(".admin-section, .secao-admin, section[id^='secao-']");
    const containerPrincipal = referenciaSecao ? referenciaSecao.parentElement : document.querySelector("main") || document.body;

    const secao = document.createElement("section");
    secao.id = "secao-fila-espera";
    secao.className = "secao-admin";

    if (!podeVer) {
        secao.hidden = true;
        secao.style.display = "none";
    }

    secao.innerHTML = `
        <div class="fila-espera-admin-header">
            <div>
                <span class="admin-kicker">Operacao</span>
                <h2>Fila de espera</h2>
                <p>
                    Acompanhe clientes interessados em horarios indisponiveis e organize retornos pelo atendimento.
                </p>
            </div>

            <button
                type="button"
                class="btn-secundario"
                onclick="carregarFilaEsperaAdmin()"
            >
                Atualizar fila
            </button>
        </div>

        <div class="fila-espera-admin-resumo">
            <article>
                <small>Aguardando</small>
                <strong id="fila-espera-total-aguardando">0</strong>
            </article>
            <article>
                <small>Chamados</small>
                <strong id="fila-espera-total-chamado">0</strong>
            </article>
            <article>
                <small>Finalizados</small>
                <strong id="fila-espera-total-finalizados">0</strong>
            </article>
        </div>

        <div id="lista-fila-espera-admin" class="lista-fila-espera-admin">
            Carregando fila de espera...
        </div>
    `;

    containerPrincipal.appendChild(secao);
}


function atualizarTextoFilaEsperaAdmin(id, valor) {
    const elemento = document.getElementById(id);

    if (elemento) {
        elemento.textContent = valor;
    }
}

function atualizarResumoFilaEsperaAdmin(itens) {
    const aguardando = itens.filter((item) => item.status === "aguardando").length;
    const chamado = itens.filter((item) => item.status === "chamado").length;
    const finalizados = itens.filter((item) => {
        return ["agendado", "cancelado", "expirado"].includes(item.status);
    }).length;

    atualizarTextoFilaEsperaAdmin("fila-espera-total-aguardando", aguardando);
    atualizarTextoFilaEsperaAdmin("fila-espera-total-chamado", chamado);
    atualizarTextoFilaEsperaAdmin("fila-espera-total-finalizados", finalizados);
}

function renderizarFilaEsperaAdmin(itens) {
    const container = document.getElementById("lista-fila-espera-admin");

    if (!container) {
        return;
    }

    const lista = Array.isArray(itens) ? itens : [];

    atualizarResumoFilaEsperaAdmin(lista);

    if (!lista.length) {
        container.innerHTML = `
            <div class="estado-vazio-admin">
                Nenhum cliente na fila de espera.
            </div>
        `;
        return;
    }

    container.innerHTML = lista.map((item) => {
        const status = String(item.status || "aguardando").toLowerCase();
        const acoesDesabilitadas = ["agendado", "cancelado", "expirado"].includes(status);

        return `
            <article class="fila-espera-card-admin status-${status}">
                <div class="fila-espera-card-topo">
                    <div>
                        <h3>${item.cliente_nome || "Cliente sem nome"}</h3>
                        <p>${item.telefone_cliente || "Telefone nao informado"}</p>
                    </div>

                    <span class="badge-fila-espera-admin">${traduzirStatusFilaEsperaAdmin(status)}</span>
                </div>

                <div class="fila-espera-card-detalhes">
                    <span><strong>Servico:</strong> ${item.servico || "Nao informado"}</span>
                    <span><strong>Profissional:</strong> ${item.profissional_preferido || "Sem preferencia"}</span>
                    <span><strong>Data:</strong> ${formatarDataFilaEsperaAdmin(item.data_desejada)}</span>
                    <span><strong>Periodo:</strong> ${formatarPeriodoFilaEsperaAdmin(item.periodo_preferido)}</span>
                </div>

                ${item.observacao ? `<p class="fila-espera-observacao-admin">${item.observacao}</p>` : ""}

                <div class="fila-espera-card-acoes">
                    ${
                        !acoesDesabilitadas
                            ? `
                    <button
                        type="button"
                        class="btn-primario"
                        onclick="abrirConversaoFilaEsperaAdmin(${item.id})"
                    >
                        Criar agendamento
                    </button>
                    `
                            : ""
                    }

                    <button
                        type="button"
                        class="btn-secundario"
                        onclick="atualizarStatusFilaEsperaAdmin(${item.id}, 'chamado')"
                        ${acoesDesabilitadas ? "disabled" : ""}
                    >
                        Chamar
                    </button>

                    <button
                        type="button"
                        class="btn-secundario"
                        onclick="atualizarStatusFilaEsperaAdmin(${item.id}, 'cancelado')"
                        ${acoesDesabilitadas ? "disabled" : ""}
                    >
                        Cancelar
                    </button>

                    <button
                        type="button"
                        class="btn-secundario"
                        onclick="atualizarStatusFilaEsperaAdmin(${item.id}, 'expirado')"
                        ${acoesDesabilitadas ? "disabled" : ""}
                    >
                        Expirar
                    </button>
                </div>
            </article>
        `;
    }).join("");
}

async function carregarFilaEsperaAdmin() {
    if (!usuarioAdminPodeVerFilaEspera()) {
        return;
    }

    const container = document.getElementById("lista-fila-espera-admin");

    if (container) {
        container.innerHTML = "Carregando fila de espera...";
    }

    try {
        const resposta = await apiRequest(`/api/${tenantSlugLogado}/admin/fila-espera`, {
            auth: true,
        });

        filaEsperaAdminCache = resposta?.fila_espera || [];
        renderizarFilaEsperaAdmin(filaEsperaAdminCache);
    } catch (erro) {
        console.error("Erro ao carregar fila de espera:", erro);

        if (container) {
            container.innerHTML = `
                <div class="estado-vazio-admin">
                    Nao foi possivel carregar a fila de espera.
                </div>
            `;
        }
    }
}

async function atualizarStatusFilaEsperaAdmin(itemId, status) {
    if (!usuarioAdminPodeVerFilaEspera()) {
        alert("Seu perfil nao tem permissao para gerenciar a fila de espera.");
        return;
    }

    try {
        await apiRequest(`/api/${tenantSlugLogado}/admin/fila-espera/${itemId}/status`, {
            method: "PUT",
            auth: true,
            body: { status },
        });

        await carregarFilaEsperaAdmin();
    } catch (erro) {
        console.error("Erro ao atualizar status da fila de espera:", erro);
        alert(erro.message || "Nao foi possivel atualizar o status da fila de espera.");
    }
}

function iniciarFilaEsperaAdminQuandoDisponivel() {
    let tentativas = 0;

    const timer = setInterval(() => {
        tentativas += 1;

        if (typeof tenantSlugLogado !== "undefined" && tenantSlugLogado) {
            criarEstruturaFilaEsperaAdmin();

            if (usuarioAdminPodeVerFilaEspera()) {
                carregarFilaEsperaAdmin();
            }

            clearInterval(timer);
            return;
        }

        if (tentativas >= 20) {
            clearInterval(timer);
        }
    }, 300);
}


let itemFilaConversaoAdmin = null;


function fecharConversaoFilaEsperaAdmin() {
    const modal = document.getElementById("modal-conversao-fila-admin");

    if (modal) {
        modal.remove();
    }

    itemFilaConversaoAdmin = null;
}


async function carregarHorariosConversaoFilaAdmin() {
    const selectHorario = document.getElementById("fila-conversao-horario");
    const campoData = document.getElementById("fila-conversao-data");
    const selectProfissional = document.getElementById("fila-conversao-profissional");

    if (!selectHorario || !campoData || !selectProfissional || !itemFilaConversaoAdmin) {
        return;
    }

    const data = campoData.value;
    const profissional = selectProfissional.value;

    selectHorario.innerHTML = `
        <option value="">Carregando horarios...</option>
    `;

    if (!data || !profissional) {
        selectHorario.innerHTML = `
            <option value="">Selecione data e profissional</option>
        `;
        return;
    }

    try {
        const servicosResposta = await apiRequest(
            `/api/${tenantSlugLogado}/servicos`,
            {
                method: "GET",
                auth: true,
            }
        );

        const servicos = Array.isArray(servicosResposta)
            ? servicosResposta
            : servicosResposta?.servicos || [];

        const servico = servicos.find(
            (item) =>
                String(item.nome || "").trim().toLowerCase()
                === String(itemFilaConversaoAdmin.servico || "").trim().toLowerCase()
        );

        if (!servico) {
            throw new Error("Servico da fila nao encontrado no catalogo.");
        }

        const duracao = Number(servico.duracao || 0);

        if (!duracao) {
            throw new Error("Duracao do servico nao informada.");
        }

        const resposta = await apiRequest(
            `/api/${tenantSlugLogado}/horarios/${encodeURIComponent(data)}/${duracao}/${encodeURIComponent(profissional)}`
        );

        const horarios = resposta?.horarios_disponiveis || [];

        if (!horarios.length) {
            selectHorario.innerHTML = `
                <option value="">Nenhum horario disponivel</option>
            `;
            return;
        }

        selectHorario.innerHTML = `
            <option value="">Selecione um horario</option>
            ${horarios
                .map(
                    (horario) =>
                        `<option value="${horario}">${horario}</option>`
                )
                .join("")}
        `;
    } catch (erro) {
        selectHorario.innerHTML = `
            <option value="">Erro ao carregar horarios</option>
        `;

        exibirMensagemAdmin(
            erro?.message || "Nao foi possivel carregar os horarios."
        );
    }
}


async function abrirConversaoFilaEsperaAdmin(itemId) {
    try {
        const resposta = await apiRequest(
            `/api/${tenantSlugLogado}/admin/fila-espera`,
            {
                auth: true,
            }
        );

        const lista = Array.isArray(resposta?.fila_espera)
            ? resposta.fila_espera
            : [];

        const item = lista.find(
            (registro) => Number(registro.id) === Number(itemId)
        );

        if (!item) {
            exibirMensagemAdmin("Item da fila nao encontrado.");
            return;
        }

        itemFilaConversaoAdmin = item;

        fecharConversaoFilaEsperaAdmin();
        itemFilaConversaoAdmin = item;

        const modal = document.createElement("div");

        modal.id = "modal-conversao-fila-admin";
        modal.className = "modal-conversao-fila-admin";

        modal.innerHTML = `
            <div class="modal-conversao-fila-conteudo">
                <div class="modal-conversao-fila-topo">
                    <div>
                        <span class="admin-kicker">Fila de espera</span>
                        <h3>Criar agendamento</h3>
                    </div>

                    <button
                        type="button"
                        class="btn-secundario"
                        onclick="fecharConversaoFilaEsperaAdmin()"
                    >
                        Fechar
                    </button>
                </div>

                <div class="modal-conversao-fila-resumo">
                    <p><strong>Cliente:</strong> ${item.cliente_nome || "-"}</p>
                    <p><strong>Telefone:</strong> ${item.telefone_cliente || "-"}</p>
                    <p><strong>Servico:</strong> ${item.servico || "-"}</p>
                </div>

                <form
                    id="form-conversao-fila-admin"
                    onsubmit="confirmarConversaoFilaEsperaAdmin(event)"
                >
                    <label>
                        Data
                        <input
                            id="fila-conversao-data"
                            type="date"
                            value="${item.data_desejada || ""}"
                            required
                        >
                    </label>

                    <label>
                        Profissional
                        <select
                            id="fila-conversao-profissional"
                            required
                        >
                            <option value="">Carregando...</option>
                        </select>
                    </label>

                    <label>
                        Horario
                        <select
                            id="fila-conversao-horario"
                            required
                        >
                            <option value="">Selecione data e profissional</option>
                        </select>
                    </label>

                    <div class="modal-conversao-fila-acoes">
                        <button
                            type="button"
                            class="btn-secundario"
                            onclick="fecharConversaoFilaEsperaAdmin()"
                        >
                            Cancelar
                        </button>

                        <button
                            type="submit"
                            class="btn-primario"
                        >
                            Confirmar agendamento
                        </button>
                    </div>
                </form>
            </div>
        `;

        document.body.appendChild(modal);

        const respostaProfissionais = await apiRequest(
            `/api/${tenantSlugLogado}/profissionais`,
            {
                auth: true,
            }
        );

        const profissionais = Array.isArray(respostaProfissionais)
            ? respostaProfissionais
            : respostaProfissionais?.profissionais || [];

        const selectProfissional = document.getElementById(
            "fila-conversao-profissional"
        );

        selectProfissional.innerHTML = `
            <option value="">Selecione um profissional</option>
            ${profissionais
                .map((profissional) => {
                    const nome =
                        profissional.nome
                        || profissional.nome_profissional
                        || "";

                    return `<option value="${nome}">${nome}</option>`;
                })
                .join("")}
        `;

        if (item.profissional_preferido) {
            selectProfissional.value = item.profissional_preferido;
        }

        document
            .getElementById("fila-conversao-data")
            ?.addEventListener(
                "change",
                carregarHorariosConversaoFilaAdmin
            );

        selectProfissional.addEventListener(
            "change",
            carregarHorariosConversaoFilaAdmin
        );

        await carregarHorariosConversaoFilaAdmin();
    } catch (erro) {
        tratarErro(erro);
    }
}


async function confirmarConversaoFilaEsperaAdmin(event) {
    event.preventDefault();

    if (!itemFilaConversaoAdmin) {
        exibirMensagemAdmin("Item da fila nao selecionado.");
        return;
    }

    const data =
        document.getElementById("fila-conversao-data")?.value || "";

    const profissional =
        document.getElementById("fila-conversao-profissional")?.value || "";

    const horario =
        document.getElementById("fila-conversao-horario")?.value || "";

    if (!data || !profissional || !horario) {
        exibirMensagemAdmin(
            "Selecione data, profissional e horario."
        );
        return;
    }

    try {
        const resposta = await apiRequest(
            `/api/${tenantSlugLogado}/admin/fila-espera/${itemFilaConversaoAdmin.id}/agendar`,
            {
                method: "POST",
                auth: true,
                body: {
                    data,
                    profissional,
                    horario,
                },
            }
        );

        fecharConversaoFilaEsperaAdmin();

        exibirMensagemAdmin(
            resposta?.mensagem
            || "Agendamento criado com sucesso."
        );

        await carregarFilaEsperaAdmin();

        if (typeof carregarAgendamentos === "function") {
            await carregarAgendamentos();
        }

        if (typeof carregarAgendaVisualDia === "function") {
            await carregarAgendaVisualDia({
                forcar: true,
            });
        }
    } catch (erro) {
        tratarErro(erro);
    }
}


window.abrirConversaoFilaEsperaAdmin =
    abrirConversaoFilaEsperaAdmin;

window.fecharConversaoFilaEsperaAdmin =
    fecharConversaoFilaEsperaAdmin;

window.confirmarConversaoFilaEsperaAdmin =
    confirmarConversaoFilaEsperaAdmin;

window.carregarHorariosConversaoFilaAdmin =
    carregarHorariosConversaoFilaAdmin;


window.carregarFilaEsperaAdmin = carregarFilaEsperaAdmin;
window.atualizarStatusFilaEsperaAdmin = atualizarStatusFilaEsperaAdmin;
window.criarEstruturaFilaEsperaAdmin = criarEstruturaFilaEsperaAdmin;

iniciarFilaEsperaAdminQuandoDisponivel();


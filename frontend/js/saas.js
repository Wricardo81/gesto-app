const SAAS_TOKEN_STORAGE_KEY =
    "gesto_saas_token";

const BANNER_COMERCIAL_SAAS_KEY =
    "gesto_banner_comercial_saas_dispensado";

let clientesSaasCache = [];
let empresaConfiguracaoAtual = null;
let avisosSaasCache = [];
let chamadosSaasCache = [];
const secoesSaasCarregadas = new Set();
const secoesSaasCarregando = new Set();
let planosAssinaturaSaasCache = [];
let empresasAssinaturasSaasCache = [];

let listenersNavegacaoSaasRegistrados = false;


function obterTokenSaas() {
    return localStorage.getItem(
        SAAS_TOKEN_STORAGE_KEY
    );
}


function salvarTokenSaas(token) {
    localStorage.setItem(
        SAAS_TOKEN_STORAGE_KEY,
        token
    );
}


function limparTokenSaas() {
    localStorage.removeItem(
        SAAS_TOKEN_STORAGE_KEY
    );
}

function exibirMensagemSaas(mensagem, tipo = "sucesso") {
    let area = document.getElementById("mensagem-saas");

    if (!area) {
        area = document.createElement("div");
        area.id = "mensagem-saas";
        area.className = "mensagem-saas";

        const painel = document.getElementById("painel-saas");

        if (painel) {
            painel.prepend(area);
        }
    }

    area.textContent = mensagem;
    area.className = `mensagem-saas ${tipo}`;
    area.style.display = "block";

    setTimeout(() => {
        area.style.display = "none";
    }, 3500);
}


async function saasRequest(
    endpoint,
    options = {}
) {
    return apiRequest(
        endpoint,
        {
            ...options,
            auth: true,
            tokenStorageKey:
                SAAS_TOKEN_STORAGE_KEY
        }
    );
}


function exibirLoginSaas() {
    document
        .getElementById("tela-login-saas")
        .style
        .display = "flex";

    document
        .getElementById("painel-saas")
        .style
        .display = "none";
}


function exibirPainelSaas() {
    document
        .getElementById("tela-login-saas")
        .style
        .display = "none";

    document
        .getElementById("painel-saas")
        .style
        .display = "block";
}


function tratarErroSaas(erro) {
    console.error(erro);

    if (
        erro.status === 401
        || erro.status === 403
    ) {
        limparTokenSaas();
        exibirLoginSaas();

        alert(
            "Sua sessão administrativa expirou. Faça login novamente."
        );

        return;
    }

    alert(
        erro.message
        || "Não foi possível concluir a operação."
    );
}


async function realizarLoginSaas(event) {
    event.preventDefault();

    const email = document
        .getElementById("login-saas-email")
        .value
        .trim();

    const senha = document
        .getElementById("login-saas-senha")
        .value;

    const mensagem = document
        .getElementById("msg-erro-login-saas");

    const botao = document
        .getElementById("btn-login-saas");

    mensagem.style.display = "none";
    botao.disabled = true;
    botao.innerText = "Entrando...";

    try {
        const dados = await apiRequest(
            "/api/saas/login",
            {
                method: "POST",
                body: {
                    email,
                    senha
                }
            }
        );

        salvarTokenSaas(
            dados.access_token
        );
        
        exibirPainelSaas();
        
        secoesSaasCarregadas.clear();
        secoesSaasCarregando.clear();
        
        inicializarNavegacaoSaas();

    } catch (erro) {
        console.error(erro);

        mensagem.innerText =
            erro.message;

        mensagem.style.display =
            "block";

    } finally {
        botao.disabled = false;
        botao.innerText =
            "Entrar no Painel Mestre";
    }
}


function fazerLogoutSaas() {
    limparTokenSaas();
    window.location.reload();
}


function normalizarSlug(texto) {
    return texto
        .normalize("NFD")
        .replace(
            /[\u0300-\u036f]/g,
            ""
        )
        .toLowerCase()
        .trim()
        .replace(
            /[^a-z0-9]+/g,
            "-"
        )
        .replace(
            /^-+|-+$/g,
            ""
        );
}


function criarCelula(texto) {
    const td = document.createElement("td");

    td.textContent = texto;

    return td;
}

function formatarDataSaas(dataISO) {
    if (!dataISO) {
        return "-";
    }

    const partes = String(dataISO).split("-");

    if (partes.length !== 3) {
        return dataISO;
    }

    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}


function traduzirStatusPagamento(status) {
    const mapa = {
        em_dia: "Em dia",
        pendente: "Pendente",
        vencido: "Vencido",
        cancelado: "Cancelado",
        teste: "Teste",
    };

    return mapa[status] || "Em dia";
}


function classeStatusPagamento(status) {
    const mapa = {
        em_dia: "status-em-dia",
        pendente: "status-pendente",
        vencido: "status-vencido",
        cancelado: "status-vencido",
        teste: "status-teste",
    };

    return mapa[status] || "status-em-dia";
}


function calcularResumoFinanceiroSaas(clientes) {
    const total = clientes.length;

    const ativos = clientes.filter(
        cliente => Boolean(cliente.acesso_ativo)
    ).length;

    const bloqueados = total - ativos;

    const emTeste = clientes.filter(
        cliente => cliente.status_pagamento === "teste"
    ).length;

    const vencidos = clientes.filter(
        cliente => Boolean(cliente.pagamento_vencido)
            || cliente.status_pagamento === "vencido"
    ).length;

    const mrrReal = clientes
        .filter(cliente => Boolean(cliente.acesso_ativo))
        .reduce((totalAtual, cliente) => {
            return totalAtual + Number(cliente.valor_mensal || 0);
        }, 0);

    return {
        total,
        ativos,
        bloqueados,
        emTeste,
        vencidos,
        mrrReal,
    };
}

function formatarMoedaSaas(valor) {
    return Number(valor || 0).toLocaleString(
        "pt-BR",
        {
            style: "currency",
            currency: "BRL",
        }
    );
}


function atualizarResumoSaas(clientes) {
    const resumo = calcularResumoFinanceiroSaas(clientes);

    document.getElementById("visor-saas-total").textContent =
        resumo.total;

    document.getElementById("visor-saas-ativas").textContent =
        resumo.ativos;

    document.getElementById("visor-saas-bloqueadas").textContent =
        resumo.bloqueados;

    document.getElementById("visor-saas-mrr").textContent =
        formatarMoedaSaas(resumo.mrrReal);
}


async function carregarClientes() {
    const tbody = document
        .getElementById("lista-clientes");

    tbody.innerHTML = "";

    try {
        const clientes = await saasRequest(
            "/api/saas/barbearias"
        );

        clientesSaasCache = clientes;
        
        atualizarResumoSaas(clientes);

        if (!clientes.length) {
            const tr =
                document.createElement("tr");

            const td =
                document.createElement("td");

            td.colSpan = 5;
            td.className = "mensagem-tabela";
            td.textContent =
                "Nenhuma empresa cadastrada.";

            tr.appendChild(td);
            tbody.appendChild(tr);

            return;
        }

        for (const cliente of clientes) {
            const tr = document.createElement("tr");
        
            tr.appendChild(
                criarCelula(`#${cliente.id}`)
            );
        
            const tdEmpresa = document.createElement("td");
        
            const nome = document.createElement("strong");
            nome.textContent = cliente.nome;
        
            const email = document.createElement("small");
            email.textContent = cliente.email || "";
        
            const link = document.createElement("small");
            link.textContent =
                `agendamento.html?tenant=${cliente.slug}`;
        
            tdEmpresa.append(
                nome,
                document.createElement("br"),
                email,
                document.createElement("br"),
                link
            );
        
            tr.appendChild(tdEmpresa);
        
            const tdPlano = document.createElement("td");
            tdPlano.innerHTML = `
                <div class="financeiro-info">
                    <strong>${cliente.plano_nome || "Profissional"}</strong>
                    <small>Slug: ${cliente.slug}</small>
                </div>
            `;
            tr.appendChild(tdPlano);
        
            tr.appendChild(
                criarCelula(
                    formatarMoedaSaas(cliente.valor_mensal || 0)
                )
            );
        
            const tdVencimento = document.createElement("td");
            tdVencimento.innerHTML = `
                <div class="financeiro-info">
                    <strong>${formatarDataSaas(cliente.vencimento_plano)}</strong>
                    <small>
                        ${
                            cliente.dias_em_atraso > 0
                                ? `${cliente.dias_em_atraso} dia(s) em atraso`
                                : `Tolerância: ${cliente.dias_tolerancia || 0} dia(s)`
                        }
                    </small>
                </div>
            `;
            tr.appendChild(tdVencimento);
        
            const tdStatusFinanceiro = document.createElement("td");
        
            const badgeFinanceiro = document.createElement("span");
        
            badgeFinanceiro.className =
                `status-badge ${classeStatusPagamento(cliente.status_pagamento)}`;
        
            badgeFinanceiro.textContent =
                traduzirStatusPagamento(cliente.status_pagamento);
        
            tdStatusFinanceiro.appendChild(badgeFinanceiro);
            tr.appendChild(tdStatusFinanceiro);
        
            const tdAcesso = document.createElement("td");
        
            const badgeAcesso = document.createElement("span");
        
            badgeAcesso.className =
                `status-badge ${
                    cliente.acesso_ativo
                        ? "status-ativo"
                        : "status-bloqueado"
                }`;
        
            badgeAcesso.textContent =
                cliente.acesso_ativo
                    ? "Liberado"
                    : "Bloqueado";
        
            tdAcesso.appendChild(badgeAcesso);
            tr.appendChild(tdAcesso);
        
            const tdAcao = document.createElement("td");
        
            tdAcao.innerHTML = `
                <div class="acoes-financeiras">
                    <button
                        type="button"
                        class="btn-pagamento"
                        onclick="marcarEmpresaComoPaga(${cliente.id})"
                    >
                        Marcar pago
                    </button>

                    <button
                        type="button"
                        class="btn-financeiro"
                        onclick="abrirModalFinanceiroSaas(${cliente.id})"
                    >
                        Financeiro
                    </button>

                    <button
                        type="button"
                        class="btn-configurar"
                        onclick="abrirModalConfiguracaoEmpresa(${cliente.id})"
                    >
                        Configurar
                    </button>

                    <button
                        type="button"
                        onclick="alterarStatus(${cliente.id})"
                    >
                        ${
                            cliente.plano_ativo
                                ? "Bloquear manual"
                                : "Desbloquear"
                        }
                    </button>
                </div>
            `;
        
            tr.appendChild(tdAcao);
        
            tbody.appendChild(tr);
        }

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


async function criarNovoCliente(event) {
    event.preventDefault();

    const nome = document
        .getElementById("novo-nome")
        .value
        .trim();

    const slug = normalizarSlug(
        document
            .getElementById("novo-slug")
            .value
    );

    const email = document
        .getElementById("novo-email")
        .value
        .trim();

    const senha = document
        .getElementById("nova-senha")
        .value;

    if (
        !nome
        || !slug
        || !email
        || senha.length < 8
    ) {
        alert(
            "Preencha nome, slug, e-mail e uma senha com pelo menos 8 caracteres."
        );

        return;
    }

    try {
        await saasRequest(
            "/api/saas/barbearias",
            {
                method: "POST",
                body: {
                    nome,
                    slug,
                    email,
                    senha
                }
            }
        );

        invalidarSecoesSaas([
            "secao-saas-dashboard",
            "secao-saas-empresas",
        ]);

        await carregarDadosDaSecaoSaas(
            "secao-saas-empresas",
            {
                forcar: true,
            }
        );

        document
            .getElementById(
                "form-nova-barbearia"
            )
            .reset();

            exibirMensagemSaas("Empresa criada com sucesso.");

        exibirMensagemSaas("Pagamento registrado com sucesso.");

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


async function alterarStatus(id) {
    try {
        await saasRequest(
            `/api/saas/barbearias/${id}/status`,
            {
                method: "PUT"
            }
        );

        invalidarSecoesSaas([
            "secao-saas-dashboard",
            "secao-saas-empresas",
        ]);

        await carregarDadosDaSecaoSaas(
            "secao-saas-empresas",
            {
                forcar: true,
            }
        );

        
        exibirMensagemSaas("Status manual atualizado com sucesso.");

    } catch (erro) {
        tratarErroSaas(erro);
    }
}

function alternarMenuSaas() {
    const menu = document.getElementById("saas-tabs");

    if (!menu) {
        return;
    }

    menu.classList.toggle("aberto");
}


function mostrarSecaoSaas(secaoId) {
    const secoes = document.querySelectorAll(".secao-saas");
    const botoes = document.querySelectorAll(".saas-tab");

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
        "gesto_saas_secao_ativa",
        secaoId
    );

    const menu = document.getElementById("saas-tabs");

    if (menu) {
        menu.classList.remove("aberto");
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });

    carregarDadosDaSecaoSaas(secaoId);
}


function inicializarNavegacaoSaas() {
    const botoes = document.querySelectorAll(".saas-tab");

    if (!listenersNavegacaoSaasRegistrados) {
        botoes.forEach((botao) => {
            botao.addEventListener("click", () => {
                mostrarSecaoSaas(botao.dataset.secao);
            });
        });

        listenersNavegacaoSaasRegistrados = true;
    }

    const secaoSalva = localStorage.getItem(
        "gesto_saas_secao_ativa"
    );

    mostrarSecaoSaas(
        secaoSalva || "secao-saas-dashboard"
    );
}


window.alternarMenuSaas = alternarMenuSaas;


async function marcarEmpresaComoPaga(id) {
    const confirmar = window.confirm(
        "Deseja marcar esta empresa como paga e avançar o vencimento em 30 dias?"
    );

    if (!confirmar) {
        return;
    }

    try {
        await saasRequest(
            `/api/saas/barbearias/${id}/financeiro`,
            {
                method: "PUT",
                body: {
                    marcar_como_pago: true,
                },
            }
        );
        invalidarSecoesSaas([
            "secao-saas-dashboard",
            "secao-saas-empresas",
        ]);

        await carregarDadosDaSecaoSaas(
            "secao-saas-empresas",
            {
                forcar: true,
            }
        );


        exibirMensagemSaas("Pagamento registrado com sucesso.");

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


function obterEmpresaSaasPorId(id) {
    return clientesSaasCache.find((cliente) => {
        return Number(cliente.id) === Number(id);
    });
}


function abrirModalFinanceiroSaas(id) {
    const cliente = obterEmpresaSaasPorId(id);

    if (!cliente) {
        alert("Empresa não encontrada na lista atual.");
        return;
    }

    document.getElementById("financeiro-empresa-id").value =
        cliente.id;

    document.getElementById("financeiro-plano-nome").value =
        cliente.plano_nome || "Profissional";

    document.getElementById("financeiro-valor-mensal").value =
        Number(cliente.valor_mensal || 0).toFixed(2);

    document.getElementById("financeiro-vencimento").value =
        cliente.vencimento_plano || "";

    document.getElementById("financeiro-status").value =
        cliente.status_pagamento || "em_dia";

    document.getElementById("financeiro-dias-tolerancia").value =
        cliente.dias_tolerancia ?? 3;

    document.getElementById("modal-financeiro-empresa").textContent =
        `${cliente.nome} • ${cliente.email || "sem e-mail"}`;

    document.getElementById("modal-financeiro-saas").style.display =
        "flex";
}


function fecharModalFinanceiroSaas() {
    const modal = document.getElementById("modal-financeiro-saas");

    if (modal) {
        modal.style.display = "none";
    }
}


async function salvarFinanceiroEmpresa(event) {
    event.preventDefault();

    const id = document.getElementById("financeiro-empresa-id").value;

    const planoNome = document
        .getElementById("financeiro-plano-nome")
        .value
        .trim();

    const valorMensal = Number(
        document.getElementById("financeiro-valor-mensal").value
    );

    const vencimentoPlano = document
        .getElementById("financeiro-vencimento")
        .value;

    const statusPagamento = document
        .getElementById("financeiro-status")
        .value;

    const diasTolerancia = Number(
        document.getElementById("financeiro-dias-tolerancia").value
    );

    if (
        !id
        || !planoNome
        || Number.isNaN(valorMensal)
        || valorMensal < 0
        || Number.isNaN(diasTolerancia)
        || diasTolerancia < 0
    ) {
        alert("Preencha os dados financeiros corretamente.");
        return;
    }

    const botao = document.getElementById("btn-salvar-financeiro-saas");

    botao.disabled = true;
    botao.textContent = "Salvando...";

    try {
        await saasRequest(
            `/api/saas/barbearias/${id}/financeiro`,
            {
                method: "PUT",
                body: {
                    plano_nome: planoNome,
                    valor_mensal: valorMensal,
                    vencimento_plano: vencimentoPlano || null,
                    status_pagamento: statusPagamento,
                    dias_tolerancia: diasTolerancia,
                    marcar_como_pago: false,
                },
            }
        );

        fecharModalFinanceiroSaas();

            invalidarSecoesSaas([
                "secao-saas-dashboard",
                "secao-saas-empresas",
            ]);

            await carregarDadosDaSecaoSaas(
                "secao-saas-empresas",
                {
                    forcar: true,
                }
            );

            exibirMensagemSaas(
                "Dados financeiros atualizados com sucesso."
            );

    } catch (erro) {
        tratarErroSaas(erro);

    } finally {
        botao.disabled = false;
        botao.textContent = "Salvar financeiro";
    }
}

window.abrirModalFinanceiroSaas = abrirModalFinanceiroSaas;
window.fecharModalFinanceiroSaas = fecharModalFinanceiroSaas;


function obterClienteSaasPorId(id) {
    return clientesSaasCache.find((cliente) => {
        return Number(cliente.id) === Number(id);
    });
}


function abrirModalConfiguracaoEmpresa(id) {
    const cliente = obterClienteSaasPorId(id);

    if (!cliente) {
        exibirMensagemSaas(
            "Empresa não encontrada na lista atual.",
            "erro"
        );

        return;
    }

    empresaConfiguracaoAtual = cliente;

    document.getElementById("config-empresa-id").value =
        cliente.id;

    document.getElementById("config-empresa-nome").value =
        cliente.nome || "";

    document.getElementById("config-empresa-email").value =
        cliente.email || "";

    document.getElementById("config-empresa-slug").value =
        cliente.slug || "";

    document.getElementById("config-empresa-plano-ativo").value =
        String(Boolean(cliente.plano_ativo));

    document.getElementById("config-empresa-nova-senha").value =
        "";

    document.getElementById("modal-configuracao-empresa-subtitulo").textContent =
        `${cliente.nome} • ${cliente.email || "sem e-mail"}`;

    const diagnostico = document.getElementById("diagnostico-empresa");

    if (diagnostico) {
        diagnostico.style.display = "none";
        diagnostico.innerHTML = "";
    }

    document.getElementById("modal-configuracao-empresa").style.display =
        "flex";
}


function fecharModalConfiguracaoEmpresa() {
    const modal = document.getElementById("modal-configuracao-empresa");

    if (modal) {
        modal.style.display = "none";
    }
}


async function copiarTextoSaas(texto, mensagemSucesso) {
    try {
        await navigator.clipboard.writeText(texto);

        exibirMensagemSaas(mensagemSucesso);

    } catch (erro) {
        console.error(erro);

        window.prompt(
            "Copie o texto abaixo:",
            texto
        );
    }
}


function montarLinkPublicoEmpresa(cliente) {
    const origem = window.location.origin;
    const caminho = window.location.pathname.replace(
        "saas.html",
        "agendamento.html"
    );

    return `${origem}${caminho}?tenant=${cliente.slug}`;
}


function montarLinkAdminEmpresa(cliente) {
    const origem = window.location.origin;
    const caminho = window.location.pathname.replace(
        "saas.html",
        "admin.html"
    );

    return `${origem}${caminho}?tenant=${cliente.slug}`;
}


function copiarLinkPublicoEmpresa() {
    if (!empresaConfiguracaoAtual) {
        return;
    }

    copiarTextoSaas(
        montarLinkPublicoEmpresa(empresaConfiguracaoAtual),
        "Link público copiado."
    );
}


function copiarLinkAdminEmpresa() {
    if (!empresaConfiguracaoAtual) {
        return;
    }

    copiarTextoSaas(
        montarLinkAdminEmpresa(empresaConfiguracaoAtual),
        "Link admin copiado."
    );
}


async function salvarConfiguracaoEmpresa(event) {
    if (event) {
        event.preventDefault();
    }

    const id = document.getElementById("config-empresa-id").value;

    const nome = document
        .getElementById("config-empresa-nome")
        .value
        .trim();

    const email = document
        .getElementById("config-empresa-email")
        .value
        .trim()
        .toLowerCase();

    const slug = document
        .getElementById("config-empresa-slug")
        .value
        .trim()
        .toLowerCase();

    const planoAtivo =
        document.getElementById("config-empresa-plano-ativo").value === "true";

    if (
        !id
        || nome.length < 2
        || !email
        || !slug
    ) {
        exibirMensagemSaas(
            "Preencha nome, e-mail e slug corretamente.",
            "erro"
        );

        return;
    }

    const clienteAtual = empresaConfiguracaoAtual;

    if (
        clienteAtual
        && clienteAtual.slug
        && clienteAtual.slug !== slug
    ) {
        const confirmou = window.confirm(
            "Você está alterando o slug/tenant da empresa. Links antigos podem parar de funcionar. Deseja continuar?"
        );

        if (!confirmou) {
            return;
        }
    }

    const botao = document.getElementById("btn-salvar-config-empresa");

    botao.disabled = true;
    botao.textContent = "Salvando...";

    try {
        const resposta = await saasRequest(
            `/api/saas/barbearias/${id}/dados`,
            {
                method: "PUT",
                body: {
                    nome,
                    email,
                    slug,
                    plano_ativo: planoAtivo,
                },
            }
        );

        empresaConfiguracaoAtual = resposta.barbearia;

            invalidarSecoesSaas([
                "secao-saas-dashboard",
                "secao-saas-empresas",
            ]);

            await carregarDadosDaSecaoSaas(
                "secao-saas-empresas",
                {
                    forcar: true,
                }
            );

            fecharModalConfiguracaoEmpresa();

        exibirMensagemSaas(
            resposta.mensagem || "Dados da empresa atualizados com sucesso."
        );

    } catch (erro) {
        tratarErroSaas(erro);

    } finally {
        botao.disabled = false;
        botao.textContent = "Salvar dados";
    }
}


async function redefinirSenhaEmpresa() {
    const id = document.getElementById("config-empresa-id").value;

    const novaSenha = document
        .getElementById("config-empresa-nova-senha")
        .value;

    if (
        !id
        || !novaSenha
        || novaSenha.length < 8
    ) {
        exibirMensagemSaas(
            "Informe uma nova senha com pelo menos 8 caracteres.",
            "erro"
        );

        return;
    }

    const confirmou = window.confirm(
        "Deseja realmente redefinir a senha desta empresa?"
    );

    if (!confirmou) {
        return;
    }

    try {
        await saasRequest(
            `/api/saas/barbearias/${id}/senha`,
            {
                method: "PUT",
                body: {
                    nova_senha: novaSenha,
                },
            }
        );

        document.getElementById("config-empresa-nova-senha").value =
            "";

        exibirMensagemSaas(
            "Senha redefinida com sucesso."
        );

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


function renderizarDiagnosticoEmpresa(dados) {
    const container = document.getElementById("diagnostico-empresa");

    if (!container) {
        return;
    }

    const diagnostico = dados.diagnostico;

    container.style.display = "block";

    const problemasHtml = diagnostico.problemas.length
        ? `
            <ul class="lista-problemas-diagnostico">
                ${
                    diagnostico.problemas
                        .map((problema) => `<li>${problema}</li>`)
                        .join("")
                }
            </ul>
        `
        : `<p class="diagnostico-ok">Nenhum problema básico encontrado.</p>`;

    container.innerHTML = `
        <h3>Diagnóstico operacional</h3>

        <div class="diagnostico-grid">
            <div class="diagnostico-item">
                <span>Configuração</span>
                <strong>${diagnostico.configuracao_existe ? "OK" : "Ausente"}</strong>
            </div>

            <div class="diagnostico-item">
                <span>Serviços</span>
                <strong>${diagnostico.total_servicos}</strong>
            </div>

            <div class="diagnostico-item">
                <span>Profissionais</span>
                <strong>${diagnostico.total_profissionais}</strong>
            </div>

            <div class="diagnostico-item">
                <span>Agendamentos</span>
                <strong>${diagnostico.total_agendamentos}</strong>
            </div>
        </div>

        ${problemasHtml}
    `;
}


async function carregarDiagnosticoEmpresa() {
    const id = document.getElementById("config-empresa-id").value;

    if (!id) {
        return;
    }

    const container = document.getElementById("diagnostico-empresa");

    if (container) {
        container.style.display = "block";
        container.innerHTML = "Carregando diagnóstico...";
    }

    try {
        const dados = await saasRequest(
            `/api/saas/barbearias/${id}/diagnostico`
        );

        renderizarDiagnosticoEmpresa(dados);

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


function traduzirTipoAvisoSaas(tipo) {
    const mapa = {
        info: "Info",
        atualizacao: "Atualização",
        promocao: "Promoção",
        manutencao: "Manutenção",
        instabilidade: "Instabilidade",
        financeiro: "Financeiro",
        urgente: "Urgente",
    };

    return mapa[tipo] || "Info";
}


function formatarPeriodoAvisoSaas(aviso) {
    const inicio = formatarDataSaas(aviso.data_inicio);
    const fim = formatarDataSaas(aviso.data_fim);

    if (aviso.data_inicio && aviso.data_fim) {
        return `${inicio} até ${fim}`;
    }

    if (aviso.data_inicio) {
        return `A partir de ${inicio}`;
    }

    if (aviso.data_fim) {
        return `Até ${fim}`;
    }

    return "Sem período definido";
}


function renderizarAvisosSaas(avisos) {
    const container = document.getElementById("lista-avisos-saas");

    if (!container) {
        return;
    }

    if (!avisos.length) {
        container.innerHTML = `
            <p class="texto-vazio-saas">
                Nenhum aviso cadastrado ainda.
            </p>
        `;

        return;
    }

    container.innerHTML = avisos
        .map((aviso) => {
            return `
                <article class="aviso-saas-card ${aviso.ativo ? "" : "inativo"}">
                    <div class="aviso-saas-card-topo">
                        <div>
                            <h4>${aviso.titulo}</h4>
                            <span class="badge-aviso tipo-${aviso.tipo}">
                                ${traduzirTipoAvisoSaas(aviso.tipo)}
                            </span>
                        </div>

                        <span class="badge-aviso">
                            ${aviso.ativo ? "Ativo" : "Inativo"}
                        </span>
                    </div>

                    <p>${aviso.mensagem}</p>

                    <div class="aviso-saas-meta">
                        <span>
                            ${aviso.global_para_todos ? "Global" : `Tenant: ${aviso.tenant_slug}`}
                        </span>

                        <span>
                            ${aviso.fixado ? "Fixado" : "Comum"}
                        </span>

                        <span>
                            ${aviso.dispensavel ? "Dispensável" : "Obrigatório"}
                        </span>

                        <span>
                            ${formatarPeriodoAvisoSaas(aviso)}
                        </span>
                    </div>

                    <div class="aviso-saas-acoes">
                        <button
                            type="button"
                            onclick="alternarStatusAvisoSaas(${aviso.id}, ${!aviso.ativo})"
                        >
                            ${aviso.ativo ? "Desativar" : "Ativar"}
                        </button>
                    </div>
                </article>
            `;
        })
        .join("");
}


async function carregarAvisosSaas() {
    const container = document.getElementById("lista-avisos-saas");

    if (container) {
        container.innerHTML = "Carregando avisos...";
    }

    try {
        const avisos = await saasRequest(
            "/api/saas/avisos"
        );

        avisosSaasCache = avisos;

        renderizarAvisosSaas(avisos);

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


async function criarAvisoSaas(event) {
    event.preventDefault();

    const titulo = document
        .getElementById("aviso-titulo")
        .value
        .trim();

    const mensagem = document
        .getElementById("aviso-mensagem")
        .value
        .trim();

    const tipo = document.getElementById("aviso-tipo").value;

    const escopo = document.getElementById("aviso-escopo").value;

    const tenantSlug = document
        .getElementById("aviso-tenant-slug")
        .value
        .trim()
        .toLowerCase();

    const fixado =
        document.getElementById("aviso-fixado").value === "true";

    const dataInicio = document.getElementById("aviso-data-inicio").value;
    const dataFim = document.getElementById("aviso-data-fim").value;

    const dispensavel = document.getElementById("aviso-dispensavel").checked;

    const globalParaTodos = escopo === "global";

    if (
        !titulo
        || !mensagem
    ) {
        exibirMensagemSaas(
            "Informe título e mensagem do aviso.",
            "erro"
        );

        return;
    }

    if (
        !globalParaTodos
        && !tenantSlug
    ) {
        exibirMensagemSaas(
            "Informe o tenant para aviso específico.",
            "erro"
        );

        return;
    }

    const botao = document.getElementById("btn-criar-aviso-saas");

    botao.disabled = true;
    botao.textContent = "Criando...";

    try {
        await saasRequest(
            "/api/saas/avisos",
            {
                method: "POST",
                body: {
                    titulo,
                    mensagem,
                    tipo,
                    tenant_slug: globalParaTodos ? null : tenantSlug,
                    global_para_todos: globalParaTodos,
                    fixado,
                    dispensavel,
                    ativo: true,
                    data_inicio: dataInicio || null,
                    data_fim: dataFim || null,
                },
            }
        );

        document.getElementById("form-aviso-saas").reset();

        invalidarSecaoSaas("secao-saas-avisos");

        await carregarDadosDaSecaoSaas(
            "secao-saas-avisos",
            {
                forcar: true,
            }
        );

        exibirMensagemSaas(
            "Aviso criado com sucesso."
        );

    } catch (erro) {
        tratarErroSaas(erro);

    } finally {
        botao.disabled = false;
        botao.textContent = "Criar aviso";
    }
}


async function alternarStatusAvisoSaas(id, ativo) {
    try {
        await saasRequest(
            `/api/saas/avisos/${id}/status`,
            {
                method: "PUT",
                body: {
                    ativo,
                },
            }
        );

        invalidarSecaoSaas("secao-saas-avisos");

        await carregarDadosDaSecaoSaas(
            "secao-saas-avisos",
            {
                forcar: true,
            }
        );
        
        exibirMensagemSaas(
                ativo
                    ? "Aviso ativado com sucesso."
                    : "Aviso desativado com sucesso."
            );

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


function traduzirTipoChamadoSaas(tipo) {
    const mapa = {
        erro: "Erro",
        bug: "Bug",
        sugestao: "Sugestão",
        elogio: "Elogio",
        outro: "Outro",
    };

    return mapa[tipo] || "Erro";
}


function traduzirStatusChamadoSaas(status) {
    const mapa = {
        aberto: "Aberto",
        em_analise: "Em análise",
        resolvido: "Resolvido",
        fechado: "Fechado",
    };

    return mapa[status] || "Aberto";
}


function renderizarChamadosSaas(chamados) {
    const container = document.getElementById("lista-chamados-saas");

    if (!container) {
        return;
    }

    if (!chamados.length) {
        container.innerHTML = `
            <p class="texto-vazio-saas">
                Nenhum chamado recebido ainda.
            </p>
        `;

        return;
    }

    container.innerHTML = chamados
        .map((chamado) => {
            const resposta = chamado.resposta_suporte
                ? `
                    <div class="resposta-suporte-saas">
                        <strong>Resposta enviada:</strong><br>
                        ${chamado.resposta_suporte}
                    </div>
                `
                : "";

            return `
                <article class="chamado-saas-card">
                    <div class="chamado-saas-topo">
                        <div>
                            <h3>#${chamado.id} — ${chamado.titulo}</h3>

                            <span class="badge-chamado-saas status-${chamado.status}">
                                ${traduzirStatusChamadoSaas(chamado.status)}
                            </span>

                            <span class="badge-chamado-saas">
                                ${traduzirTipoChamadoSaas(chamado.tipo)}
                            </span>
                        </div>

                        <span class="badge-chamado-saas">
                            Tenant: ${chamado.tenant_slug}
                        </span>
                    </div>

                    <p>${chamado.descricao}</p>

                    ${resposta}

                    <div class="chamado-saas-meta">
                        <span>Origem: ${chamado.pagina_origem || "-"}</span>
                        <span>Contato: ${chamado.contato_nome || "-"}</span>
                        <span>E-mail: ${chamado.contato_email || "-"}</span>
                        <span>Criado em: ${formatarDataSaas(chamado.criado_em?.slice(0, 10))}</span>
                    </div>

                    <div class="chamado-saas-acoes">
                        <button type="button" onclick="atualizarStatusChamadoSaas(${chamado.id}, 'em_analise')">
                            Em análise
                        </button>

                        <button type="button" onclick="atualizarStatusChamadoSaas(${chamado.id}, 'resolvido')">
                            Resolver
                        </button>

                        <button type="button" onclick="atualizarStatusChamadoSaas(${chamado.id}, 'fechado')">
                            Fechar
                        </button>

                        <button type="button" onclick="atualizarStatusChamadoSaas(${chamado.id}, 'aberto')">
                            Reabrir
                        </button>
                    </div>
                </article>
            `;
        })
        .join("");
}


async function carregarChamadosSaas() {
    const container = document.getElementById("lista-chamados-saas");

    if (container) {
        container.innerHTML = "Carregando chamados...";
    }

    try {
        const chamados = await saasRequest(
            "/api/saas/suporte/chamados"
        );

        chamadosSaasCache = chamados;

        renderizarChamadosSaas(chamados);

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


async function atualizarStatusChamadoSaas(id, status) {
    const resposta = prompt(
        "Resposta do suporte para este chamado:",
        ""
    );

    if (resposta === null) {
        return;
    }

    try {
        await saasRequest(
            `/api/saas/suporte/chamados/${id}/status`,
            {
                method: "PUT",
                body: {
                    status,
                    resposta_suporte: resposta.trim() || null,
                },
            }
        );

        invalidarSecaoSaas("secao-saas-suporte");

        await carregarDadosDaSecaoSaas(
            "secao-saas-suporte",
            {
                forcar: true,
            }
        );

exibirMensagemSaas(
    "Chamado atualizado com sucesso."
);

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


window.carregarChamadosSaas = carregarChamadosSaas;
window.atualizarStatusChamadoSaas = atualizarStatusChamadoSaas;


async function carregarEmpresasSaasCompat() {
    if (typeof carregarClientesSaas === "function") {
        return carregarClientesSaas();
    }

    if (typeof carregarBarbeariasSaas === "function") {
        return carregarBarbeariasSaas();
    }

    if (typeof carregarClientes === "function") {
        return carregarClientes();
    }

    if (typeof carregarBarbearias === "function") {
        return carregarBarbearias();
    }

    throw new Error(
        "Função de carregamento de empresas não encontrada no saas.js."
    );
}


async function carregarDadosDaSecaoSaas(secaoId, opcoes = {}) {
    const forcar = Boolean(opcoes.forcar);

    if (!secaoId) {
        return;
    }

    if (secoesSaasCarregando.has(secaoId)) {
        return;
    }

    if (
        secoesSaasCarregadas.has(secaoId)
        && !forcar
    ) {
        return;
    }

    secoesSaasCarregando.add(secaoId);

    try {
        if (secaoId === "secao-saas-dashboard") {
            await carregarEmpresasSaasCompat();
            await carregarMetricasDashboardSaas();
        }

        if (secaoId === "secao-saas-empresas") {
            await carregarEmpresasSaasCompat();
        }

        if (secaoId === "secao-saas-criar") {
            // Não precisa carregar dados externos.
        }

        if (secaoId === "secao-saas-avisos") {
            await carregarAvisosSaas();
        }

        if (secaoId === "secao-saas-suporte") {
            await carregarChamadosSaas();
        }

        if (secaoId === "secao-saas-assinaturas") {
            await carregarAssinaturasSaas();
        }

        secoesSaasCarregadas.add(secaoId);

    } catch (erro) {
        console.error(
            "Erro ao carregar seção SaaS:",
            secaoId,
            erro
        );

        tratarErroSaas(erro);

    } finally {
        secoesSaasCarregando.delete(secaoId);
    }
}


function invalidarSecaoSaas(secaoId) {
    secoesSaasCarregadas.delete(secaoId);
}


function invalidarSecoesSaas(secaoIds = []) {
    secaoIds.forEach((secaoId) => {
        invalidarSecaoSaas(secaoId);
    });
}


async function atualizarPainelSaas() {
    const secaoAtual =
        document.querySelector(".secao-saas.ativa")?.id
        || localStorage.getItem("gesto_saas_secao_ativa")
        || "secao-saas-dashboard";

    await carregarDadosDaSecaoSaas(
        secaoAtual,
        {
            forcar: true,
        }
    );

    exibirMensagemSaas(
        "Painel SaaS atualizado com sucesso."
    );
}

window.atualizarPainelSaas = atualizarPainelSaas;


function traduzirStatusAssinaturaSaas(status) {
    const mapa = {
        trial: "Teste",
        checkout_criado: "Checkout criado",
        checkout_concluido: "Checkout concluído",
        active: "Ativa",
        trialing: "Teste ativo",
        past_due: "Pagamento atrasado",
        unpaid: "Não pago",
        canceled: "Cancelada",
        incomplete: "Incompleta",
        incomplete_expired: "Expirada",
        desconhecido: "Desconhecido",
        desativada: "Desativada",
    };

    return mapa[status] || status || "Sem assinatura";
}


function obterPlanoPorCodigoSaas(codigo) {
    return planosAssinaturaSaasCache.find((plano) => {
        return plano.codigo === codigo;
    });
}


function renderizarPlanosAssinaturaSaas(planos) {
    const container = document.getElementById("planos-saas-grid");

    if (!container) {
        return;
    }

    if (!planos.length) {
        container.innerHTML = `
            <p class="texto-vazio-saas">
                Nenhum plano configurado.
            </p>
        `;

        return;
    }

    container.innerHTML = planos
        .map((plano) => {
            const destaque = plano.codigo === "anual"
                ? "destaque"
                : "";

            return `
                <article class="plano-saas-card ${destaque}">
                    <h3>${plano.nome}</h3>

                    <p>
                        Ideal para empresas que querem manter o sistema ativo
                        com previsibilidade.
                    </p>

                    <strong class="plano-saas-preco">
                        ${formatarMoedaSaas(plano.valor_mensal_equivalente)}/mês
                    </strong>

                    <span class="plano-saas-total">
                        Total do período: ${formatarMoedaSaas(plano.valor_total)}
                    </span>

                    ${
                        plano.desconto_percentual > 0
                            ? `
                                <span class="plano-saas-desconto">
                                    ${plano.desconto_percentual}% de desconto
                                </span>
                            `
                            : `
                                <span class="plano-saas-desconto">
                                    Sem fidelidade
                                </span>
                            `
                    }
                </article>
            `;
        })
        .join("");
}


function obterValorFiltroSaas(id) {
    const elemento = document.getElementById(id);

    if (!elemento) {
        return "";
    }

    return String(elemento.value || "").trim().toLowerCase();
}


function empresaCombinaComBuscaSaas(empresa, busca) {
    if (!busca) {
        return true;
    }

    const textoEmpresa = [
        empresa.nome,
        empresa.slug,
        empresa.email,
        empresa.telefone,
    ]
        .map((valor) => String(valor || "").toLowerCase())
        .join(" ");

    return textoEmpresa.includes(busca);
}


function empresaCombinaComStatusSaas(empresa, statusFiltro) {
    if (!statusFiltro) {
        return true;
    }

    const statusAssinatura = String(
        empresa.status_assinatura || ""
    ).trim().toLowerCase();

    const statusPagamento = String(
        empresa.status_pagamento || ""
    ).trim().toLowerCase();

    const empresaDesativada =
        statusAssinatura === "desativada";

    if (statusFiltro === "ativa") {
        return !empresaDesativada;
    }

    if (statusFiltro === "desativada") {
        return empresaDesativada;
    }

    if (statusFiltro === "em_dia") {
        return statusPagamento === "em_dia";
    }

    if (statusFiltro === "pendente") {
        return statusPagamento === "pendente";
    }

    if (statusFiltro === "cancelado") {
        return statusPagamento === "cancelado";
    }

    if (statusFiltro === "trial") {
        return (
            statusAssinatura === "trial"
            || statusAssinatura === "trialing"
        );
    }

    return true;
}


function empresaCombinaComPlanoSaas(empresa, planoFiltro) {
    if (!planoFiltro) {
        return true;
    }

    const planoEmpresa = String(
        empresa.plano_codigo || "sem_plano"
    ).trim().toLowerCase();

    return planoEmpresa === planoFiltro;
}


function obterEmpresasFiltradasSaas() {
    const busca = obterValorFiltroSaas(
        "filtro-busca-empresa-saas"
    );

    const statusFiltro = obterValorFiltroSaas(
        "filtro-status-empresa-saas"
    );

    const planoFiltro = obterValorFiltroSaas(
        "filtro-plano-empresa-saas"
    );

    return empresasAssinaturasSaasCache.filter((empresa) => {
        return (
            empresaCombinaComBuscaSaas(empresa, busca)
            && empresaCombinaComStatusSaas(empresa, statusFiltro)
            && empresaCombinaComPlanoSaas(empresa, planoFiltro)
        );
    });
}


function aplicarFiltrosEmpresasSaas() {
    const empresasFiltradas = obterEmpresasFiltradasSaas();

    renderizarAssinaturasEmpresasSaasSemAtualizarCache(
        empresasFiltradas
    );
}


function limparFiltrosEmpresasSaas() {
    const campoBusca = document.getElementById(
        "filtro-busca-empresa-saas"
    );

    const campoStatus = document.getElementById(
        "filtro-status-empresa-saas"
    );

    const campoPlano = document.getElementById(
        "filtro-plano-empresa-saas"
    );

    if (campoBusca) {
        campoBusca.value = "";
    }

    if (campoStatus) {
        campoStatus.value = "";
    }

    if (campoPlano) {
        campoPlano.value = "";
    }

    aplicarFiltrosEmpresasSaas();
}


function configurarFiltrosEmpresasSaas() {
    const campoBusca = document.getElementById(
        "filtro-busca-empresa-saas"
    );

    const campoStatus = document.getElementById(
        "filtro-status-empresa-saas"
    );

    const campoPlano = document.getElementById(
        "filtro-plano-empresa-saas"
    );

    if (campoBusca) {
        campoBusca.addEventListener(
            "input",
            aplicarFiltrosEmpresasSaas
        );
    }

    if (campoStatus) {
        campoStatus.addEventListener(
            "change",
            aplicarFiltrosEmpresasSaas
        );
    }

    if (campoPlano) {
        campoPlano.addEventListener(
            "change",
            aplicarFiltrosEmpresasSaas
        );
    }
}


function renderizarAssinaturasEmpresasSaas(empresas) {
    empresasAssinaturasSaasCache = empresas || [];

    renderizarAssinaturasEmpresasSaasSemAtualizarCache(
        empresasAssinaturasSaasCache
    );
}


function renderizarAssinaturasEmpresasSaasSemAtualizarCache(empresas) {
    const container = document.getElementById(
        "lista-assinaturas-empresas-saas"
    );

    if (!container) {
        return;
    }

    if (!empresas.length) {
        container.innerHTML = `
            <p class="texto-vazio-saas">
                Nenhuma empresa encontrada com os filtros atuais.
            </p>
        `;

        return;
    }

    container.innerHTML = empresas
    .map((empresa) => {
        const planoAtual = obterPlanoPorCodigoSaas(
            empresa.plano_codigo
        );

        const statusAssinatura = String(
            empresa.status_assinatura || ""
        ).toLowerCase();

        const empresaDesativada =
            statusAssinatura === "desativada";

        const pagamentoPendente =
            String(empresa.status_pagamento || "").toLowerCase() === "pendente";

        const pagamentoCancelado =
            String(empresa.status_pagamento || "").toLowerCase() === "cancelado";

        const empresaEmDia =
            String(empresa.status_pagamento || "").toLowerCase() === "em_dia";

        return `
            <article class="assinatura-empresa-card">
                    <div class="assinatura-empresa-info">
                    <h4>
                        ${empresa.nome}
                        ${empresaDesativada ? `<span class="badge-empresa-desativada">Desativada</span>` : ""}
                        ${empresaEmDia ? `<span class="badge-empresa-ativa">Em dia</span>` : ""}
                        ${pagamentoPendente ? `<span class="badge-empresa-pendente">Pendente</span>` : ""}
                        ${pagamentoCancelado && !empresaDesativada ? `<span class="badge-empresa-cancelada">Pagamento cancelado</span>` : ""}
                    </h4>

                        <p>
                            ${empresa.email || "Sem e-mail"}<br>
                            Tenant: ${empresa.slug}
                        </p>

                        <div class="assinatura-empresa-meta">
                            <span>
                                Assinatura: ${traduzirStatusAssinaturaSaas(empresa.status_assinatura)}
                            </span>

                            <span>
                                Plano: ${planoAtual ? planoAtual.nome : empresa.plano_nome || "Não definido"}
                            </span>

                            <span>
                                Pagamento: ${traduzirStatusPagamento(empresa.status_pagamento)}
                            </span>

                            <span>
                                Vencimento: ${formatarDataSaas(empresa.vencimento_plano)}
                            </span>
                        </div>
                    </div>

                    <div class="assinatura-empresa-acoes">
                        <div class="grupo-gateway-assinatura">
                            <strong>Stripe</strong>

                            <button
                                type="button"
                                onclick="criarCheckoutAssinaturaSaas(${empresa.id}, 'mensal')"
                            >
                                Mensal
                            </button>

                            <button
                                type="button"
                                onclick="criarCheckoutAssinaturaSaas(${empresa.id}, 'trimestral')"
                            >
                                Trimestral
                            </button>

                            <button
                                type="button"
                                class="destaque"
                                onclick="criarCheckoutAssinaturaSaas(${empresa.id}, 'anual')"
                            >
                                Anual
                            </button>
                        </div>

                        <div class="grupo-gateway-assinatura mercado-pago">
                            <strong>Mercado Pago</strong>

                            <button
                                type="button"
                                onclick="criarCheckoutMercadoPagoSaas(${empresa.id}, 'mensal')"
                            >
                                Mensal
                            </button>

                            <button
                                type="button"
                                onclick="criarCheckoutMercadoPagoSaas(${empresa.id}, 'trimestral')"
                            >
                                Trimestral
                            </button>

                            <button
                                type="button"
                                class="destaque"
                                onclick="criarCheckoutMercadoPagoSaas(${empresa.id}, 'anual')"
                            >
                                Anual
                            </button>
                        </div>

                        <div class="grupo-gateway-assinatura">
                            <strong>Status da empresa</strong>

                            <button
                                type="button"
                                class="${empresaDesativada ? "btn-reativar-empresa-saas" : "btn-desativar-empresa-saas"}"
                                onclick="alterarStatusEmpresaSaas(${empresa.id}, ${empresaDesativada ? "true" : "false"})"
                            >
                                ${empresaDesativada ? "Reativar empresa" : "Desativar empresa"}
                            </button>

                            ${empresaDesativada ? `
                                <button
                                    type="button"
                                    class="btn-excluir-empresa-saas"
                                    onclick="excluirEmpresaTesteSaas(${empresa.id})"
                                >
                                    Excluir empresa de teste
                                </button>
                            ` : ""}
                        </div>
                    </div>
                </article>
            `;
        })
        .join("");
}


function formatarMoedaSaas(valor) {
    const numero = Number(valor || 0);

    return numero.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
    });
}


function atualizarTextoElementoSaas(id, valor) {
    const elemento = document.getElementById(id);

    if (!elemento) {
        return;
    }

    elemento.innerText = valor;
}


function traduzirPlanoCodigoSaas(codigo) {
    const mapa = {
        mensal: "Mensal",
        trimestral: "Trimestral",
        anual: "Anual",
        sem_plano: "Sem plano",
    };

    return mapa[codigo] || codigo || "Não definido";
}


function renderizarMetricasDashboardSaas(metricas) {
    if (!metricas) {
        return;
    }

    atualizarTextoElementoSaas(
        "metrica-total-empresas",
        metricas.total_empresas ?? 0
    );

    atualizarTextoElementoSaas(
        "metrica-total-ativas",
        metricas.total_ativas ?? 0
    );

    atualizarTextoElementoSaas(
        "metrica-total-desativadas",
        metricas.total_desativadas ?? 0
    );

    atualizarTextoElementoSaas(
        "metrica-receita-mensal",
        formatarMoedaSaas(metricas.receita_mensal_estimada)
    );

    atualizarTextoElementoSaas(
        "metrica-total-em-dia",
        metricas.total_em_dia ?? 0
    );

    atualizarTextoElementoSaas(
        "metrica-total-pendentes",
        metricas.total_pendentes ?? 0
    );

    atualizarTextoElementoSaas(
        "metrica-total-agendamentos",
        metricas.total_agendamentos ?? 0
    );

    const planoMaisUsado = metricas.plano_mais_usado;

    atualizarTextoElementoSaas(
        "metrica-plano-mais-usado",
        planoMaisUsado
            ? `${traduzirPlanoCodigoSaas(planoMaisUsado.codigo)} (${planoMaisUsado.total_empresas})`
            : "Não definido"
    );

    renderizarTabelaResumoEmpresasDashboardSaas(
        metricas.empresas || []
    );

    renderizarAlertasOperacionaisSaas(
        metricas.empresas || []
    );
    
    renderizarRankingAgendamentosSaas(
        metricas.empresas || []
    );
}


function renderizarTabelaResumoEmpresasDashboardSaas(empresas) {
    const container = document.getElementById(
        "tabela-resumo-empresas-dashboard-saas"
    );

    if (!container) {
        return;
    }

    if (!empresas.length) {
        container.innerHTML = `
            <p class="texto-vazio-saas">
                Nenhuma empresa encontrada.
            </p>
        `;

        return;
    }

    container.innerHTML = `
        <div class="tabela-scroll-saas">
            <table class="tabela-dashboard-saas">
                <thead>
                    <tr>
                        <th>Empresa</th>
                        <th>Plano</th>
                        <th>Status</th>
                        <th>Pagamento</th>
                        <th>Receita</th>
                        <th>Agendamentos</th>
                    </tr>
                </thead>

                <tbody>
                    ${empresas
                        .map((empresa) => {
                            const empresaDesativada =
                                empresa.empresa_desativada === true;

                            const pagamentoEmDia =
                                empresa.pagamento_em_dia === true;

                            return `
                                <tr>
                                    <td>
                                        <strong>${empresa.nome || "Sem nome"}</strong>
                                        <small>${empresa.slug || ""}</small>
                                    </td>

                                    <td>
                                        ${traduzirPlanoCodigoSaas(empresa.plano_codigo)}
                                    </td>

                                    <td>
                                        ${
                                            empresaDesativada
                                                ? `<span class="badge-empresa-desativada">Desativada</span>`
                                                : `<span class="badge-empresa-ativa">Ativa</span>`
                                        }
                                    </td>

                                    <td>
                                        ${
                                            pagamentoEmDia
                                                ? `<span class="badge-empresa-ativa">Em dia</span>`
                                                : `<span class="badge-empresa-pendente">${traduzirStatusPagamento(empresa.status_pagamento)}</span>`
                                        }
                                    </td>

                                    <td>
                                        ${formatarMoedaSaas(empresa.valor_mensal)}
                                    </td>

                                    <td>
                                        ${empresa.agendamentos_total ?? 0}
                                    </td>
                                </tr>
                            `;
                        })
                        .join("")}
                </tbody>
            </table>
        </div>
    `;
}


async function carregarMetricasDashboardSaas() {
    try {
        const metricas = await saasRequest(
            "/api/saas/dashboard/metricas"
        );

        renderizarMetricasDashboardSaas(metricas);

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


async function carregarPlanosAssinaturaSaas() {
    const planos = await saasRequest(
        "/api/saas/assinaturas/planos"
    );

    planosAssinaturaSaasCache = planos;

    renderizarPlanosAssinaturaSaas(planos);

    return planos;
}


async function carregarAssinaturasSaas() {
    const containerPlanos = document.getElementById("planos-saas-grid");

    const containerEmpresas = document.getElementById(
        "lista-assinaturas-empresas-saas"
    );

    if (containerPlanos) {
        containerPlanos.innerHTML = "Carregando planos...";
    }

    if (containerEmpresas) {
        containerEmpresas.innerHTML = "Carregando empresas...";
    }

    try {
        const planos = await carregarPlanosAssinaturaSaas();

        const respostaEmpresas = await saasRequest(
            "/api/saas/barbearias"
        );

        const empresas = Array.isArray(respostaEmpresas)
            ? respostaEmpresas
            : (
                respostaEmpresas?.barbearias
                || respostaEmpresas?.clientes
                || respostaEmpresas?.empresas
                || respostaEmpresas?.items
                || []
            );

        clientesSaasCache = empresas;

        try {
            atualizarResumoSaas(empresas);

        } catch (erroResumo) {
            console.warn(
                "Resumo SaaS não atualizado nesta seção:",
                erroResumo
            );
        }

        renderizarAssinaturasEmpresasSaas(empresas);

        return {
            planos,
            empresas,
        };

    } catch (erro) {
        console.error(
            "Erro ao carregar assinaturas SaaS:",
            erro
        );

        if (containerEmpresas) {
            containerEmpresas.innerHTML = `
                <p class="texto-vazio-saas">
                    Não foi possível carregar as empresas.
                    ${erro.message || ""}
                </p>
            `;
        }

        tratarErroSaas(erro);
    }
}


async function criarCheckoutAssinaturaSaas(empresaId, planoCodigo) {
    const confirmar = window.confirm(
        `Deseja gerar checkout do plano ${planoCodigo.toUpperCase()} para esta empresa?`
    );

    if (!confirmar) {
        return;
    }

    try {
        const resposta = await saasRequest(
            "/api/saas/assinaturas/checkout",
            {
                method: "POST",
                body: {
                    barbearia_id: empresaId,
                    plano_codigo: planoCodigo,
                },
            }
        );

        console.log(
            "Resposta checkout Stripe:",
            resposta
        );

        if (
            !resposta
            || !resposta.checkout_url
        ) {
            exibirMensagemSaas(
                "Checkout criado, mas o backend não retornou a URL do Stripe.",
                "erro"
            );

            return;
        }

        invalidarSecoesSaas([
            "secao-saas-dashboard",
            "secao-saas-empresas",
            "secao-saas-assinaturas",
        ]);

        window.location.href = resposta.checkout_url;

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


async function criarCheckoutMercadoPagoSaas(empresaId, planoCodigo) {
    const confirmar = window.confirm(
        `Deseja gerar checkout Mercado Pago do plano ${planoCodigo.toUpperCase()} para esta empresa?`
    );

    if (!confirmar) {
        return;
    }

    try {
        const resposta = await saasRequest(
            "/api/saas/mercado-pago/checkout",
            {
                method: "POST",
                body: {
                    barbearia_id: empresaId,
                    plano_codigo: planoCodigo,
                },
            }
        );

        console.log(
            "Resposta checkout Mercado Pago:",
            resposta
        );

        if (
            !resposta
            || !resposta.checkout_url
        ) {
            exibirMensagemSaas(
                "Checkout criado, mas o Mercado Pago não retornou a URL.",
                "erro"
            );

            return;
        }

        invalidarSecoesSaas([
            "secao-saas-dashboard",
            "secao-saas-empresas",
            "secao-saas-assinaturas",
        ]);

        window.location.href = resposta.checkout_url;

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


function tratarRetornoPagamentosSaas() {
    const parametros = new URLSearchParams(
        window.location.search
    );

    const statusStripe = parametros.get("stripe");
    const statusMercadoPago = parametros.get("mercado_pago");

    if (
        !statusStripe
        && !statusMercadoPago
    ) {
        return;
    }

    if (statusStripe === "sucesso") {
        exibirMensagemSaas(
            "Pagamento recebido pelo Stripe. Atualizando assinatura..."
        );

        localStorage.setItem(
            "gesto_saas_secao_ativa",
            "secao-saas-assinaturas"
        );
    }

    if (statusStripe === "cancelado") {
        exibirMensagemSaas(
            "Checkout Stripe cancelado. Nenhuma alteração foi feita.",
            "erro"
        );
    }

    if (statusMercadoPago === "sucesso") {
        exibirMensagemSaas(
            "Pagamento Mercado Pago recebido. Atualizando assinatura..."
        );

        localStorage.setItem(
            "gesto_saas_secao_ativa",
            "secao-saas-assinaturas"
        );
    }

    if (statusMercadoPago === "pendente") {
        exibirMensagemSaas(
            "Pagamento Mercado Pago está pendente. Atualize mais tarde para conferir.",
            "erro"
        );

        localStorage.setItem(
            "gesto_saas_secao_ativa",
            "secao-saas-assinaturas"
        );
    }

    if (statusMercadoPago === "falha") {
        exibirMensagemSaas(
            "Pagamento Mercado Pago não foi concluído.",
            "erro"
        );

        localStorage.setItem(
            "gesto_saas_secao_ativa",
            "secao-saas-assinaturas"
        );
    }

    invalidarSecoesSaas([
        "secao-saas-dashboard",
        "secao-saas-empresas",
        "secao-saas-assinaturas",
    ]);

    const urlLimpa = `${window.location.origin}${window.location.pathname}`;

    window.history.replaceState(
        {},
        document.title,
        urlLimpa
    );
}

async function alterarStatusEmpresaSaas(barbeariaId, ativar) {
    const acao = ativar ? "reativar" : "desativar";

    const confirmar = window.confirm(
        `Deseja realmente ${acao} esta empresa?`
    );

    if (!confirmar) {
        return;
    }

    try {
        await saasRequest(
            `/api/saas/barbearias/${barbeariaId}/ativacao`,
            {
                method: "PUT",
                body: {
                    ativa: ativar,
                },
            }
        );

        exibirMensagemSaas(
            ativar
                ? "Empresa reativada com sucesso."
                : "Empresa desativada com sucesso."
        );

        invalidarSecoesSaas([
            "secao-saas-dashboard",
            "secao-saas-empresas",
            "secao-saas-assinaturas",
        ]);

        await carregarDadosDaSecaoSaas(
            "secao-saas-assinaturas",
            {
                forcar: true,
            }
        );

        await carregarMetricasDashboardSaas();


    } catch (erro) {
        tratarErroSaas(erro);
    }
}


function obterAlertasOperacionaisSaas(empresas) {
    const alertas = [];

    empresas.forEach((empresa) => {
        const statusPagamento = String(
            empresa.status_pagamento || ""
        ).trim().toLowerCase();

        const statusAssinatura = String(
            empresa.status_assinatura || ""
        ).trim().toLowerCase();

        const semPlano =
            !empresa.plano_codigo
            || empresa.plano_codigo === "sem_plano";

        if (empresa.empresa_desativada === true) {
            alertas.push({
                tipo: "desativada",
                titulo: empresa.nome || "Empresa sem nome",
                descricao: "Empresa desativada manualmente pelo SaaS Master.",
                prioridade: 1,
            });

            return;
        }

        if (statusPagamento === "pendente") {
            alertas.push({
                tipo: "pendente",
                titulo: empresa.nome || "Empresa sem nome",
                descricao: "Pagamento pendente. Acompanhe para evitar bloqueio.",
                prioridade: 2,
            });
        }

        if (statusPagamento === "cancelado") {
            alertas.push({
                tipo: "cancelada",
                titulo: empresa.nome || "Empresa sem nome",
                descricao: "Pagamento cancelado ou assinatura interrompida.",
                prioridade: 3,
            });
        }

        if (semPlano) {
            alertas.push({
                tipo: "sem-plano",
                titulo: empresa.nome || "Empresa sem nome",
                descricao: "Empresa sem plano definido.",
                prioridade: 4,
            });
        }

        if (
            statusAssinatura === "trial"
            || statusAssinatura === "trialing"
        ) {
            alertas.push({
                tipo: "trial",
                titulo: empresa.nome || "Empresa sem nome",
                descricao: "Empresa em período de teste.",
                prioridade: 5,
            });
        }
    });

    return alertas.sort((a, b) => a.prioridade - b.prioridade);
}


function renderizarAlertasOperacionaisSaas(empresas) {
    const container = document.getElementById(
        "alertas-operacionais-saas"
    );

    if (!container) {
        return;
    }

    const alertas = obterAlertasOperacionaisSaas(empresas);

    if (!alertas.length) {
        container.innerHTML = `
            <p class="texto-vazio-saas">
                Nenhum alerta operacional no momento.
            </p>
        `;

        return;
    }

    container.innerHTML = alertas
        .map((alerta) => {
            return `
                <article class="alerta-operacional-saas alerta-${alerta.tipo}">
                    <div>
                        <strong>${alerta.titulo}</strong>
                        <p>${alerta.descricao}</p>
                    </div>

                    <span>${alerta.tipo.replace("-", " ")}</span>
                </article>
            `;
        })
        .join("");
}


function renderizarRankingAgendamentosSaas(empresas) {
    const container = document.getElementById(
        "ranking-agendamentos-saas"
    );

    if (!container) {
        return;
    }

    const ranking = [...empresas]
        .sort((a, b) => {
            return Number(b.agendamentos_total || 0)
                - Number(a.agendamentos_total || 0);
        })
        .slice(0, 5);

    if (!ranking.length) {
        container.innerHTML = `
            <p class="texto-vazio-saas">
                Nenhuma empresa encontrada para o ranking.
            </p>
        `;

        return;
    }

    container.innerHTML = ranking
        .map((empresa, indice) => {
            const posicao = indice + 1;

            return `
                <article class="item-ranking-saas">
                    <div class="posicao-ranking-saas">
                        ${posicao}
                    </div>

                    <div class="info-ranking-saas">
                        <strong>${empresa.nome || "Empresa sem nome"}</strong>
                        <span>${empresa.slug || ""}</span>
                    </div>

                    <div class="total-ranking-saas">
                        <strong>${empresa.agendamentos_total ?? 0}</strong>
                        <span>agendamentos</span>
                    </div>
                </article>
            `;
        })
        .join("");
}


async function excluirEmpresaTesteSaas(barbeariaId) {
    const confirmacaoEsperada = `EXCLUIR-${barbeariaId}`;

    const primeiraConfirmacao = window.confirm(
        "Esta ação é permanente e apagará a empresa e seus dados relacionados. " +
        "Use apenas para empresas de teste. Deseja continuar?"
    );

    if (!primeiraConfirmacao) {
        return;
    }

    const confirmacaoDigitada = window.prompt(
        `Para confirmar a exclusão, digite exatamente: ${confirmacaoEsperada}`
    );

    if (confirmacaoDigitada !== confirmacaoEsperada) {
        exibirMensagemSaas(
            "Exclusão cancelada. Confirmação inválida."
        );
        return;
    }

    try {
        const resposta = await saasRequest(
            `/api/saas/barbearias/${barbeariaId}`,
            {
                method: "DELETE",
                body: {
                    confirmacao: confirmacaoDigitada,
                },
            }
        );

        exibirMensagemSaas(
            resposta.mensagem || "Empresa excluída com sucesso."
        );

        invalidarSecoesSaas([
            "secao-saas-dashboard",
            "secao-saas-empresas",
            "secao-saas-assinaturas",
        ]);

        await carregarDadosDaSecaoSaas(
            "secao-saas-assinaturas",
            {
                forcar: true,
            }
        );

        await carregarMetricasDashboardSaas();

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


function exibirBannerComercialSaas() {
    const banner = document.getElementById(
        "banner-comercial-saas"
    );

    if (!banner) {
        return;
    }

    const dispensado = localStorage.getItem(
        BANNER_COMERCIAL_SAAS_KEY
    );

    if (dispensado === "true") {
        banner.classList.remove("visivel");
        return;
    }

    banner.classList.add("visivel");
}


function dispensarBannerComercialSaas() {
    localStorage.setItem(
        BANNER_COMERCIAL_SAAS_KEY,
        "true"
    );

    const banner = document.getElementById(
        "banner-comercial-saas"
    );

    if (banner) {
        banner.classList.remove("visivel");
    }
}


    window.dispensarBannerComercialSaas =
        dispensarBannerComercialSaas;


async function iniciarPainelSaas() {
    const formLoginSaas = document.getElementById("form-login-saas");

    if (formLoginSaas) {
        formLoginSaas.addEventListener(
            "submit",
            realizarLoginSaas
        );
    }

    const formNovaBarbearia = document.getElementById(
        "form-nova-barbearia"
    );

    if (formNovaBarbearia) {
        formNovaBarbearia.addEventListener(
            "submit",
            criarNovoCliente
        );
    }

    const formAvisoSaas = document.getElementById("form-aviso-saas");

    if (formAvisoSaas) {
        formAvisoSaas.addEventListener(
            "submit",
            criarAvisoSaas
        );
    }

    const formFinanceiro = document.getElementById(
        "form-financeiro-saas"
    );

    if (formFinanceiro) {
        formFinanceiro.addEventListener(
            "submit",
            salvarFinanceiroEmpresa
        );
    }

    const botaoSair = document.getElementById("btn-sair-saas");

    if (botaoSair) {
        botaoSair.addEventListener(
            "click",
            fazerLogoutSaas
        );
    }

    if (!obterTokenSaas()) {
        exibirLoginSaas();
        return;
    }

    exibirPainelSaas();

    configurarFiltrosEmpresasSaas();

    exibirBannerComercialSaas();

    tratarRetornoPagamentosSaas();

    inicializarNavegacaoSaas();
    }

window.addEventListener(
    "DOMContentLoaded",
    iniciarPainelSaas
);

window.abrirModalConfiguracaoEmpresa = abrirModalConfiguracaoEmpresa;
window.fecharModalConfiguracaoEmpresa = fecharModalConfiguracaoEmpresa;
window.copiarLinkPublicoEmpresa = copiarLinkPublicoEmpresa;
window.copiarLinkAdminEmpresa = copiarLinkAdminEmpresa;
window.redefinirSenhaEmpresa = redefinirSenhaEmpresa;
window.carregarDiagnosticoEmpresa = carregarDiagnosticoEmpresa;
window.salvarConfiguracaoEmpresa = salvarConfiguracaoEmpresa;
window.carregarAvisosSaas = carregarAvisosSaas;
window.alternarStatusAvisoSaas = alternarStatusAvisoSaas;
window.carregarAssinaturasSaas = carregarAssinaturasSaas;
window.criarCheckoutAssinaturaSaas = criarCheckoutAssinaturaSaas;
window.criarCheckoutMercadoPagoSaas = criarCheckoutMercadoPagoSaas;
window.alterarStatusEmpresaSaas = alterarStatusEmpresaSaas;
window.excluirEmpresaTesteSaas = excluirEmpresaTesteSaas;
window.limparFiltrosEmpresasSaas = limparFiltrosEmpresasSaas;
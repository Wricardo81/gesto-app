const SAAS_TOKEN_STORAGE_KEY =
    "gesto_saas_token";
let clientesSaasCache = [];
let empresaConfiguracaoAtual = null;
let avisosSaasCache = [];

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

        await carregarClientes();

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

        document
            .getElementById(
                "form-nova-barbearia"
            )
            .reset();

        await carregarClientes();

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

        await carregarClientes();
        
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
}


function inicializarNavegacaoSaas() {
    const botoes = document.querySelectorAll(".saas-tab");

    botoes.forEach((botao) => {
        botao.addEventListener("click", () => {
            mostrarSecaoSaas(botao.dataset.secao);
        });
    });

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

        await carregarClientes();

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

        await carregarClientes();

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

        await carregarClientes();

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

        await carregarAvisosSaas();

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

        await carregarAvisosSaas();

        exibirMensagemSaas(
            ativo
                ? "Aviso ativado com sucesso."
                : "Aviso desativado com sucesso."
        );

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


async function iniciarPainelSaas() {
    document
        .getElementById("form-login-saas")
        .addEventListener(
            "submit",
            realizarLoginSaas
        );

    document
        .getElementById(
            "form-nova-barbearia"
        )
        .addEventListener(
            "submit",
            criarNovoCliente
    );

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

    document
        .getElementById("btn-sair-saas")
        .addEventListener(
            "click",
            fazerLogoutSaas
    );
    
    inicializarNavegacaoSaas();

    if (!obterTokenSaas()) {
        exibirLoginSaas();
        return;
    }

    exibirPainelSaas();

    await carregarClientes();

    mostrarSecaoSaas("secao-saas-empresas");

    exibirMensagemSaas(
        "Empresa criada com sucesso."
    );
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
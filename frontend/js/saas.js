const SAAS_TOKEN_STORAGE_KEY =
    "gesto_saas_token";


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
                        onclick="editarFinanceiroEmpresa(${cliente.id})"
                    >
                        Financeiro
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

        alert("Pagamento registrado com sucesso.");

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


async function editarFinanceiroEmpresa(id) {
    const planoNome = prompt(
        "Nome do plano:",
        "Profissional"
    );

    if (planoNome === null) {
        return;
    }

    const valorTexto = prompt(
        "Valor mensal:",
        "99"
    );

    if (valorTexto === null) {
        return;
    }

    const vencimentoPlano = prompt(
        "Data de vencimento no formato YYYY-MM-DD:",
        ""
    );

    if (vencimentoPlano === null) {
        return;
    }

    const statusPagamento = prompt(
        "Status: em_dia, pendente, vencido, cancelado ou teste",
        "em_dia"
    );

    if (statusPagamento === null) {
        return;
    }

    const diasToleranciaTexto = prompt(
        "Dias de tolerância:",
        "3"
    );

    if (diasToleranciaTexto === null) {
        return;
    }

    const valorMensal = Number(
        String(valorTexto).replace(",", ".")
    );

    const diasTolerancia = Number(
        diasToleranciaTexto
    );

    if (
        !planoNome.trim()
        || Number.isNaN(valorMensal)
        || valorMensal < 0
        || Number.isNaN(diasTolerancia)
        || diasTolerancia < 0
    ) {
        alert("Dados financeiros inválidos.");
        return;
    }

    try {
        await saasRequest(
            `/api/saas/barbearias/${id}/financeiro`,
            {
                method: "PUT",
                body: {
                    plano_nome: planoNome.trim(),
                    valor_mensal: valorMensal,
                    vencimento_plano: vencimentoPlano.trim() || null,
                    status_pagamento: statusPagamento.trim().toLowerCase(),
                    dias_tolerancia: diasTolerancia,
                    marcar_como_pago: false,
                },
            }
        );

        await carregarClientes();

        exibirMensagemSaas("Dados financeiros atualizados com sucesso.");

    } catch (erro) {
        tratarErroSaas(erro);
    }
}


window.marcarEmpresaComoPaga = marcarEmpresaComoPaga;
window.editarFinanceiroEmpresa = editarFinanceiroEmpresa;

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
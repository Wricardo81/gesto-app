let tenantSlug = "";
let telefoneAtual = "";
let codigoSelecionadoParaCancelar = "";


function obterTenantDaUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("tenant") || "";
}


function normalizarTelefone(telefone) {
    return String(telefone || "").replace(/\D/g, "");
}


function formatarMoeda(valor) {
    return Number(valor || 0).toLocaleString(
        "pt-BR",
        {
            style: "currency",
            currency: "BRL",
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


function traduzirStatus(status) {
    const mapa = {
        confirmado: "Confirmado",
        concluido: "Concluído",
        cancelado: "Cancelado",
        faltou: "Faltou",
    };

    return mapa[status] || "Confirmado";
}


function classeStatus(status) {
    const mapa = {
        confirmado: "status-confirmado",
        concluido: "status-concluido",
        cancelado: "status-cancelado",
        faltou: "status-faltou",
    };

    return mapa[status] || "status-confirmado";
}


function exibirMensagem(texto, tipo = "sucesso") {
    const mensagem = document.getElementById("mensagem");

    mensagem.textContent = texto;
    mensagem.className = `mensagem ${tipo}`;
}


function limparMensagem() {
    const mensagem = document.getElementById("mensagem");

    mensagem.textContent = "";
    mensagem.className = "mensagem";
}


async function carregarConfiguracaoVisual() {
    if (!tenantSlug) {
        return;
    }

    try {
        const config = await apiRequest(
            `/api/${tenantSlug}/configuracoes`
        );

        const nome = config.nome_publico || tenantSlug;
        const logoUrl = config.logo_url || "";

        document.title = `${nome} | Meus Agendamentos`;

        document.getElementById("nome-estabelecimento").textContent =
            nome;

        const linkVoltar = document.getElementById(
            "link-voltar-agendamento"
        );

        linkVoltar.href = `./agendamento.html?tenant=${tenantSlug}`;

        const logoBox = document.getElementById("marca-logo");

        if (logoUrl) {
            logoBox.innerHTML = `
                <img
                    src="${logoUrl}"
                    alt="${nome}"
                    onerror="this.parentElement.textContent='G';"
                >
            `;
        }

        if (config.cor_fundo) {
            document.documentElement.style.setProperty(
                "--cor-fundo",
                config.cor_fundo
            );
        }

        if (config.cor_tema) {
            document.documentElement.style.setProperty(
                "--cor-destaque",
                config.cor_tema
            );
        }

    } catch (erro) {
        console.warn(
            "Não foi possível carregar identidade visual:",
            erro
        );
    }
}


function renderizarAgendamentos(dados) {
    const resumo = document.getElementById("resumo-agendamentos");
    const lista = document.getElementById("lista-agendamentos");

    resumo.style.display = "block";
    resumo.textContent = `
        ${dados.total} agendamento(s) encontrado(s).
        Política de cancelamento: até ${dados.limite_cancelamento_horas} hora(s) antes.
    `;

    lista.innerHTML = "";

    if (!dados.agendamentos || !dados.agendamentos.length) {
        lista.innerHTML = `
            <div class="agendamento-card">
                Nenhum agendamento encontrado para este telefone.
            </div>
        `;
        return;
    }

    for (const agendamento of dados.agendamentos) {
        const status = agendamento.status || "confirmado";
        const podeCancelar = Boolean(agendamento.pode_cancelar);
        const codigoPublico = agendamento.codigo_publico || "";

        const card = document.createElement("article");
        card.className = "agendamento-card";

        card.innerHTML = `
            <div class="agendamento-topo">
                <div>
                    <h3>${agendamento.servico || "-"}</h3>
                    <p>
                        ${formatarDataBR(agendamento.data)}
                        às ${agendamento.horario || "-"}
                    </p>
                </div>

                <span class="badge-status ${classeStatus(status)}">
                    ${traduzirStatus(status)}
                </span>
            </div>

            <div class="dados-grid">
                <div class="dado">
                    <small>Profissional</small>
                    <strong>${agendamento.profissional || "-"}</strong>
                </div>

                <div class="dado">
                    <small>Valor</small>
                    <strong>${formatarMoeda(agendamento.valor)}</strong>
                </div>

                <div class="dado">
                    <small>Código</small>
                    <strong>${codigoPublico || "Indisponível"}</strong>
                </div>
            </div>

            <p class="aviso-cancelamento">
                ${
                    podeCancelar
                        ? "Este agendamento ainda pode ser cancelado online."
                        : agendamento.motivo || "Este agendamento não pode ser cancelado online."
                }
            </p>

            ${
                agendamento.motivo_cancelamento
                    ? `<p class="aviso-cancelamento"><strong>Motivo do cancelamento:</strong> ${agendamento.motivo_cancelamento}</p>`
                    : ""
            }

            <div class="acoes-card">
                <button
                    type="button"
                    class="btn-perigo"
                    ${podeCancelar && codigoPublico ? "" : "disabled"}
                    onclick="abrirModalCancelamento('${codigoPublico}')"
                >
                    Cancelar agendamento
                </button>
            </div>
        `;

        lista.appendChild(card);
    }
}


async function buscarAgendamentos(event) {
    event.preventDefault();

    limparMensagem();

    const inputTelefone = document.getElementById("telefone-cliente");
    const telefone = normalizarTelefone(inputTelefone.value);

    if (!telefone) {
        exibirMensagem(
            "Informe um telefone válido.",
            "erro"
        );
        return;
    }

    telefoneAtual = telefone;

    localStorage.setItem(
        `gesto_cliente_telefone_${tenantSlug}`,
        telefoneAtual
    );

    const botao = document.getElementById("btn-buscar");
    botao.disabled = true;
    botao.textContent = "Buscando...";

    try {
        const dados = await apiRequest(
            `/api/${tenantSlug}/agendamentos/publico?telefone=${telefoneAtual}`
        );

        renderizarAgendamentos(dados);

    } catch (erro) {
        console.error(erro);

        exibirMensagem(
            erro.message || "Não foi possível buscar seus agendamentos.",
            "erro"
        );

    } finally {
        botao.disabled = false;
        botao.textContent = "Buscar";
    }
}


function abrirModalCancelamento(codigoPublico) {
    if (!codigoPublico) {
        exibirMensagem(
            "Este agendamento não possui código público para cancelamento.",
            "erro"
        );
        return;
    }

    codigoSelecionadoParaCancelar = codigoPublico;

    document.getElementById("motivo-cancelamento").value = "";
    document.getElementById("modal-cancelamento").style.display = "flex";
}


function fecharModalCancelamento() {
    codigoSelecionadoParaCancelar = "";
    document.getElementById("modal-cancelamento").style.display = "none";
}


async function confirmarCancelamentoCliente() {
    const motivo = document
        .getElementById("motivo-cancelamento")
        .value
        .trim();

    if (!codigoSelecionadoParaCancelar) {
        exibirMensagem(
            "Nenhum agendamento selecionado.",
            "erro"
        );
        return;
    }

    if (!telefoneAtual) {
        exibirMensagem(
            "Informe o telefone novamente para cancelar.",
            "erro"
        );
        return;
    }

    try {
        await apiRequest(
            `/api/${tenantSlug}/agendamentos/publico/${codigoSelecionadoParaCancelar}/cancelar`,
            {
                method: "PUT",
                body: {
                    telefone_cliente: telefoneAtual,
                    motivo_cancelamento: motivo || "Cancelado pelo cliente",
                },
            }
        );

        fecharModalCancelamento();

        exibirMensagem(
            "Agendamento cancelado com sucesso.",
            "sucesso"
        );

        const dados = await apiRequest(
            `/api/${tenantSlug}/agendamentos/publico?telefone=${telefoneAtual}`
        );

        renderizarAgendamentos(dados);

    } catch (erro) {
        console.error(erro);

        exibirMensagem(
            erro.message || "Não foi possível cancelar o agendamento.",
            "erro"
        );

        fecharModalCancelamento();
    }
}


function inicializarPagina() {
    tenantSlug = obterTenantDaUrl();

    if (!tenantSlug) {
        exibirMensagem(
            "Tenant não informado na URL. Acesse pelo link do estabelecimento.",
            "erro"
        );
        return;
    }

    const telefoneSalvo = localStorage.getItem(
        `gesto_cliente_telefone_${tenantSlug}`
    );

    if (telefoneSalvo) {
        document.getElementById("telefone-cliente").value = telefoneSalvo;
    }

    document
        .getElementById("form-busca-agendamentos")
        .addEventListener(
            "submit",
            buscarAgendamentos
        );

    carregarConfiguracaoVisual();
}


window.abrirModalCancelamento = abrirModalCancelamento;
window.fecharModalCancelamento = fecharModalCancelamento;
window.confirmarCancelamentoCliente = confirmarCancelamentoCliente;

window.onload = inicializarPagina;
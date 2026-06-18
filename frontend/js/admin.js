let tenantSlugLogado = "";
let configuracaoAtual = {};
let listenersDePreviewRegistrados = false;
let listenersCRMRegistrados = false;
let listenersBloqueiosRegistrados = false;
let listenersAgendaVisualRegistrados = false;
const secoesAdminCarregadas = new Set();
const secoesAdminCarregando = new Set();

/* =========================================================
   UTILITÁRIOS
========================================================= */

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
        alert("Selecione um arquivo de imagem.");
        inputArquivo.value = "";
        return;
    }

    const tamanhoMaximo = 2 * 1024 * 1024;

    if (arquivo.size > tamanhoMaximo) {
        alert("A imagem deve ter no máximo 2MB.");
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
        alert(
            erro.message
            || "Erro ao enviar imagem."
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
        alert("Sua sessão expirou ou é inválida. Faça login novamente.");
        fazerLogout();
        return;
    }

    if (erro.status === 403) {
        alert("Você não possui permissão para executar esta ação.");
        return;
    }

    alert(
        erro.message
        || "Não foi possível concluir a operação."
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
        iniciarPainel();

    } catch (erro) {
        console.error(erro);

        mensagem.innerText = erro.message;
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

    botoes.forEach((botao) => {
        botao.addEventListener("click", () => {
            mostrarSecaoAdmin(botao.dataset.secao);
        });
    });

    const secaoSalva = localStorage.getItem(
        "gesto_admin_secao_ativa"
    );

    mostrarSecaoAdmin(
        secaoSalva || "secao-dashboard"
    );
}


window.alternarMenuAdmin = alternarMenuAdmin;


function iniciarPainel() {
    if (!existeSessaoLocal()) {
        document
            .getElementById("tela-login")
            .style
            .display = "flex";

        document
            .getElementById("painel-principal")
            .style
            .display = "none";

        return;
    }

    tenantSlugLogado = obterTenantLogado();

    if (!tenantSlugLogado) {
        alert("Sessão inválida. Faça login novamente.");

        fazerLogout();

        return;
    }

    document
        .getElementById("tela-login")
        .style
        .display = "none";

    document
        .getElementById("painel-principal")
        .style
        .display = "block";

    document
        .getElementById("tag-tenant")
        .innerText = `@${tenantSlugLogado}`;

    atualizarLinkPublico();
    registrarListenersDePreview();
    registrarListenersCRM();
    registrarListenersBloqueiosAgenda();
    registrarListenersAgendaVisual();
    inicializarNavegacaoAdmin();

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
            await carregarAgendaVisualDia();

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
    carregarTudo();



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

async function carregarConfiguracaoAtual() {
    if (!adminProntoParaRequisicao()) {
        return;
    }
    try {
        const config = await apiRequest(
            `/api/${tenantSlugLogado}/configuracoes`
        );

        configuracaoAtual = config;

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

    } catch (erro) {
        console.warn(
            "Configurações ainda não cadastradas:",
            erro
        );
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
            exibirMensagemPainel(
                "Configurações salvas com sucesso."
            );
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
            area.innerHTML = `
                <p class="mensagem-vazia">
                    Nenhum profissional cadastrado.
                </p>
            `;

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
        alert("Informe o nome do profissional.");
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
            area.innerHTML = `
                <p class="mensagem-vazia">
                    Nenhum serviço cadastrado.
                </p>
            `;

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
        alert(
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
                    <td colspan="7" class="mensagem-tabela">
                        Nenhum agendamento encontrado.
                    </td>
                </tr>
            `;

            return;
        }

        for (const agendamento of dados.agendamentos) {
            const tr = document.createElement("tr");

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
                </div>
            `;
            tr.appendChild(tdAcoes);

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
            
            tbody.appendChild(tr);
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

        tratarErro(erro);
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
        alert("O motivo do cancelamento é obrigatório.");
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
        await carregarAgendaVisualDia();

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
        alert("Este agendamento não possui telefone válido.");
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
        alert("Informe a data do bloqueio.");
        return;
    }

    if (!diaInteiro && (!horarioInicio || !horarioFim)) {
        alert("Informe horário inicial e final para bloqueio parcial.");
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
        await carregarAgendaVisualDia();
        await carregarAgendamentos();

        invalidarSecoesAdmin([
            "secao-agenda",
            "secao-bloqueios-agenda",
        ]);

        alert("Bloqueio criado com sucesso.");

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
        await carregarAgendaVisualDia();

        invalidarSecoesAdmin([
            "secao-agenda",
            "secao-bloqueios-agenda",
        ]);

        alert("Bloqueio removido com sucesso.");

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
        campoData.addEventListener("change", carregarAgendaVisualDia);
    }

    if (campoProfissional) {
        campoProfissional.addEventListener("change", carregarAgendaVisualDia);
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

    container.innerHTML = "";

    if (!linhaDoTempo.length) {
        container.innerHTML = `
            <div class="mensagem-vazia">
                Nenhum horário configurado para esta data.
            </div>
        `;

        return;
    }

    for (const slot of linhaDoTempo) {
        const eventosDoHorario = eventos.filter((evento) => {
            return eventoPertenceAoHorario(
                evento,
                slot.horario
            );
        });

        const linha = document.createElement("div");

        linha.className = "agenda-linha-horario";

        linha.innerHTML = `
            <div class="agenda-horario-label">
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
}


async function carregarAgendaVisualDia() {
    if (!adminProntoParaRequisicao()) {
        return;
    }
    
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

    container.innerHTML = `
        <div class="mensagem-vazia">
            Carregando agenda visual...
        </div>
    `;

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


async function carregarTudo() {
    const secaoSalva = localStorage.getItem(
        "gesto_admin_secao_ativa"
    );

    const secaoInicial = secaoSalva || "secao-dashboard";

    await carregarDadosDaSecaoAdmin(
        secaoInicial,
        {
            forcar: true,
        }
    );
}


window.onload = iniciarPainel;
let tenantSlugLogado = "";
let configuracaoAtual = {};
let listenersDePreviewRegistrados = false;

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


function valorCampo(id, padrao = "") {
    const elemento = document.getElementById(id);

    if (!elemento) {
        return padrao;
    }

    return elemento.value?.trim?.() ?? padrao;
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

    carregarTudo();
}


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


/* =========================================================
   CARREGAMENTO INICIAL
========================================================= */

async function carregarTudo() {
    await Promise.all([
        carregarConfiguracaoAtual(),
        carregarEquipe(),
        carregarServicos(),
        carregarAgendamentos(),
    ]);
}


window.onload = iniciarPainel;
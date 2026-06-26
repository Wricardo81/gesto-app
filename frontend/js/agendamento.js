let tenantSlug = "";

let reserva = {
    servico: null,
    profissional: null,
    data: "",
    horario: ""
};

let identificadorUltimaBusca = 0;
let assinaturaTenantInativa = false;


/* =========================================================
   UTILITÁRIOS
========================================================= */

function obterDataLocalFormatada() {
    const hoje = new Date();

    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, "0");
    const dia = String(hoje.getDate()).padStart(2, "0");

    return `${ano}-${mes}-${dia}`;
}

function obterDetalheErroApi(erro) {
    if (!erro) {
        return null;
    }

    if (erro.detail) {
        return erro.detail;
    }

    if (erro.data && erro.data.detail) {
        return erro.data.detail;
    }

    if (erro.response && erro.response.detail) {
        return erro.response.detail;
    }

    if (erro.message) {
        return erro.message;
    }

    return null;
}


function formatarMoeda(valor) {
    return Number(valor).toLocaleString(
        "pt-BR",
        {
            style: "currency",
            currency: "BRL"
        }
    );
}


function exibirMensagem(texto, tipo = "informacao") {
    const elemento = document.getElementById("mensagem-status");

    elemento.innerText = texto;
    elemento.className = `mensagem-status ${tipo}`;
}


function limparMensagem() {
    exibirMensagem("");
}


function atualizarBotaoFinalizar() {
    const botao = document.getElementById("btn-agendar");

    const reservaCompleta = Boolean(
        reserva.servico
        && reserva.profissional
        && reserva.data
        && reserva.horario
    );

    botao.disabled = !reservaCompleta;
}


/* =========================================================
   TENANT
========================================================= */

function obterTenantPelaUrl() {
    const parametros = new URLSearchParams(
        window.location.search
    );

    /*
      "tenant" será o padrão oficial.
      "b" continua funcionando temporariamente para preservar
      compatibilidade com links antigos.
    */
    return (
        parametros.get("tenant")
        || parametros.get("b")
        || ""
    );
}


/* =========================================================
   CARREGAMENTO INICIAL
========================================================= */

function alternarMenuPublico() {
    const menu = document.getElementById("etapas-agendamento");

    if (!menu) {
        return;
    }

    menu.classList.toggle("aberto");
}


function mostrarEtapaPublica(etapaId) {
    const secoes = document.querySelectorAll(".secao-agendamento");
    const botoes = document.querySelectorAll(".etapa-agendamento");

    secoes.forEach((secao) => {
        secao.classList.toggle(
            "ativa",
            secao.id === etapaId
        );
    });

    botoes.forEach((botao) => {
        botao.classList.toggle(
            "ativa",
            botao.dataset.etapa === etapaId
        );
    });

    const menu = document.getElementById("etapas-agendamento");

    if (menu) {
        menu.classList.remove("aberto");
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });
}


function inicializarNavegacaoPublica() {
    const botoes = document.querySelectorAll(".etapa-agendamento");

    botoes.forEach((botao) => {
        botao.addEventListener("click", () => {
            mostrarEtapaPublica(botao.dataset.etapa);
        });
    });

    mostrarEtapaPublica("etapa-servico");
}


window.alternarMenuPublico = alternarMenuPublico;
window.mostrarEtapaPublica = mostrarEtapaPublica;


async function iniciarAplicativo() {
    tenantSlug = obterTenantPelaUrl();

    function configurarLinkMeusAgendamentos() {
        const link = document.getElementById("link-meus-agendamentos");
    
        if (!link || !tenantSlug) {
            return;
        }
    
        link.href = `./meus-agendamentos.html?tenant=${tenantSlug}`;
    }

    if (!tenantSlug) {
        exibirMensagem(
            "Link de agendamento inválido. Solicite um novo link ao estabelecimento.",
            "erro"
        );

        document.getElementById("btn-agendar").disabled = true;

        return;
    }

    const inputData = document.getElementById("input-data");

    inputData.min = obterDataLocalFormatada();

    inputData.addEventListener(
        "change",
        buscarHorariosLivres
    );

    document
        .getElementById("btn-agendar")
        .addEventListener(
            "click",
            confirmarAgendamento
        );

    try {
        await Promise.all([
            carregarConfiguracoes(),
            carregarServicos(),
            carregarProfissionais()
        ]);

    } catch (erro) {
        console.error(erro);

        exibirMensagem(
            erro.message
            || "Não foi possível carregar a agenda. Tente novamente mais tarde.",
            "erro"
        );
    }

    configurarLinkMeusAgendamentos();
    inicializarNavegacaoPublica();
    atualizarBotaoFinalizar();
}


/* =========================================================
   CONFIGURAÇÕES VISUAIS
========================================================= */

async function carregarConfiguracoes() {
    const config = await apiRequest(
        `/api/${encodeURIComponent(tenantSlug)}/configuracoes`
    );

    if (
        config.empresa_desativada === true
        || config.status_assinatura === "desativada"
        || config.acesso_liberado === false
        || config.acesso_ativo === false
    ) {
        mostrarAvisoAssinaturaInativa(
            "O acesso deste estabelecimento está bloqueado manualmente pela administração da plataforma."
        );

        const formulario = document.getElementById("form-agendamento");

        if (formulario) {
            formulario.style.display = "none";
        }

        return;
    }

    const nomePublico =
        config.nome_publico
        || tenantSlug.replaceAll("-", " ");

    document.getElementById("nome-loja").innerText =
        nomePublico;

    document.title = `Agendamento — ${nomePublico}`;

    const telefone =
        config.whatsapp_comercial
        || config.telefone
        || "";

    if (telefone) {
        document
            .getElementById("telefone-loja")
            .innerText = `WhatsApp: ${telefone}`;
    }

    const enderecoEl = document.getElementById("endereco-loja");

    if (config.endereco) {
        enderecoEl.innerText = config.endereco;
    } else {
        enderecoEl.innerText = "";
    }

    if (config.cor_tema) {
        document.documentElement.style.setProperty(
            "--destaque",
            config.cor_tema
        );
    }

    if (config.cor_fundo) {
        document.documentElement.style.setProperty(
            "--bg-principal",
            config.cor_fundo
        );
    }

    const tituloPublicoEmpresa = document.getElementById(
        "titulo-publico-empresa"
    );
    
    const subtituloPublicoEmpresa = document.getElementById(
        "subtitulo-publico-empresa"
    );
    
    if (tituloPublicoEmpresa) {
        tituloPublicoEmpresa.innerText = config.nome
            ? `Agende seu horário na ${config.nome}`
            : "Agende seu horário em poucos cliques";
    }
    
    if (subtituloPublicoEmpresa) {
        subtituloPublicoEmpresa.innerText = config.descricao
            || "Escolha o serviço, profissional, data e horário disponível. A confirmação é rápida e simples.";
    }

    const logoBox = document.getElementById("logo-loja");

    if (config.logo_url) {
        logoBox.innerHTML = `
            <img src="${config.logo_url}" alt="Logo de ${nomePublico}">
        `;
    } else {
        logoBox.textContent = "Logo";
    }

    const banner = document.getElementById("banner-loja");

    if (config.logomarca_url) {
        banner.style.backgroundImage = `
            linear-gradient(135deg, rgba(15,23,42,0.25), rgba(15,23,42,0.85)),
            url("${config.logomarca_url}")
        `;
    }

    const mensagemPublica = document.getElementById("mensagem-publica");

    if (config.mensagem_publica) {
        mensagemPublica.innerText = config.mensagem_publica;
        mensagemPublica.style.display = "block";
    } else if (config.instrucoes) {
        mensagemPublica.innerText = config.instrucoes;
        mensagemPublica.style.display = "block";
    } else {
        mensagemPublica.style.display = "none";
    }

    renderizarLinksMarca(config, telefone);

    configurarConsentimentos(config);
}

function normalizarUrl(url) {
    const valor = String(url || "").trim();

    if (!valor) {
        return "";
    }

    if (
        valor.startsWith("http://")
        || valor.startsWith("https://")
    ) {
        return valor;
    }

    return `https://${valor}`;
}


function normalizarInstagram(valor) {
    const texto = String(valor || "").trim();

    if (!texto) {
        return "";
    }

    if (texto.startsWith("@")) {
        return `https://instagram.com/${texto.slice(1)}`;
    }

    if (!texto.includes(".")) {
        return `https://instagram.com/${texto}`;
    }

    return normalizarUrl(texto);
}


function normalizarFacebook(valor) {
    const texto = String(valor || "").trim();

    if (!texto) {
        return "";
    }

    if (!texto.includes(".") && !texto.startsWith("http")) {
        return `https://facebook.com/${texto}`;
    }

    return normalizarUrl(texto);
}


function normalizarTikTok(valor) {
    const texto = String(valor || "").trim();

    if (!texto) {
        return "";
    }

    if (texto.startsWith("@")) {
        return `https://www.tiktok.com/${texto}`;
    }

    if (!texto.includes(".") && !texto.startsWith("http")) {
        return `https://www.tiktok.com/@${texto}`;
    }

    return normalizarUrl(texto);
}


function montarUrlWhatsApp(telefone) {
    const numeroLimpo = String(telefone || "").replace(/\D/g, "");

    if (!numeroLimpo) {
        return "";
    }

    if (numeroLimpo.startsWith("55")) {
        return `https://wa.me/${numeroLimpo}`;
    }

    return `https://wa.me/55${numeroLimpo}`;
}


function renderizarLinksMarca(config, telefone) {
    const container = document.getElementById("links-marca");

    container.innerHTML = "";

    const links = [];

    const whatsappUrl = montarUrlWhatsApp(telefone);

    if (whatsappUrl) {
        links.push({
            texto: "WhatsApp",
            icone: "💬",
            url: whatsappUrl,
        });
    }

    if (config.google_maps_url) {
        links.push({
            texto: "Como chegar",
            icone: "📍",
            url: normalizarUrl(config.google_maps_url),
        });
    }

    if (config.instagram_url) {
        links.push({
            texto: "Instagram",
            icone: "📸",
            url: normalizarInstagram(config.instagram_url),
        });
    }

    if (config.facebook_url) {
        links.push({
            texto: "Facebook",
            icone: "f",
            url: normalizarFacebook(config.facebook_url),
        });
    }

    if (config.tiktok_url) {
        links.push({
            texto: "TikTok",
            icone: "♪",
            url: normalizarTikTok(config.tiktok_url),
        });
    }

    if (config.site_url) {
        links.push({
            texto: "Site",
            icone: "🌐",
            url: normalizarUrl(config.site_url),
        });
    }

    for (const link of links) {
        const a = document.createElement("a");

        a.href = link.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";

        a.innerHTML = `
            <span class="link-icone">${link.icone}</span>
            <span>${link.texto}</span>
        `;

        container.appendChild(a);
    }
}


function configurarConsentimentos(config) {
    const boxLembrete = document.getElementById(
        "box-lembrete-whatsapp"
    );

    const boxPromocoes = document.getElementById(
        "box-promocoes-whatsapp"
    );

    const inputLembrete = document.getElementById(
        "aceita-lembrete-whatsapp"
    );

    const inputPromocoes = document.getElementById(
        "aceita-promocoes-whatsapp"
    );

    if (config.captar_whatsapp_lembretes) {
        boxLembrete.style.display = "flex";
        inputLembrete.checked = true;
    } else {
        boxLembrete.style.display = "none";
        inputLembrete.checked = false;
    }

    if (config.captar_whatsapp_promocoes) {
        boxPromocoes.style.display = "flex";
    } else {
        boxPromocoes.style.display = "none";
        inputPromocoes.checked = false;
    }
}


function checkboxMarcado(id) {
    const elemento = document.getElementById(id);

    return Boolean(elemento && elemento.checked);
}


/* =========================================================
   SERVIÇOS
========================================================= */

async function carregarServicos() {
    const servicos = await apiRequest(
        `/api/${encodeURIComponent(tenantSlug)}/servicos`
    );

    const container = document.getElementById("lista-servicos");

    container.innerHTML = "";

    if (!servicos.length) {
        container.innerText = "Nenhum serviço disponível.";
        return;
    }

    for (const servico of servicos) {
        const botao = document.createElement("button");

        botao.type = "button";
        botao.className = "btn-opcao";

        const nome = document.createElement("span");
        nome.innerText = servico.nome;

        const preco = document.createElement("strong");
        preco.innerText = formatarMoeda(servico.preco);

        botao.append(nome, preco);

        botao.addEventListener(
            "click",
            () => selecionarServico(
                botao,
                servico
            )
        );

        container.appendChild(botao);
    }
}


function selecionarServico(botaoSelecionado, servico) {
    document
        .querySelectorAll("#lista-servicos .btn-opcao")
        .forEach(
            botao => botao.classList.remove("selecionado")
        );

    botaoSelecionado.classList.add("selecionado");

    reserva.servico = servico;
    reserva.horario = "";

    buscarHorariosLivres();
    atualizarBotaoFinalizar();
    mostrarEtapaPublica("etapa-profissional");
}


/* =========================================================
   PROFISSIONAIS
========================================================= */

async function carregarProfissionais() {
    const profissionais = await apiRequest(
        `/api/${encodeURIComponent(tenantSlug)}/profissionais`
    );

    const container = document.getElementById(
        "lista-profissionais"
    );

    container.innerHTML = "";

    if (!profissionais.length) {
        container.innerText = "Nenhum profissional disponível.";
        return;
    }

    for (const profissional of profissionais) {
        const botao = document.createElement("button");

        botao.type = "button";
        botao.className = "btn-opcao";
        botao.innerText = profissional.nome;

        botao.addEventListener(
            "click",
            () => selecionarProfissional(
                botao,
                profissional
            )
        );

        container.appendChild(botao);
    }
}


function selecionarProfissional(
    botaoSelecionado,
    profissional
) {
    document
        .querySelectorAll(
            "#lista-profissionais .btn-opcao"
        )
        .forEach(
            botao => botao.classList.remove("selecionado")
        );

    botaoSelecionado.classList.add("selecionado");

    reserva.profissional = profissional;
    reserva.horario = "";

    buscarHorariosLivres();
    atualizarBotaoFinalizar();
    mostrarEtapaPublica("etapa-horario");
}


/* =========================================================
   HORÁRIOS
========================================================= */


function erroEhAssinaturaInativa(erro) {
    const detalhe = obterDetalheErroApi(erro);

    if (erro && Number(erro.status) === 402) {
        return true;
    }

    if (
        detalhe
        && typeof detalhe === "object"
        && detalhe.codigo === "ASSINATURA_INATIVA"
    ) {
        return true;
    }

    const mensagem = String(
        erro?.message
        || erro?.detail
        || ""
    ).toLowerCase();

    return (
        mensagem.includes("assinatura")
        || mensagem.includes("payment required")
    );
}


function mostrarAvisoAssinaturaInativa(mensagemPersonalizada = null) {
    assinaturaTenantInativa = true;

    const aviso = document.getElementById("aviso-assinatura-inativa");

    if (aviso) {
        const paragrafo = aviso.querySelector("p");

        if (paragrafo && mensagemPersonalizada) {
            paragrafo.textContent = mensagemPersonalizada;
        }

        aviso.style.display = "block";
    }

    const etapaHorario = document.getElementById("etapa-horario");
    const etapaDados = document.getElementById("etapa-dados");

    if (etapaHorario) {
        etapaHorario.classList.add("formulario-bloqueado");
    }

    if (etapaDados) {
        etapaDados.classList.add("formulario-bloqueado");
    }

    const listaHorarios = document.getElementById("lista-horarios");

    if (listaHorarios) {
        listaHorarios.innerHTML = `
        <p class="horarios-vazios">
            Agenda temporariamente indisponível para novos agendamentos.
        </p>
    `;
    }
}


function ocultarAvisoAssinaturaInativa() {
    assinaturaTenantInativa = false;

    const aviso = document.getElementById("aviso-assinatura-inativa");

    if (aviso) {
        aviso.style.display = "none";
    }

    const etapaHorario = document.getElementById("etapa-horario");
    const etapaDados = document.getElementById("etapa-dados");

    if (etapaHorario) {
        etapaHorario.classList.remove("formulario-bloqueado");
    }

    if (etapaDados) {
        etapaDados.classList.remove("formulario-bloqueado");
    }
}

async function buscarHorariosLivres() {
    reserva.data = document
        .getElementById("input-data")
        .value;

        if (
            reserva.data
            && !/^\d{4}-\d{2}-\d{2}$/.test(reserva.data)
        ) {
            exibirMensagem(
                "Informe uma data válida.",
                "erro"
            );
        
            return;
        }
        
        if (
            reserva.data
            && reserva.data < obterDataLocalFormatada()
        ) {
            exibirMensagem(
                "Não é possível agendar para uma data passada.",
                "erro"
            );
        
            return;
        }

    reserva.horario = "";

    atualizarBotaoFinalizar();

    const container = document.getElementById(
        "lista-horarios"
    );



    container.innerHTML = "";

    if (
        !reserva.servico
        || !reserva.profissional
        || !reserva.data
    ) {
        return;
    }

    const identificadorBuscaAtual =
        ++identificadorUltimaBusca;

    document
        .getElementById("msg-horarios")
        .style
        .display = "block";

        try {
            ocultarAvisoAssinaturaInativa();
    
            const url =
                `/api/${encodeURIComponent(tenantSlug)}`
                + `/horarios/${encodeURIComponent(reserva.data)}`
                + `/${encodeURIComponent(reserva.servico.duracao)}`
                + `/${encodeURIComponent(reserva.profissional.nome)}`;
    
            const dados = await apiRequest(url);

        /*
          Se o usuário alterar rapidamente serviço ou profissional,
          ignoramos respostas antigas que chegarem atrasadas.
        */
        if (
            identificadorBuscaAtual
            !== identificadorUltimaBusca
        ) {
            return;
        }

        if (!dados.horarios_disponiveis.length) {
            container.innerHTML = `
                <p class="horarios-vazios">
                    Nenhum horário livre para esta seleção.
                </p>
            `;

            return;
        }

        for (
            const horario
            of dados.horarios_disponiveis
        ) {
            const botao = document.createElement("button");

            botao.type = "button";
            botao.className = "btn-horario";
            botao.innerText = horario;

            botao.addEventListener(
                "click",
                () => selecionarHorario(
                    botao,
                    horario
                )
            );

            container.appendChild(botao);
        }

    }      catch (erro) {
        if (erroEhAssinaturaInativa(erro)) {
            const detalhe = obterDetalheErroApi(erro);

            mostrarAvisoAssinaturaInativa(
                typeof detalhe === "string"
                    ? detalhe
                    : detalhe?.mensagem
                        || "No momento, este estabelecimento não está recebendo novos agendamentos online."
            );

            return;
        }

        exibirMensagem(
            erro.message
            || "Não foi possível carregar os horários disponíveis.",
            "erro"
            );
            
    } finally {
        if (
            identificadorBuscaAtual
            === identificadorUltimaBusca
        ) {
            document
                .getElementById("msg-horarios")
                .style
                .display = "none";
        }
    }
}


        function selecionarHorario(
            botaoSelecionado,
            horario
        ) {
            document
                .querySelectorAll(".btn-horario")
                .forEach(
                    botao => botao.classList.remove("selecionado")
                );

            botaoSelecionado.classList.add("selecionado");

            reserva.horario = horario;

            atualizarBotaoFinalizar();
            mostrarEtapaPublica("etapa-dados");
        }


/* =========================================================
   CONFIRMAÇÃO
========================================================= */

function resetarFluxoAgendamento() {
    reserva.servico = null;
    reserva.profissional = null;
    reserva.data = "";
    reserva.horario = "";

    document
        .querySelectorAll(
            ".selecionado, .ativo"
        )
        .forEach((elemento) => {
            elemento.classList.remove("selecionado");
            elemento.classList.remove("ativo");
        });

    const campoNome = document
        .getElementById("cliente-nome");

    const campoTelefone = document
        .getElementById("cliente-telefone");

    const campoData = document
        .getElementById("input-data");

    if (campoNome) {
        campoNome.value = "";
    }

    if (campoTelefone) {
        campoTelefone.value = "";
    }

    if (campoData) {
        campoData.value = "";
    }

    const listaHorarios = document
        .getElementById("lista-horarios");

    if (listaHorarios) {
        listaHorarios.innerHTML = `
            <p class="horarios-vazios">
                Selecione um serviço, um profissional e uma data para ver os horários disponíveis.
            </p>
        `;
    }

    atualizarBotaoFinalizar();
}


async function confirmarAgendamento() {
    limparMensagem();

    if (assinaturaTenantInativa) {
        mostrarAvisoAssinaturaInativa(
            "A agenda deste estabelecimento está temporariamente indisponível para novos agendamentos."
        );

        return;
    }

    const clienteNome = document
        .getElementById("cliente-nome")
        .value
        .trim();

    const telefoneCliente = document
        .getElementById("cliente-telefone")
        .value
        .trim();

    if (
        !reserva.servico
        || !reserva.profissional
        || !reserva.data
        || !reserva.horario
    ) {
        exibirMensagem(
            "Selecione serviço, profissional, data e horário.",
            "erro"
        );

        return;
    }

    if (
        !clienteNome
        || telefoneCliente.length < 8
    ) {
        exibirMensagem(
            "Informe seu nome e um telefone válido.",
            "erro"
        );

        return;
    }

    const botao = document.getElementById("btn-agendar");

    botao.disabled = true;
    botao.innerText = "Confirmando...";

    try {
        const dados = await apiRequest(
            `/api/${encodeURIComponent(tenantSlug)}/agendar`,
            {
                method: "POST",
                body: {
                    cliente_nome: clienteNome,
                    servico: reserva.servico.nome,
                    data: reserva.data,
                    horario: reserva.horario,
                    valor: reserva.servico.preco,
                    profissional: reserva.profissional.nome,
                    telefone_cliente: telefoneCliente,
                    aceita_lembrete_whatsapp: checkboxMarcado(
                        "aceita-lembrete-whatsapp"
                    ),
                    aceita_promocoes_whatsapp: checkboxMarcado(
                        "aceita-promocoes-whatsapp"
                    )
                }
            }
        );


        exibirMensagem(
            `Agendamento confirmado para ${dados.data} às ${dados.horario}.`,
            "sucesso"
        );

        resetarFluxoAgendamento();

        setTimeout(() => {
            limparMensagem();
        }, 4000);

        await buscarHorariosLivres();

    } catch (erro) {
        console.error(erro);

        if (erroEhAssinaturaInativa(erro)) {
            const detalhe = obterDetalheErroApi(erro);

            mostrarAvisoAssinaturaInativa(
                typeof detalhe === "string"
                    ? detalhe
                    : detalhe?.mensagem
                        || "A agenda deste estabelecimento está temporariamente indisponível para novos agendamentos."
            );

            return;
        }

        if (erro.status === 402) {
            alert(
                erro.message
                || "A agenda desta empresa está temporariamente indisponível."
            );
        
            return;
        }

        if (erro.status === 409) {
            exibirMensagem(
                "Este horário acabou de ficar indisponível. Escolha outro horário.",
                "erro"
            );

            return;
        }

        exibirMensagem(
            erro.message
            || "Não foi possível confirmar o agendamento.",
            "erro"
        );

    } finally {
        botao.innerText = "Confirmar Agendamento";

        atualizarBotaoFinalizar();
    }
}


window.addEventListener(
    "DOMContentLoaded",
    iniciarAplicativo
);
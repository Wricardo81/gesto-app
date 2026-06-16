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


async function carregarClientes() {
    const tbody = document
        .getElementById("lista-clientes");

    tbody.innerHTML = "";

    try {
        const clientes = await saasRequest(
            "/api/saas/barbearias"
        );

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
            const tr =
                document.createElement("tr");

            tr.appendChild(
                criarCelula(`#${cliente.id}`)
            );

            const tdEmpresa =
                document.createElement("td");

            const nome =
                document.createElement("strong");

            nome.textContent = cliente.nome;

            const email =
                document.createElement("small");

            email.textContent =
                cliente.email || "";

            const link =
                document.createElement("small");

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

            tr.appendChild(
                criarCelula(cliente.slug)
            );

            const tdStatus =
                document.createElement("td");

            const badge =
                document.createElement("span");

            badge.className =
                `status-badge ${
                    cliente.plano_ativo
                        ? "status-ativo"
                        : "status-bloqueado"
                }`;

            badge.textContent =
                cliente.plano_ativo
                    ? "Pagamento em dia"
                    : "Acesso bloqueado";

            tdStatus.appendChild(badge);
            tr.appendChild(tdStatus);

            const tdAcao =
                document.createElement("td");

            const botao =
                document.createElement("button");

            botao.type = "button";
            botao.className = "btn-acao";

            botao.textContent =
                cliente.plano_ativo
                    ? "Bloquear acesso"
                    : "Desbloquear";

            botao.addEventListener(
                "click",
                () => alterarStatus(
                    cliente.id
                )
            );

            tdAcao.appendChild(botao);
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

        alert(
            "Empresa criada com sucesso."
        );

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

    document
        .getElementById("btn-sair-saas")
        .addEventListener(
            "click",
            fazerLogoutSaas
        );

    if (!obterTokenSaas()) {
        exibirLoginSaas();
        return;
    }

    exibirPainelSaas();

    await carregarClientes();
}


window.addEventListener(
    "DOMContentLoaded",
    iniciarPainelSaas
);
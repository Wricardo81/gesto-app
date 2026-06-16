function salvarSessao({ access_token, tenant_slug }) {
    localStorage.setItem("gesto_token", access_token);
    localStorage.setItem("gesto_tenant", tenant_slug);
}

function obterToken() {
    return localStorage.getItem("gesto_token");
}

function obterTenantLogado() {
    return localStorage.getItem("gesto_tenant");
}

function existeSessaoLocal() {
    return Boolean(
        obterToken()
        && obterTenantLogado()
    );
}

function limparSessao() {
    localStorage.removeItem("gesto_token");
    localStorage.removeItem("gesto_tenant");
}

async function autenticar(email, senha) {
    const dados = await apiRequest(
        "/api/auth/login",
        {
            method: "POST",
            body: {
                email,
                senha
            }
        }
    );

    salvarSessao(dados);

    return dados;
}

function fazerLogout() {
    limparSessao();
    window.location.reload();
}
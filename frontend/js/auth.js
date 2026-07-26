function salvarSessao(dados) {
    localStorage.removeItem("gesto_token");
    localStorage.removeItem("gesto_tenant");
    localStorage.removeItem("gesto_saas_token");
    sessionStorage.removeItem("bitsagenda_ultimo_request_id_erro");

    if (dados.access_token) {
        localStorage.setItem("gesto_token", dados.access_token);
    }

    if (dados.tenant_slug) {
        localStorage.setItem("gesto_tenant", dados.tenant_slug);
    }
}

function obterToken() {
  return localStorage.getItem("gesto_token");
}

function obterTenantLogado() {
  return localStorage.getItem("gesto_tenant");
}

function existeSessaoLocal() {
  return Boolean(obterToken() && obterTenantLogado());
}

function limparSessao() {
  localStorage.removeItem("gesto_token");
  localStorage.removeItem("gesto_tenant");
}

async function autenticar(email, senha) {
    localStorage.removeItem("gesto_token");
    localStorage.removeItem("gesto_tenant");
    localStorage.removeItem("gesto_saas_token");
    sessionStorage.removeItem("bitsagenda_ultimo_request_id_erro");

    const resposta = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email,
            senha,
        }),
    });

    const dados = await resposta.json();

    if (!resposta.ok) {
        throw new Error(dados.detail || "Erro ao fazer login.");
    }

    salvarSessao(dados);

    return dados;
}

function fazerLogout() {
  localStorage.removeItem("gesto_token");
  localStorage.removeItem("gesto_tenant");
  localStorage.removeItem("gesto_saas_token");
  localStorage.removeItem("gesto_admin_secao_ativa");
  sessionStorage.removeItem("bitsagenda_ultimo_request_id_erro");

  window.location.href = "./admin.html";
}

function salvarSessao({ access_token, tenant_slug }) {
  localStorage.removeItem("gesto_token");
  localStorage.removeItem("gesto_tenant");
  localStorage.removeItem("gesto_saas_token");

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
  localStorage.removeItem("gesto_admin_secao_ativa");

  sessionStorage.removeItem("bitsagenda_ultimo_request_id_erro");
  const dados = await apiRequest("/api/auth/login", {
    method: "POST",
    body: {
      email,
      senha,
    },
  });

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

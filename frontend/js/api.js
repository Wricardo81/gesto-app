const API_BASE_URL =
  window.GESTO_CONFIG?.API_BASE_URL || "http://127.0.0.1:8000";

function gerarRequestId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }

  return `bitsagenda-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function obterUltimoRequestIdErro() {
  return sessionStorage.getItem("bitsagenda_ultimo_request_id_erro");
}

function salvarUltimoRequestIdErro(requestId) {
  if (!requestId) {
    return;
  }

  sessionStorage.setItem("bitsagenda_ultimo_request_id_erro", requestId);
}

async function apiRequest(
  endpoint,
  {
    method = "GET",
    body = null,
    auth = false,
    tokenStorageKey = "gesto_token",
    headers = {},
  } = {},
) {
  const requestId = headers["X-Request-ID"] || gerarRequestId();

  const finalHeaders = {
    ...headers,
    "X-Request-ID": requestId,
  };

  if (body !== null) {
    finalHeaders["Content-Type"] = "application/json";
  }

  if (auth) {
    const token = localStorage.getItem(tokenStorageKey);

    if (!token) {
      const erro = new Error("Sessão expirada. Faça login novamente.");

      erro.status = 401;
      erro.requestId = requestId;

      salvarUltimoRequestIdErro(requestId);

      throw erro;
    }

    finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  let resposta = null;

  try {
    resposta = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers: finalHeaders,
      body: body !== null ? JSON.stringify(body) : null,
    });
  } catch (erroRede) {
    const erro = new Error("Sem conexão com o servidor no momento.");

    erro.status = 0;
    erro.requestId = requestId;
    erro.data = {
      offline: true,
      originalError: erroRede?.message || null,
    };

    salvarUltimoRequestIdErro(requestId);

    throw erro;
  }

  const responseRequestId = resposta.headers.get("X-Request-ID") || requestId;

  const contentType = resposta.headers.get("content-type") || "";

  let dados = null;

  if (contentType.includes("application/json")) {
    dados = await resposta.json();
  } else {
    const texto = await resposta.text();
    dados = texto || null;
  }

  if (!resposta.ok) {
    const mensagem =
      dados?.detail ||
      dados?.message ||
      dados ||
      "Erro ao se comunicar com a API.";

    const erro = new Error(mensagem);

    erro.status = resposta.status;
    erro.data = dados;
    erro.requestId = responseRequestId;

    salvarUltimoRequestIdErro(responseRequestId);

    throw erro;
  }

  return dados;
}

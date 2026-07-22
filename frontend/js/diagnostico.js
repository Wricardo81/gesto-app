function obterRequestIdDoErro(erro) {
  return (
    erro?.requestId ||
    sessionStorage.getItem("bitsagenda_ultimo_request_id_erro") ||
    null
  );
}

function montarMensagemErroComDiagnostico(mensagem, erro = null) {
  const requestId = obterRequestIdDoErro(erro);

  if (!requestId) {
    return mensagem;
  }

  return `${mensagem}\n\nCódigo do erro: ${requestId}`;
}

async function copiarTextoDiagnostico(texto) {
  if (!texto) {
    return false;
  }

  try {
    await navigator.clipboard.writeText(texto);
    return true;
  } catch (erro) {
    console.warn("Não foi possível copiar diagnóstico:", erro);
    return false;
  }
}

function exibirDiagnosticoErro(containerId, erro, mensagemPadrao) {
  const container = document.getElementById(containerId);

  if (!container) {
    return;
  }

  const requestId = obterRequestIdDoErro(erro);
  const mensagem =
    erro?.message || mensagemPadrao || "Ocorreu um erro inesperado.";

  container.innerHTML = "";

  const caixa = document.createElement("div");
  caixa.className = "diagnostico-erro-card";

  const titulo = document.createElement("strong");
  titulo.textContent = mensagem;

  caixa.appendChild(titulo);

  if (requestId) {
    const codigo = document.createElement("code");
    codigo.textContent = `Código do erro: ${requestId}`;

    const botao = document.createElement("button");
    botao.type = "button";
    botao.textContent = "Copiar código";
    botao.addEventListener("click", async function () {
      const copiado = await copiarTextoDiagnostico(requestId);
      botao.textContent = copiado
        ? "Código copiado"
        : "Não foi possível copiar";

      setTimeout(function () {
        botao.textContent = "Copiar código";
      }, 2200);
    });

    caixa.appendChild(codigo);
    caixa.appendChild(botao);
  }

  container.appendChild(caixa);
}

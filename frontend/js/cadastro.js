(function () {
  const form = document.getElementById("form-cadastro-publico");
  const mensagem = document.getElementById("mensagem-cadastro-publico");
  const botao = document.getElementById("btn-cadastro-publico");

  if (!form) {
    return;
  }

  function valorCampo(id) {
    return document.getElementById(id)?.value?.trim() || "";
  }

  function exibirMensagemCadastro(texto, tipo = "erro") {
    if (!mensagem) {
      return;
    }

    mensagem.textContent = texto;
    mensagem.className = `cadastro-publico-mensagem ${tipo}`;
    mensagem.style.display = "block";
  }

  form.addEventListener("submit", async function (evento) {
    evento.preventDefault();

    const payload = {
      nome: valorCampo("cadastro-nome"),
      responsavel: valorCampo("cadastro-responsavel"),
      email: valorCampo("cadastro-email"),
      telefone: valorCampo("cadastro-telefone"),
      senha: valorCampo("cadastro-senha"),
      tipo_negocio: valorCampo("cadastro-tipo-negocio") || null,
    };

    if (
      !payload.nome ||
      !payload.responsavel ||
      !payload.email ||
      !payload.telefone ||
      !payload.senha
    ) {
      exibirMensagemCadastro("Preencha todos os campos obrigatórios.");
      return;
    }

    if (payload.senha.length < 6) {
      exibirMensagemCadastro("A senha precisa ter pelo menos 6 caracteres.");
      return;
    }

    if (botao) {
      botao.disabled = true;
      botao.textContent = "Criando sua conta...";
    }

    try {
      const resposta = await apiRequest("/api/saas/public/cadastro", {
        method: "POST",
        body: payload,
      });

      localStorage.setItem("gesto_token", resposta.access_token);
      localStorage.setItem("gesto_tenant", resposta.tenant_slug);

      exibirMensagemCadastro(
        "Conta criada com sucesso. Redirecionando para o painel...",
        "sucesso",
      );

      setTimeout(function () {
        window.location.href = `./admin.html?tenant=${encodeURIComponent(resposta.tenant_slug)}`;
      }, 900);
    } catch (erro) {
      console.error("Erro no cadastro público:", erro);

      exibirMensagemCadastro(
        montarMensagemErroComDiagnostico(
          erro.message || "Não foi possível criar sua conta.",
          erro,
        ),
        "erro",
      );
    } finally {
      if (botao) {
        botao.disabled = false;
        botao.textContent = "Criar minha conta grátis";
      }
    }
  });
})();

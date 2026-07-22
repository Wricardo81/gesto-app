(function () {
  const form = document.getElementById("form-cadastro-publico");
  const mensagem = document.getElementById("mensagem-cadastro-publico");
    const botao = document.getElementById("btn-cadastro-publico");
    const campoPlano = document.getElementById("cadastro-plano-codigo");
    const textoPlano = document.getElementById("cadastro-plano-selecionado");

  if (!form) {
    return;
    }

    function obterPlanoDaUrl() {
      const parametros = new URLSearchParams(window.location.search);
      const plano = parametros.get("plano") || "teste";

      const planosPermitidos = ["teste", "mensal", "trimestral", "anual"];

      if (!planosPermitidos.includes(plano)) {
        return "teste";
      }

      return plano;
    }

    function nomePlano(plano) {
      const nomes = {
        teste: "Teste grátis",
        mensal: "Plano mensal",
        trimestral: "Plano trimestral",
        anual: "Plano anual",
      };

      return nomes[plano] || "Teste grátis";
    }

    function aplicarPlanoSelecionado() {
      const plano = obterPlanoDaUrl();

      if (campoPlano) {
        campoPlano.value = plano;
      }

      if (textoPlano) {
        textoPlano.textContent = `Plano selecionado: ${nomePlano(plano)}`;
      }

      if (botao) {
        botao.textContent =
          plano === "teste"
            ? "Criar minha conta grátis"
            : `Criar conta e continuar com ${nomePlano(plano)}`;
      }
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

    function planoEhPago(plano) {
      return ["mensal", "trimestral", "anual"].includes(plano);
    }

    async function iniciarCheckoutAposCadastro(respostaCadastro) {
      const plano = respostaCadastro?.plano_codigo || "teste";
      const tenantSlug = respostaCadastro?.tenant_slug;
      const empresaId = respostaCadastro?.empresa_id;

      if (!planoEhPago(plano)) {
        window.location.href = `./admin.html?tenant=${encodeURIComponent(tenantSlug)}`;

        return;
      }

      if (!tenantSlug || !empresaId) {
        window.location.href = `./admin.html?tenant=${encodeURIComponent(tenantSlug)}&pagamento=pendente`;

        return;
      }

      const respostaCheckout = await apiRequest(
        `/api/${tenantSlug}/admin/assinaturas/stripe/checkout`,
        {
          method: "POST",
          auth: true,
          body: {
            barbearia_id: empresaId,
            plano_codigo: plano,
          },
        },
      );

      if (!respostaCheckout?.checkout_url) {
        window.location.href = `./admin.html?tenant=${encodeURIComponent(tenantSlug)}&pagamento=pendente`;

        return;
      }

      window.location.href = respostaCheckout.checkout_url;
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
      plano_codigo: valorCampo("cadastro-plano-codigo") || "teste",
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
        planoEhPago(resposta.plano_codigo)
          ? "Conta criada com sucesso. Abrindo pagamento seguro..."
          : "Conta criada com sucesso. Redirecionando para o painel...",
        "sucesso",
      );

      setTimeout(async function () {
        try {
          await iniciarCheckoutAposCadastro(resposta);
        } catch (erroCheckout) {
          console.error(
            "Erro ao iniciar checkout após cadastro:",
            erroCheckout,
          );

          exibirMensagemCadastro(
            montarMensagemErroComDiagnostico(
              "Conta criada, mas não foi possível abrir o pagamento. Você será redirecionado para o painel.",
              erroCheckout,
            ),
            "erro",
          );

          setTimeout(function () {
            window.location.href = `./admin.html?tenant=${encodeURIComponent(resposta.tenant_slug)}&pagamento=pendente`;
          }, 1800);
        }
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
        const plano = valorCampo("cadastro-plano-codigo") || "teste";

        botao.disabled = false;
        botao.textContent =
          plano === "teste"
            ? "Criar minha conta grátis"
            : `Criar conta e continuar com ${nomePlano(plano)}`;
      }
    }
  });
})();

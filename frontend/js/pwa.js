(function () {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  function atualizarBotoesInstalacaoPwa(disponivel) {
    const botoes = document.querySelectorAll("[data-pwa-install]");

    botoes.forEach(function (botao) {
      botao.style.display = disponivel ? "inline-flex" : "none";
      botao.disabled = !disponivel;
    });
  }

  async function registrarServiceWorker() {
    try {
      const registro = await navigator.serviceWorker.register(
        "./service-worker.js",
      );

      console.info("PWA registrado:", registro.scope);
    } catch (erro) {
      console.warn("Não foi possível registrar o PWA:", erro);
    }
  }

  window.addEventListener("load", function () {
    registrarServiceWorker();

    atualizarBotoesInstalacaoPwa(Boolean(window.bitsAgendaInstallPrompt));
  });

  window.addEventListener("beforeinstallprompt", function (evento) {
    evento.preventDefault();

    console.info("PWA instalação disponível.");

    window.bitsAgendaInstallPrompt = evento;

    atualizarBotoesInstalacaoPwa(true);

    document.dispatchEvent(
      new CustomEvent("bitsagenda:pwa-instalacao-disponivel"),
    );
  });

  window.addEventListener("appinstalled", function () {
    console.info("BitsAgenda OS instalado como app.");

    window.bitsAgendaInstallPrompt = null;

    atualizarBotoesInstalacaoPwa(false);
  });

  window.instalarBitsAgenda = async function () {
    const promptInstalacao = window.bitsAgendaInstallPrompt;

    if (!promptInstalacao) {
      return {
        disponivel: false,
        mensagem:
          "Instalação ainda não disponível neste navegador. No celular, toque nos três pontinhos e escolha Instalar app.",
      };
    }

    promptInstalacao.prompt();

    const escolha = await promptInstalacao.userChoice;

    window.bitsAgendaInstallPrompt = null;

    atualizarBotoesInstalacaoPwa(false);

    return {
      disponivel: true,
      resultado: escolha.outcome,
    };
  };

  window.instalarGestoApp = window.instalarBitsAgenda;

  window.addEventListener("click", async function (evento) {
    const botao = evento.target.closest("[data-pwa-install]");

    if (!botao) {
      return;
    }

    evento.preventDefault();

    const resultado = await window.instalarBitsAgenda();

    if (!resultado.disponivel) {
      alert(resultado.mensagem);
    }
  });
})();

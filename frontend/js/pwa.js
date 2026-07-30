(function () {
  if (!("serviceWorker" in navigator)) {
    return;
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

    window.addEventListener("load", registrarServiceWorker);
    

  window.addEventListener("beforeinstallprompt", function (evento) {
    evento.preventDefault();

    console.info("PWA instalação disponível.");

    window.bitsAgendaInstallPrompt = evento;

    document.dispatchEvent(
      new CustomEvent("bitsagenda:pwa-instalacao-disponivel"),
    );
  });

  window.instalarBitsAgenda = async function () {
    const promptInstalacao = window.bitsAgendaInstallPrompt;

    if (!promptInstalacao) {
      return {
        disponivel: false,
        mensagem: "Instalação ainda não disponível neste navegador.",
      };
    }

    promptInstalacao.prompt();

    const escolha = await promptInstalacao.userChoice;

    window.bitsAgendaInstallPrompt = null;

    return {
      disponivel: true,
      resultado: escolha.outcome,
    };
  };

  window.instalarGestoApp = window.instalarBitsAgenda;
})();

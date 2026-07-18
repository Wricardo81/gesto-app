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

    window.gestoAppInstallPrompt = evento;

    document.dispatchEvent(new CustomEvent("gesto:pwa-instalacao-disponivel"));
  });

  window.instalarGestoApp = async function () {
    const promptInstalacao = window.gestoAppInstallPrompt;

    if (!promptInstalacao) {
      return {
        disponivel: false,
        mensagem: "Instalação ainda não disponível neste navegador.",
      };
    }

    promptInstalacao.prompt();

    const escolha = await promptInstalacao.userChoice;

    window.gestoAppInstallPrompt = null;

    return {
      disponivel: true,
      resultado: escolha.outcome,
    };
  };
})();

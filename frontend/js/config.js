(function () {
    const hostname = window.location.hostname;

    const ambienteLocal =
        hostname === "127.0.0.1"
        || hostname === "localhost";

    window.GESTO_CONFIG = {
        API_BASE_URL: ambienteLocal
            ? "http://127.0.0.1:8000"
            : "https://api.seudominio.com",

        FRONTEND_BASE_URL: ambienteLocal
            ? "http://127.0.0.1:5500/frontend"
            : "https://app.seudominio.com",

        AMBIENTE: ambienteLocal
            ? "development"
            : "production"
    };
})();
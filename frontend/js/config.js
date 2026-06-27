(function () {
    const hostname = window.location.hostname;

    const ambienteLocal =
        hostname === "127.0.0.1"
        || hostname === "localhost";

    const BACKEND_PRODUCAO = "https://gesto-app.onrender.com";

    window.GESTO_CONFIG = {
        API_BASE_URL: ambienteLocal
            ? "http://127.0.0.1:8000"
            : BACKEND_PRODUCAO,

        FRONTEND_BASE_URL: ambienteLocal
            ? "http://127.0.0.1:5500/frontend"
            : window.location.origin,

        AMBIENTE: ambienteLocal
            ? "development"
            : "production"
    };
})();
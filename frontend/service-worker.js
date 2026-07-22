const CACHE_NAME = "gesto-app-pwa-v7";

const APP_SHELL = [
  "./",
  "./index.html",
  "./admin.html",
  "./saas.html",
  "./agendamento.html",
  "./meus-agendamentos.html",
  "./manifest.webmanifest",
  "./js/config.js",
  "./js/api.js",
  "./js/auth.js",
  "./js/admin.js",
  "./js/saas.js",
  "./js/diagnostico.js",
  "./js/agendamento.js",
  "./css/admin.css",
  "./css/saas.css",
  "./css/landing.css",
  "./css/pwa.css",
  "./offline.html",
  "./cadastro.html",
  "./js/cadastro.js",
  "./icons/bitsagenda-icon-192.png",
  "./icons/bitsagenda-icon-512.png",
  "./icons/bitsagenda-maskable-512.png",
];

function montarUrl(caminho) {
  return new URL(caminho, self.registration.scope).toString();
}

self.addEventListener("install", function (evento) {
  evento.waitUntil(
    caches
      .open(CACHE_NAME)
      .then(function (cache) {
        return cache.addAll(APP_SHELL.map(montarUrl));
      })
      .then(function () {
        return self.skipWaiting();
      }),
  );
});

self.addEventListener("activate", function (evento) {
  evento.waitUntil(
    caches
      .keys()
      .then(function (nomesCaches) {
        return Promise.all(
          nomesCaches
            .filter(function (nomeCache) {
              return nomeCache !== CACHE_NAME;
            })
            .map(function (nomeCache) {
              return caches.delete(nomeCache);
            }),
        );
      })
      .then(function () {
        return self.clients.claim();
      }),
  );
});

self.addEventListener("fetch", function (event) {
  const request = event.request;

  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  if (url.pathname.includes("/api/")) {
    event.respondWith(
      fetch(request).catch(function () {
        return new Response(
          JSON.stringify({
            offline: true,
            message: "Sem conexão com o servidor no momento.",
          }),
          {
            status: 503,
            headers: {
              "Content-Type": "application/json",
            },
          },
        );
      }),
    );

    return;
  }

  event.respondWith(
    caches.match(request).then(function (cachedResponse) {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(request).catch(function () {
        if (request.mode === "navigate") {
          return caches.match("./offline.html");
        }

        return caches.match("./offline.html");
      });
    }),
  );
});

const CACHE_NAME = "gesto-app-pwa-v3";

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
  "./js/agendamento.js",
  "./css/admin.css",
  "./css/saas.css",
  "./css/landing.css",
  "./css/pwa.css",
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

self.addEventListener("fetch", function (evento) {
  const requisicao = evento.request;

  if (requisicao.method !== "GET") {
    return;
  }

  const url = new URL(requisicao.url);

  if (url.origin !== self.location.origin) {
    return;
  }

  if (url.pathname.includes("/api/")) {
    return;
  }

  if (requisicao.mode === "navigate") {
    evento.respondWith(
      fetch(requisicao)
        .then(function (resposta) {
          const copiaResposta = resposta.clone();

          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(requisicao, copiaResposta);
          });

          return resposta;
        })
        .catch(function () {
          return caches.match(requisicao).then(function (respostaCache) {
            return respostaCache || caches.match(montarUrl("./index.html"));
          });
        }),
    );

    return;
  }

  evento.respondWith(
    caches.match(requisicao).then(function (respostaCache) {
      const buscaRede = fetch(requisicao)
        .then(function (respostaRede) {
          if (respostaRede && respostaRede.status === 200) {
            const copiaResposta = respostaRede.clone();

            caches.open(CACHE_NAME).then(function (cache) {
              cache.put(requisicao, copiaResposta);
            });
          }

          return respostaRede;
        })
        .catch(function () {
          return respostaCache;
        });

      return respostaCache || buscaRede;
    }),
  );
});

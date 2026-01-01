self.addEventListener("install", event => {
    console.log("Service Worker instalado");
});

self.addEventListener("activate", event => {
    console.log("Service Worker ativo");
});

self.addEventListener("fetch", event => {
    // Por enquanto, tudo online
});

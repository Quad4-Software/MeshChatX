/* Registers the service worker and injects PWA metadata.
   Progressive enhancement only: without JS the docs render normally.
   The site root is derived from this script's own URL so it works
   whether the site is mounted at the origin root or a subpath. */
(function () {
  "use strict";

  var script = document.currentScript;
  var base = script
    ? new URL("../", script.src)
    : new URL("/", location.href);

  var head = document.head;

  if (!head.querySelector('link[rel="manifest"]')) {
    var manifest = document.createElement("link");
    manifest.rel = "manifest";
    manifest.href = new URL("manifest.webmanifest", base).href;
    head.appendChild(manifest);
  }

  var themes = [
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0b" },
    { media: "(prefers-color-scheme: light)", color: "#fafafa" },
  ];
  themes.forEach(function (entry) {
    var meta = document.createElement("meta");
    meta.name = "theme-color";
    meta.media = entry.media;
    meta.content = entry.color;
    head.appendChild(meta);
  });

  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", function () {
    navigator.serviceWorker.register(new URL("sw.js", base).href);
  });

  window.addEventListener("online", function () {
    navigator.serviceWorker.getRegistration().then(function (registration) {
      if (registration) registration.update();
    });
  });
})();

import { RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL } from "./reticulumDocsEntryUrl.js";

/**
 * Open the in-app documentation tool to a path under /reticulum-docs/.
 * @param {import('vue-router').Router} router
 * @param {string} [relPath] - path after /reticulum-docs/ (may include #fragment)
 */
export function openBundledReticulumManualPath(router, relPath = RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL) {
    return router.push({
        name: "documentation",
        query: { reticulum: encodeURIComponent(relPath) },
    });
}

/**
 * Host-agnostic deep link for the bundled Reticulum manual (handled in App.vue
 * `handleProtocolLink`). Use in LXMF, notifications, or when the browser base URL is unknown.
 * @param {string} relPath - path under /reticulum-docs/ (e.g. `manual/interfaces.html#section`)
 * @param {"meshchatx" | "meshchat"} [scheme=meshchatx]
 * @returns {string} e.g. `meshchatx://docs?reticulum=manual%2Finterfaces.html`
 */
export function bundledReticulumManualDeepLink(relPath, scheme = "meshchatx") {
    const s = scheme === "meshchat" ? "meshchat" : "meshchatx";
    const q = new URLSearchParams();
    q.set("reticulum", relPath);
    return `${s}://docs?${q.toString()}`;
}

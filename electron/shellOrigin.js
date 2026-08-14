"use strict";

const LOCAL_BACKEND_HOSTS = new Set(["127.0.0.1", "localhost"]);
const LOCAL_BACKEND_PORT = "9337";

/**
 * Parse a URL string. Returns null when the input is not a valid absolute URL.
 * @param {unknown} url
 * @returns {URL | null}
 */
function parseAbsoluteUrl(url) {
    if (!url || typeof url !== "string") {
        return null;
    }
    try {
        return new URL(url);
    } catch {
        return null;
    }
}

/**
 * Inner http(s) URL of a blob URL, or null.
 * blob:https://host/uuid has an origin of https://host, not the blob scheme itself.
 * @param {unknown} url
 * @returns {string | null}
 */
function blobInnerHttpUrl(url) {
    if (!url || typeof url !== "string" || !url.startsWith("blob:")) {
        return null;
    }
    const inner = url.slice("blob:".length);
    const parsed = parseAbsoluteUrl(inner);
    if (!parsed) {
        return null;
    }
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        return null;
    }
    return inner;
}

/**
 * Whether the URL is the MeshChatX local backend origin (loading / API checks).
 * Parses so userinfo like http://127.0.0.1:9337@example.com is not local.
 * @param {unknown} url
 * @returns {boolean}
 */
function isLocalBackendUrl(url) {
    const parsed = parseAbsoluteUrl(url);
    if (!parsed) {
        return false;
    }
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        return false;
    }
    if (parsed.username !== "" || parsed.password !== "") {
        return false;
    }
    const host = String(parsed.hostname || "").toLowerCase();
    if (!LOCAL_BACKEND_HOSTS.has(host)) {
        return false;
    }
    return parsed.port === LOCAL_BACKEND_PORT;
}

/**
 * blob: URLs whose inner origin is the local backend (print preview).
 * @param {unknown} url
 * @returns {boolean}
 */
function isTrustedBlobUrl(url) {
    const inner = blobInnerHttpUrl(url);
    return inner != null && isLocalBackendUrl(inner);
}

/**
 * file: loading.html and crash.html in the Electron shell. Not arbitrary files.
 * @param {unknown} url
 * @returns {boolean}
 */
function isTrustedShellFileUrl(url) {
    const parsed = parseAbsoluteUrl(url);
    if (!parsed || parsed.protocol !== "file:") {
        return false;
    }
    let pathname = parsed.pathname || "";
    try {
        pathname = decodeURIComponent(pathname);
    } catch {
        return false;
    }
    const normalized = pathname.replace(/\\/g, "/").toLowerCase();
    return normalized.endsWith("/loading.html") || normalized.endsWith("/crash.html");
}

/**
 * Origins allowed to call preload window.electron IPC.
 * file: loading/crash pages, the local backend, and trusted print blobs.
 * @param {unknown} url
 * @returns {boolean}
 */
function isTrustedShellOrigin(url) {
    if (isTrustedShellFileUrl(url)) {
        return true;
    }
    if (isTrustedBlobUrl(url)) {
        return true;
    }
    return isLocalBackendUrl(url);
}

/**
 * Whether window.open should create a child Electron window instead of the OS browser.
 * Local backend popouts and call.html must stay in Electron so they keep the app session.
 * @param {unknown} url
 * @returns {boolean}
 */
function shouldOpenInElectronWindow(url) {
    if (!url || typeof url !== "string") {
        return false;
    }
    if (url.startsWith("blob:")) {
        return isTrustedBlobUrl(url);
    }
    if (!isLocalBackendUrl(url)) {
        return false;
    }
    const parsed = parseAbsoluteUrl(url);
    if (!parsed) {
        return false;
    }
    const pathname = parsed.pathname || "";
    if (pathname === "/call.html" || pathname.endsWith("/call.html")) {
        return true;
    }
    return parsed.hash.startsWith("#/popout/");
}

/**
 * Whether the main frame may navigate to this URL inside Electron (local app shell).
 * External http(s) links must open in the system browser instead.
 * data: and file: are denied. blob: is allowed only when the inner origin is local.
 * @param {unknown} url
 * @returns {boolean}
 */
function shouldAllowInWindowNavigation(url) {
    if (!url || typeof url !== "string") {
        return false;
    }
    if (url.startsWith("blob:")) {
        return isTrustedBlobUrl(url);
    }
    return isLocalBackendUrl(url);
}

/**
 * URL of the renderer frame that invoked an ipcMain handler.
 * Prefers senderFrame.url, then sender.getURL().
 * @param {unknown} event
 * @returns {string}
 */
function senderUrlFromIpcEvent(event) {
    if (!event || typeof event !== "object") {
        return "";
    }
    const frame = event.senderFrame;
    if (frame && typeof frame.url === "string" && frame.url) {
        return frame.url;
    }
    const sender = event.sender;
    if (sender && typeof sender.getURL === "function") {
        try {
            const url = sender.getURL();
            return typeof url === "string" ? url : "";
        } catch {
            return "";
        }
    }
    return "";
}

/**
 * Whether ipcMain may run for this invoke. Same allowlist as preload.
 * @param {unknown} event
 * @returns {boolean}
 */
function isTrustedIpcEvent(event) {
    return isTrustedShellOrigin(senderUrlFromIpcEvent(event));
}

module.exports = {
    isLocalBackendUrl,
    isTrustedBlobUrl,
    isTrustedShellFileUrl,
    isTrustedShellOrigin,
    isTrustedIpcEvent,
    senderUrlFromIpcEvent,
    shouldOpenInElectronWindow,
    shouldAllowInWindowNavigation,
};

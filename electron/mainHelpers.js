"use strict";

const IGNORED_CLI_ARGUMENTS = new Set(["--no-sandbox", "--ozone-platform-hint=auto"]);

/**
 * Arguments after argv[0], excluding known Chromium/Electron noise flags.
 * @param {string[]} argv Typically process.argv
 * @returns {string[]}
 */
function getUserProvidedArguments(argv) {
    const list = Array.isArray(argv) ? argv : [];
    return list.slice(1).filter((arg) => !IGNORED_CLI_ARGUMENTS.has(arg));
}

/**
 * @param {unknown} details Electron render-process-gone details
 * @returns {string}
 */
function formatRenderProcessGoneDetails(details) {
    if (!details) {
        return "no details";
    }
    return JSON.stringify(
        {
            reason: details.reason || "unknown",
            exitCode: details.exitCode,
        },
        null,
        2
    );
}

/**
 * Whether the URL is the MeshChatX local backend origin (loading / API checks).
 * @param {unknown} url
 * @returns {boolean}
 */
function isLocalBackendUrl(url) {
    if (!url || typeof url !== "string") {
        return false;
    }
    return (
        url.startsWith("http://127.0.0.1:9337") ||
        url.startsWith("https://127.0.0.1:9337") ||
        url.startsWith("http://localhost:9337") ||
        url.startsWith("https://localhost:9337")
    );
}

module.exports = {
    getUserProvidedArguments,
    formatRenderProcessGoneDetails,
    isLocalBackendUrl,
};

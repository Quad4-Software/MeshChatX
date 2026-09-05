// SPDX-License-Identifier: 0BSD
/**
 * Shared channel and URL for the Nomad crash-tab renderer frame.
 */

export const NOMAD_CRASH_TAB_CHANNEL = "nomad-crash-tab";

/**
 * Same-origin URL for the Vite multi-page crash-tab entry.
 *
 * @returns {string}
 */
export function nomadCrashTabRendererUrl() {
    try {
        return new URL("/nomad-crash-tab.html", window.location.origin).href;
    } catch {
        return "/nomad-crash-tab.html";
    }
}

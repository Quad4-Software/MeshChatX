// SPDX-License-Identifier: 0BSD
/**
 * Shared channel and URL for the Nomad crash-tab renderer frame.
 */

declare const __APP_BUILD_TIME__: string | undefined;

export const NOMAD_CRASH_TAB_CHANNEL = "nomad-crash-tab";

/**
 * Same-origin URL for the Vite multi-page crash-tab entry. The build-time
 * query pins the URL to this bundle so a heuristic-cached copy from an older
 * build (which references deleted hashed chunks) can never be served after
 * an update or restart.
 */
export function nomadCrashTabRendererUrl(): string {
    const build = typeof __APP_BUILD_TIME__ !== "undefined" ? __APP_BUILD_TIME__ : "";
    const suffix = build ? `?v=${encodeURIComponent(build)}` : "";
    try {
        return new URL(`/nomad-crash-tab.html${suffix}`, window.location.origin).href;
    } catch {
        return `/nomad-crash-tab.html${suffix}`;
    }
}

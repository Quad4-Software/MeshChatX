// SPDX-License-Identifier: 0BSD

/**
 * Client-side service worker registration helpers (browser only, not Electron).
 */

/**
 * Reload only when replacing an existing controller, and only once per page life.
 * @param {{ hadController: boolean, refreshing: boolean }} state
 * @returns {{ shouldReload: boolean, nextRefreshing: boolean }}
 */
export function decideControllerChangeReload(state) {
    const hadController = Boolean(state?.hadController);
    const refreshing = Boolean(state?.refreshing);
    if (!hadController || refreshing) {
        return { shouldReload: false, nextRefreshing: refreshing };
    }
    return { shouldReload: true, nextRefreshing: true };
}

/**
 * @param {unknown} error
 * @returns {boolean}
 */
export function isIgnorableServiceWorkerRegistrationError(error) {
    const errorMessage = error && typeof error === "object" && "message" in error ? String(error.message || "") : "";
    const errorName = error && typeof error === "object" && "name" in error ? String(error.name || "") : "";
    return (
        errorName === "SecurityError" ||
        errorMessage.includes("SSL certificate") ||
        errorMessage.includes("certificate")
    );
}

/**
 * Registration options that keep SW script discovery fresh.
 * @returns {{ updateViaCache: "none" }}
 */
export function serviceWorkerRegisterOptions() {
    return { updateViaCache: "none" };
}

/**
 * Vite HMR breaks if a leftover PWA worker intercepts modules.
 * Register only for production-like browser loads (not Electron, not Vite DEV).
 *
 * @param {{ isDev?: boolean, isElectron?: boolean }} state
 * @returns {boolean}
 */
export function shouldRegisterServiceWorker(state) {
    return !state?.isDev && !state?.isElectron;
}

/**
 * Drop existing registrations so a previous task run session cannot cache Vite.
 *
 * @param {{ getRegistrations?: () => Promise<Array<{ unregister?: () => Promise<boolean> }>> }} [serviceWorker]
 * @returns {Promise<boolean[]>}
 */
export async function unregisterServiceWorkersIfPresent(serviceWorker) {
    if (!serviceWorker || typeof serviceWorker.getRegistrations !== "function") {
        return [];
    }
    const registrations = await serviceWorker.getRegistrations();
    if (!Array.isArray(registrations) || registrations.length === 0) {
        return [];
    }
    const results = [];
    for (const registration of registrations) {
        if (registration && typeof registration.unregister === "function") {
            results.push(Boolean(await registration.unregister()));
        }
    }
    return results;
}

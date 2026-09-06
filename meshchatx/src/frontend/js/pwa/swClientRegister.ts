// SPDX-License-Identifier: 0BSD

/**
 * Client-side service worker registration helpers (browser only, not Electron).
 */

export type ControllerChangeReloadState = {
    hadController: boolean;
    refreshing: boolean;
};

export type ControllerChangeReloadDecision = {
    shouldReload: boolean;
    nextRefreshing: boolean;
};

/** Reload only when replacing an existing controller, and only once per page life. */
export function decideControllerChangeReload(state: ControllerChangeReloadState): ControllerChangeReloadDecision {
    const hadController = Boolean(state?.hadController);
    const refreshing = Boolean(state?.refreshing);
    if (!hadController || refreshing) {
        return { shouldReload: false, nextRefreshing: refreshing };
    }
    return { shouldReload: true, nextRefreshing: true };
}

export function isIgnorableServiceWorkerRegistrationError(error: unknown): boolean {
    const errorMessage = error && typeof error === "object" && "message" in error ? String(error.message || "") : "";
    const errorName = error && typeof error === "object" && "name" in error ? String(error.name || "") : "";
    return (
        errorName === "SecurityError" ||
        errorMessage.includes("SSL certificate") ||
        errorMessage.includes("certificate")
    );
}

/** Registration options that keep SW script discovery fresh. */
export function serviceWorkerRegisterOptions(): { updateViaCache: "none" } {
    return { updateViaCache: "none" };
}

/**
 * Vite HMR breaks if a leftover PWA worker intercepts modules.
 * Register only for production-like browser loads (not Electron, not Vite DEV).
 */
export function shouldRegisterServiceWorker(state: { isDev?: boolean; isElectron?: boolean }): boolean {
    return !state?.isDev && !state?.isElectron;
}

type UnregisterableRegistration = {
    unregister?: () => Promise<boolean>;
};

type ServiceWorkerLike = {
    getRegistrations?: () => Promise<readonly UnregisterableRegistration[] | UnregisterableRegistration[]>;
};

/**
 * Drop existing registrations so a previous task run session cannot cache Vite.
 */
export async function unregisterServiceWorkersIfPresent(serviceWorker?: ServiceWorkerLike): Promise<boolean[]> {
    if (!serviceWorker || typeof serviceWorker.getRegistrations !== "function") {
        return [];
    }
    const registrations = await serviceWorker.getRegistrations();
    if (!Array.isArray(registrations) || registrations.length === 0) {
        return [];
    }
    const results: boolean[] = [];
    for (const registration of registrations) {
        if (registration && typeof registration.unregister === "function") {
            results.push(Boolean(await registration.unregister()));
        }
    }
    return results;
}

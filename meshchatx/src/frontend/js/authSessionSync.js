import { apiPath } from "./constants.js";
import { useAuthStore } from "./stores/authStore.js";

/** Max wait for auth status during navigation guards and reconnect resync. */
export const AUTH_STATUS_TIMEOUT_MS = 10000;

/**
 * Copy auth status fields from the API into the auth store.
 * @param {Record<string, unknown> | null | undefined} status
 */
export function applyAuthStatusToStores(status) {
    if (!status || typeof status !== "object") {
        return;
    }
    const authStore = useAuthStore();
    authStore.authEnabled = !!status.auth_enabled;
    authStore.authenticated = !!status.authenticated;
    authStore.demoMode = !!status.demo_mode;
    if (typeof status.is_loopback_bind === "boolean") {
        authStore.isLoopbackBind = status.is_loopback_bind;
    }
    authStore.authSessionResolved = true;
}

/**
 * @param {import("./apiClient.js").createApiClient} api
 * @param {{ timeoutMs?: number }} [options]
 * @returns {Promise<Record<string, unknown>>}
 */
export async function fetchAuthStatus(api, options = {}) {
    const timeoutMs = options.timeoutMs ?? AUTH_STATUS_TIMEOUT_MS;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await api.get(apiPath("/auth/status"), { signal: controller.signal });
        return response.data ?? {};
    } finally {
        clearTimeout(timer);
    }
}

/**
 * Decide where a navigation should land after reading auth status.
 * @param {{ name?: string | null }} to
 * @param {Record<string, unknown>} status
 * @returns {{ allow: true } | { redirect: string }}
 */
export function authNavigationTargetForStatus(to, status) {
    if (!status.auth_enabled) {
        return { allow: true };
    }
    if (status.authenticated) {
        if (to.name === "auth") {
            return { redirect: "/" };
        }
        return { allow: true };
    }
    if (to.name === "auth") {
        return { allow: true };
    }
    return { redirect: "/auth" };
}

/**
 * Auth guard oracle used by the router beforeEach hook.
 * @param {{ name?: string | null }} to
 * @param {import("./apiClient.js").createApiClient} api
 * @returns {Promise<{ allow: true } | { redirect: string }>}
 */
export async function resolveAuthNavigation(to, api) {
    try {
        const status = await fetchAuthStatus(api);
        applyAuthStatusToStores(status);
        return authNavigationTargetForStatus(to, status);
    } catch (e) {
        const authStore = useAuthStore();
        authStore.authSessionResolved = true;
        if (e.response?.status === 401 || e.response?.status === 403) {
            authStore.authenticated = false;
            return { redirect: "/auth" };
        }
        return { allow: true };
    }
}

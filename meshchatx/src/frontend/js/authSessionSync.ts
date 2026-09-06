import GlobalState from "./GlobalState.js";

/** Max wait for auth status during navigation guards and reconnect resync. */
export const AUTH_STATUS_TIMEOUT_MS = 10000;

/**
 * Copy auth status fields from the API into GlobalState.
 * @param {Record<string, unknown> | null | undefined} status
 */
export function applyAuthStatusToGlobalState(status) {
    if (!status || typeof status !== "object") {
        return;
    }
    GlobalState.authEnabled = !!status.auth_enabled;
    GlobalState.authenticated = !!status.authenticated;
    GlobalState.demoMode = !!status.demo_mode;
    if (typeof status.is_loopback_bind === "boolean") {
        GlobalState.isLoopbackBind = status.is_loopback_bind;
    }
    GlobalState.authSessionResolved = true;
}

/**
 * @param {import("./apiClient.js").createApiClient} api
 * @param {{ timeoutMs?: number }} [options]
 * @returns {Promise<Record<string, unknown>>}
 */
export async function fetchAuthStatus(api, options: any = {}) {
    const timeoutMs = options.timeoutMs ?? AUTH_STATUS_TIMEOUT_MS;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await api.get("/api/v1/auth/status", { signal: controller.signal });
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
        applyAuthStatusToGlobalState(status);
        return authNavigationTargetForStatus(to, status);
    } catch (e: unknown) {
        GlobalState.authSessionResolved = true;
        const status = (e as { response?: { status?: number } })?.response?.status;
        if (status === 401 || status === 403) {
            GlobalState.authenticated = false;
            return { redirect: "/auth" };
        }
        return { allow: true };
    }
}

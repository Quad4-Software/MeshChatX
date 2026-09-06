import type { ApiClient } from "./apiClient.js";
import GlobalState from "./GlobalState.js";

/** Max wait for auth status during navigation guards and reconnect resync. */
export const AUTH_STATUS_TIMEOUT_MS = 10000;

export type AuthStatusPayload = Record<string, unknown> & {
    auth_enabled?: unknown;
    authenticated?: unknown;
    demo_mode?: unknown;
    is_loopback_bind?: unknown;
};

export type AuthNavTarget = { name?: string | null };

export type AuthNavigationDecision = { allow: true } | { redirect: string };

export type FetchAuthStatusOptions = {
    timeoutMs?: number;
};

/** Copy auth status fields from the API into GlobalState. */
export function applyAuthStatusToGlobalState(status: AuthStatusPayload | null | undefined): void {
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

export async function fetchAuthStatus(
    api: ApiClient,
    options: FetchAuthStatusOptions = {}
): Promise<AuthStatusPayload> {
    const timeoutMs = options.timeoutMs ?? AUTH_STATUS_TIMEOUT_MS;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await api.get<AuthStatusPayload>("/api/v1/auth/status", {
            signal: controller.signal,
        });
        return response.data ?? {};
    } finally {
        clearTimeout(timer);
    }
}

/** Decide where a navigation should land after reading auth status. */
export function authNavigationTargetForStatus(to: AuthNavTarget, status: AuthStatusPayload): AuthNavigationDecision {
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

/** Auth guard oracle used by the router beforeEach hook. */
export async function resolveAuthNavigation(to: AuthNavTarget, api: ApiClient): Promise<AuthNavigationDecision> {
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

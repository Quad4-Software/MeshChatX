// SPDX-License-Identifier: 0BSD

export const STARTUP_STAGE_LABELS: any = {
    http: "Getting things ready…",
    starting: "Getting RNS ready…",
    rns: "Starting RNS…",
    identity: "Almost there…",
    ready: "Ready",
    failed: "Startup failed",
};

/**
 * Interpret a /api/v1/status JSON body for boot gating.
 * Only own properties are trusted so prototype pollution cannot spoof readiness.
 * @param {unknown} data
 * @returns {{ kind: "ready" | "ui" | "degraded" | "failed" | "starting" | "invalid", stage?: string, error?: string, label?: string }}
 */
export function interpretStartupStatus(data) {
    if (!data || typeof data !== "object" || Array.isArray(data)) {
        return { kind: "invalid" };
    }
    const own = (key) => Object.prototype.hasOwnProperty.call(data, key);
    const status = own("status") ? data.status : undefined;
    const stage = own("stage") && typeof data.stage === "string" ? data.stage : undefined;
    const networkReady = own("network_ready") && data.network_ready === true;
    const uiReady = own("ui_ready") && data.ui_ready === true;
    const networkDegraded = own("network_degraded") && data.network_degraded === true;
    const error = own("error") && typeof data.error === "string" ? data.error : undefined;

    if (status === "failed") {
        // HTTP is up and the backend marked UI as usable: mount the app in
        // degraded mode so settings/interfaces remain reachable for recovery.
        if (uiReady || networkDegraded) {
            return {
                kind: "degraded",
                stage: stage || "failed",
                error,
            };
        }
        return {
            kind: "failed",
            stage: stage || "failed",
            error,
        };
    }
    if (status === "ok" || networkReady) {
        return { kind: "ready", stage: stage || "ready" };
    }
    if (status === "starting" || status === undefined) {
        const resolvedStage = stage || "starting";
        const label = STARTUP_STAGE_LABELS[resolvedStage] || "Starting RNS…";
        // HTTP is bound and the shell may mount while RNS/identity finish.
        if (uiReady) {
            return {
                kind: "ui",
                stage: resolvedStage,
                label,
            };
        }
        return {
            kind: "starting",
            stage: resolvedStage,
            label,
        };
    }
    return { kind: "invalid", stage };
}

/**
 * Poll /api/v1/status until the UI may mount (ui_ready), mesh is ready, or degraded.
 * @param {{
 *   fetchImpl?: typeof fetch,
 *   now?: () => number,
 *   sleep?: (ms: number) => Promise<void>,
 *   timeoutMs?: number,
 *   onLine?: (text: string) => void,
 *   onErrorState?: () => void,
 *   onDegraded?: (error?: string) => void,
 *   statusUrl?: string,
 *   mountOnUiReady?: boolean,
 * }} [options]
 * @returns {Promise<"ready" | "ui" | "degraded" | false>}
 */
export async function waitForNetworkReady(options: any = {}) {
    const fetchImpl = options.fetchImpl || fetch;
    const now = options.now || Date.now;
    const sleep = options.sleep || ((ms) => new Promise<any>((resolve) => setTimeout(resolve, ms)));
    const timeoutMs = options.timeoutMs ?? 120000;
    const onLine = options.onLine || (() => {});
    const onErrorState = options.onErrorState || (() => {});
    const onDegraded = options.onDegraded || (() => {});
    const statusUrl = options.statusUrl || "/api/v1/status";
    const mountOnUiReady = options.mountOnUiReady !== false;

    const deadline = now() + timeoutMs;
    let delayMs = 200;
    while (now() < deadline) {
        try {
            const response = await fetchImpl(statusUrl, { cache: "no-store" });
            if (response.ok) {
                const data = await response.json();
                const interpreted = interpretStartupStatus(data);
                if (interpreted.kind === "degraded") {
                    onLine(interpreted.error || "RNS unavailable. Opening recovery UI…");
                    onDegraded(interpreted.error);
                    return "degraded";
                }
                if (interpreted.kind === "failed") {
                    onLine(interpreted.error || "Network startup failed.");
                    onErrorState();
                    return false;
                }
                if (interpreted.kind === "ready") {
                    return "ready";
                }
                if (interpreted.kind === "ui" && mountOnUiReady) {
                    onLine(interpreted.label || "Opening the app…");
                    return "ui";
                }
                if (interpreted.kind === "starting" || interpreted.kind === "ui") {
                    onLine(interpreted.label || "Getting things ready…");
                }
            }
        } catch {
            onLine("Still starting…");
        }
        await sleep(delayMs);
        delayMs = Math.min(delayMs + 100, 1000);
    }
    onLine("Network startup timed out. Try reloading.");
    onErrorState();
    return false;
}

/**
 * Continue polling until mesh network_ready or degraded/failed.
 * Used after an early UI mount on ui_ready.
 * @param {{
 *   fetchImpl?: typeof fetch,
 *   now?: () => number,
 *   sleep?: (ms: number) => Promise<void>,
 *   timeoutMs?: number,
 *   onLine?: (text: string) => void,
 *   onErrorState?: () => void,
 *   onDegraded?: (error?: string) => void,
 *   statusUrl?: string,
 * }} [options]
 * @returns {Promise<"ready" | "degraded" | false>}
 */
export async function waitForMeshReady(options: any = {}) {
    return waitForNetworkReady({
        ...options,
        mountOnUiReady: false,
    });
}

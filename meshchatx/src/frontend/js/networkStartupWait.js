// SPDX-License-Identifier: 0BSD AND MIT

export const STARTUP_STAGE_LABELS = {
    http: "Getting things ready…",
    starting: "Getting the mesh ready…",
    rns: "Connecting to the mesh…",
    identity: "Almost there…",
    ready: "Ready",
    failed: "Startup failed",
};

/**
 * Interpret a /api/v1/status JSON body for boot gating.
 * @param {unknown} data
 * @returns {{ kind: "ready" | "failed" | "starting" | "invalid", stage?: string, error?: string, label?: string }}
 */
export function interpretStartupStatus(data) {
    if (!data || typeof data !== "object") {
        return { kind: "invalid" };
    }
    const status = data.status;
    const stage = typeof data.stage === "string" ? data.stage : undefined;
    if (status === "failed") {
        return {
            kind: "failed",
            stage: stage || "failed",
            error: typeof data.error === "string" ? data.error : undefined,
        };
    }
    if (status === "ok" || data.network_ready === true) {
        return { kind: "ready", stage: stage || "ready" };
    }
    if (status === "starting" || status === undefined) {
        const resolvedStage = stage || "starting";
        return {
            kind: "starting",
            stage: resolvedStage,
            label: STARTUP_STAGE_LABELS[resolvedStage] || "Starting network…",
        };
    }
    return { kind: "invalid", stage };
}

/**
 * Poll /api/v1/status until the network stack is ready.
 * @param {{
 *   fetchImpl?: typeof fetch,
 *   now?: () => number,
 *   sleep?: (ms: number) => Promise<void>,
 *   timeoutMs?: number,
 *   onLine?: (text: string) => void,
 *   onErrorState?: () => void,
 *   statusUrl?: string,
 * }} [options]
 * @returns {Promise<boolean>}
 */
export async function waitForNetworkReady(options = {}) {
    const fetchImpl = options.fetchImpl || fetch;
    const now = options.now || Date.now;
    const sleep = options.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    const timeoutMs = options.timeoutMs ?? 120000;
    const onLine = options.onLine || (() => {});
    const onErrorState = options.onErrorState || (() => {});
    const statusUrl = options.statusUrl || "/api/v1/status";

    const deadline = now() + timeoutMs;
    let delayMs = 200;
    while (now() < deadline) {
        try {
            const response = await fetchImpl(statusUrl, { cache: "no-store" });
            if (response.ok) {
                const data = await response.json();
                const interpreted = interpretStartupStatus(data);
                if (interpreted.kind === "failed") {
                    onLine(interpreted.error || "Network startup failed.");
                    onErrorState();
                    return false;
                }
                if (interpreted.kind === "ready") {
                    return true;
                }
                if (interpreted.kind === "starting") {
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

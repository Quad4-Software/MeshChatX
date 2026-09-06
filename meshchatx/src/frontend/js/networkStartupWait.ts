// SPDX-License-Identifier: 0BSD

export const STARTUP_STAGE_LABELS: Record<string, string> = {
    http: "Getting things ready…",
    starting: "Getting RNS ready…",
    rns: "Starting RNS…",
    identity: "Almost there…",
    ready: "Ready",
    failed: "Startup failed",
};

export type StartupStatusKind = "ready" | "ui" | "degraded" | "failed" | "starting" | "invalid";

export type InterpretedStartupStatus = {
    kind: StartupStatusKind;
    stage?: string;
    error?: string;
    label?: string;
};

/**
 * Interpret a /api/v1/status JSON body for boot gating.
 * Only own properties are trusted so prototype pollution cannot spoof readiness.
 */
export function interpretStartupStatus(data: unknown): InterpretedStartupStatus {
    if (!data || typeof data !== "object" || Array.isArray(data)) {
        return { kind: "invalid" };
    }
    const record = data as Record<string, unknown>;
    const own = (key: string) => Object.prototype.hasOwnProperty.call(record, key);
    const status = own("status") ? record.status : undefined;
    const stage = own("stage") && typeof record.stage === "string" ? record.stage : undefined;
    const networkReady = own("network_ready") && record.network_ready === true;
    const uiReady = own("ui_ready") && record.ui_ready === true;
    const networkDegraded = own("network_degraded") && record.network_degraded === true;
    const error = own("error") && typeof record.error === "string" ? record.error : undefined;

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

export type NetworkStartupWaitOptions = {
    fetchImpl?: typeof fetch;
    now?: () => number;
    sleep?: (ms: number) => Promise<void>;
    timeoutMs?: number;
    onLine?: (text: string) => void;
    onErrorState?: () => void;
    onDegraded?: (error?: string) => void;
    statusUrl?: string;
    mountOnUiReady?: boolean;
};

export type NetworkReadyResult = "ready" | "ui" | "degraded" | false;
export type MeshReadyResult = "ready" | "degraded" | false;

/** Poll /api/v1/status until the UI may mount (ui_ready), mesh is ready, or degraded. */
export async function waitForNetworkReady(options: NetworkStartupWaitOptions = {}): Promise<NetworkReadyResult> {
    const fetchImpl = options.fetchImpl || fetch;
    const now = options.now || Date.now;
    const sleep = options.sleep || ((ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms)));
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
 */
export async function waitForMeshReady(
    options: Omit<NetworkStartupWaitOptions, "mountOnUiReady"> = {}
): Promise<MeshReadyResult> {
    return waitForNetworkReady({
        ...options,
        mountOnUiReady: false,
    }) as Promise<MeshReadyResult>;
}

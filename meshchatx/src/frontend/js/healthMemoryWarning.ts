// SPDX-License-Identifier: 0BSD

/**
 * Session-scoped high-memory warning toast helpers.
 *
 * Host RAM pressure arrives via WebSocket health_warning (kind memory_low).
 * Client JS heap pressure is sampled locally when performance.memory exists.
 * Toast is sticky (duration 0) and shown at most once per pressure episode.
 */

export const MEMORY_WARNING_TOAST_KEY = "health-memory-warning";
export const MEMORY_WARNING_MESSAGE_KEY = "app.memory_pressure_warning";
export const CLIENT_HEAP_RATIO_THRESHOLD = 0.85;
export const CLIENT_HEAP_CONSECUTIVE_NEEDED = 2;
export const CLIENT_HEAP_SAMPLE_INTERVAL_MS = 30000;

let dismissedThisEpisode = false;
let toastVisible = false;
let consecutiveHighHeap = 0;

export function resetMemoryWarningStateForTests(): void {
    dismissedThisEpisode = false;
    toastVisible = false;
    consecutiveHighHeap = 0;
}

type WarningPayloadLike = {
    data?: Record<string, unknown>;
    kind?: unknown;
};

function warningDataFromPayload(payload: unknown): Record<string, unknown> | null {
    if (!payload || typeof payload !== "object") {
        return null;
    }
    const record = payload as WarningPayloadLike;
    if (record.data && typeof record.data === "object") {
        return record.data as Record<string, unknown>;
    }
    return record as Record<string, unknown>;
}

export function isMemoryHealthWarningPayload(payload: unknown): boolean {
    const data = warningDataFromPayload(payload);
    return Boolean(data && data.kind === "memory_low");
}

export function isMemoryRecoveredPayload(payload: unknown): boolean {
    const data = warningDataFromPayload(payload);
    return Boolean(data && data.kind === "memory_recovered");
}

export type MemoryWarningSourceOptions = {
    fromHealthWs?: boolean;
    fromClientHeap?: boolean;
};

export function shouldShowMemoryWarningToast(options: MemoryWarningSourceOptions = {}): boolean {
    if (dismissedThisEpisode || toastVisible) {
        return false;
    }
    return Boolean(options.fromHealthWs || options.fromClientHeap);
}

export function markMemoryWarningShown(): void {
    toastVisible = true;
}

export function markMemoryWarningDismissed(): void {
    toastVisible = false;
    dismissedThisEpisode = true;
    consecutiveHighHeap = 0;
}

export function markMemoryWarningRecovered(): void {
    dismissedThisEpisode = false;
    toastVisible = false;
    consecutiveHighHeap = 0;
}

export type MemoryInfoLike = {
    jsHeapSizeLimit?: number;
    usedJSHeapSize?: number;
};

export type ClientHeapSampleResult = {
    shouldWarn: boolean;
    reason: string;
    ratio?: number;
    consecutive?: number;
};

export function evaluateClientHeapSample(
    memoryInfo: MemoryInfoLike | Record<string, unknown> | null | undefined
): ClientHeapSampleResult {
    if (!memoryInfo || typeof memoryInfo.jsHeapSizeLimit !== "number" || memoryInfo.jsHeapSizeLimit <= 0) {
        consecutiveHighHeap = 0;
        return { shouldWarn: false, reason: "unavailable" };
    }
    const used = memoryInfo.usedJSHeapSize;
    if (typeof used !== "number" || !Number.isFinite(used) || used < 0) {
        consecutiveHighHeap = 0;
        return { shouldWarn: false, reason: "invalid" };
    }
    const ratio = used / memoryInfo.jsHeapSizeLimit;
    if (ratio < CLIENT_HEAP_RATIO_THRESHOLD) {
        consecutiveHighHeap = 0;
        return { shouldWarn: false, reason: "below_threshold", ratio };
    }
    consecutiveHighHeap += 1;
    if (consecutiveHighHeap < CLIENT_HEAP_CONSECUTIVE_NEEDED) {
        return {
            shouldWarn: false,
            reason: "need_consecutive",
            ratio,
            consecutive: consecutiveHighHeap,
        };
    }
    return {
        shouldWarn: true,
        reason: "high_heap",
        ratio,
        consecutive: consecutiveHighHeap,
    };
}

export type ToastWarningUtils = {
    warning: (message: string, duration?: number, key?: string | null) => void;
};

/** Returns true when a toast was shown. */
export function showMemoryWarningToastIfNeeded(
    toastUtils: ToastWarningUtils | null | undefined,
    options: MemoryWarningSourceOptions = {}
): boolean {
    if (!shouldShowMemoryWarningToast(options)) {
        return false;
    }
    if (!toastUtils || typeof toastUtils.warning !== "function") {
        return false;
    }
    toastUtils.warning(MEMORY_WARNING_MESSAGE_KEY, 0, MEMORY_WARNING_TOAST_KEY);
    markMemoryWarningShown();
    return true;
}

export type HealthWarningHandleResult = "shown" | "recovered" | "ignored";

export function handleHealthWarningPayload(
    payload: unknown,
    toastUtils: ToastWarningUtils | null | undefined
): HealthWarningHandleResult {
    if (isMemoryRecoveredPayload(payload)) {
        markMemoryWarningRecovered();
        return "recovered";
    }
    if (!isMemoryHealthWarningPayload(payload)) {
        return "ignored";
    }
    return showMemoryWarningToastIfNeeded(toastUtils, { fromHealthWs: true }) ? "shown" : "ignored";
}

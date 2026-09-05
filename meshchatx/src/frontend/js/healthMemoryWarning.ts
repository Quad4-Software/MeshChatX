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

export function resetMemoryWarningStateForTests() {
    dismissedThisEpisode = false;
    toastVisible = false;
    consecutiveHighHeap = 0;
}

function warningDataFromPayload(payload) {
    if (!payload || typeof payload !== "object") {
        return null;
    }
    if (payload.data && typeof payload.data === "object") {
        return payload.data;
    }
    return payload;
}

/**
 * @param {unknown} payload
 * @returns {boolean}
 */
export function isMemoryHealthWarningPayload(payload) {
    const data = warningDataFromPayload(payload);
    return Boolean(data && data.kind === "memory_low");
}

/**
 * @param {unknown} payload
 * @returns {boolean}
 */
export function isMemoryRecoveredPayload(payload) {
    const data = warningDataFromPayload(payload);
    return Boolean(data && data.kind === "memory_recovered");
}

/**
 * @param {{ fromHealthWs?: boolean, fromClientHeap?: boolean }} options
 * @returns {boolean}
 */
export function shouldShowMemoryWarningToast(options: any = {}) {
    if (dismissedThisEpisode || toastVisible) {
        return false;
    }
    return Boolean(options.fromHealthWs || options.fromClientHeap);
}

export function markMemoryWarningShown() {
    toastVisible = true;
}

export function markMemoryWarningDismissed() {
    toastVisible = false;
    dismissedThisEpisode = true;
    consecutiveHighHeap = 0;
}

export function markMemoryWarningRecovered() {
    dismissedThisEpisode = false;
    toastVisible = false;
    consecutiveHighHeap = 0;
}

/**
 * @param {{ jsHeapSizeLimit?: number, usedJSHeapSize?: number } | null | undefined} memoryInfo
 * @returns {{ shouldWarn: boolean, reason: string, ratio?: number, consecutive?: number }}
 */
export function evaluateClientHeapSample(memoryInfo) {
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

/**
 * @param {{ warning: (message: string, duration?: number, key?: string | null) => void }} toastUtils
 * @param {{ fromHealthWs?: boolean, fromClientHeap?: boolean }} options
 * @returns {boolean} true when a toast was shown
 */
export function showMemoryWarningToastIfNeeded(toastUtils, options: any = {}) {
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

/**
 * @param {unknown} payload
 * @param {{ warning: (message: string, duration?: number, key?: string | null) => void }} toastUtils
 * @returns {"shown" | "recovered" | "ignored"}
 */
export function handleHealthWarningPayload(payload, toastUtils) {
    if (isMemoryRecoveredPayload(payload)) {
        markMemoryWarningRecovered();
        return "recovered";
    }
    if (!isMemoryHealthWarningPayload(payload)) {
        return "ignored";
    }
    return showMemoryWarningToastIfNeeded(toastUtils, { fromHealthWs: true }) ? "shown" : "ignored";
}

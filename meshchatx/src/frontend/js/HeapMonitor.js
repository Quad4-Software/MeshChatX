// SPDX-License-Identifier: 0BSD

let intervalId = null;
const DEFAULT_INTERVAL = 5000;

function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
}

function sample() {
    const m = performance.memory;
    if (!m) {
        console.log(
            "[HeapMonitor] performance.memory not available (requires Chrome with --enable-precise-memory-info)"
        );
        return null;
    }
    return {
        heap: m.usedJSHeapSize,
        total: m.totalJSHeapSize,
        limit: m.jsHeapSizeLimit,
        ts: Date.now(),
    };
}

function log() {
    const s = sample();
    if (!s) return;
    console.log(
        `[HeapMonitor] ${formatBytes(s.heap)} used / ${formatBytes(s.total)} total / ${formatBytes(s.limit)} limit (${((s.heap / s.limit) * 100).toFixed(1)}%)`
    );
}

export function enableHeapMonitor(intervalMs) {
    if (!performance.memory) {
        console.warn(
            "[HeapMonitor] performance.memory is not available. Use Chrome and pass --enable-precise-memory-info."
        );
        return;
    }
    if (intervalId !== null) {
        clearInterval(intervalId);
    }
    const ms = intervalMs && intervalMs > 0 ? intervalMs : DEFAULT_INTERVAL;
    log();
    intervalId = setInterval(log, ms);
    console.log(`[HeapMonitor] enabled, sampling every ${ms}ms`);
}

export function disableHeapMonitor() {
    if (intervalId !== null) {
        clearInterval(intervalId);
        intervalId = null;
    }
    console.log("[HeapMonitor] disabled");
}

export function heapSnapshot() {
    const s = sample();
    if (s) {
        console.table(s);
        console.log(
            `[HeapMonitor] heap usage: ${formatBytes(s.heap)} / ${formatBytes(s.limit)} (${((s.heap / s.limit) * 100).toFixed(1)}%)`
        );
    }
}

// Auto-start if VITE_HEAP_MONITOR is set
if (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_HEAP_MONITOR) {
    const interval = parseInt(import.meta.env.VITE_HEAP_MONITOR, 10);
    enableHeapMonitor(interval > 0 ? interval : undefined);
}

// Expose on window for runtime toggle
if (typeof window !== "undefined") {
    window.enableHeapMonitor = enableHeapMonitor;
    window.disableHeapMonitor = disableHeapMonitor;
    window.heapSnapshot = heapSnapshot;
}

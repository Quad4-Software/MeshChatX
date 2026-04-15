/**
 * @param {number} attemptIndex 0 = first retry after disconnect
 * @param {number} baseMs
 * @param {number} maxMs
 */
export function getNextReconnectDelayMs(attemptIndex, baseMs, maxMs) {
    const raw = baseMs * 2 ** Math.max(0, attemptIndex);
    return Math.min(maxMs, Math.floor(raw));
}

/**
 * Human-readable duration for disconnected banner (count-up).
 * @param {number} elapsedMs
 */
export function formatDisconnectedDuration(elapsedMs) {
    let t = Math.max(0, Math.floor(elapsedMs));
    const s = Math.floor(t / 1000);
    if (s < 60) {
        return `${s}s`;
    }
    const m = Math.floor(s / 60);
    const secRem = s % 60;
    if (m < 60) {
        return secRem > 0 ? `${m}m ${secRem}s` : `${m}m`;
    }
    const h = Math.floor(m / 60);
    const minRem = m % 60;
    if (h < 24) {
        return minRem > 0 ? `${h}h ${minRem}m` : `${h}h`;
    }
    const d = Math.floor(h / 24);
    const hrRem = h % 24;
    return hrRem > 0 ? `${d}d ${hrRem}h` : `${d}d`;
}

export function reconnectDelayWithJitterMs(attemptIndex, baseMs, maxMs, jitterMaxMs) {
    const base = getNextReconnectDelayMs(attemptIndex, baseMs, maxMs);
    const jitter = jitterMaxMs > 0 ? Math.floor(Math.random() * jitterMaxMs) : 0;
    return base + jitter;
}

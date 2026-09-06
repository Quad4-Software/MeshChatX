/** Wait this long after a disconnect before showing the banner. Brief reconnects that get a backend frame stay quiet. */
export const WS_DISCONNECT_BANNER_GRACE_MS = 2500;

/** attemptIndex 0 = first retry after disconnect */
export function getNextReconnectDelayMs(attemptIndex: number, baseMs: number, maxMs: number): number {
    const raw = baseMs * 2 ** Math.max(0, attemptIndex);
    return Math.min(maxMs, Math.floor(raw));
}

/** Human-readable duration for disconnected banner (count-up). */
export function formatDisconnectedDuration(elapsedMs: number): string {
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

export function reconnectDelayWithJitterMs(
    attemptIndex: number,
    baseMs: number,
    maxMs: number,
    jitterMaxMs: number
): number {
    const base = getNextReconnectDelayMs(attemptIndex, baseMs, maxMs);
    const jitter = jitterMaxMs > 0 ? Math.floor(Math.random() * jitterMaxMs) : 0;
    return base + jitter;
}

/* SPDX-License-Identifier: 0BSD */

const RESUME_TIMEOUT_MS = 2000;

export async function ensureAudioContextRunning(ctx, timeoutMs = RESUME_TIMEOUT_MS) {
    if (!ctx) {
        return null;
    }
    if (ctx.state === "running") {
        return ctx;
    }
    if (typeof ctx.resume !== "function") {
        return null;
    }
    let timer = null;
    try {
        await Promise.race([
            Promise.resolve()
                .then(() => ctx.resume())
                .catch(() => {}),
            new Promise((resolve) => {
                timer = setTimeout(resolve, timeoutMs);
            }),
        ]);
    } finally {
        if (timer !== null) {
            clearTimeout(timer);
        }
    }
    return ctx.state === "running" ? ctx : null;
}

export function decodeAudioDataCompat(ctx, audioData) {
    const decode = ctx?.decodeAudioData;
    if (typeof decode !== "function") {
        return Promise.reject(new Error("decodeAudioData unavailable"));
    }
    if (decode.length > 1) {
        return new Promise((resolve, reject) => {
            decode.call(ctx, audioData, resolve, reject);
        });
    }
    try {
        return Promise.resolve(decode.call(ctx, audioData));
    } catch (error) {
        return Promise.reject(error);
    }
}

export async function decodeAudioArrayBuffer(audioData) {
    if (typeof OfflineAudioContext === "function") {
        const offline = new OfflineAudioContext(1, 1, 44100);
        return await decodeAudioDataCompat(offline, audioData);
    }
    const AudioContextCtor = typeof window !== "undefined" ? window.AudioContext || window.webkitAudioContext : null;
    if (typeof AudioContextCtor !== "function") {
        throw new Error("Web Audio unavailable");
    }
    const ctx = new AudioContextCtor();
    try {
        return await decodeAudioDataCompat(ctx, audioData);
    } finally {
        try {
            await ctx.close?.();
        } catch {
            // ignore
        }
    }
}

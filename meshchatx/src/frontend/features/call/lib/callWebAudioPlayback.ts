// SPDX-License-Identifier: 0BSD

import {
    DEFAULT_AUDIO_OUTPUT_DEVICE_ID,
    DEFAULT_AUDIO_SAMPLE_RATE,
    INT16_SAMPLE_MAX,
} from "./constants.js";

declare const window: {
    AudioContext?: typeof AudioContext;
    webkitAudioContext?: typeof AudioContext;
};

/**
 * Extracts Int16Array from binary payload
 */
export function extractInt16Samples(payload: unknown): Int16Array | null {
    if (!payload) return null;
    if (payload instanceof ArrayBuffer) {
        return new Int16Array(payload);
    }
    if (ArrayBuffer.isView(payload)) {
        const byteLengthEven = Math.floor(payload.byteLength / 2) * 2;
        return new Int16Array(payload.buffer, payload.byteOffset, byteLengthEven / 2);
    }
    return null;
}

/**
 * Computes RMS and peak signal level normalized to 0 to 1
 */
export function computeSignalLevel(samples: Int16Array | Float32Array | number[], scale: number = 1): number {
    if (!samples || samples.length === 0) return 0;
    let peak = 0;
    let sumSq = 0;
    for (let i = 0; i < samples.length; i += 1) {
        const value = Math.abs(Number(samples[i])) / scale;
        if (value > peak) peak = value;
        sumSq += value * value;
    }
    const rms = Math.sqrt(sumSq / samples.length);
    const boosted = Math.max(peak * 0.8, rms * 2.4);
    if (!Number.isFinite(boosted)) return 0;
    const normalized = boosted > 1 && boosted <= 100 ? boosted / 100 : boosted;
    return Math.max(0, Math.min(1, normalized));
}

/**
 * Creates or returns an active AudioContext
 */
export function getOrCreateAudioContext(existing: AudioContext | null): AudioContext {
    if (existing && existing.state !== "closed") {
        return existing;
    }
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextCtor) {
        throw new Error("AudioContext is unavailable");
    }
    try {
        return new AudioContextCtor({ sampleRate: DEFAULT_AUDIO_SAMPLE_RATE });
    } catch {
        return new AudioContextCtor();
    }
}

/**
 * Resumes AudioContext if suspended
 */
export async function resumeAudioContext(ctx: AudioContext | null): Promise<void> {
    if (ctx && ctx.state === "suspended" && typeof ctx.resume === "function") {
        try {
            await ctx.resume();
        } catch {
            // ignore
        }
    }
}

export interface PlaybackState {
    audioCtx: AudioContext | null;
    remoteAudioEl: HTMLAudioElement | null;
    selectedAudioOutputId: string;
}

/**
 * Plays remote PCM audio buffer through Web Audio API destination or element
 */
export function playRemotePcmBuffer(
    arrayBuffer: ArrayBuffer,
    state: PlaybackState,
    onRemoteLevel?: (level: number) => void
): void {
    if (!state.audioCtx || !arrayBuffer) return;
    const pcm = extractInt16Samples(arrayBuffer);
    if (!pcm || pcm.length === 0) return;

    if (onRemoteLevel) {
        const remoteLevel = computeSignalLevel(pcm, INT16_SAMPLE_MAX);
        onRemoteLevel(remoteLevel);
    }

    const floatBuf = new Float32Array(pcm.length);
    for (let i = 0; i < pcm.length; i += 1) {
        floatBuf[i] = (pcm[i] ?? 0) / INT16_SAMPLE_MAX;
    }
    const audioBuffer = state.audioCtx.createBuffer(1, floatBuf.length, DEFAULT_AUDIO_SAMPLE_RATE);
    audioBuffer.copyToChannel(floatBuf, 0);
    const bufferSource = state.audioCtx.createBufferSource();
    bufferSource.buffer = audioBuffer;

    const sinkId = state.selectedAudioOutputId;
    const useSetSinkId =
        sinkId && sinkId !== DEFAULT_AUDIO_OUTPUT_DEVICE_ID && "setSinkId" in HTMLMediaElement.prototype;

    if (useSetSinkId) {
        if (!state.remoteAudioEl) {
            state.remoteAudioEl = new Audio();
            state.remoteAudioEl.autoplay = true;
        }
        const dest = state.audioCtx.createMediaStreamDestination();
        bufferSource.connect(dest);
        bufferSource.start();
        state.remoteAudioEl.srcObject = dest.stream;
        (state.remoteAudioEl as any).setSinkId(sinkId).catch((err: unknown) => console.warn("setSinkId failed", err));
    } else {
        bufferSource.connect(state.audioCtx.destination);
        bufferSource.start();
    }
}

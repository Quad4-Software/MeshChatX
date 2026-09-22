// SPDX-License-Identifier: 0BSD

import {
    VISUALIZER_BG_COLOR,
    VISUALIZER_CENTER_LINE_COLOR,
    VISUALIZER_DECAY_LEVEL,
    VISUALIZER_DECAY_TARGET,
    VISUALIZER_DEFAULT_HEIGHT,
    VISUALIZER_DEFAULT_WIDTH,
    VISUALIZER_LOCAL_COLOR,
    VISUALIZER_MIN_HEIGHT,
    VISUALIZER_MIN_WIDTH,
    VISUALIZER_PHASE_STEP,
    VISUALIZER_REMOTE_COLOR,
    VISUALIZER_STEP,
} from "./constants.js";
import type { ActiveCall } from "./types.js";

export interface VisualizerState {
    localAudioLevel: number;
    remoteAudioLevel: number;
    localAudioTarget: number;
    remoteAudioTarget: number;
    visualizerPhase: number;
    prevCallTxBytes: number;
    prevCallRxBytes: number;
    visualizerRafId: number | null;
    visualizerEnabled: boolean;
}

/**
 * Creates default initial visualizer state
 */
export function createInitialVisualizerState(): VisualizerState {
    return {
        localAudioLevel: 0,
        remoteAudioLevel: 0,
        localAudioTarget: 0,
        remoteAudioTarget: 0,
        visualizerPhase: 0,
        prevCallTxBytes: 0,
        prevCallRxBytes: 0,
        visualizerRafId: null,
        visualizerEnabled: true,
    };
}

/**
 * Captures the absolute peak level from a buffer of samples
 */
export function capturePeakLevel(samples: Int16Array | Float32Array | number[] | null | undefined): number {
    if (!samples || samples.length === 0) return 0;
    let peak = 0;
    for (let i = 0; i < samples.length; i += 1) {
        const value = Math.abs(Number(samples[i]));
        if (value > peak) peak = value;
    }
    return peak;
}

/**
 * Normalizes an audio level to a 0.0 to 1.0 range
 */
export function normalizeAudioLevel(level: number | null | undefined): number {
    const val = Number(level);
    if (!Number.isFinite(val)) return 0;
    const normalized = val > 1 && val <= 100 ? val / 100 : val;
    return Math.max(0, Math.min(1, normalized));
}

/**
 * Computes signal level using peak and RMS
 */
export function computeSignalLevel(
    samples: Int16Array | Float32Array | number[] | null | undefined,
    scale: number = 1
): number {
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
    return normalizeAudioLevel(boosted);
}

/**
 * Updates visualizer targets from call link statistics when real PCM audio stream is not active
 */
export function updateVisualizerFromCallStats(
    newCall: ActiveCall | null | undefined,
    oldCall: ActiveCall | null | undefined,
    state: VisualizerState,
    hasRealAudioStream: boolean = false
): void {
    if (!newCall || newCall.status !== 6) {
        state.prevCallTxBytes = 0;
        state.prevCallRxBytes = 0;
        state.localAudioTarget = 0;
        state.remoteAudioTarget = 0;
        return;
    }

    if (hasRealAudioStream) {
        state.prevCallTxBytes = Number(newCall.tx_bytes || 0);
        state.prevCallRxBytes = Number(newCall.rx_bytes || 0);
        return;
    }

    const tx = Number(newCall.tx_bytes || 0);
    const rx = Number(newCall.rx_bytes || 0);
    const prevTx = oldCall && oldCall.hash === newCall.hash ? state.prevCallTxBytes : tx;
    const prevRx = oldCall && oldCall.hash === newCall.hash ? state.prevCallRxBytes : rx;
    const txDelta = Math.max(0, tx - prevTx);
    const rxDelta = Math.max(0, rx - prevRx);

    const txLevel = normalizeAudioLevel(Math.log10(1 + txDelta) / 2.8);
    const rxLevel = normalizeAudioLevel(Math.log10(1 + rxDelta) / 2.8);
    state.localAudioTarget = Math.max(state.localAudioTarget, txLevel);
    state.remoteAudioTarget = Math.max(state.remoteAudioTarget, rxLevel);
    state.localAudioLevel = Math.max(state.localAudioLevel, state.localAudioTarget);
    state.remoteAudioLevel = Math.max(state.remoteAudioLevel, state.remoteAudioTarget);

    state.prevCallTxBytes = tx;
    state.prevCallRxBytes = rx;
}

/**
 * Resizes canvas taking into account device pixel ratio
 */
export function resizeAudioVisualizerCanvas(canvas: HTMLCanvasElement | null | undefined): boolean {
    if (!canvas) return false;
    const cssWidth = Math.max(VISUALIZER_MIN_WIDTH, Math.floor(canvas.clientWidth || VISUALIZER_DEFAULT_WIDTH));
    const cssHeight = Math.max(VISUALIZER_MIN_HEIGHT, Math.floor(canvas.clientHeight || VISUALIZER_DEFAULT_HEIGHT));
    const dpr = Math.max(1, typeof window !== "undefined" ? Number(window.devicePixelRatio) || 1 : 1);
    const targetWidth = Math.floor(cssWidth * dpr);
    const targetHeight = Math.floor(cssHeight * dpr);
    if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
        canvas.width = targetWidth;
        canvas.height = targetHeight;
    }
    return true;
}

/**
 * Draws a single waveform path onto 2D canvas context
 */
export function drawWavePath(
    ctx: CanvasRenderingContext2D,
    level: number,
    color: string,
    phaseOffset: number,
    direction: number,
    width: number,
    height: number,
    centerY: number,
    phase: number
): void {
    const clampedLevel = normalizeAudioLevel(level);
    if (clampedLevel < 0.003) {
        return;
    }
    const amp = clampedLevel * (height * 0.4);
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    for (let x = 0; x <= width; x += VISUALIZER_STEP) {
        const t = (x / width) * Math.PI * 6 + phase + phaseOffset;
        const envelope = 0.5 + 0.5 * Math.sin((x / width) * Math.PI);
        const y = centerY + direction * Math.sin(t) * amp * envelope;
        if (x === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
}

/**
 * Renders a complete visualizer frame onto canvas context and updates decay
 */
export function renderVisualizerFrame(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number,
    state: VisualizerState
): void {
    const centerY = height / 2;
    state.visualizerPhase += VISUALIZER_PHASE_STEP;
    state.localAudioTarget *= VISUALIZER_DECAY_TARGET;
    state.remoteAudioTarget *= VISUALIZER_DECAY_TARGET;
    state.localAudioLevel = Math.max(state.localAudioLevel * VISUALIZER_DECAY_LEVEL, state.localAudioTarget);
    state.remoteAudioLevel = Math.max(state.remoteAudioLevel * VISUALIZER_DECAY_LEVEL, state.remoteAudioTarget);

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = VISUALIZER_BG_COLOR;
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = VISUALIZER_CENTER_LINE_COLOR;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();

    drawWavePath(
        ctx,
        state.localAudioLevel,
        VISUALIZER_LOCAL_COLOR,
        0,
        -1,
        width,
        height,
        centerY,
        state.visualizerPhase
    );
    drawWavePath(
        ctx,
        state.remoteAudioLevel,
        VISUALIZER_REMOTE_COLOR,
        Math.PI / 2,
        1,
        width,
        height,
        centerY,
        state.visualizerPhase
    );
}

/**
 * Controller to start and stop canvas animation loop
 */
export class AudioVisualizerController {
    private canvasGetter: () => HTMLCanvasElement | null | undefined;
    private state: VisualizerState;

    constructor(canvasGetter: () => HTMLCanvasElement | null | undefined, state?: VisualizerState) {
        this.canvasGetter = canvasGetter;
        this.state = state || createInitialVisualizerState();
    }

    public getState(): VisualizerState {
        return this.state;
    }

    public start(): void {
        if (!this.state.visualizerEnabled || this.state.visualizerRafId) {
            return;
        }
        if (
            typeof window === "undefined" ||
            typeof window.requestAnimationFrame !== "function" ||
            typeof window.cancelAnimationFrame !== "function"
        ) {
            this.state.visualizerEnabled = false;
            return;
        }
        const canvas = this.canvasGetter();
        if (!canvas || typeof canvas.getContext !== "function") {
            return;
        }
        if (!resizeAudioVisualizerCanvas(canvas)) {
            this.state.visualizerEnabled = false;
            return;
        }
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            this.state.visualizerEnabled = false;
            return;
        }

        const loop = () => {
            const currentCanvas = this.canvasGetter();
            if (!currentCanvas || typeof currentCanvas.getContext !== "function") {
                this.stop();
                return;
            }
            if (!resizeAudioVisualizerCanvas(currentCanvas)) {
                this.disable();
                return;
            }
            const currentCtx = currentCanvas.getContext("2d");
            if (!currentCtx) {
                this.disable();
                return;
            }
            renderVisualizerFrame(currentCtx, currentCanvas.width, currentCanvas.height, this.state);
            this.state.visualizerRafId = window.requestAnimationFrame(loop);
        };

        this.state.visualizerRafId = window.requestAnimationFrame(loop);
    }

    public stop(): void {
        if (this.state.visualizerRafId && typeof window !== "undefined") {
            window.cancelAnimationFrame(this.state.visualizerRafId);
            this.state.visualizerRafId = null;
        }
        this.state.localAudioLevel = 0;
        this.state.remoteAudioLevel = 0;
        this.state.localAudioTarget = 0;
        this.state.remoteAudioTarget = 0;
    }

    public disable(): void {
        this.state.visualizerEnabled = false;
        this.stop();
    }
}

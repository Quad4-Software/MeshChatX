import { afterEach, describe, expect, it, vi } from "vitest";
import MicrophoneRecorder from "@/js/MicrophoneRecorder";

function installFakeAudioContext({ sampleRate = 48000, withScriptProcessor = false } = {}) {
    const workletNode = {
        port: {
            onmessage: null,
        },
        connect: vi.fn(),
        disconnect: vi.fn(),
    };
    const gainNode = {
        gain: { value: 0 },
        connect: vi.fn(),
        disconnect: vi.fn(),
    };
    const sourceNode = {
        connect: vi.fn(),
        disconnect: vi.fn(),
    };
    const scriptProcessorNode = withScriptProcessor
        ? { connect: vi.fn(), disconnect: vi.fn(), onaudioprocess: null }
        : null;
    const ctx = {
        sampleRate,
        destination: {},
        resume: vi.fn().mockResolvedValue(undefined),
        close: vi.fn().mockResolvedValue(undefined),
        createMediaStreamSource: vi.fn(() => sourceNode),
        createGain: vi.fn(() => gainNode),
        audioWorklet: {
            addModule: vi.fn().mockResolvedValue(undefined),
        },
    };
    if (withScriptProcessor) {
        ctx.createScriptProcessor = vi.fn(() => scriptProcessorNode);
    }
    const original = globalThis.AudioContext;
    const originalAWN = globalThis.AudioWorkletNode;
    globalThis.AudioContext = vi.fn(function FakeAudioContext() {
        return ctx;
    });
    globalThis.AudioWorkletNode = vi.fn(function FakeAudioWorkletNode() {
        return workletNode;
    });
    return {
        ctx,
        workletNode,
        gainNode,
        sourceNode,
        scriptProcessorNode,
        restore() {
            if (typeof original === "undefined") {
                Reflect.deleteProperty(globalThis, "AudioContext");
            } else {
                globalThis.AudioContext = original;
            }
            if (typeof originalAWN === "undefined") {
                Reflect.deleteProperty(globalThis, "AudioWorkletNode");
            } else {
                globalThis.AudioWorkletNode = originalAWN;
            }
        },
    };
}

function installMediaDevices(getUserMedia) {
    const original = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");
    Object.defineProperty(navigator, "mediaDevices", {
        configurable: true,
        value: { getUserMedia },
    });
    return () => {
        if (original) {
            Object.defineProperty(navigator, "mediaDevices", original);
        } else {
            Reflect.deleteProperty(navigator, "mediaDevices");
        }
    };
}

describe("MicrophoneRecorder", () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it("returns false when mediaDevices API is unavailable", async () => {
        const recorder = new MicrophoneRecorder();
        const restore = installMediaDevices(undefined);
        Object.defineProperty(navigator, "mediaDevices", {
            configurable: true,
            value: undefined,
        });

        try {
            await expect(recorder.start()).resolves.toBe(false);
        } finally {
            restore();
        }
    });

    it("returns false when AudioContext is unavailable", async () => {
        const recorder = new MicrophoneRecorder();
        const getUserMedia = vi.fn().mockResolvedValue({
            getTracks: () => [{ stop: vi.fn() }],
        });
        const restoreMedia = installMediaDevices(getUserMedia);

        const originalAC = globalThis.AudioContext;
        const originalWebkitAC = globalThis.webkitAudioContext;
        Reflect.deleteProperty(globalThis, "AudioContext");
        Reflect.deleteProperty(globalThis, "webkitAudioContext");

        try {
            await expect(recorder.start()).resolves.toBe(false);
            expect(getUserMedia).not.toHaveBeenCalled();
        } finally {
            if (typeof originalAC !== "undefined") globalThis.AudioContext = originalAC;
            if (typeof originalWebkitAC !== "undefined") globalThis.webkitAudioContext = originalWebkitAC;
            restoreMedia();
        }
    });

    it("rejects stop() before start()", async () => {
        const recorder = new MicrophoneRecorder();
        await expect(recorder.stop()).rejects.toThrow("Cannot stop recording before start()");
    });

    it("captures PCM samples and returns a WAV/PCM blob on stop", async () => {
        const stopTrack = vi.fn();
        const getUserMedia = vi.fn().mockResolvedValue({
            getTracks: () => [{ stop: stopTrack }],
        });
        const restoreMedia = installMediaDevices(getUserMedia);
        const audio = installFakeAudioContext({ sampleRate: 48000 });

        try {
            const recorder = new MicrophoneRecorder();
            await expect(recorder.start()).resolves.toBe(true);

            expect(audio.ctx.createMediaStreamSource).toHaveBeenCalledTimes(1);
            expect(audio.ctx.audioWorklet.addModule).toHaveBeenCalledTimes(1);
            expect(audio.ctx.audioWorklet.addModule.mock.calls[0][0]).toMatch(/^blob:/);
            expect(globalThis.AudioWorkletNode).toHaveBeenCalledWith(
                audio.ctx,
                "microphone-pcm-float",
                expect.objectContaining({
                    numberOfInputs: 1,
                    numberOfOutputs: 1,
                    channelCount: 1,
                })
            );
            expect(audio.sourceNode.connect).toHaveBeenCalledWith(audio.workletNode);
            expect(audio.workletNode.connect).toHaveBeenCalledWith(audio.gainNode);
            expect(audio.gainNode.connect).toHaveBeenCalledWith(audio.ctx.destination);

            const frame = new Float32Array(1024);
            for (let i = 0; i < frame.length; i++) {
                frame[i] = Math.sin((i / frame.length) * Math.PI * 2) * 0.5;
            }
            expect(typeof audio.workletNode.port.onmessage).toBe("function");
            audio.workletNode.port.onmessage({ data: frame.buffer.slice(0) });

            const blob = await recorder.stop();
            expect(blob).toBeInstanceOf(Blob);
            expect(blob.type).toBe("audio/wav");

            const buffer = await blob.arrayBuffer();
            const view = new DataView(buffer);
            const magic = String.fromCharCode(view.getUint8(0), view.getUint8(1), view.getUint8(2), view.getUint8(3));
            const wave = String.fromCharCode(view.getUint8(8), view.getUint8(9), view.getUint8(10), view.getUint8(11));
            expect(magic).toBe("RIFF");
            expect(wave).toBe("WAVE");
            expect(view.getUint16(20, true)).toBe(1);
            expect(view.getUint16(22, true)).toBe(1);
            expect(view.getUint32(24, true)).toBe(48000);
            expect(view.getUint16(34, true)).toBe(16);
            expect(buffer.byteLength).toBe(44 + frame.length * 2);
            expect(stopTrack).toHaveBeenCalledTimes(1);
            expect(audio.ctx.close).toHaveBeenCalledTimes(1);
        } finally {
            audio.restore();
            restoreMedia();
        }
    });

    it("captures via ScriptProcessor when not in a secure context", async () => {
        vi.stubGlobal("isSecureContext", false);
        const stopTrack = vi.fn();
        const getUserMedia = vi.fn().mockResolvedValue({
            getTracks: () => [{ stop: stopTrack }],
        });
        const restoreMedia = installMediaDevices(getUserMedia);
        const audio = installFakeAudioContext({ sampleRate: 48000, withScriptProcessor: true });

        try {
            const recorder = new MicrophoneRecorder();
            await expect(recorder.start()).resolves.toBe(true);

            expect(audio.ctx.audioWorklet.addModule).not.toHaveBeenCalled();
            expect(audio.ctx.createScriptProcessor).toHaveBeenCalledWith(4096, 1, 1);
            expect(audio.sourceNode.connect).toHaveBeenCalledWith(audio.scriptProcessorNode);
            expect(audio.scriptProcessorNode.connect).toHaveBeenCalledWith(audio.gainNode);

            const frame = new Float32Array(256);
            for (let i = 0; i < frame.length; i++) {
                frame[i] = 0.25;
            }
            expect(typeof audio.scriptProcessorNode.onaudioprocess).toBe("function");
            audio.scriptProcessorNode.onaudioprocess({
                inputBuffer: { getChannelData: () => frame },
            });

            const blob = await recorder.stop();
            expect(blob.type).toBe("audio/wav");
            const buffer = await blob.arrayBuffer();
            expect(buffer.byteLength).toBe(44 + frame.length * 2);
        } finally {
            audio.restore();
            restoreMedia();
        }
    });
});

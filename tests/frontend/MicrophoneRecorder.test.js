import { afterEach, describe, expect, it, vi } from "vitest";
import MicrophoneRecorder from "@/js/MicrophoneRecorder";

describe("MicrophoneRecorder", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("returns false when mediaDevices API is unavailable", async () => {
        const recorder = new MicrophoneRecorder();
        const mediaDevicesDescriptor = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");
        Object.defineProperty(navigator, "mediaDevices", {
            configurable: true,
            value: undefined,
        });

        try {
            await expect(recorder.start()).resolves.toBe(false);
        } finally {
            if (mediaDevicesDescriptor) {
                Object.defineProperty(navigator, "mediaDevices", mediaDevicesDescriptor);
            } else {
                Reflect.deleteProperty(navigator, "mediaDevices");
            }
        }
    });

    it("returns false when MediaRecorder is unavailable", async () => {
        const recorder = new MicrophoneRecorder();
        const originalMediaRecorder = globalThis.MediaRecorder;
        const getUserMedia = vi.fn().mockResolvedValue({
            getTracks: () => [{ stop: vi.fn() }],
        });
        Object.defineProperty(navigator, "mediaDevices", {
            configurable: true,
            value: {
                getUserMedia,
            },
        });

        Reflect.deleteProperty(globalThis, "MediaRecorder");

        try {
            await expect(recorder.start()).resolves.toBe(false);
            expect(getUserMedia).not.toHaveBeenCalled();
        } finally {
            if (typeof originalMediaRecorder === "undefined") {
                Reflect.deleteProperty(globalThis, "MediaRecorder");
            } else {
                globalThis.MediaRecorder = originalMediaRecorder;
            }
        }
    });

    it("rejects stop() before start()", async () => {
        const recorder = new MicrophoneRecorder();
        await expect(recorder.stop()).rejects.toThrow("Cannot stop recording before start()");
    });

    it("stops tracks and resolves a blob on successful stop", async () => {
        const stopTrack = vi.fn();
        const getUserMedia = vi.fn().mockResolvedValue({
            getTracks: () => [{ stop: stopTrack }],
        });
        const mediaDevicesDescriptor = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");
        Object.defineProperty(navigator, "mediaDevices", {
            configurable: true,
            value: {
                getUserMedia,
            },
        });

        const originalMediaRecorder = globalThis.MediaRecorder;
        class FakeMediaRecorder {
            constructor() {
                this.mimeType = "audio/webm";
                this.ondataavailable = null;
                this.onstop = null;
            }

            start() {
                if (this.ondataavailable) {
                    this.ondataavailable({ data: new Blob(["audio"], { type: this.mimeType }) });
                }
            }

            stop() {
                if (this.onstop) {
                    this.onstop();
                }
            }
        }
        globalThis.MediaRecorder = FakeMediaRecorder;
        const recorder = new MicrophoneRecorder();

        try {
            await expect(recorder.start()).resolves.toBe(true);
            const blob = await recorder.stop();
            expect(blob).toBeInstanceOf(Blob);
            expect(blob.type).toBe("audio/webm");
            expect(stopTrack).toHaveBeenCalledTimes(1);
        } finally {
            if (mediaDevicesDescriptor) {
                Object.defineProperty(navigator, "mediaDevices", mediaDevicesDescriptor);
            } else {
                Reflect.deleteProperty(navigator, "mediaDevices");
            }
            if (typeof originalMediaRecorder === "undefined") {
                Reflect.deleteProperty(globalThis, "MediaRecorder");
            } else {
                globalThis.MediaRecorder = originalMediaRecorder;
            }
        }
    });
});

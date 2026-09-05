import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AudioWaveformPlayer from "../../meshchatx/src/frontend/features/messages/components/AudioWaveformPlayer.svelte";

class MockAudioContext {
    constructor() {
        this.state = "suspended";
        this.currentTime = 0;
        this.destination = {};
    }
    decodeAudioData() {
        return Promise.resolve({
            duration: 10,
            getChannelData: () => new Float32Array(100),
            numberOfChannels: 1,
            sampleRate: 44100,
        });
    }
    createBufferSource() {
        return {
            buffer: null,
            connect: vi.fn(),
            start: vi.fn(),
            stop: vi.fn(),
            onended: null,
        };
    }
    resume() {
        this.state = "running";
        return Promise.resolve();
    }
    close() {
        return Promise.resolve();
    }
}

global.fetch = vi.fn(() =>
    Promise.resolve({
        ok: true,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
    })
);

HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    scale: vi.fn(),
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
}));

describe("AudioWaveformPlayer.svelte", () => {
    beforeEach(() => {
        vi.stubGlobal("AudioContext", MockAudioContext);
        vi.stubGlobal("webkitAudioContext", MockAudioContext);
    });

    afterEach(() => {
        cleanup();
        vi.clearAllMocks();
        vi.unstubAllGlobals();
    });

    it("renders and loads audio", async () => {
        const { container } = render(AudioWaveformPlayer, { props: { src: "test-audio.wav" } });
        expect(container.querySelector(".audio-waveform-player")).toBeTruthy();
        await waitFor(() => expect(screen.getByText("0:00 / 0:10")).toBeTruthy());
        expect(container.querySelector("canvas")?.hidden).toBe(false);
    });

    it("starts playback", async () => {
        const onplay = vi.fn();
        render(AudioWaveformPlayer, { props: { src: "test-audio.wav", onplay } });
        await waitFor(() => expect(screen.getByText("0:00 / 0:10")).toBeTruthy());
        const playButton = screen.getByRole("button");
        await fireEvent.click(playButton);
        expect(onplay).toHaveBeenCalledOnce();
    });

    it("formats unloaded time", () => {
        render(AudioWaveformPlayer, { props: { src: "" } });
        expect(screen.getByText("0:00 / 0:00")).toBeTruthy();
    });
});

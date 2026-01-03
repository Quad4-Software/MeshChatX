import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AudioWaveformPlayer from "../../meshchatx/src/frontend/components/messages/AudioWaveformPlayer.vue";

// Mock AudioContext
class MockAudioContext {
    constructor() {
        this.state = "suspended";
        this.currentTime = 0;
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

// Mock fetch
global.fetch = vi.fn(() =>
    Promise.resolve({
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
    })
);

// Mock Canvas
HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    scale: vi.fn(),
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
}));

describe("AudioWaveformPlayer.vue", () => {
    beforeEach(() => {
        vi.stubGlobal("AudioContext", MockAudioContext);
        vi.stubGlobal("webkitAudioContext", MockAudioContext);
    });

    it("renders and loads audio", async () => {
        const wrapper = mount(AudioWaveformPlayer, {
            props: {
                src: "test-audio.wav",
            },
            global: {
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });

        expect(wrapper.find(".audio-waveform-player").exists()).toBe(true);

        // Wait for audio to load
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        expect(wrapper.vm.totalDuration).toBe(10);
        expect(wrapper.find("canvas").isVisible()).toBe(true);
    });

    it("toggles playback", async () => {
        const wrapper = mount(AudioWaveformPlayer, {
            props: {
                src: "test-audio.wav",
            },
            global: {
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });

        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));

        const playButton = wrapper.find("button");
        await playButton.trigger("click");

        expect(wrapper.vm.isPlaying).toBe(true);
        expect(wrapper.emitted("play")).toBeTruthy();

        await playButton.trigger("click");
        expect(wrapper.vm.isPlaying).toBe(false);
    });

    it("formats time correctly", () => {
        const wrapper = mount(AudioWaveformPlayer, {
            props: { src: "" },
            global: { stubs: { MaterialDesignIcon: true } },
        });

        expect(wrapper.vm.formatTime(65)).toBe("1:05");
        expect(wrapper.vm.formatTime(10)).toBe("0:10");
        expect(wrapper.vm.formatTime(3600)).toBe("60:00");
    });
});

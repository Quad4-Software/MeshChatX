import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AudioWaveformPlayer from "../../meshchatx/src/frontend/components/messages/AudioWaveformPlayer.vue";

// Mock AudioContext
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

// Mock fetch
global.fetch = vi.fn(() =>
    Promise.resolve({
        ok: true,
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

        await vi.waitFor(() => expect(wrapper.vm.isPlaying).toBe(true));
        expect(wrapper.emitted("play")).toBeTruthy();

        await playButton.trigger("click");
        expect(wrapper.vm.isPlaying).toBe(false);
        wrapper.unmount();
    });

    it("creates the playback context lazily and resumes before starting", async () => {
        const wrapper = mount(AudioWaveformPlayer, {
            props: { src: "test-audio.wav" },
            global: { stubs: { MaterialDesignIcon: true } },
        });

        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));
        expect(wrapper.vm.audioContext).toBe(null);

        await wrapper.find("button").trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.isPlaying).toBe(true));

        expect(wrapper.vm.audioContext.state).toBe("running");
        expect(wrapper.vm.playbackMode).toBe("webaudio");
        expect(wrapper.vm.sourceNode.start).toHaveBeenCalled();
        wrapper.unmount();
    });

    function stubElementPlayback() {
        const instances = [];
        vi.stubGlobal(
            "Audio",
            vi.fn(function (src) {
                const el = {
                    src,
                    preload: "",
                    currentTime: 0,
                    duration: 10,
                    readyState: 4,
                    paused: true,
                    onended: null,
                    play: vi.fn().mockResolvedValue(undefined),
                    pause: vi.fn(),
                    addEventListener: vi.fn(),
                };
                instances.push(el);
                return el;
            })
        );
        URL.createObjectURL = vi.fn(() => "blob:mock-audio");
        URL.revokeObjectURL = vi.fn();
        return instances;
    }

    it("falls back to HTMLAudioElement when the context never runs", async () => {
        class StuckAudioContext extends MockAudioContext {
            resume() {
                return Promise.resolve();
            }
        }
        vi.stubGlobal("AudioContext", StuckAudioContext);
        vi.stubGlobal("webkitAudioContext", StuckAudioContext);
        const audioInstances = stubElementPlayback();

        const wrapper = mount(AudioWaveformPlayer, {
            props: { src: "test-audio.wav" },
            global: { stubs: { MaterialDesignIcon: true } },
        });

        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));
        await wrapper.find("button").trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.isPlaying).toBe(true));

        expect(wrapper.vm.playbackMode).toBe("element");
        expect(wrapper.vm.audioElement.src).toBe("blob:mock-audio");
        expect(audioInstances[0].play).toHaveBeenCalled();
        expect(wrapper.emitted("play")).toBeTruthy();
        wrapper.unmount();
    });

    it("falls back to HTMLAudioElement when decode fails", async () => {
        class DecodeFailContext extends MockAudioContext {
            decodeAudioData() {
                return Promise.reject(new Error("decode failed"));
            }
        }
        vi.stubGlobal("AudioContext", DecodeFailContext);
        vi.stubGlobal("webkitAudioContext", DecodeFailContext);
        const audioInstances = stubElementPlayback();

        const wrapper = mount(AudioWaveformPlayer, {
            props: { src: "test-audio.wav" },
            global: { stubs: { MaterialDesignIcon: true } },
        });

        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));
        expect(wrapper.vm.audioBuffer).toBe(null);
        expect(wrapper.vm.useElementPlayback).toBe(true);

        await wrapper.find("button").trigger("click");
        await vi.waitFor(() => expect(wrapper.vm.isPlaying).toBe(true));

        expect(wrapper.vm.playbackMode).toBe("element");
        expect(audioInstances[0].play).toHaveBeenCalled();
        wrapper.unmount();
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

afterEach(() => {
    delete URL.createObjectURL;
    delete URL.revokeObjectURL;
});

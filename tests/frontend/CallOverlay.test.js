import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import CallOverlay from "@/components/call/CallOverlay.vue";

describe("CallOverlay.vue", () => {
    const defaultProps = {
        activeCall: {
            remote_identity_hash: "test_hash_long_enough_to_format",
            remote_identity_name: "Test User",
            status: 6, // Established
            is_incoming: false,
            is_voicemail: false,
            call_start_time: Date.now() / 1000 - 60, // 1 minute ago
            tx_bytes: 1024,
            rx_bytes: 2048,
        },
        isEnded: false,
        wasDeclined: false,
        voicemailStatus: {
            is_recording: false,
        },
    };

    const mountCallOverlay = (props = {}) => {
        return mount(CallOverlay, {
            props: { ...defaultProps, ...props },
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: {
                        push: vi.fn(),
                    },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LxmfUserIcon: true,
                    AudioWaveformPlayer: true,
                },
            },
        });
    };

    it("renders when there is an active call", () => {
        const wrapper = mountCallOverlay();
        expect(wrapper.exists()).toBe(true);
        expect(wrapper.text()).toContain("Test User");
        expect(wrapper.text()).toContain("call.active_call");
    });

    it("shows remote hash if name is missing", () => {
        const wrapper = mountCallOverlay({
            activeCall: {
                ...defaultProps.activeCall,
                remote_identity_name: null,
                remote_identity_hash: "deadbeefcafebabe",
            },
        });
        // The formatter produces <deadbeef...cafebabe>
        expect(wrapper.text()).toContain("deadbeef");
        expect(wrapper.text()).toContain("cafebabe");
    });

    it("toggles minimization when chevron is clicked", async () => {
        const wrapper = mountCallOverlay();

        // Initial state
        expect(wrapper.vm.isMinimized).toBe(false);

        // Find the minimize button - it's the button with chevron icon in the header
        // Since MaterialDesignIcon is stubbed, we find it by finding buttons in the header
        // The minimize button is the last button in the header section
        const header = wrapper.find(".p-3.flex.items-center");
        const headerButtons = header.findAll("button");
        const minimizeButton = headerButtons[headerButtons.length - 1];

        await minimizeButton.trigger("click");
        expect(wrapper.vm.isMinimized).toBe(true);

        await minimizeButton.trigger("click");
        expect(wrapper.vm.isMinimized).toBe(false);
    });

    it("emits hangup event when hangup button is clicked", async () => {
        const wrapper = mountCallOverlay();
        // The hangup button has @click="hangupCall"
        // Find the button with phone-hangup icon stub
        const buttons = wrapper.findAll("button");
        const hangupButton = buttons.find((b) => b.attributes("title") === "call.hangup_call");

        if (hangupButton) {
            await hangupButton.trigger("click");
            expect(wrapper.emitted().hangup).toBeTruthy();
        } else {
            // fallback to finding by class if title stubbing is weird
            const redButton = wrapper.find("button.bg-red-600");
            await redButton.trigger("click");
            expect(wrapper.emitted().hangup).toBeTruthy();
        }
    });

    it("displays 'call.recording_voicemail' when voicemail is active", () => {
        const wrapper = mountCallOverlay({
            activeCall: {
                ...defaultProps.activeCall,
                is_voicemail: true,
            },
        });
        expect(wrapper.text()).toContain("call.recording_voicemail");
    });

    it("displays 'call.call_ended' when isEnded is true", () => {
        const wrapper = mountCallOverlay({
            isEnded: true,
        });
        expect(wrapper.text()).toContain("call.call_ended");
    });

    it("displays 'call.call_declined' when wasDeclined is true", () => {
        const wrapper = mountCallOverlay({
            wasDeclined: true,
        });
        expect(wrapper.text()).toContain("call.call_declined");
    });

    it("shows duration timer for active calls", () => {
        const wrapper = mountCallOverlay({
            activeCall: {
                ...defaultProps.activeCall,
                call_start_time: Math.floor(Date.now() / 1000) - 75, // 1:15 ago
            },
        });
        // 01:15 should be present
        expect(wrapper.text()).toContain("01:15");
    });

    it("handles extremely long names in the overlay", () => {
        const extremelyLongName = "Very ".repeat(20) + "Long Name";
        const wrapper = mountCallOverlay({
            activeCall: {
                ...defaultProps.activeCall,
                remote_identity_name: extremelyLongName,
            },
        });
        const nameElement = wrapper.find(".truncate");
        expect(nameElement.exists()).toBe(true);
        expect(nameElement.text()).toContain("Long Name");
    });

    it("handles large transfer statistics", () => {
        const wrapper = mountCallOverlay({
            activeCall: {
                ...defaultProps.activeCall,
                tx_bytes: 1024 * 1024 * 1024 * 5, // 5 GB
                rx_bytes: 1024 * 1024 * 500, // 500 MB
            },
        });
        expect(wrapper.text()).toContain("5 GB");
        expect(wrapper.text()).toContain("500 MB");
    });

    it("navigates to Call phone tab after answering", async () => {
        const push = vi.fn().mockResolvedValue(undefined);
        global.api = { get: vi.fn().mockResolvedValue({}), post: vi.fn().mockResolvedValue({}) };
        const wrapper = mount(CallOverlay, {
            props: {
                ...defaultProps,
                activeCall: {
                    ...defaultProps.activeCall,
                    is_incoming: true,
                    status: 4,
                },
            },
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: { push },
                    $route: { name: "messages", query: {} },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LxmfUserIcon: true,
                    AudioWaveformPlayer: true,
                },
            },
        });
        await wrapper.vm.answerCall();
        expect(global.api.post).toHaveBeenCalledWith("/api/v1/telephone/answer");
        expect(push).toHaveBeenCalledWith({ name: "call", query: { tab: "phone" } });
    });

    it("answerCall probes getUserMedia with bare audio before posting", async () => {
        const stop = vi.fn();
        const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] });
        const mediaDesc = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");
        Object.defineProperty(navigator, "mediaDevices", {
            configurable: true,
            value: { getUserMedia, enumerateDevices: vi.fn().mockResolvedValue([]) },
        });
        global.api = { get: vi.fn().mockResolvedValue({}), post: vi.fn().mockResolvedValue({}) };
        const wrapper = mount(CallOverlay, {
            props: {
                ...defaultProps,
                activeCall: {
                    ...defaultProps.activeCall,
                    is_incoming: true,
                    status: 4,
                },
            },
            global: {
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn().mockResolvedValue(undefined) },
                    $route: { name: "call", query: { tab: "phone" } },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LxmfUserIcon: true,
                    AudioWaveformPlayer: true,
                },
            },
        });
        try {
            await wrapper.vm.answerCall();
            expect(getUserMedia).toHaveBeenCalledWith({ audio: true });
            expect(stop).toHaveBeenCalled();
            expect(global.api.post).toHaveBeenCalledWith("/api/v1/telephone/answer");
        } finally {
            if (mediaDesc) {
                Object.defineProperty(navigator, "mediaDevices", mediaDesc);
            } else {
                Reflect.deleteProperty(navigator, "mediaDevices");
            }
        }
    });
});

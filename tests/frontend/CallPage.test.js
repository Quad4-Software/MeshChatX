import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import CallPage from "@/components/call/CallPage.vue";

describe("CallPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                const defaultData = {
                    config: {},
                    calls: [],
                    call_history: [],
                    announces: [],
                    voicemails: [],
                    active_call: null,
                    discovery: [],
                    contacts: [],
                    profiles: [],
                    ringtones: [],
                    voicemail: { unread_count: 0 },
                };

                if (url.includes("/api/v1/config")) return Promise.resolve({ data: { config: {} } });
                if (url.includes("/api/v1/telephone/history")) return Promise.resolve({ data: { call_history: [] } });
                if (url.includes("/api/v1/announces")) return Promise.resolve({ data: { announces: [] } });
                if (url.includes("/api/v1/telephone/status")) return Promise.resolve({ data: { active_call: null } });
                if (url.includes("/api/v1/telephone/voicemail/status"))
                    return Promise.resolve({ data: { has_espeak: false } });
                if (url.includes("/api/v1/telephone/ringtones/status"))
                    return Promise.resolve({ data: { enabled: true } });
                if (url.includes("/api/v1/telephone/ringtones")) return Promise.resolve({ data: { ringtones: [] } });
                if (url.includes("/api/v1/telephone/audio-profiles"))
                    return Promise.resolve({ data: { audio_profiles: [], default_audio_profile_id: null } });
                if (url.includes("/api/v1/contacts")) return Promise.resolve({ data: { contacts: [] } });

                return Promise.resolve({ data: defaultData });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
    });

    const mountCallPage = (routeQuery = {}) => {
        return mount(CallPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: {
                        query: routeQuery,
                    },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LoadingSpinner: true,
                    LxmfUserIcon: true,
                    Toggle: true,
                    AudioWaveformPlayer: true,
                    RingtoneEditor: true,
                },
            },
        });
    };

    it("respects tab query parameter on mount", async () => {
        const wrapper = mountCallPage({ tab: "voicemail" });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.activeTab).toBe("voicemail");
    });

    it("performs optimistic mute updates", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();

        // Setup active call
        wrapper.vm.activeCall = {
            status: 6, // ESTABLISHED
            is_mic_muted: false,
            is_speaker_muted: false,
        };
        await wrapper.vm.$nextTick();

        // Toggle mic
        await wrapper.vm.toggleMicrophone();

        // Should be muted immediately (optimistic)
        expect(wrapper.vm.activeCall.is_mic_muted).toBe(true);
        expect(axiosMock.get).toHaveBeenCalledWith(expect.stringContaining("/api/v1/telephone/mute-transmit"));
    });

    it("renders tabs correctly", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();

        // The tabs are hardcoded strings: Phone, Phonebook, Voicemail, Contacts
        expect(wrapper.text()).toContain("Phone");
        expect(wrapper.text()).toContain("Phonebook");
        expect(wrapper.text()).toContain("Voicemail");
        expect(wrapper.text()).toContain("Contacts");
    });

    it("switches tabs when clicked", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();

        // Initial tab should be phone
        expect(wrapper.vm.activeTab).toBe("phone");

        // Click Phonebook tab
        const buttons = wrapper.findAll("button");
        const phonebookTab = buttons.find((b) => b.text() === "Phonebook");
        if (phonebookTab) {
            await phonebookTab.trigger("click");
            expect(wrapper.vm.activeTab).toBe("phonebook");
        } else {
            throw new Error("Phonebook tab not found");
        }
    });

    it("displays 'New Call' UI by default when no active call", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("New Call");
        expect(wrapper.find('input[type="text"]').exists()).toBe(true);
    });

    it("attempts to place a call when 'Call' button is clicked", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();

        const input = wrapper.find('input[type="text"]');
        await input.setValue("test-destination");

        // Find Call button - it's hardcoded "Call"
        const buttons = wrapper.findAll("button");
        const callButton = buttons.find((b) => b.text() === "Call");
        if (callButton) {
            await callButton.trigger("click");
            // CallPage.vue uses window.api.get(`/api/v1/telephone/call/${hashToCall}`)
            expect(axiosMock.get).toHaveBeenCalledWith(
                expect.stringContaining("/api/v1/telephone/call/test-destination")
            );
        } else {
            throw new Error("Call button not found");
        }
    });

    // Keep in sync with tests/backend/test_lxst_telephony_profiles_contract.py
    const LXST_TELEPHONY_AUDIO_PROFILES_CONTRACT = {
        default_audio_profile_id: 64,
        audio_profiles: [
            { id: 16, name: "Ultra Low Bandwidth" },
            { id: 32, name: "Very Low Bandwidth" },
            { id: 48, name: "Low Bandwidth" },
            { id: 64, name: "Medium Quality" },
            { id: 80, name: "High Quality" },
            { id: 96, name: "Super High Quality" },
            { id: 112, name: "Ultra Low Latency" },
            { id: 128, name: "Low Latency" },
        ],
    };

    it("getAudioProfiles maps API default and profile list (LXST contract)", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        axiosMock.get.mockResolvedValueOnce({ data: LXST_TELEPHONY_AUDIO_PROFILES_CONTRACT });
        await wrapper.vm.getAudioProfiles();
        expect(wrapper.vm.audioProfiles).toEqual(LXST_TELEPHONY_AUDIO_PROFILES_CONTRACT.audio_profiles);
        expect(wrapper.vm.selectedAudioProfileId).toBe(64);
    });

    it("toggleDoNotDisturb patches config", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.config = { do_not_disturb_enabled: false };
        await wrapper.vm.toggleDoNotDisturb(true);
        expect(axiosMock.patch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/config"), {
            do_not_disturb_enabled: true,
        });
    });

    it("toggleAllowCallsFromContactsOnly patches config", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.config = { telephone_allow_calls_from_contacts_only: false };
        await wrapper.vm.toggleAllowCallsFromContactsOnly(true);
        expect(axiosMock.patch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/config"), {
            telephone_allow_calls_from_contacts_only: true,
        });
    });

    it("ensureWebAudio stops when web audio bridge disabled", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.config = { telephone_web_audio_enabled: false };
        const stop = vi.spyOn(wrapper.vm, "stopWebAudio");
        await wrapper.vm.ensureWebAudio({ enabled: true });
        expect(stop).toHaveBeenCalled();
    });

    it("ensureWebAudio starts when bridge enabled and call active", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.config = { telephone_web_audio_enabled: true };
        wrapper.vm.activeCall = { status: 6 };
        const start = vi.spyOn(wrapper.vm, "startWebAudio").mockResolvedValue(undefined);
        await wrapper.vm.ensureWebAudio({ enabled: true, frame_ms: 48 });
        expect(start).toHaveBeenCalled();
        expect(wrapper.vm.audioFrameMs).toBe(48);
    });

    it("ensureWebAudio stops when no active call", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.config = { telephone_web_audio_enabled: true };
        wrapper.vm.activeCall = null;
        const stop = vi.spyOn(wrapper.vm, "stopWebAudio");
        await wrapper.vm.ensureWebAudio({ enabled: true });
        expect(stop).toHaveBeenCalled();
    });
});

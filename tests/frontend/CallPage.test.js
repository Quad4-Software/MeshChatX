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
        window.axios = axiosMock;
    });

    afterEach(() => {
        delete window.axios;
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
            // CallPage.vue uses window.axios.get(`/api/v1/telephone/call/${hashToCall}`)
            expect(axiosMock.get).toHaveBeenCalledWith(
                expect.stringContaining("/api/v1/telephone/call/test-destination")
            );
        } else {
            throw new Error("Call button not found");
        }
    });
});

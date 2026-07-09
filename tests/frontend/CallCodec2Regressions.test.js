/**
 * Regression guards for call dialing / contact form / Android ringtone policy.
 *
 * Locks in:
 * - 32-char RNS hash extraction (was only matching 64-char hex)
 * - History add-contact must not store LXMF/LXST dest as identity hash
 * - telephone_ringing respects block_all_from_strangers as well as contacts-only
 */
import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createRouter, createWebHashHistory } from "vue-router";
import { createI18n } from "vue-i18n";
import { createVuetify } from "vuetify";
import CallPage from "@/components/call/CallPage.vue";
import App from "../../meshchatx/src/frontend/components/App.vue";
import { appPackageVersion } from "./fixtures/repoPackageVersion.js";

const vuetify = createVuetify();
const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: {
        en: {
            call: {
                enter_identity_hash_to_call_error: "Enter a hash",
                name_and_hash_required: "Name and hash required",
            },
            app: {
                name: "MeshChatX",
                changelog_title: "What's New",
                do_not_show_again: "Do not show again",
            },
            common: { close: "Close" },
        },
    },
});

describe("Call dial / contact regressions", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (String(url).includes("/api/v1/config")) {
                    return Promise.resolve({
                        data: {
                            config: {
                                telephone_enabled: true,
                                telephone_allow_calls_from_contacts_only: true,
                                telephone_audio_profile_id: 64,
                            },
                        },
                    });
                }
                if (String(url).includes("/api/v1/telephone/status")) {
                    return Promise.resolve({
                        data: {
                            enabled: true,
                            active_call: null,
                            initiation_status: null,
                            web_audio: { enabled: false },
                        },
                    });
                }
                if (String(url).includes("/api/v1/telephone/audio-profiles")) {
                    return Promise.resolve({
                        data: { default_audio_profile_id: 64, audio_profiles: [] },
                    });
                }
                if (String(url).includes("/api/v1/telephone/contacts")) {
                    return Promise.resolve({ data: { contacts: [], total_count: 0 } });
                }
                if (String(url).includes("/api/v1/telephone/history")) {
                    return Promise.resolve({ data: { call_history: [] } });
                }
                if (String(url).includes("/api/v1/telephone/voicemail")) {
                    return Promise.resolve({
                        data: {
                            has_espeak: false,
                            is_recording: false,
                            is_greeting_recording: false,
                            has_greeting: false,
                            voicemails: [],
                            unread_count: 0,
                        },
                    });
                }
                if (String(url).includes("/api/v1/telephone/ringtones")) {
                    return Promise.resolve({ data: [] });
                }
                if (String(url).includes("/api/v1/telephone/call/")) {
                    return Promise.resolve({ data: { message: "Call initiation started" } });
                }
                if (String(url).includes("/api/v1/announces")) {
                    return Promise.resolve({ data: { announces: [] } });
                }
                return Promise.resolve({ data: {} });
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

    const mountCallPage = () =>
        mount(CallPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
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

    it("regression: dialer accepts 32-char RNS hashes from pasted text", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        const hash32 = "cd".repeat(16);
        await wrapper.vm.call(`please call ${hash32} now`);
        expect(axiosMock.get).toHaveBeenCalledWith(`/api/v1/telephone/call/${hash32}`);
    });

    it("regression: dialer does not require 64-char hex", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        const hash32 = "ef".repeat(16);
        await wrapper.vm.call(hash32);
        expect(axiosMock.get).toHaveBeenCalledWith(`/api/v1/telephone/call/${hash32}`);
    });

    it("regression: addContactFromHistory keeps identity and destination fields separate", async () => {
        const wrapper = mountCallPage();
        await wrapper.vm.$nextTick();
        const identity = "11".repeat(16);
        const lxmf = "22".repeat(16);
        const lxst = "33".repeat(16);
        await wrapper.vm.addContactFromHistory({
            remote_identity_name: "Pat",
            remote_identity_hash: identity,
            remote_destination_hash: lxmf,
            remote_telephony_hash: lxst,
        });
        expect(wrapper.vm.contactForm.remote_identity_hash).toBe(identity);
        expect(wrapper.vm.contactForm.lxmf_address).toBe(lxmf);
        expect(wrapper.vm.contactForm.lxst_address).toBe(lxst);
        expect(wrapper.vm.contactForm.remote_identity_hash).not.toBe(lxmf);
        expect(wrapper.vm.contactForm.remote_identity_hash).not.toBe(lxst);
    });
});

describe("App telephone_ringing policy regressions", () => {
    let axiosMock;
    let router;

    beforeEach(() => {
        router = createRouter({
            history: createWebHashHistory(),
            routes: [
                { path: "/", name: "messages", component: { template: "<div/>" } },
                { path: "/call", name: "call", component: { template: "<div/>" } },
            ],
        });
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/app/info") {
                    return Promise.resolve({
                        data: {
                            app_info: {
                                version: appPackageVersion,
                                tutorial_seen: true,
                                changelog_seen_version: appPackageVersion,
                            },
                        },
                    });
                }
                if (url === "/api/v1/config") {
                    return Promise.resolve({
                        data: {
                            config: {
                                theme: "dark",
                                do_not_disturb_enabled: false,
                                telephone_allow_calls_from_contacts_only: false,
                                block_all_from_strangers: false,
                            },
                        },
                    });
                }
                if (url === "/api/v1/auth/status") {
                    return Promise.resolve({ data: { auth_enabled: false } });
                }
                if (url === "/api/v1/blocked-destinations") {
                    return Promise.resolve({ data: { blocked_destinations: [] } });
                }
                if (String(url).includes("/api/v1/telephone/status")) {
                    return Promise.resolve({
                        data: { enabled: true, active_call: null, initiation_status: null },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
        vi.restoreAllMocks();
    });

    async function mountApp() {
        const wrapper = mount(App, {
            global: {
                plugins: [router, vuetify, i18n],
                stubs: {
                    MaterialDesignIcon: true,
                    LxmfUserIcon: true,
                    NotificationBell: true,
                    LanguageSelector: true,
                    CallOverlay: true,
                    CommandPalette: true,
                    IntegrityWarningModal: true,
                    RouterView: true,
                    VDialog: true,
                    VCard: true,
                    VCardText: true,
                    VCardActions: true,
                    VBtn: true,
                    VIcon: true,
                    VToolbar: true,
                    VToolbarTitle: true,
                    VSpacer: true,
                    VProgressCircular: true,
                    VCheckbox: true,
                    VDivider: true,
                },
            },
        });
        await router.isReady();
        await new Promise((r) => setTimeout(r, 30));
        return wrapper;
    }

    it("regression: block_all_from_strangers suppresses ringtone for non-contacts", async () => {
        const wrapper = await mountApp();
        wrapper.vm.config = {
            do_not_disturb_enabled: false,
            telephone_allow_calls_from_contacts_only: false,
            block_all_from_strangers: true,
        };
        const playRingtone = vi.spyOn(wrapper.vm, "playRingtone").mockImplementation(() => {});
        const handlers = wrapper.vm.getShellWsHandlers();
        handlers.telephone_ringing({
            remote_identity_hash: "aa".repeat(16),
            remote_identity_name: "Stranger",
            is_contact: false,
        });
        expect(playRingtone).not.toHaveBeenCalled();
    });

    it("regression: contacts-only still rings for contacts", async () => {
        const wrapper = await mountApp();
        wrapper.vm.config = {
            do_not_disturb_enabled: false,
            telephone_allow_calls_from_contacts_only: true,
            block_all_from_strangers: false,
        };
        const playRingtone = vi.spyOn(wrapper.vm, "playRingtone").mockImplementation(() => {});
        vi.spyOn(wrapper.vm, "updateTelephoneStatus").mockResolvedValue(undefined);
        globalThis.Notification = class {
            static requestPermission() {
                return Promise.resolve("denied");
            }
        };
        const handlers = wrapper.vm.getShellWsHandlers();
        handlers.telephone_ringing({
            remote_identity_hash: "bb".repeat(16),
            remote_identity_name: "Friend",
            is_contact: true,
        });
        expect(playRingtone).toHaveBeenCalledTimes(1);
    });
});

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
import { sanitizeCallInputHash } from "@/features/call/lib/callHistory.ts";
import App from "../../meshchatx/src/frontend/components/App.vue";
import { appPackageVersion } from "./fixtures/repoPackageVersion.js";

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

/**
 * Builds contact form fields from a call history entry (identity vs dest split).
 */
function contactFormFromHistory(entry) {
    return {
        name: entry.remote_identity_name || "",
        remote_identity_hash: entry.remote_identity_hash || "",
        lxmf_address: entry.remote_destination_hash || "",
        lxst_address: entry.remote_telephony_hash || "",
        preferred_ringtone_id: null,
    };
}

describe("Call dial / contact regressions", () => {
    it("regression: dialer accepts 32-char RNS hashes from pasted text", () => {
        const hash32 = "cd".repeat(16);
        expect(sanitizeCallInputHash(`please call ${hash32} now`)).toBe(hash32);
    });

    it("regression: dialer does not require 64-char hex", () => {
        const hash32 = "ef".repeat(16);
        expect(sanitizeCallInputHash(hash32)).toBe(hash32);
    });

    it("regression: addContactFromHistory keeps identity and destination fields separate", () => {
        const identity = "11".repeat(16);
        const lxmf = "22".repeat(16);
        const lxst = "33".repeat(16);
        const contactForm = contactFormFromHistory({
            remote_identity_name: "Pat",
            remote_identity_hash: identity,
            remote_destination_hash: lxmf,
            remote_telephony_hash: lxst,
        });
        expect(contactForm.remote_identity_hash).toBe(identity);
        expect(contactForm.lxmf_address).toBe(lxmf);
        expect(contactForm.lxst_address).toBe(lxst);
        expect(contactForm.remote_identity_hash).not.toBe(lxmf);
        expect(contactForm.remote_identity_hash).not.toBe(lxst);
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
                plugins: [router, i18n],
                stubs: {
                    MaterialDesignIcon: true,
                    LxmfUserIcon: true,
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

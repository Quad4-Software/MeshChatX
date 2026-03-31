import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import App from "../../meshchatx/src/frontend/components/App.vue";
import { createRouter, createWebHashHistory } from "vue-router";
import { createI18n } from "vue-i18n";
import { createVuetify } from "vuetify";

// Mock axios
const axiosMock = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
};
window.api = axiosMock;

const vuetify = createVuetify();

const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: {
        en: {
            app: {
                name: "MeshChatX",
                changelog_title: "What's New",
                do_not_show_again: "Do not show again",
            },
            common: {
                close: "Close",
            },
        },
    },
});

const routes = [
    { path: "/", name: "messages", component: { template: "<div>Messages</div>" } },
    { path: "/nomadnetwork", name: "nomadnetwork", component: { template: "<div>Nomad</div>" } },
    { path: "/map", name: "map", component: { template: "<div>Map</div>" } },
    { path: "/archives", name: "archives", component: { template: "<div>Archives</div>" } },
    { path: "/call", name: "call", component: { template: "<div>Call</div>" } },
    { path: "/interfaces", name: "interfaces", component: { template: "<div>Interfaces</div>" } },
    { path: "/network-visualiser", name: "network-visualiser", component: { template: "<div>Network</div>" } },
    { path: "/tools", name: "tools", component: { template: "<div>Tools</div>" } },
    { path: "/settings", name: "settings", component: { template: "<div>Settings</div>" } },
    { path: "/identities", name: "identities", component: { template: "<div>Identities</div>" } },
    { path: "/about", name: "about", component: { template: "<div>About</div>" } },
    { path: "/profile/icon", name: "profile.icon", component: { template: "<div>Profile</div>" } },
    { path: "/changelog", name: "changelog", component: { template: "<div>Changelog</div>" } },
    { path: "/tutorial", name: "tutorial", component: { template: "<div>Tutorial</div>" } },
];

describe("App.vue Modals", () => {
    let router;
    beforeEach(() => {
        router = createRouter({
            history: createWebHashHistory(),
            routes,
        });
        vi.clearAllMocks();
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") {
                return Promise.resolve({
                    data: {
                        app_info: {
                            version: "4.4.0",
                            tutorial_seen: true,
                            changelog_seen_version: "4.4.0",
                        },
                    },
                });
            }
            if (url === "/api/v1/config") {
                return Promise.resolve({ data: { config: { theme: "dark" } } });
            }
            if (url === "/api/v1/auth/status") {
                return Promise.resolve({ data: { auth_enabled: false } });
            }
            if (url === "/api/v1/blocked-destinations") {
                return Promise.resolve({ data: { blocked_destinations: [] } });
            }
            if (url === "/api/v1/telephone/status") {
                return Promise.resolve({ data: { active_call: null } });
            }
            if (url === "/api/v1/lxmf/propagation-node/status") {
                return Promise.resolve({ data: { propagation_node_status: { state: "idle" } } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    it("should show tutorial modal if not seen", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") {
                return Promise.resolve({
                    data: {
                        app_info: {
                            version: "4.4.0",
                            tutorial_seen: false,
                            changelog_seen_version: "0.0.0",
                        },
                    },
                });
            }
            if (url === "/api/v1/community-interfaces") {
                return Promise.resolve({ data: { interfaces: [] } });
            }
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: { theme: "dark" } } });
            if (url === "/api/v1/auth/status") return Promise.resolve({ data: { auth_enabled: false } });
            if (url === "/api/v1/blocked-destinations") return Promise.resolve({ data: { blocked_destinations: [] } });
            if (url === "/api/v1/telephone/status") return Promise.resolve({ data: { active_call: null } });
            if (url === "/api/v1/lxmf/propagation-node/status")
                return Promise.resolve({ data: { propagation_node_status: { state: "idle" } } });
            return Promise.resolve({ data: {} });
        });

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
                    // Stub all Vuetify components
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
        await new Promise((resolve) => setTimeout(resolve, 200));

        expect(wrapper.vm.$refs.tutorialModal.visible).toBe(true);
    });

    it("should show changelog modal if version changed", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/app/info") {
                return Promise.resolve({
                    data: {
                        app_info: {
                            version: "4.4.0",
                            tutorial_seen: true,
                            changelog_seen_version: "3.9.0",
                        },
                    },
                });
            }
            if (url === "/api/v1/app/changelog") {
                return Promise.resolve({ data: { html: "<h1>New Features</h1>", version: "4.4.0" } });
            }
            if (url === "/api/v1/config") return Promise.resolve({ data: { config: { theme: "dark" } } });
            if (url === "/api/v1/auth/status") return Promise.resolve({ data: { auth_enabled: false } });
            if (url === "/api/v1/blocked-destinations") return Promise.resolve({ data: { blocked_destinations: [] } });
            if (url === "/api/v1/telephone/status") return Promise.resolve({ data: { active_call: null } });
            if (url === "/api/v1/lxmf/propagation-node/status")
                return Promise.resolve({ data: { propagation_node_status: { state: "idle" } } });
            return Promise.resolve({ data: {} });
        });

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
                    // Stub all Vuetify components
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
        await new Promise((resolve) => setTimeout(resolve, 200));

        expect(wrapper.vm.$refs.changelogModal.visible).toBe(true);
    });
});

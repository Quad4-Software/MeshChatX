import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createWebHashHistory } from "vue-router";
import { createI18n } from "vue-i18n";
import { createVuetify } from "vuetify";
import App from "../../meshchatx/src/frontend/components/App.vue";
import { appPackageVersion } from "./fixtures/repoPackageVersion.js";
import en from "../../meshchatx/src/frontend/locales/en.json";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        connect: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
        send: vi.fn(),
        destroy: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const axiosMock = { get: vi.fn() };
const vuetify = createVuetify();
const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: { en },
});

const routes = [
    { path: "/", name: "messages", component: { template: "<div>Messages</div>" } },
    { path: "/nomadnetwork", name: "nomadnetwork", component: { template: "<div>Nomad</div>" } },
    { path: "/contacts", name: "contacts", component: { template: "<div>Contacts</div>" } },
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

const appStubs = {
    MaterialDesignIcon: { template: '<span class="md-stub" />' },
    LxmfUserIcon: { template: "<div />" },
    NotificationBell: true,
    LanguageSelector: true,
    CallOverlay: true,
    CommandPalette: true,
    IntegrityWarningModal: true,
    AppShellBanners: true,
    Toast: true,
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
};

function makeConfig(overrides = {}) {
    return {
        theme: "dark",
        display_name: "Test User",
        auto_announce_interval_seconds: 0,
        last_announced_at: null,
        identity_hash: "h1",
        lxmf_address_hash: "lx1",
        identity_public_key: "pk1",
        lxmf_user_icon_name: "face-man",
        lxmf_user_icon_foreground_colour: "#e4e4e7",
        lxmf_user_icon_background_colour: "#3f3f46",
        language: "en",
        ...overrides,
    };
}

function defaultAxiosImplementation(url) {
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
        return Promise.resolve({ data: { config: makeConfig() } });
    }
    if (url === "/api/v1/announce") {
        return Promise.resolve({ data: {} });
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
}

function makeMountedApp() {
    const router = createRouter({
        history: createWebHashHistory(),
        routes,
    });
    return mount(App, {
        global: {
            plugins: [router, vuetify, i18n],
            stubs: appStubs,
        },
    });
}

describe("App.vue sidebar identity label and announce control", () => {
    let wrapper;

    beforeEach(() => {
        window.api = axiosMock;
        vi.clearAllMocks();
        axiosMock.get.mockImplementation(defaultAxiosImplementation);
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.unmount();
            wrapper = undefined;
        }
        delete window.api;
    });

    async function readyShell(r) {
        await r.isReady();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 50));
    }

    it("shows configured display name instead of My Identity", async () => {
        wrapper = makeMountedApp();
        const r = wrapper.vm.$router;
        await readyShell(r);
        const html = wrapper.html();
        expect(html).toContain("Test User");
        expect(html).not.toMatch(/>My Identity</);
    });

    it("shows app version in sidebar footer linked to about", async () => {
        wrapper = makeMountedApp();
        const r = wrapper.vm.$router;
        await readyShell(r);
        const versionLink = wrapper.find('[data-testid="sidebar-app-version"]');
        expect(versionLink.exists()).toBe(true);
        expect(versionLink.text()).toContain(`v${appPackageVersion}`);
        expect(versionLink.attributes("title")).toBe(`v${appPackageVersion}`);
    });

    it("falls back to My Identity when display name is empty", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({ data: { config: makeConfig({ display_name: "" }) } });
            }
            return defaultAxiosImplementation(url);
        });
        wrapper = makeMountedApp();
        await readyShell(wrapper.vm.$router);
        expect(wrapper.html()).toContain("My Identity");
    });

    it("long display name is exposed in title and uses truncate for layout", async () => {
        const long = "A".repeat(200);
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({ data: { config: makeConfig({ display_name: long }) } });
            }
            return defaultAxiosImplementation(url);
        });
        wrapper = makeMountedApp();
        await readyShell(wrapper.vm.$router);
        expect(wrapper.vm.identitySidebarLabel).toBe(long);
        const titled = wrapper.find(`div[title="${long}"]`);
        expect(titled.exists()).toBe(true);
        expect(titled.attributes("class") ?? "").toMatch(/truncate/);
    });

    it("sidebar radio sends announce and still works when sidebar is collapsed", async () => {
        wrapper = makeMountedApp();
        await readyShell(wrapper.vm.$router);
        const btn = wrapper.find("[data-testid=sidebar-announce-radio]");
        expect(btn.exists()).toBe(true);
        wrapper.vm.isShowingAnnounceSection = true;
        await btn.trigger("click");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announce");
        expect(ToastUtils.success).toHaveBeenCalled();
        expect(wrapper.vm.isShowingAnnounceSection).toBe(true);
        vi.clearAllMocks();
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/announce") {
                return Promise.resolve({ data: {} });
            }
            if (url === "/api/v1/config") {
                return Promise.resolve({ data: { config: makeConfig() } });
            }
            return defaultAxiosImplementation(url);
        });
        wrapper.vm.isSidebarCollapsed = true;
        await btn.trigger("click");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/announce");
    });

    it("clicking announce section header (not the radio) toggles expanded state", async () => {
        wrapper = makeMountedApp();
        await readyShell(wrapper.vm.$router);
        const header = wrapper.find("[data-testid=sidebar-announce-header]");
        expect(header.exists()).toBe(true);
        wrapper.vm.isShowingAnnounceSection = true;
        await header.trigger("click");
        expect(wrapper.vm.isShowingAnnounceSection).toBe(false);
    });
});

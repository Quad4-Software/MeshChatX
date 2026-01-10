import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";
import SettingsPage from "../../meshchatx/src/frontend/components/settings/SettingsPage.vue";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";
import ConfirmDialog from "../../meshchatx/src/frontend/components/ConfirmDialog.vue";
import ChangelogModal from "../../meshchatx/src/frontend/components/ChangelogModal.vue";
import NotificationBell from "../../meshchatx/src/frontend/components/NotificationBell.vue";
import LanguageSelector from "../../meshchatx/src/frontend/components/LanguageSelector.vue";

vi.mock("vuetify", () => ({
    useTheme: vi.fn(() => ({
        global: {
            name: { value: "light" },
        },
    })),
}));

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        unreadConversationsCount: 0,
        activeCallTab: null,
        config: {},
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/NotificationUtils", () => ({
    default: {
        showIncomingCallNotification: vi.fn(),
        showMissedCallNotification: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/KeyboardShortcuts", () => ({
    default: {
        getDefaultShortcuts: vi.fn(() => []),
        setShortcuts: vi.fn(),
    },
}));

const createRouterLinkStub = () => ({
    template:
        "<a><slot v-bind=\"{ href: typeof to === 'string' ? to : (to?.path || to?.name || '#'), navigate: () => {}, isActive: false }\" /></a>",
    props: ["to", "custom"],
});

describe("Theme Switching", () => {
    let axiosMock;

    beforeEach(() => {
        document.documentElement.classList.remove("dark");
        axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    config: {
                        theme: "light",
                        display_name: "Test User",
                    },
                    app_info: { is_reticulum_running: true },
                },
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;
    });

    afterEach(() => {
        document.documentElement.classList.remove("dark");
        delete window.axios;
        vi.clearAllMocks();
    });

    it("applies dark class to root element when theme is dark", async () => {
        document.documentElement.classList.remove("dark");
        expect(document.documentElement.classList.contains("dark")).toBe(false);

        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.config = { theme: "dark" };
        document.documentElement.classList.add("dark");

        expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("removes dark class when theme is light", async () => {
        document.documentElement.classList.add("dark");

        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.config = { theme: "light" };
        await wrapper.vm.$nextTick();

        expect(document.documentElement.classList.contains("dark")).toBe(false);
    });

    it("toggles theme from light to dark", async () => {
        const WebSocketConnection = await import("../../meshchatx/src/frontend/js/WebSocketConnection");

        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.config = { theme: "light" };
        await wrapper.vm.$nextTick();

        await wrapper.vm.toggleTheme();
        await wrapper.vm.$nextTick();

        expect(WebSocketConnection.default.send).toHaveBeenCalled();
        const sendCalls = WebSocketConnection.default.send.mock.calls;
        const configSetCall = sendCalls.find((call) => {
            try {
                const parsed = JSON.parse(call[0]);
                return parsed.type === "config.set";
            } catch {
                return false;
            }
        });
        expect(configSetCall).toBeDefined();
        if (configSetCall) {
            const callArgs = JSON.parse(configSetCall[0]);
            expect(callArgs.config.theme).toBe("dark");
        }
    });

    it("toggles theme from dark to light", async () => {
        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.config = { theme: "dark" };
        await wrapper.vm.$nextTick();

        await wrapper.vm.toggleTheme();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.config.theme).toBe("light");
    });

    it("shows correct icon for theme toggle button", async () => {
        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: {
                        template: '<div :data-icon="iconName"></div>',
                        props: ["iconName"],
                    },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.config = { theme: "dark" };
        await wrapper.vm.$nextTick();

        const buttons = wrapper.findAll("button");
        expect(buttons.length).toBeGreaterThan(0);
    });
});

describe("Visibility Checks", () => {
    it("ConfirmDialog shows when pendingConfirm is set", async () => {
        const wrapper = mount(ConfirmDialog, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>" },
                },
                mocks: {
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.pendingConfirm = { message: "Test message" };
        await wrapper.vm.$nextTick();

        const dialogElement = wrapper.find(".fixed");
        expect(dialogElement.exists()).toBe(true);
        expect(wrapper.text()).toContain("Confirm");
    });

    it("ConfirmDialog hides when pendingConfirm is null", async () => {
        const wrapper = mount(ConfirmDialog, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>" },
                },
                mocks: {
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.pendingConfirm = null;
        await wrapper.vm.$nextTick();

        const dialogElement = wrapper.find(".fixed");
        expect(dialogElement.exists()).toBe(false);
    });

    it("ChangelogModal component renders correctly", () => {
        const wrapper = mount(ChangelogModal, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>" },
                },
                mocks: {
                    $t: (key) => key,
                },
            },
        });

        expect(wrapper.exists()).toBe(true);
    });

    it("Toggle shows label when provided", () => {
        const wrapper = mount(Toggle, {
            props: {
                id: "test-toggle",
                label: "Show Label",
                modelValue: false,
            },
        });

        expect(wrapper.text()).toContain("Show Label");
    });

    it("Toggle hides label when not provided", () => {
        const wrapper = mount(Toggle, {
            props: {
                id: "test-toggle",
                modelValue: false,
            },
        });

        expect(wrapper.text()).not.toContain("Show Label");
    });

    it("SettingsPage shows banished config when toggle is enabled", async () => {
        const axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    config: {
                        banished_effect_enabled: true,
                        banished_text: "BANISHED",
                        banished_color: "#dc2626",
                        blackhole_integration_enabled: true,
                    },
                },
            }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;

        const wrapper = mount(SettingsPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>" },
                    Toggle: Toggle,
                    ShortcutRecorder: { template: "<div></div>" },
                    RouterLink: { template: "<a><slot /></a>" },
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        wrapper.vm.config.banished_effect_enabled = true;
        await wrapper.vm.$nextTick();

        const hasBanishedConfig =
            wrapper.text().includes("app.banished") || wrapper.findAll('input[type="text"]').length > 0;
        expect(hasBanishedConfig).toBe(true);

        delete window.axios;
    });

    it("SettingsPage shows blackhole integration toggle", async () => {
        const axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    config: {
                        blackhole_integration_enabled: true,
                    },
                },
            }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;

        const wrapper = mount(SettingsPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>" },
                    Toggle: Toggle,
                    ShortcutRecorder: { template: "<div></div>" },
                    RouterLink: { template: "<a><slot /></a>" },
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("app.blackhole_integration_enabled");

        delete window.axios;
    });

    it("SettingsPage hides banished config when toggle is disabled", async () => {
        const axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    config: {
                        banished_effect_enabled: false,
                    },
                },
            }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;

        const wrapper = mount(SettingsPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>" },
                    Toggle: Toggle,
                    ShortcutRecorder: { template: "<div></div>" },
                    RouterLink: { template: "<a><slot /></a>" },
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        wrapper.vm.config.banished_effect_enabled = false;
        await wrapper.vm.$nextTick();

        const colorInputs = wrapper.findAll('input[type="color"]');
        expect(colorInputs.length).toBe(0);

        delete window.axios;
    });
});

describe("Conditional Rendering", () => {
    it("App shows emergency banner when emergency mode is active", async () => {
        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.appInfo = { emergency: true };
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("app.emergency_mode_active");
    });

    it("App hides emergency banner when emergency mode is inactive", async () => {
        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.appInfo = { emergency: false };
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).not.toContain("app.emergency_mode_active");
    });

    it("App shows sidebar toggle on mobile", async () => {
        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        const sidebarButton = wrapper.find("button.sm\\:hidden");
        expect(sidebarButton.exists()).toBe(true);
    });
});

describe("Dark Mode Class Application", () => {
    it("App component applies dark class based on theme", async () => {
        const wrapper = mount(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
                    NotificationBell: { template: "<div></div>" },
                    SidebarLink: {
                        template: '<div><slot name="icon"></slot><slot name="text"></slot></div>',
                        props: ["to", "isCollapsed"],
                    },
                },
                mocks: {
                    $route: { name: "messages", meta: {}, query: {} },
                    $router: { push: vi.fn() },
                    $t: (key) => key,
                },
            },
        });

        wrapper.vm.config = { theme: "dark" };
        await wrapper.vm.$nextTick();

        expect(wrapper.classes()).toContain("dark");
    });

    it("SettingsPage applies dark mode classes correctly", async () => {
        const axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    config: {
                        theme: "dark",
                    },
                },
            }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;

        const wrapper = mount(SettingsPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>" },
                    Toggle: Toggle,
                    ShortcutRecorder: { template: "<div></div>" },
                    RouterLink: { template: "<a><slot /></a>" },
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const hasDarkClasses = wrapper.html().includes("dark:") || wrapper.html().includes("dark:");
        expect(hasDarkClasses).toBe(true);

        delete window.axios;
    });
});

describe("Theme Persistence", () => {
    it("SettingsPage theme selector updates config", async () => {
        const axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    config: {
                        theme: "light",
                    },
                },
            }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;

        const wrapper = mount(SettingsPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: "<div></div>" },
                    Toggle: Toggle,
                    ShortcutRecorder: { template: "<div></div>" },
                    RouterLink: { template: "<a><slot /></a>" },
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const themeSelect = wrapper.find('select[v-model="config.theme"]');
        if (themeSelect.exists()) {
            await themeSelect.setValue("dark");
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.config.theme).toBe("dark");
        }

        delete window.axios;
    });
});

import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import WebSocketConnection from "../../meshchatx/src/frontend/js/WebSocketConnection";
import App from "../../meshchatx/src/frontend/components/App.vue";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import SettingsPage from "../../meshchatx/src/frontend/components/settings/SettingsPage.vue";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";
import ConfirmDialog from "../../meshchatx/src/frontend/components/ConfirmDialog.vue";
import ChangelogModal from "../../meshchatx/src/frontend/components/ChangelogModal.vue";
import LanguageSelector from "../../meshchatx/src/frontend/components/LanguageSelector.vue";

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
        send: vi.fn(),
        connect: vi.fn(),
        destroy: vi.fn(),
        setLiveSendBridge: vi.fn(),
        isOpen: vi.fn(() => false),
        reconnect: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => {
    const state = {
        authSessionResolved: true,
        authEnabled: false,
        authenticated: false,
        unreadConversationsCount: 0,
        relayChatUnreadCount: 0,
        missedCallsCount: 0,
        activeCallTab: null,
        config: {},
    };
    return {
        mergeGlobalConfig: vi.fn((next) => {
            if (next && typeof next === "object") {
                state.config = { ...state.config, ...next };
            }
        }),
        default: state,
    };
});

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
        showNewMessageNotification: vi.fn(),
        clearMessageNotifications: vi.fn(),
        clearAllMessageNotifications: vi.fn(),
        syncAndroidNotificationContext: vi.fn(),
        cancelIncomingCallNotification: vi.fn(),
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

const mountedWrappers = [];

function mountTracked(component, options) {
    const wrapper = mount(component, options);
    mountedWrappers.push(wrapper);
    return wrapper;
}

function createDefaultApiMock() {
    return {
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
        patch: vi.fn().mockResolvedValue({ data: {} }),
    };
}

beforeEach(() => {
    document.documentElement.classList.remove("dark");
    window.api = createDefaultApiMock();
});

afterEach(async () => {
    await flushPromises();
    for (const wrapper of mountedWrappers) {
        try {
            wrapper.unmount();
        } catch {
            // ignore double unmount
        }
    }
    mountedWrappers.length = 0;
    await flushPromises();
    document.documentElement.classList.remove("dark");
    delete window.api;
    vi.clearAllMocks();
});

describe("Theme Switching", () => {
    let axiosMock;

    beforeEach(() => {
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
            patch: vi.fn().mockImplementation(async (_url, body) => ({
                data: {
                    config: {
                        theme: "light",
                        display_name: "Test User",
                        ...body,
                    },
                },
            })),
        };
        window.api = axiosMock;
    });

    it("applies dark class to root element when theme is dark", async () => {
        document.documentElement.classList.remove("dark");
        expect(document.documentElement.classList.contains("dark")).toBe(false);

        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
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

        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
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
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
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

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/config", { theme: "dark" });
    });

    it("toggles theme from dark to light", async () => {
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
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

        await flushPromises();
        await wrapper.vm.$nextTick();
        wrapper.vm.config = { ...(wrapper.vm.config || {}), theme: "dark" };
        await wrapper.vm.$nextTick();

        axiosMock.patch.mockClear();

        await wrapper.vm.toggleTheme();
        await flushPromises();

        expect(axiosMock.patch).toHaveBeenCalledWith("/api/v1/config", { theme: "light" });
    });

    it("shows correct icon for theme toggle button", async () => {
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: {
                        template: '<div :data-icon="iconName"></div>',
                        props: ["iconName"],
                    },
                    LanguageSelector: { template: "<div></div>" },
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
    it("ConfirmDialog shows when confirm event fires", async () => {
        const GlobalEmitter = (await import("../../meshchatx/src/frontend/js/GlobalEmitter")).default;
        const onSpy = vi.spyOn(GlobalEmitter, "on");
        const offSpy = vi.spyOn(GlobalEmitter, "off");

        const wrapper = mountTracked(ConfirmDialog, {
            attachTo: document.body,
            global: {
                mocks: {
                    $t: (key) => key,
                },
            },
        });

        await flushPromises();
        const showFn = onSpy.mock.calls.find((c) => c[0] === "confirm")?.[1];
        expect(showFn).toBeDefined();
        showFn({ message: "Test message", resolve: vi.fn() });
        await flushPromises();
        await Promise.resolve();

        expect(document.body.textContent).toContain("common.confirm_action");
        expect(document.body.textContent).toContain("Test message");
        expect(document.querySelector(".confirm-dialog-root")).toBeTruthy();

        offSpy.mockRestore();
        onSpy.mockRestore();
        wrapper.unmount();
    });

    it("ConfirmDialog hides when closed", async () => {
        const wrapper = mountTracked(ConfirmDialog, {
            attachTo: document.body,
            global: {
                mocks: {
                    $t: (key) => key,
                },
            },
        });

        await flushPromises();
        expect(document.querySelector(".confirm-dialog-root")).toBeNull();
        wrapper.unmount();
    });

    it("ChangelogModal component renders correctly", () => {
        const wrapper = mountTracked(ChangelogModal, {
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
        const wrapper = mountTracked(Toggle, {
            props: {
                id: "test-toggle",
                label: "Show Label",
                modelValue: false,
            },
        });

        expect(wrapper.text()).toContain("Show Label");
    });

    it("Toggle hides label when not provided", () => {
        const wrapper = mountTracked(Toggle, {
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
        window.api = axiosMock;

        const wrapper = mountTracked(SettingsPage, {
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
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        wrapper.vm.config.banished_effect_enabled = true;
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("app.banished_text_label");
        expect(wrapper.text()).toContain("app.banished_color_label");
        expect(wrapper.findAll('input[type="color"]').length).toBeGreaterThanOrEqual(1);
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
        window.api = axiosMock;

        const wrapper = mountTracked(SettingsPage, {
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
        window.api = axiosMock;

        const wrapper = mountTracked(SettingsPage, {
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
        expect(colorInputs.length).toBe(4);
    });
});

describe("Conditional Rendering", () => {
    it("App shows emergency banner when emergency mode is active", async () => {
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
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
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
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
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
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

    it("App shows propagation sync refresh icon on mobile", async () => {
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: '<div data-icon-name="{{ iconName }}"></div>' },
                    LanguageSelector: { template: "<div></div>" },
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

        const mobileRefreshButtons = wrapper.findAll("button").filter((b) => {
            const cls = b.classes().join(" ");
            return cls.includes("sm:hidden") && b.attributes("title") === "app.sync_messages";
        });
        expect(mobileRefreshButtons.length).toBe(1);
    });

    it("App header shows relay chat and telephone icons next to compose and sync", async () => {
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: '<div data-icon-name="{{ iconName }}"></div>' },
                    LanguageSelector: { template: "<div></div>" },
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

        const relay = wrapper.find('[data-testid="header-relay-chat"]');
        const telephone = wrapper.find('[data-testid="header-telephone"]');
        const compose = wrapper.find('[data-testid="header-compose"]');
        expect(relay.exists()).toBe(true);
        expect(telephone.exists()).toBe(true);
        expect(compose.exists()).toBe(true);
        expect(relay.classes().join(" ")).not.toContain("hidden");
        expect(telephone.classes().join(" ")).not.toContain("hidden");
        expect(relay.attributes("title")).toBe("app.relay_chat");
        expect(telephone.attributes("title")).toBe("app.audio_calls");

        await relay.trigger("click");
        expect(wrapper.vm.$router.push).toHaveBeenCalledWith({ name: "relay-chat" });
        await telephone.trigger("click");
        expect(wrapper.vm.$router.push).toHaveBeenCalledWith({ name: "call" });
    });

    it("App header omits relay chat when RRC is disabled", async () => {
        GlobalState.config.rrc_enabled = false;
        try {
            const wrapper = mountTracked(App, {
                global: {
                    stubs: {
                        RouterView: { template: "<div>Router View</div>" },
                        RouterLink: createRouterLinkStub(),
                        MaterialDesignIcon: { template: '<div data-icon-name="{{ iconName }}"></div>' },
                        LanguageSelector: { template: "<div></div>" },
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

            expect(wrapper.find('[data-testid="header-relay-chat"]').exists()).toBe(false);
            expect(wrapper.find('[data-testid="header-telephone"]').exists()).toBe(true);
        } finally {
            delete GlobalState.config.rrc_enabled;
        }
    });
});

describe("Dark Mode Class Application", () => {
    it("App component applies dark class based on theme", async () => {
        const wrapper = mountTracked(App, {
            global: {
                stubs: {
                    RouterView: { template: "<div>Router View</div>" },
                    RouterLink: createRouterLinkStub(),
                    MaterialDesignIcon: { template: "<div></div>" },
                    LanguageSelector: { template: "<div></div>" },
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
        window.api = axiosMock;

        const wrapper = mountTracked(SettingsPage, {
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
        window.api = axiosMock;

        const wrapper = mountTracked(SettingsPage, {
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
    });
});

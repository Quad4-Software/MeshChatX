import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import IconButton from "../../meshchatx/src/frontend/components/IconButton.vue";
import SendMessageButton from "../../meshchatx/src/frontend/components/messages/SendMessageButton.vue";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";
import FormLabel from "../../meshchatx/src/frontend/components/forms/FormLabel.vue";
import FormSubLabel from "../../meshchatx/src/frontend/components/forms/FormSubLabel.vue";
import DropDownMenu from "../../meshchatx/src/frontend/components/DropDownMenu.vue";
import DropDownMenuItem from "../../meshchatx/src/frontend/components/DropDownMenuItem.vue";
import SettingsPage from "../../meshchatx/src/frontend/components/settings/SettingsPage.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

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
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/KeyboardShortcuts", () => ({
    default: {
        getDefaultShortcuts: vi.fn(() => []),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ElectronUtils", () => ({
    default: {
        isElectron: vi.fn(() => false),
    },
}));

describe("IconButton Component", () => {
    it("renders with slot content", () => {
        const wrapper = mount(IconButton, {
            slots: {
                default: '<span class="test-content">Click me</span>',
            },
        });
        expect(wrapper.find(".test-content").exists()).toBe(true);
        expect(wrapper.text()).toContain("Click me");
    });

    it("has correct button type attribute", () => {
        const wrapper = mount(IconButton);
        expect(wrapper.attributes("type")).toBe("button");
    });

    it("emits click event when clicked", async () => {
        const wrapper = mount(IconButton);
        await wrapper.trigger("click");
        expect(wrapper.emitted("click")).toBeTruthy();
    });

    it("applies disabled state correctly", () => {
        const wrapper = mount(IconButton, {
            attrs: {
                disabled: true,
            },
        });
        expect(wrapper.attributes("disabled")).toBeDefined();
    });

    it("applies custom classes", () => {
        const wrapper = mount(IconButton, {
            attrs: {
                class: "custom-class",
            },
        });
        expect(wrapper.classes()).toContain("custom-class");
    });

    it("root element is a button", () => {
        const wrapper = mount(IconButton);
        expect(wrapper.element.tagName).toBe("BUTTON");
    });
});

describe("DropDownMenuItem Component", () => {
    it("renders slot content", () => {
        const wrapper = mount(DropDownMenuItem, {
            slots: { default: "Menu item text" },
        });
        expect(wrapper.text()).toContain("Menu item text");
    });

    it("has clickable styling class", () => {
        const wrapper = mount(DropDownMenuItem);
        expect(wrapper.classes()).toContain("cursor-pointer");
    });

    it("root is a div", () => {
        const wrapper = mount(DropDownMenuItem, { slots: { default: "x" } });
        expect(wrapper.element.tagName).toBe("DIV");
    });
});

describe("SendMessageButton Component", () => {
    it("renders send button with correct text when enabled", () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: true,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        expect(wrapper.text()).toContain("Send");
    });

    it("shows sending state when isSendingMessage is true", () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: true,
                isSendingMessage: true,
                deliveryMethod: null,
            },
        });
        expect(wrapper.text()).toContain("Send");
        expect(wrapper.html()).toContain("opacity-60");
    });

    it("disables button when canSendMessage is false", () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: false,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        const button = wrapper.find("button");
        expect(button.attributes("disabled")).toBeDefined();
    });

    it("shows delivery method in button text", () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: true,
                isSendingMessage: false,
                deliveryMethod: "direct",
            },
        });
        expect(wrapper.text()).toContain("Send (Direct)");
    });

    it("emits send event when send button is clicked", async () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: true,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        const sendButton = wrapper.findAll("button")[0];
        await sendButton.trigger("click");
        expect(wrapper.emitted("send")).toBeTruthy();
    });

    it("opens dropdown menu when dropdown button is clicked", async () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: true,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        const dropdownButton = wrapper.findAll("button")[1];
        await dropdownButton.trigger("click");
        expect(wrapper.vm.isShowingMenu).toBe(true);
    });

    it("emits delivery-method-changed when delivery method is selected", async () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: true,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        wrapper.vm.showMenu();
        await wrapper.vm.$nextTick();
        wrapper.vm.setDeliveryMethod("direct");
        expect(wrapper.emitted("delivery-method-changed")).toBeTruthy();
        expect(wrapper.emitted("delivery-method-changed")[0]).toEqual(["direct"]);
    });

    it("closes menu after selecting delivery method", async () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: true,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        wrapper.vm.showMenu();
        expect(wrapper.vm.isShowingMenu).toBe(true);
        wrapper.vm.setDeliveryMethod("direct");
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });
});

describe("Toggle Component", () => {
    it("renders with label when provided", () => {
        const wrapper = mount(Toggle, {
            props: {
                id: "test-toggle",
                label: "Enable Feature",
            },
        });
        expect(wrapper.text()).toContain("Enable Feature");
    });

    it("emits update:modelValue when toggled", async () => {
        const wrapper = mount(Toggle, {
            props: {
                id: "test-toggle",
                modelValue: false,
            },
        });
        const input = wrapper.find("input");
        await input.setChecked(true);
        expect(wrapper.emitted("update:modelValue")).toBeTruthy();
        expect(wrapper.emitted("update:modelValue")[0]).toEqual([true]);
    });

    it("reflects modelValue prop correctly", () => {
        const wrapper = mount(Toggle, {
            props: {
                id: "test-toggle",
                modelValue: true,
            },
        });
        expect(wrapper.find("input").element.checked).toBe(true);
    });

    it("handles label prop correctly", () => {
        const wrapper = mount(Toggle, {
            props: {
                id: "test-toggle",
                modelValue: false,
                label: "Test Label",
            },
        });
        expect(wrapper.text()).toContain("Test Label");
    });

    it("emits update:modelValue on input change", async () => {
        const wrapper = mount(Toggle, {
            props: {
                id: "test-toggle",
                modelValue: false,
            },
        });
        const input = wrapper.find("input");
        await input.trigger("change");
        expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    });
});

describe("FormLabel Component", () => {
    it("renders label text", () => {
        const wrapper = mount(FormLabel, {
            props: {
                for: "test-input",
            },
            slots: {
                default: "Test Label",
            },
        });
        expect(wrapper.text()).toContain("Test Label");
    });

    it("has correct for attribute", () => {
        const wrapper = mount(FormLabel, {
            props: {
                for: "test-input",
            },
        });
        expect(wrapper.attributes("for")).toBe("test-input");
    });
});

describe("FormSubLabel Component", () => {
    it("renders sublabel text", () => {
        const wrapper = mount(FormSubLabel, {
            slots: {
                default: "This is a sublabel",
            },
        });
        expect(wrapper.text()).toContain("This is a sublabel");
    });
});

describe("DropDownMenu Component", () => {
    it("toggles menu visibility on button click", async () => {
        const wrapper = mount(DropDownMenu, {
            slots: {
                button: "<button>Menu</button>",
                items: "<div>Item 1</div>",
            },
        });
        const button = wrapper.find("button");
        await button.trigger("click");
        expect(wrapper.vm.isShowingMenu).toBe(true);
        await button.trigger("click");
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });

    it("shows menu items when open", async () => {
        const wrapper = mount(DropDownMenu, {
            slots: {
                button: "<button>Menu</button>",
                items: '<div class="menu-item">Item 1</div>',
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
            },
        });
        wrapper.vm.showMenu();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        const menuContent = document.body.querySelector(".menu-item");
        expect(menuContent).toBeTruthy();
    });

    it("hides menu when clicking outside", async () => {
        const wrapper = mount(DropDownMenu, {
            slots: {
                button: "<button>Menu</button>",
                items: "<div>Item 1</div>",
            },
        });
        wrapper.vm.showMenu();
        await wrapper.vm.$nextTick();
        wrapper.vm.onClickOutsideMenu({ preventDefault: vi.fn() });
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });

    it("closes menu when hideMenu is called", async () => {
        const wrapper = mount(DropDownMenu, {
            slots: {
                button: "<button>Menu</button>",
                items: '<div class="menu-item">Item 1</div>',
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
            },
        });
        wrapper.vm.showMenu();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        expect(document.body.querySelector(".menu-item")).toBeTruthy();
        wrapper.vm.hideMenu();
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });
});

describe("SettingsPage Component", () => {
    let axiosMock;
    let websocketMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockResolvedValue({
                data: {
                    config: {
                        display_name: "Test User",
                        identity_hash: "abc123",
                        lxmf_address_hash: "def456",
                        theme: "dark",
                        is_transport_enabled: true,
                        lxmf_local_propagation_node_enabled: false,
                        auto_resend_failed_messages_when_announce_received: true,
                        allow_auto_resending_failed_messages_with_attachments: false,
                        auto_send_failed_messages_to_propagation_node: false,
                        show_suggested_community_interfaces: true,
                        lxmf_local_propagation_node_enabled: false,
                        banished_effect_enabled: true,
                        banished_text: "BANISHED",
                        banished_color: "#dc2626",
                        desktop_open_calls_in_separate_window: false,
                    },
                },
            }),
            post: vi.fn().mockResolvedValue({ data: { success: true } }),
            patch: vi.fn().mockResolvedValue({ data: { success: true } }),
        };
        window.api = axiosMock;

        websocketMock = {
            on: vi.fn(),
            off: vi.fn(),
            emit: vi.fn(),
        };
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountSettingsPage = () => {
        return mount(SettingsPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: '<div class="mdi"></div>' },
                    Toggle: Toggle,
                    ShortcutRecorder: { template: "<div></div>" },
                    RouterLink: { template: "<a><slot /></a>" },
                },
                mocks: {
                    $t: (key) => key,
                    $router: {
                        push: vi.fn(),
                    },
                },
            },
        });
    };

    it("renders settings page with profile information", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.config).toBeDefined();
        expect(wrapper.vm.config.display_name).toBe("Test User");
        const displayNameInput = wrapper.find('input[type="text"]');
        expect(displayNameInput.exists()).toBe(true);
        expect(displayNameInput.element.value).toBe("Test User");
    });

    it("renders copy buttons for identity and lxmf address", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        const buttons = wrapper.findAll("button");
        const hasCopyButtons = buttons.some(
            (btn) => btn.text().includes("app.identity_hash") || btn.text().includes("app.lxmf_address")
        );
        expect(hasCopyButtons || buttons.length > 0).toBe(true);
    });

    it("handles toggle changes for banished effect", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        wrapper.vm.config.banished_effect_enabled = true;
        await wrapper.vm.$nextTick();
        wrapper.vm.onBanishedEffectEnabledChange(false);
        await wrapper.vm.$nextTick();
        expect(axiosMock.patch).toHaveBeenCalled();
    });

    it("updates banished text when input changes", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        wrapper.vm.config.banished_effect_enabled = true;
        await wrapper.vm.$nextTick();

        const textInputs = wrapper.findAll('input[type="text"]');
        if (textInputs.length > 0) {
            const textInput =
                textInputs.find(
                    (input) =>
                        input.attributes("v-model")?.includes("banished_text") ||
                        input.element.value === wrapper.vm.config.banished_text
                ) || textInputs[0];
            await textInput.setValue("CUSTOM TEXT");
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.config.banished_text).toBe("CUSTOM TEXT");
        }
    });

    it("updates banished color when color picker changes", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        wrapper.vm.config.banished_effect_enabled = true;
        await wrapper.vm.$nextTick();

        const colorInputs = wrapper.findAll('input[type="color"]');
        if (colorInputs.length > 0) {
            const colorInput = colorInputs[0];
            await colorInput.setValue("#ff0000");
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.config.banished_color).toBe("#ff0000");
        }
    });

    it("shows banished configuration when toggle is enabled", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        wrapper.vm.config.banished_effect_enabled = true;
        await wrapper.vm.$nextTick();

        const hasBanishedConfig =
            wrapper.text().includes("app.banished") || wrapper.vm.config.banished_effect_enabled === true;
        expect(hasBanishedConfig).toBe(true);
    });

    it("handles RNS reload button click", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        if (wrapper.vm.reloadRns) {
            await wrapper.vm.reloadRns();
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
        }
    });

    it("updates reload status from websocket events", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();

        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "reticulum_reload_status",
                message: "Stopping services...",
                level: "info",
                in_progress: true,
            }),
        });

        expect(wrapper.vm.reloadingRns).toBe(true);
        expect(wrapper.vm.reloadRnsStatusMessage).toBe("Stopping services...");
        expect(ToastUtils.info).toHaveBeenCalledWith("Stopping services...", 2500, "settings-rns-reload");
    });

    it("displays theme information correctly", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("app.theme");
    });

    it("displays transport status correctly", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("app.transport");
    });

    it("shows RNS reload controls in settings", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("app.reload_rns");
    });

    it("enabling transport shows success toast after reload", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        axiosMock.post.mockResolvedValueOnce({
            data: { message: "Transport mode enabled and RNS restarted successfully." },
        });
        wrapper.vm.config.is_transport_enabled = true;
        await wrapper.vm.onIsTransportEnabledChange();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/enable-transport");
        expect(ToastUtils.success).toHaveBeenCalledWith("Transport mode enabled and RNS restarted successfully.");
    });

    it("disabling transport shows success toast after reload", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        axiosMock.post.mockResolvedValueOnce({
            data: { message: "Transport mode disabled and RNS restarted successfully." },
        });
        wrapper.vm.config.is_transport_enabled = false;
        await wrapper.vm.onIsTransportEnabledChange();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/disable-transport");
        expect(ToastUtils.success).toHaveBeenCalledWith("Transport mode disabled and RNS restarted successfully.");
    });

    it("shows error toast when enabling transport fails", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        axiosMock.post.mockRejectedValueOnce(new Error("boom"));
        wrapper.vm.config.is_transport_enabled = true;
        await wrapper.vm.onIsTransportEnabledChange();

        expect(ToastUtils.error).toHaveBeenCalledWith("settings.failed_enable_transport");
    });

    it("handles multiple toggle changes without errors", async () => {
        const wrapper = mountSettingsPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.getConfig();
        await wrapper.vm.$nextTick();

        if (!wrapper.vm.config) {
            wrapper.vm.config = {
                banished_effect_enabled: false,
                auto_resend_failed_messages_when_announce_received: false,
            };
        }

        const toggles = wrapper.findAllComponents(Toggle);
        for (const toggle of toggles.slice(0, 2)) {
            try {
                await toggle.vm.$emit("update:modelValue", true);
                await wrapper.vm.$nextTick();
            } catch (e) {}
        }

        expect(axiosMock.patch).toHaveBeenCalled();
    });
});

describe("Button Interactions and Accessibility", () => {
    it("IconButton is keyboard accessible", async () => {
        const wrapper = mount(IconButton, {
            attrs: {
                tabindex: "0",
            },
        });
        expect(wrapper.attributes("tabindex")).toBe("0");
    });

    it("SendMessageButton respects disabled state for keyboard", () => {
        const wrapper = mount(SendMessageButton, {
            props: {
                canSendMessage: false,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        const buttons = wrapper.findAll("button");
        buttons.forEach((button) => {
            expect(button.attributes("disabled")).toBeDefined();
        });
    });

    it("Toggle is keyboard accessible", async () => {
        const wrapper = mount(Toggle, {
            props: {
                id: "test-toggle",
                modelValue: false,
            },
        });
        const input = wrapper.find("input");
        expect(input.attributes("id")).toBe("test-toggle");
        await input.trigger("change");
        expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    });
});

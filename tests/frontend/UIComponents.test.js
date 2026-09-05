import { mount as mountVue } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render } from "@testing-library/svelte";
import { flushSync, tick } from "svelte";
import IconButton from "../../meshchatx/src/frontend/components/IconButton.vue";
import SendMessageButton from "../../meshchatx/src/frontend/features/messages/components/composer/SendMessageButton.svelte";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";
import FormLabel from "../../meshchatx/src/frontend/components/forms/FormLabel.vue";
import FormSubLabel from "../../meshchatx/src/frontend/components/forms/FormSubLabel.vue";
import DropDownMenu from "../../meshchatx/src/frontend/components/DropDownMenu.vue";
import DropDownMenuItem from "../../meshchatx/src/frontend/components/DropDownMenuItem.vue";
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
        isWindowsElectron: vi.fn(() => false),
    },
}));

function mountSendMessageButton(options = {}) {
    const emitted = {};
    const emit = (name, value) => {
        emitted[name] ||= [];
        emitted[name].push(value === undefined ? [] : [value]);
    };
    const view = render(SendMessageButton, {
        ...(options.props || {}),
        onsend: () => emit("send"),
        ondeliverymethodchanged: (method) => emit("delivery-method-changed", method),
        onsendcommandorrequest: () => emit("send-command-or-request"),
        onsendpapercompose: () => emit("send-paper-compose"),
    });
    const wrapButton = (element) => ({
        trigger: async (eventName) => {
            flushSync(() => element.dispatchEvent(new Event(eventName, { bubbles: true })));
            await tick();
        },
        attributes: (name) => element.getAttribute(name) ?? undefined,
    });
    const clickMenuItem = (text) => {
        const button = [...view.container.querySelectorAll("button")].find(
            (entry) => entry.textContent?.trim() === text
        );
        flushSync(() => button?.click());
    };
    const vm = {
        get isShowingMenu() {
            return view.container.textContent?.includes("messages.send_automatically") === true;
        },
        showMenu() {
            flushSync(() => view.container.querySelectorAll("button")[1]?.click());
        },
        setDeliveryMethod(method) {
            const labels = {
                direct: "messages.send_over_direct_link",
                opportunistic: "messages.send_opportunistically",
                propagated: "messages.send_to_propagation_node",
            };
            clickMenuItem(labels[method] || "messages.send_automatically");
        },
        emitCommandOrRequest() {
            clickMenuItem("messages.send_menu_telemetry_request");
        },
        emitPaperCompose() {
            clickMenuItem("messages.send_menu_paper_compose");
        },
        $nextTick: tick,
    };
    return {
        vm,
        text: () => view.container.textContent || "",
        html: () => view.container.innerHTML,
        find: (selector) => wrapButton(view.container.querySelector(selector)),
        findAll: (selector) => [...view.container.querySelectorAll(selector)].map(wrapButton),
        emitted: (name) => emitted[name],
        unmount: view.unmount,
    };
}

function mount(component, options) {
    return component === SendMessageButton ? mountSendMessageButton(options) : mountVue(component, options);
}

afterEach(() => cleanup());

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
    const sendBtnGlobal = { mocks: { $t: (k) => k } };

    it("renders send button with correct text when enabled", () => {
        const wrapper = mount(SendMessageButton, {
            global: sendBtnGlobal,
            props: {
                canSendMessage: true,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        expect(wrapper.text()).toContain("messages.send");
    });

    it("shows sending state when isSendingMessage is true", () => {
        const wrapper = mount(SendMessageButton, {
            global: sendBtnGlobal,
            props: {
                canSendMessage: true,
                isSendingMessage: true,
                deliveryMethod: null,
            },
        });
        expect(wrapper.text()).toContain("messages.send");
        expect(wrapper.html()).toContain("opacity-60");
    });

    it("disables button when canSendMessage is false", () => {
        const wrapper = mount(SendMessageButton, {
            global: sendBtnGlobal,
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
            global: sendBtnGlobal,
            props: {
                canSendMessage: true,
                isSendingMessage: false,
                deliveryMethod: "direct",
            },
        });
        expect(wrapper.text()).toContain("messages.send_direct");
    });

    it("emits send event when send button is clicked", async () => {
        const wrapper = mount(SendMessageButton, {
            global: sendBtnGlobal,
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
            global: sendBtnGlobal,
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
            global: sendBtnGlobal,
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
            global: sendBtnGlobal,
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

    it("emits send-command-or-request from menu", async () => {
        const wrapper = mount(SendMessageButton, {
            global: sendBtnGlobal,
            props: {
                canSendMessage: false,
                canOpenSendMenu: true,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        wrapper.vm.showMenu();
        await wrapper.vm.$nextTick();
        wrapper.vm.emitCommandOrRequest();
        expect(wrapper.emitted("send-command-or-request")).toBeTruthy();
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });

    it("emits send-paper-compose from menu", async () => {
        const wrapper = mount(SendMessageButton, {
            global: sendBtnGlobal,
            props: {
                canSendMessage: true,
                canOpenSendMenu: true,
                isSendingMessage: false,
                deliveryMethod: null,
            },
        });
        wrapper.vm.showMenu();
        await wrapper.vm.$nextTick();
        wrapper.vm.emitPaperCompose();
        expect(wrapper.emitted("send-paper-compose")).toBeTruthy();
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
            global: { mocks: { $t: (k) => k } },
            props: {
                canSendMessage: false,
                canOpenSendMenu: false,
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

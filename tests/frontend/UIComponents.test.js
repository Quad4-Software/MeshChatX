import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render } from "@testing-library/svelte";
import { flushSync, tick } from "svelte";
import SendMessageButton from "../../meshchatx/src/frontend/features/messages/components/composer/SendMessageButton.svelte";
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
            return view.container.textContent?.includes("Send automatically") === true;
        },
        showMenu() {
            flushSync(() => view.container.querySelectorAll("button")[1]?.click());
        },
        setDeliveryMethod(method) {
            const labels = {
                direct: "Send over direct link",
                opportunistic: "Send opportunistically",
                propagated: "Send to propagation node",
            };
            clickMenuItem(labels[method] || "Send automatically");
        },
        emitCommandOrRequest() {
            clickMenuItem("Send as Command or Request");
        },
        emitPaperCompose() {
            clickMenuItem("Paper message from composition (LXM)");
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
    return mountSendMessageButton(options);
}

afterEach(() => cleanup());

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

    it("emits send-command-or-request from menu", async () => {
        const wrapper = mount(SendMessageButton, {
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

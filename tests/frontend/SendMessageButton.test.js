// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import SendMessageButton from "../../meshchatx/src/frontend/components/messages/composer/SendMessageButton.vue";
import { clickOutsideDirective as touchClickOutside } from "../../meshchatx/src/frontend/libs/clickOutside.js";

const mountButton = (directive, props = {}) =>
    mount(SendMessageButton, {
        props: {
            deliveryMethod: null,
            canSendMessage: true,
            canOpenSendMenu: true,
            ...props,
        },
        global: {
            mocks: { $t: (key) => key },
            directives: { "click-outside": directive },
        },
    });

// The directive attaches its document listeners from setTimeout(0) callbacks
// scheduled during mount, so pending timers must run before outside events.
const flushDirectiveListeners = async (wrapper) => {
    await wrapper.vm.$nextTick();
    await vi.runOnlyPendingTimersAsync();
};

const dispatchOnDocumentElement = (type) => {
    document.documentElement.dispatchEvent(new Event(type, { bubbles: false }));
};

const runLongPressReleaseAssertions = async (wrapper, button, outsideEventType) => {
    await button.trigger("pointerdown");
    vi.advanceTimersByTime(499);
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.isShowingMenu).toBe(false);

    vi.advanceTimersByTime(1);
    await flushDirectiveListeners(wrapper);
    expect(wrapper.vm.isShowingMenu).toBe(true);

    // contextmenu during/right after the hold must not dismiss the menu
    // and must prevent the native context menu.
    const contextMenuEvent = new MouseEvent("contextmenu", { bubbles: true, cancelable: true });
    button.element.dispatchEvent(contextMenuEvent);
    await wrapper.vm.$nextTick();
    expect(contextMenuEvent.defaultPrevented).toBe(true);
    expect(wrapper.vm.isShowingMenu).toBe(true);

    await button.trigger("pointerup");
    await button.trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.isShowingMenu).toBe(true);
    expect(wrapper.emitted("send")).toBeUndefined();

    dispatchOnDocumentElement(outsideEventType);
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.isShowingMenu).toBe(false);
};

describe("SendMessageButton compact long-press menu (mouse events)", () => {
    let mouseClickOutside;

    beforeAll(async () => {
        // jsdom exposes window.ontouchstart, which makes the directive pick
        // touch events. Remove it and re-import for the desktop event set.
        const descriptor = Object.getOwnPropertyDescriptor(window, "ontouchstart");
        delete window.ontouchstart;
        vi.resetModules();
        const mod = await import("../../meshchatx/src/frontend/libs/clickOutside.js");
        mouseClickOutside = mod.clickOutsideDirective;
        if (descriptor) {
            Object.defineProperty(window, "ontouchstart", descriptor);
        }
    });

    beforeEach(() => {
        vi.useFakeTimers();
    });

    it("keeps the menu open after a long-press release and does not send", async () => {
        const wrapper = mountButton(mouseClickOutside, { compact: true });
        const button = wrapper.find("button");
        await runLongPressReleaseAssertions(wrapper, button, "click");
    });

    it("still sends on a short tap without opening the menu", async () => {
        const wrapper = mountButton(mouseClickOutside, { compact: true });
        const button = wrapper.find("button");

        await button.trigger("pointerdown");
        vi.advanceTimersByTime(200);
        await button.trigger("pointerup");
        await button.trigger("click");
        await wrapper.vm.$nextTick();

        expect(wrapper.emitted("send")).toHaveLength(1);
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });

    it("non-compact dropdown still opens and closes on outside click", async () => {
        const wrapper = mountButton(mouseClickOutside, { compact: false });
        const buttons = wrapper.findAll("button");
        const menuButton = buttons[buttons.length - 1];

        await menuButton.trigger("click");
        await flushDirectiveListeners(wrapper);
        expect(wrapper.vm.isShowingMenu).toBe(true);

        dispatchOnDocumentElement("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isShowingMenu).toBe(false);
    });
});

describe("SendMessageButton compact long-press menu (touch events)", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    it("keeps the menu open after a long-press release and does not send", async () => {
        const wrapper = mountButton(touchClickOutside, { compact: true });
        const button = wrapper.find("button");
        await runLongPressReleaseAssertions(wrapper, button, "touchstart");
    });
});

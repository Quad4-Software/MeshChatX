import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PromptDialog from "../../meshchatx/src/frontend/components/PromptDialog.vue";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

const MaterialDesignIcon = { template: '<div class="mdi"></div>', props: ["iconName"] };

function mountDialog() {
    return mount(PromptDialog, {
        attachTo: document.body,
        global: {
            components: { MaterialDesignIcon },
            mocks: {
                $t: (key) => key,
            },
        },
    });
}

function promptHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "prompt")?.[1];
}

function confirmHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
}

describe("PromptDialog UI", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.on).mockClear();
        vi.mocked(GlobalEmitter.off).mockClear();
    });

    afterEach(() => {
        document.body.innerHTML = "";
    });

    it("registers prompt listener on mount", () => {
        const wrapper = mountDialog();
        expect(GlobalEmitter.on).toHaveBeenCalledWith("prompt", expect.any(Function));
        expect(GlobalEmitter.on).toHaveBeenCalledWith("confirm", expect.any(Function));
        wrapper.unmount();
    });

    it("shows dialog with default value when show is called", async () => {
        const wrapper = mountDialog();
        const showFn = promptHandler();
        expect(showFn).toBeDefined();
        showFn({ message: "Version name?", defaultValue: "upload-1", resolve: vi.fn() });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.pendingPrompt).toEqual({ message: "Version name?" });
        expect(wrapper.vm.inputValue).toBe("upload-1");
        expect(wrapper.text()).toContain("Version name?");
        wrapper.unmount();
    });

    it("calls resolve with input value when OK clicked", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await wrapper.vm.$nextTick();
        wrapper.vm.inputValue = "reticulum-manual";
        await wrapper.find("button.bg-blue-600").trigger("click");
        expect(resolve).toHaveBeenCalledWith("reticulum-manual");
        expect(wrapper.vm.pendingPrompt).toBeNull();
        wrapper.unmount();
    });

    it("calls resolve(null) when Cancel clicked", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await wrapper.vm.$nextTick();
        const cancelBtn = wrapper.findAll("button").find((b) => b.text() === "common.cancel");
        await cancelBtn.trigger("click");
        expect(resolve).toHaveBeenCalledWith(null);
        expect(wrapper.vm.pendingPrompt).toBeNull();
        wrapper.unmount();
    });

    it("resolves the previous waiter with null when a second prompt opens", async () => {
        const first = vi.fn();
        const second = vi.fn();
        const wrapper = mountDialog();
        const showFn = promptHandler();
        showFn({ message: "First?", defaultValue: "a", resolve: first });
        await wrapper.vm.$nextTick();
        showFn({ message: "Second?", defaultValue: "b", resolve: second });
        await wrapper.vm.$nextTick();
        expect(first).toHaveBeenCalledWith(null);
        expect(wrapper.vm.pendingPrompt).toEqual({ message: "Second?" });
        expect(second).not.toHaveBeenCalled();
        wrapper.unmount();
    });

    it("cancels on window Escape", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await wrapper.vm.$nextTick();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        expect(resolve).toHaveBeenCalledWith(null);
        expect(wrapper.vm.pendingPrompt).toBeNull();
        wrapper.unmount();
    });

    it("does not submit while an IME composition Enter is in progress", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await wrapper.vm.$nextTick();
        const input = wrapper.find("input");
        await input.trigger("keydown", { key: "Enter", isComposing: true });
        expect(resolve).not.toHaveBeenCalled();
        expect(wrapper.vm.pendingPrompt).not.toBeNull();
        wrapper.unmount();
    });

    it("cancels the pending waiter when a confirm opens", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await wrapper.vm.$nextTick();
        confirmHandler()();
        expect(resolve).toHaveBeenCalledWith(null);
        expect(wrapper.vm.pendingPrompt).toBeNull();
        wrapper.unmount();
    });

    it("resolves null when unmounted while open", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await wrapper.vm.$nextTick();
        wrapper.unmount();
        expect(resolve).toHaveBeenCalledWith(null);
    });
});

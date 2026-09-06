import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConfirmDialog from "../../meshchatx/src/frontend/components/ConfirmDialog.vue";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

const MaterialDesignIcon = { template: '<div class="mdi"></div>', props: ["iconName"] };

function mountDialog() {
    return mount(ConfirmDialog, {
        attachTo: document.body,
        global: {
            components: { MaterialDesignIcon },
            mocks: { $t: (key) => key },
        },
    });
}

function confirmHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
}

function promptHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "prompt")?.[1];
}

describe("ConfirmDialog UI", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.on).mockClear();
        vi.mocked(GlobalEmitter.off).mockClear();
    });

    afterEach(() => {
        document.body.innerHTML = "";
    });

    it("registers confirm listener on mount", () => {
        mountDialog();
        expect(GlobalEmitter.on).toHaveBeenCalledWith("confirm", expect.any(Function));
        expect(GlobalEmitter.on).toHaveBeenCalledWith("prompt", expect.any(Function));
    });

    it("does not show dialog when pendingConfirm is null", () => {
        const wrapper = mountDialog();
        expect(wrapper.vm.pendingConfirm).toBeNull();
        expect(wrapper.find(".fixed.inset-0").exists()).toBe(false);
        wrapper.unmount();
    });

    it("shows dialog with message when show is called", async () => {
        const wrapper = mountDialog();
        const showFn = confirmHandler();
        expect(showFn).toBeDefined();
        showFn({ message: "Delete this item?", resolve: vi.fn() });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.pendingConfirm).toEqual({ message: "Delete this item?", title: "" });
        expect(wrapper.text()).toContain("common.confirm_action");
        expect(wrapper.text()).toContain("Delete this item?");
        wrapper.unmount();
    });

    it("has Cancel and Confirm buttons when visible", async () => {
        const wrapper = mountDialog();
        confirmHandler()({ message: "Sure?", resolve: vi.fn() });
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("common.cancel");
        expect(wrapper.text()).toContain("common.confirm");
        wrapper.unmount();
    });

    it("calls resolve(true) and clears when Confirm clicked", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        confirmHandler()({ message: "Sure?", resolve });
        await wrapper.vm.$nextTick();
        await wrapper.find("button.danger-action").trigger("click");
        expect(resolve).toHaveBeenCalledWith(true);
        expect(wrapper.vm.pendingConfirm).toBeNull();
        wrapper.unmount();
    });

    it("calls resolve(false) when Cancel clicked", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        confirmHandler()({ message: "Sure?", resolve });
        await wrapper.vm.$nextTick();
        const cancelBtn = wrapper.findAll("button").find((b) => b.text() === "common.cancel");
        await cancelBtn.trigger("click");
        expect(resolve).toHaveBeenCalledWith(false);
        expect(wrapper.vm.pendingConfirm).toBeNull();
        wrapper.unmount();
    });

    it("resolves the previous waiter with false when a second confirm opens", async () => {
        const first = vi.fn();
        const second = vi.fn();
        const wrapper = mountDialog();
        const showFn = confirmHandler();
        showFn({ message: "First?", resolve: first });
        await wrapper.vm.$nextTick();
        showFn({ message: "Second?", resolve: second });
        await wrapper.vm.$nextTick();
        expect(first).toHaveBeenCalledWith(false);
        expect(wrapper.vm.pendingConfirm).toEqual({ message: "Second?", title: "" });
        expect(second).not.toHaveBeenCalled();
        wrapper.unmount();
    });

    it("shows an optional title when provided", async () => {
        const wrapper = mountDialog();
        confirmHandler()({ message: "All messages will be lost.", title: "Delete conversations", resolve: vi.fn() });
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("Delete conversations");
        expect(wrapper.text()).not.toContain("common.confirm_action");
        wrapper.unmount();
    });

    it("cancels on Escape and confirms on Enter", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        const showFn = confirmHandler();
        showFn({ message: "Sure?", resolve });
        await wrapper.vm.$nextTick();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        expect(resolve).toHaveBeenCalledWith(false);
        expect(wrapper.vm.pendingConfirm).toBeNull();

        const resolveEnter = vi.fn();
        showFn({ message: "Sure again?", resolve: resolveEnter });
        await wrapper.vm.$nextTick();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        expect(resolveEnter).toHaveBeenCalledWith(true);
        wrapper.unmount();
    });

    it("does not confirm on the Enter key that opened the dialog", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        confirmHandler()({ message: "Delete?", resolve });
        await wrapper.vm.$nextTick();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, repeat: true }));
        expect(resolve).not.toHaveBeenCalled();
        expect(wrapper.vm.pendingConfirm).not.toBeNull();

        window.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        expect(resolve).toHaveBeenCalledWith(true);
        wrapper.unmount();
    });

    it("lets Enter on Cancel dismiss instead of confirming", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        confirmHandler()({ message: "Sure?", resolve });
        await wrapper.vm.$nextTick();
        const cancelBtn = wrapper.find("[data-confirm-cancel]").element;
        cancelBtn.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        expect(resolve).not.toHaveBeenCalledWith(true);
        wrapper.unmount();
    });

    it("cancels the pending waiter when a prompt opens", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        confirmHandler()({ message: "Sure?", resolve });
        await wrapper.vm.$nextTick();
        promptHandler()();
        expect(resolve).toHaveBeenCalledWith(false);
        expect(wrapper.vm.pendingConfirm).toBeNull();
        wrapper.unmount();
    });

    it("resolves false when unmounted while open", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        confirmHandler()({ message: "Sure?", resolve });
        await wrapper.vm.$nextTick();
        wrapper.unmount();
        expect(resolve).toHaveBeenCalledWith(false);
    });
});

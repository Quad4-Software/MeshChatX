import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PromptDialog from "../../meshchatx/src/frontend/components/PromptDialog.vue";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

const MaterialDesignIcon = { template: '<div class="mdi"></div>', props: ["iconName"] };

function mountDialog() {
    return mount(PromptDialog, {
        global: {
            components: { MaterialDesignIcon },
            mocks: {
                $t: (key) => key,
            },
        },
    });
}

describe("PromptDialog UI", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.on).mockClear();
        vi.mocked(GlobalEmitter.off).mockClear();
    });

    it("registers prompt listener on mount", () => {
        mountDialog();
        expect(GlobalEmitter.on).toHaveBeenCalledWith("prompt", expect.any(Function));
    });

    it("shows dialog with default value when show is called", async () => {
        const wrapper = mountDialog();
        const showFn = GlobalEmitter.on.mock.calls.find((c) => c[0] === "prompt")?.[1];
        expect(showFn).toBeDefined();
        showFn({ message: "Version name?", defaultValue: "upload-1", resolve: vi.fn() });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.pendingPrompt).toEqual({ message: "Version name?" });
        expect(wrapper.vm.inputValue).toBe("upload-1");
        expect(wrapper.text()).toContain("Version name?");
    });

    it("calls resolve with input value when OK clicked", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        const showFn = GlobalEmitter.on.mock.calls.find((c) => c[0] === "prompt")?.[1];
        showFn({ message: "Name?", defaultValue: "a", resolve });
        await wrapper.vm.$nextTick();
        wrapper.vm.inputValue = "reticulum-manual";
        await wrapper.find("button.bg-blue-600").trigger("click");
        expect(resolve).toHaveBeenCalledWith("reticulum-manual");
        expect(wrapper.vm.pendingPrompt).toBeNull();
    });

    it("calls resolve(null) when Cancel clicked", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        const showFn = GlobalEmitter.on.mock.calls.find((c) => c[0] === "prompt")?.[1];
        showFn({ message: "Name?", defaultValue: "a", resolve });
        await wrapper.vm.$nextTick();
        const cancelBtn = wrapper.findAll("button").find((b) => b.text() === "common.cancel");
        await cancelBtn.trigger("click");
        expect(resolve).toHaveBeenCalledWith(null);
        expect(wrapper.vm.pendingPrompt).toBeNull();
    });

    it("resolves the previous waiter with null when a second prompt opens", async () => {
        const first = vi.fn();
        const second = vi.fn();
        const wrapper = mountDialog();
        const showFn = GlobalEmitter.on.mock.calls.find((c) => c[0] === "prompt")?.[1];
        showFn({ message: "First?", defaultValue: "a", resolve: first });
        await wrapper.vm.$nextTick();
        showFn({ message: "Second?", defaultValue: "b", resolve: second });
        await wrapper.vm.$nextTick();
        expect(first).toHaveBeenCalledWith(null);
        expect(wrapper.vm.pendingPrompt).toEqual({ message: "Second?" });
        expect(second).not.toHaveBeenCalled();
    });
});

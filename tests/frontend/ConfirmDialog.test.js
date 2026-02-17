import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ConfirmDialog from "../../meshchatx/src/frontend/components/ConfirmDialog.vue";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

const MaterialDesignIcon = { template: "<div class=\"mdi\"></div>", props: ["iconName"] };

function mountDialog() {
    return mount(ConfirmDialog, {
        global: { components: { MaterialDesignIcon } },
    });
}

describe("ConfirmDialog UI", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.on).mockClear();
        vi.mocked(GlobalEmitter.off).mockClear();
    });

    it("registers confirm listener on mount", () => {
        mountDialog();
        expect(GlobalEmitter.on).toHaveBeenCalledWith("confirm", expect.any(Function));
    });

    it("does not show dialog when pendingConfirm is null", () => {
        const wrapper = mountDialog();
        expect(wrapper.vm.pendingConfirm).toBeNull();
        expect(wrapper.find(".fixed.inset-0").exists()).toBe(false);
    });

    it("shows dialog with message when show is called", async () => {
        const wrapper = mountDialog();
        const showFn = GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
        expect(showFn).toBeDefined();
        showFn({ message: "Delete this item?", resolve: vi.fn() });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.pendingConfirm).toEqual({ message: "Delete this item?" });
        expect(wrapper.text()).toContain("Confirm Action");
        expect(wrapper.text()).toContain("Delete this item?");
    });

    it("has Cancel and Confirm buttons when visible", async () => {
        const wrapper = mountDialog();
        const showFn = GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
        showFn({ message: "Sure?", resolve: vi.fn() });
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("Cancel");
        expect(wrapper.text()).toContain("Confirm");
    });

    it("calls resolve(true) and clears when Confirm clicked", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        const showFn = GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
        showFn({ message: "Sure?", resolve });
        await wrapper.vm.$nextTick();
        await wrapper.find("button.bg-red-600").trigger("click");
        expect(resolve).toHaveBeenCalledWith(true);
        expect(wrapper.vm.pendingConfirm).toBeNull();
    });

    it("calls resolve(false) when Cancel clicked", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        const showFn = GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
        showFn({ message: "Sure?", resolve });
        await wrapper.vm.$nextTick();
        const cancelBtn = wrapper.findAll("button").find((b) => b.text() === "Cancel");
        await cancelBtn.trigger("click");
        expect(resolve).toHaveBeenCalledWith(false);
        expect(wrapper.vm.pendingConfirm).toBeNull();
    });
});

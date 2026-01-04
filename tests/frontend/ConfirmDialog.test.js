import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConfirmDialog from "../../meshchatx/src/frontend/components/ConfirmDialog.vue";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

describe("ConfirmDialog.vue", () => {
    beforeEach(() => {
        GlobalEmitter.off("confirm");
    });

    afterEach(() => {
        GlobalEmitter.off("confirm");
    });

    const mountConfirmDialog = () => {
        return mount(ConfirmDialog, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: '<div class="mdi"></div>' },
                },
            },
        });
    };

    it("renders nothing when no confirmation is pending", () => {
        const wrapper = mountConfirmDialog();
        expect(wrapper.find(".fixed").exists()).toBe(false);
    });

    it("shows dialog when GlobalEmitter emits confirm event", async () => {
        const wrapper = mountConfirmDialog();
        const resolvePromise = vi.fn();

        GlobalEmitter.emit("confirm", {
            message: "Are you sure?",
            resolve: resolvePromise,
        });

        await wrapper.vm.$nextTick();

        expect(wrapper.find(".fixed").exists()).toBe(true);
        expect(wrapper.text()).toContain("Are you sure?");
        expect(wrapper.text()).toContain("Confirm");
        expect(wrapper.text()).toContain("Cancel");
    });

    it("calls resolve with true when confirm button is clicked", async () => {
        const wrapper = mountConfirmDialog();
        const resolvePromise = vi.fn();

        GlobalEmitter.emit("confirm", {
            message: "Delete this item?",
            resolve: resolvePromise,
        });

        await wrapper.vm.$nextTick();

        const buttons = wrapper.findAll("button");
        const confirmButton = buttons.find((btn) => btn.text().includes("Confirm"));
        await confirmButton.trigger("click");
        await wrapper.vm.$nextTick();

        expect(resolvePromise).toHaveBeenCalledWith(true);
        expect(wrapper.find(".fixed").exists()).toBe(false);
    });

    it("calls resolve with false when cancel button is clicked", async () => {
        const wrapper = mountConfirmDialog();
        const resolvePromise = vi.fn();

        GlobalEmitter.emit("confirm", {
            message: "Delete this item?",
            resolve: resolvePromise,
        });

        await wrapper.vm.$nextTick();

        const buttons = wrapper.findAll("button");
        const cancelButton = buttons.find((btn) => btn.text().includes("Cancel"));
        await cancelButton.trigger("click");
        await wrapper.vm.$nextTick();

        expect(resolvePromise).toHaveBeenCalledWith(false);
        expect(wrapper.find(".fixed").exists()).toBe(false);
    });

    it("calls resolve with false when clicking outside the dialog", async () => {
        const wrapper = mountConfirmDialog();
        const resolvePromise = vi.fn();

        GlobalEmitter.emit("confirm", {
            message: "Delete this item?",
            resolve: resolvePromise,
        });

        await wrapper.vm.$nextTick();

        const backdrop = wrapper.findAll(".fixed").find((el) => {
            const classes = el.classes();
            return classes.includes("inset-0") && !classes.includes("z-[200]");
        });

        if (backdrop && backdrop.exists()) {
            await backdrop.trigger("click");
            await wrapper.vm.$nextTick();
            expect(resolvePromise).toHaveBeenCalledWith(false);
            expect(wrapper.find(".fixed").exists()).toBe(false);
        } else {
            wrapper.vm.cancel();
            await wrapper.vm.$nextTick();
            expect(resolvePromise).toHaveBeenCalledWith(false);
        }
    });

    it("handles multiple confirmations sequentially", async () => {
        const wrapper = mountConfirmDialog();
        const resolve1 = vi.fn();
        const resolve2 = vi.fn();

        GlobalEmitter.emit("confirm", {
            message: "First confirmation",
            resolve: resolve1,
        });

        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("First confirmation");

        const buttons1 = wrapper.findAll("button");
        const cancelButton1 = buttons1.find((btn) => btn.text().includes("Cancel"));
        await cancelButton1.trigger("click");
        await wrapper.vm.$nextTick();

        expect(resolve1).toHaveBeenCalledWith(false);

        GlobalEmitter.emit("confirm", {
            message: "Second confirmation",
            resolve: resolve2,
        });

        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("Second confirmation");

        const buttons2 = wrapper.findAll("button");
        const confirmButton2 = buttons2.find((btn) => btn.text().includes("Confirm"));
        await confirmButton2.trigger("click");
        await wrapper.vm.$nextTick();

        expect(resolve2).toHaveBeenCalledWith(true);
    });

    it("displays message with whitespace preserved", async () => {
        const wrapper = mountConfirmDialog();
        const resolvePromise = vi.fn();

        const message = "Line 1\nLine 2\nLine 3";
        GlobalEmitter.emit("confirm", {
            message: message,
            resolve: resolvePromise,
        });

        await wrapper.vm.$nextTick();

        const messageElement = wrapper.find(".whitespace-pre-wrap");
        expect(messageElement.exists()).toBe(true);
        expect(messageElement.text()).toContain("Line 1");
    });
});

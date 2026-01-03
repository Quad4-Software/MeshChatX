import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import Toast from "@/components/Toast.vue";
import GlobalEmitter from "@/js/GlobalEmitter";

describe("Toast.vue", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
        // Clear all listeners from GlobalEmitter to avoid test pollution
        GlobalEmitter.off("toast");
    });

    it("adds a toast when GlobalEmitter emits 'toast'", async () => {
        const wrapper = mount(Toast);

        GlobalEmitter.emit("toast", { message: "Test Message", type: "success" });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Test Message");
        expect(wrapper.findComponent({ name: "MaterialDesignIcon" }).props("iconName")).toBe("check-circle");
    });

    it("removes a toast after duration", async () => {
        const wrapper = mount(Toast);

        GlobalEmitter.emit("toast", { message: "Test Message", duration: 1000 });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Test Message");

        vi.advanceTimersByTime(1001);
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).not.toContain("Test Message");
    });

    it("removes a toast when clicking the close button", async () => {
        const wrapper = mount(Toast);

        GlobalEmitter.emit("toast", { message: "Test Message", duration: 0 });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Test Message");

        const closeButton = wrapper.find("button");
        await closeButton.trigger("click");

        expect(wrapper.text()).not.toContain("Test Message");
    });

    it("assigns correct classes for different toast types", async () => {
        const wrapper = mount(Toast);

        GlobalEmitter.emit("toast", { message: "Success", type: "success" });
        GlobalEmitter.emit("toast", { message: "Error", type: "error" });
        await wrapper.vm.$nextTick();

        const toasts = wrapper.findAll(".pointer-events-auto");
        expect(toasts[0].classes()).toContain("border-green-500/30");
        expect(toasts[1].classes()).toContain("border-red-500/30");
    });
});

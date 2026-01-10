import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import Toast from "@/components/Toast.vue";
import GlobalEmitter from "@/js/GlobalEmitter";

describe("Toast.vue", () => {
    let wrapper;

    beforeEach(() => {
        vi.useFakeTimers();
        wrapper = mount(Toast, {
            global: {
                mocks: {
                    $t: (msg) => msg,
                },
                stubs: {
                    TransitionGroup: { template: "<div><slot /></div>" },
                    MaterialDesignIcon: {
                        name: "MaterialDesignIcon",
                        template: '<div class="mdi-stub"></div>',
                        props: ["iconName"],
                    },
                },
            },
        });
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.unmount();
        }
        vi.useRealTimers();
    });

    it("adds a toast when GlobalEmitter emits 'toast'", async () => {
        GlobalEmitter.emit("toast", { message: "Test Message", type: "success" });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Test Message");
        const icon = wrapper.findComponent({ name: "MaterialDesignIcon" });
        expect(icon.exists()).toBe(true);
        expect(icon.props("iconName")).toBe("check-circle");
    });

    it("removes a toast after duration", async () => {
        GlobalEmitter.emit("toast", { message: "Test Message", duration: 1000 });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Test Message");

        vi.advanceTimersByTime(1001);
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).not.toContain("Test Message");
    });

    it("removes a toast when clicking the close button", async () => {
        GlobalEmitter.emit("toast", { message: "Test Message", duration: 0 });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Test Message");

        const closeButton = wrapper.find("button");
        await closeButton.trigger("click");
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).not.toContain("Test Message");
    });

    it("assigns correct classes for different toast types", async () => {
        GlobalEmitter.emit("toast", { message: "Success", type: "success" });
        GlobalEmitter.emit("toast", { message: "Error", type: "error" });
        await wrapper.vm.$nextTick();

        const toasts = wrapper.findAll(".pointer-events-auto");
        expect(toasts[0].classes()).toContain("border-green-500/30");
        expect(toasts[1].classes()).toContain("border-red-500/30");
    });
});

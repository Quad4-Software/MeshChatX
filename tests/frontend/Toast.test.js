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

    it("removes a toast when GlobalEmitter emits toast-dismiss with matching key", async () => {
        GlobalEmitter.emit("toast", { message: "Loading", type: "loading", duration: 0, key: "job-1" });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Loading");

        GlobalEmitter.emit("toast-dismiss", { key: "job-1" });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).not.toContain("Loading");
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

    it("shows no toasts initially", () => {
        expect(wrapper.findAll(".pointer-events-auto").length).toBe(0);
    });

    it("single toast has a close button", async () => {
        GlobalEmitter.emit("toast", { message: "Hi", duration: 0 });
        await wrapper.vm.$nextTick();
        const toast = wrapper.find(".pointer-events-auto");
        expect(toast.find("button").exists()).toBe(true);
    });

    it("positions container with mobile-safe bottom offset", () => {
        const container = wrapper.find("[class*='fixed']");
        expect(container.exists()).toBe(true);
        const cls = container.classes().join(" ");
        expect(cls).toContain("max-sm:bottom-");
        expect(cls).not.toContain("max-sm:bottom-[calc(5.75rem");
    });

    it("dismisses toast on horizontal swipe past threshold", async () => {
        GlobalEmitter.emit("toast", { message: "Swipe me", duration: 0 });
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Swipe me");
        const toastVm = wrapper.vm.toasts[0];

        // Simulate swipe right by 120px (past 100px threshold)
        wrapper.vm.onTouchStart({ touches: [{ clientX: 100, clientY: 50 }] }, toastVm);
        wrapper.vm.onTouchMove({ touches: [{ clientX: 220, clientY: 50 }] }, toastVm);
        wrapper.vm.onTouchEnd(toastVm);
        await vi.advanceTimersByTimeAsync(300);
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).not.toContain("Swipe me");
    });

    it("snaps toast back when swipe is below threshold", async () => {
        GlobalEmitter.emit("toast", { message: "Stay", duration: 0 });
        await wrapper.vm.$nextTick();

        const toastVm = wrapper.vm.toasts[0];

        wrapper.vm.onTouchStart({ touches: [{ clientX: 100, clientY: 50 }] }, toastVm);
        wrapper.vm.onTouchMove({ touches: [{ clientX: 140, clientY: 50 }] }, toastVm);
        wrapper.vm.onTouchEnd(toastVm);
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Stay");
        expect(toastVm._swipeX).toBe(0);
    });
});

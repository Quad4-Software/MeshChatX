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

    it("emits toast-dismissed with key when a keyed toast is closed", async () => {
        const dismissed = vi.fn();
        GlobalEmitter.on("toast-dismissed", dismissed);
        GlobalEmitter.emit("toast", {
            message: "Memory",
            type: "warning",
            duration: 0,
            key: "health-memory-warning",
        });
        await wrapper.vm.$nextTick();
        await wrapper.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        expect(dismissed).toHaveBeenCalledWith({ key: "health-memory-warning" });
        GlobalEmitter.off("toast-dismissed", dismissed);
    });

    it("assigns correct classes for different toast types", async () => {
        GlobalEmitter.emit("toast", { message: "Success", type: "success" });
        GlobalEmitter.emit("toast", { message: "Error", type: "error" });
        await wrapper.vm.$nextTick();

        const toasts = wrapper.findAll(".pointer-events-auto");
        expect(toasts[0].classes()).toContain("border-sem-success/30");
        expect(toasts[1].classes()).toContain("border-sem-danger/30");
    });

    it("replaces an unkeyed toast with the same message and type instead of stacking", async () => {
        GlobalEmitter.emit("toast", { message: "Syncing", type: "info" });
        await wrapper.vm.$nextTick();

        GlobalEmitter.emit("toast", { message: "Syncing", type: "info" });
        await wrapper.vm.$nextTick();

        const toasts = wrapper.findAll(".pointer-events-auto");
        expect(toasts.length).toBe(1);
        expect(wrapper.text()).toContain("Syncing");
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
        expect(cls).toContain("max-sm:bottom-[calc(4.5rem+max(1.25rem,env(safe-area-inset-bottom,0px)))]");
        expect(cls).not.toContain("max-sm:bottom-[calc(1rem+env(safe-area-inset-bottom,0px))]");
    });

    it("close control has a 44px touch target", async () => {
        GlobalEmitter.emit("toast", { message: "Hi", duration: 0 });
        await wrapper.vm.$nextTick();
        const closeButton = wrapper.find("button");
        expect(closeButton.classes().join(" ")).toContain("min-h-[44px]");
        expect(closeButton.classes().join(" ")).toContain("min-w-[44px]");
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

    it("renders an action button and runs the handler on click", async () => {
        const handler = vi.fn();
        GlobalEmitter.emit("toast", {
            message: "No node",
            type: "error",
            duration: 0,
            action: { label: "Configure", handler },
        });
        await wrapper.vm.$nextTick();

        const actionButton = wrapper.findAll("button").find((b) => b.text().includes("Configure"));
        expect(actionButton).toBeTruthy();
        await actionButton.trigger("click");
        await wrapper.vm.$nextTick();

        expect(handler).toHaveBeenCalledOnce();
        expect(wrapper.text()).not.toContain("No node");
    });

    it("dismisses the toast even when the action handler throws", async () => {
        const handler = vi.fn(() => {
            throw new Error("boom");
        });
        const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
        GlobalEmitter.emit("toast", {
            message: "No node",
            type: "error",
            duration: 0,
            action: { label: "Configure", handler },
        });
        await wrapper.vm.$nextTick();
        const actionButton = wrapper.findAll("button").find((b) => b.text().includes("Configure"));
        await actionButton.trigger("click");
        expect(handler).toHaveBeenCalledOnce();
        // Toast still dismisses even though the handler threw.
        expect(wrapper.text()).not.toContain("No node");
        consoleSpy.mockRestore();
    });

    it("shows only one toast at a time on mobile viewports", async () => {
        const originalMm = window.matchMedia;
        window.matchMedia = vi.fn((q) => ({
            matches: q.includes("max-width"),
            media: q,
            addEventListener: () => {},
            removeEventListener: () => {},
        }));

        GlobalEmitter.emit("toast", { message: "First", type: "info", duration: 0 });
        await wrapper.vm.$nextTick();
        GlobalEmitter.emit("toast", { message: "Second", type: "error", duration: 0 });
        await wrapper.vm.$nextTick();

        const toasts = wrapper.findAll(".pointer-events-auto");
        expect(toasts.length).toBe(1);
        expect(wrapper.text()).toContain("Second");
        expect(wrapper.text()).not.toContain("First");
        window.matchMedia = originalMm;
    });

    it("stacks toasts on desktop viewports", async () => {
        const originalMm = window.matchMedia;
        window.matchMedia = vi.fn((q) => ({
            matches: false,
            media: q,
            addEventListener: () => {},
            removeEventListener: () => {},
        }));

        GlobalEmitter.emit("toast", { message: "One", type: "info", duration: 0 });
        GlobalEmitter.emit("toast", { message: "Two", type: "info", duration: 0 });
        await wrapper.vm.$nextTick();

        expect(wrapper.findAll(".pointer-events-auto").length).toBe(2);
        window.matchMedia = originalMm;
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

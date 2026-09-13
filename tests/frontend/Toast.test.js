import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { tick } from "svelte";
import Toast from "@/ui/svelte/Toast.svelte";
import GlobalEmitter from "@/js/GlobalEmitter";

describe("Toast.svelte", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        cleanup();
        vi.useRealTimers();
    });

    it("adds a toast when GlobalEmitter emits toast", async () => {
        const { container } = render(Toast);
        GlobalEmitter.emit("toast", { message: "Test Message", type: "success" });
        await tick();
        expect(container.textContent).toContain("Test Message");
        const icon = container.querySelector("svg");
        expect(icon).toBeTruthy();
        expect(icon.className.baseVal || icon.getAttribute("class") || "").toContain("text-green-500");
    });

    it("removes a toast after duration", async () => {
        const { container } = render(Toast);
        GlobalEmitter.emit("toast", { message: "Test Message", duration: 1000 });
        await tick();
        expect(container.textContent).toContain("Test Message");
        await vi.advanceTimersByTimeAsync(1001);
        await tick();
        expect(container.textContent).not.toContain("Test Message");
    });

    it("removes a toast when GlobalEmitter emits toast-dismiss with matching key", async () => {
        const { container } = render(Toast);
        GlobalEmitter.emit("toast", { message: "Loading", type: "loading", duration: 0, key: "job-1" });
        await tick();
        expect(container.textContent).toContain("Loading");
        GlobalEmitter.emit("toast-dismiss", { key: "job-1" });
        await tick();
        expect(container.textContent).not.toContain("Loading");
    });

    it("removes a toast when clicking the close button", async () => {
        const { container } = render(Toast);
        GlobalEmitter.emit("toast", { message: "Test Message", duration: 0 });
        await tick();
        expect(container.textContent).toContain("Test Message");
        await fireEvent.click(container.querySelector("button"));
        await tick();
        expect(container.textContent).not.toContain("Test Message");
    });

    it("emits toast-dismissed with key when a keyed toast is closed", async () => {
        const dismissed = vi.fn();
        GlobalEmitter.on("toast-dismissed", dismissed);
        render(Toast);
        GlobalEmitter.emit("toast", {
            message: "Memory",
            type: "warning",
            duration: 0,
            key: "health-memory-warning",
        });
        await tick();
        await fireEvent.click(screen.getByRole("button"));
        await tick();
        expect(dismissed).toHaveBeenCalledWith({ key: "health-memory-warning" });
        GlobalEmitter.off("toast-dismissed", dismissed);
    });

    it("assigns correct classes for different toast types", async () => {
        const { container } = render(Toast);
        GlobalEmitter.emit("toast", { message: "Success", type: "success" });
        GlobalEmitter.emit("toast", { message: "Error", type: "error" });
        await tick();
        const toasts = container.querySelectorAll(".pointer-events-auto");
        expect(toasts[0].className).toContain("border-green-500/30");
        expect(toasts[1].className).toContain("border-red-500/30");
    });

    it("shows no toasts initially", () => {
        const { container } = render(Toast);
        expect(container.querySelectorAll(".pointer-events-auto").length).toBe(0);
    });

    it("positions container with mobile-safe bottom offset", () => {
        const { container } = render(Toast);
        const el = container.querySelector("[class*='fixed']");
        expect(el).toBeTruthy();
        expect(el.className).toContain("max-sm:bottom-[calc(5.5rem+env(safe-area-inset-bottom,0px))]");
    });

    it("renders non-string toast payloads without throwing", async () => {
        const { container } = render(Toast);
        GlobalEmitter.emit("toast", { message: 42, type: "info", duration: 0 });
        await tick();
        expect(container.textContent).toContain("42");
    });

    it("translates dotted i18n keys and leaves plain sentences alone", async () => {
        const { container } = render(Toast);
        GlobalEmitter.emit("toast", { message: "Hello world.", type: "success", duration: 0 });
        GlobalEmitter.emit("toast", { message: "app.announce_sent", type: "info", duration: 0 });
        await tick();
        expect(container.textContent).toContain("Hello world.");
        // Key is looked up (fixture locale resolves announce_sent) rather than shown raw.
        expect(container.textContent).not.toContain("app.announce_sent");
        expect(container.textContent?.toLowerCase()).toMatch(/announce/);
    });
});

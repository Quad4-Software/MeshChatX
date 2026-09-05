import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConfirmDialog from "../../meshchatx/src/frontend/components/ConfirmDialog.vue";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.js";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

function mountDialog() {
    return mount(ConfirmDialog, {
        attachTo: document.body,
    });
}

function confirmHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
}

function promptHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "prompt")?.[1];
}

async function flush() {
    await Promise.resolve();
    await Promise.resolve();
}

describe("ConfirmDialog UI", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.on).mockClear();
        vi.mocked(GlobalEmitter.off).mockClear();
        registerTranslator(null);
        registerFallbackMessages({
            common: {
                confirm_action: "common.confirm_action",
                cancel: "common.cancel",
                confirm: "common.confirm",
            },
        });
    });

    afterEach(() => {
        document.body.innerHTML = "";
    });

    it("registers confirm listener on mount", async () => {
        mountDialog();
        await flush();
        expect(GlobalEmitter.on).toHaveBeenCalledWith("confirm", expect.any(Function));
        expect(GlobalEmitter.on).toHaveBeenCalledWith("prompt", expect.any(Function));
    });

    it("does not show dialog when closed", async () => {
        mountDialog();
        await flush();
        expect(document.querySelector(".confirm-dialog-root")).toBeNull();
    });

    it("shows dialog with message when show is called", async () => {
        mountDialog();
        await flush();
        const showFn = confirmHandler();
        expect(showFn).toBeDefined();
        showFn({ message: "Delete this item?", resolve: vi.fn() });
        await flush();
        expect(document.body.textContent).toContain("common.confirm_action");
        expect(document.body.textContent).toContain("Delete this item?");
    });

    it("has Cancel and Confirm buttons when visible", async () => {
        mountDialog();
        await flush();
        confirmHandler()({ message: "Sure?", resolve: vi.fn() });
        await flush();
        expect(document.body.textContent).toContain("common.cancel");
        expect(document.body.textContent).toContain("common.confirm");
    });

    it("calls resolve(true) and clears when Confirm clicked", async () => {
        const resolve = vi.fn();
        mountDialog();
        await flush();
        confirmHandler()({ message: "Sure?", resolve });
        await flush();
        document.querySelector("button.bg-red-600").click();
        await flush();
        expect(resolve).toHaveBeenCalledWith(true);
        expect(document.querySelector(".confirm-dialog-root")).toBeNull();
    });

    it("calls resolve(false) when Cancel clicked", async () => {
        const resolve = vi.fn();
        mountDialog();
        await flush();
        confirmHandler()({ message: "Sure?", resolve });
        await flush();
        document.querySelector("[data-confirm-cancel]").click();
        await flush();
        expect(resolve).toHaveBeenCalledWith(false);
    });

    it("resolves the previous waiter with false when a second confirm opens", async () => {
        const first = vi.fn();
        const second = vi.fn();
        mountDialog();
        await flush();
        const showFn = confirmHandler();
        showFn({ message: "First?", resolve: first });
        await flush();
        showFn({ message: "Second?", resolve: second });
        await flush();
        expect(first).toHaveBeenCalledWith(false);
        expect(document.body.textContent).toContain("Second?");
        expect(second).not.toHaveBeenCalled();
    });

    it("shows an optional title when provided", async () => {
        mountDialog();
        await flush();
        confirmHandler()({ message: "All messages will be lost.", title: "Delete conversations", resolve: vi.fn() });
        await flush();
        expect(document.body.textContent).toContain("Delete conversations");
        expect(document.body.textContent).not.toContain("common.confirm_action");
    });

    it("cancels on Escape and confirms on Enter", async () => {
        const resolve = vi.fn();
        mountDialog();
        await flush();
        const showFn = confirmHandler();
        showFn({ message: "Sure?", resolve });
        await flush();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        await flush();
        expect(resolve).toHaveBeenCalledWith(false);
        expect(document.querySelector(".confirm-dialog-root")).toBeNull();

        const resolveEnter = vi.fn();
        showFn({ message: "Sure again?", resolve: resolveEnter });
        await flush();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        await flush();
        expect(resolveEnter).toHaveBeenCalledWith(true);
    });

    it("does not confirm on the Enter key that opened the dialog", async () => {
        const resolve = vi.fn();
        mountDialog();
        await flush();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        confirmHandler()({ message: "Delete?", resolve });
        await flush();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, repeat: true }));
        await flush();
        expect(resolve).not.toHaveBeenCalled();
        expect(document.querySelector(".confirm-dialog-root")).not.toBeNull();

        window.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        await flush();
        expect(resolve).toHaveBeenCalledWith(true);
    });

    it("lets Enter on Cancel dismiss instead of confirming", async () => {
        const resolve = vi.fn();
        mountDialog();
        await flush();
        confirmHandler()({ message: "Sure?", resolve });
        await flush();
        const cancelBtn = document.querySelector("[data-confirm-cancel]");
        cancelBtn.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        await flush();
        expect(resolve).not.toHaveBeenCalledWith(true);
    });

    it("cancels the pending waiter when a prompt opens", async () => {
        const resolve = vi.fn();
        mountDialog();
        await flush();
        confirmHandler()({ message: "Sure?", resolve });
        await flush();
        promptHandler()();
        await flush();
        expect(resolve).toHaveBeenCalledWith(false);
        expect(document.querySelector(".confirm-dialog-root")).toBeNull();
    });

    it("resolves false when unmounted while open", async () => {
        const resolve = vi.fn();
        const wrapper = mountDialog();
        await flush();
        confirmHandler()({ message: "Sure?", resolve });
        await flush();
        wrapper.unmount();
        await flush();
        expect(resolve).toHaveBeenCalledWith(false);
    });
});

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { tick } from "svelte";
import ConfirmDialog from "../../meshchatx/src/frontend/ui/svelte/ConfirmDialog.svelte";
import { registerFallbackMessages, registerTranslator } from "../../meshchatx/src/frontend/js/i18n.js";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

function confirmHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
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
        cleanup();
        document.body.innerHTML = "";
    });

    it("registers confirm listener on mount", () => {
        render(ConfirmDialog);
        expect(GlobalEmitter.on).toHaveBeenCalledWith("confirm", expect.any(Function));
        expect(GlobalEmitter.on).toHaveBeenCalledWith("prompt", expect.any(Function));
    });

    it("does not show dialog when closed", () => {
        render(ConfirmDialog);
        expect(document.querySelector(".confirm-dialog-root")).toBeNull();
    });

    it("shows dialog with message when show is called", async () => {
        render(ConfirmDialog);
        const showFn = confirmHandler();
        expect(showFn).toBeDefined();
        showFn({ message: "Delete this item?", resolve: vi.fn() });
        await tick();
        expect(document.body.textContent).toContain("common.confirm_action");
        expect(document.body.textContent).toContain("Delete this item?");
    });

    it("has Cancel and Confirm buttons when visible", async () => {
        render(ConfirmDialog);
        confirmHandler()({ message: "Sure?", resolve: vi.fn() });
        await tick();
        expect(document.body.textContent).toContain("common.cancel");
        expect(document.body.textContent).toContain("common.confirm");
    });

    it("calls resolve(true) and clears when Confirm clicked", async () => {
        const resolve = vi.fn();
        render(ConfirmDialog);
        confirmHandler()({ message: "Sure?", resolve });
        await tick();
        const confirmBtn = document.querySelector("button.bg-red-600");
        expect(confirmBtn).toBeTruthy();
        await fireEvent.click(confirmBtn);
        await tick();
        expect(resolve).toHaveBeenCalledWith(true);
        expect(document.querySelector(".confirm-dialog-root")).toBeNull();
    });

    it("calls resolve(false) when Cancel clicked", async () => {
        const resolve = vi.fn();
        render(ConfirmDialog);
        confirmHandler()({ message: "Sure?", resolve });
        await tick();
        await fireEvent.click(document.querySelector("[data-confirm-cancel]"));
        await tick();
        expect(resolve).toHaveBeenCalledWith(false);
    });

    it("resolves the previous waiter with false when a second confirm opens", async () => {
        const first = vi.fn();
        const second = vi.fn();
        render(ConfirmDialog);
        const showFn = confirmHandler();
        showFn({ message: "First?", resolve: first });
        await tick();
        showFn({ message: "Second?", resolve: second });
        await tick();
        expect(first).toHaveBeenCalledWith(false);
        expect(document.body.textContent).toContain("Second?");
        expect(second).not.toHaveBeenCalled();
    });
});

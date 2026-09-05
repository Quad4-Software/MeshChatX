import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { tick } from "svelte";
import PromptDialog from "../../meshchatx/src/frontend/ui/svelte/PromptDialog.svelte";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

function promptHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "prompt")?.[1];
}

function confirmHandler() {
    return GlobalEmitter.on.mock.calls.find((c) => c[0] === "confirm")?.[1];
}

describe("PromptDialog UI", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.on).mockClear();
        vi.mocked(GlobalEmitter.off).mockClear();
    });

    afterEach(() => {
        cleanup();
        document.body.innerHTML = "";
    });

    it("registers prompt listener on mount", () => {
        const { unmount } = render(PromptDialog);
        expect(GlobalEmitter.on).toHaveBeenCalledWith("prompt", expect.any(Function));
        expect(GlobalEmitter.on).toHaveBeenCalledWith("confirm", expect.any(Function));
        unmount();
    });

    it("shows dialog with default value when show is called", async () => {
        render(PromptDialog);
        const showFn = promptHandler();
        expect(showFn).toBeDefined();
        showFn({ message: "Version name?", defaultValue: "upload-1", resolve: vi.fn() });
        await tick();
        expect(screen.getByText("Version name?")).toBeTruthy();
        expect(screen.getByRole("textbox").value).toBe("upload-1");
    });

    it("calls resolve with input value when OK clicked", async () => {
        const resolve = vi.fn();
        render(PromptDialog);
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await tick();
        const input = screen.getByRole("textbox");
        await fireEvent.input(input, { target: { value: "reticulum-manual" } });
        await fireEvent.click(screen.getByRole("button", { name: "OK" }));
        expect(resolve).toHaveBeenCalledWith("reticulum-manual");
        expect(screen.queryByRole("dialog")).toBeNull();
    });

    it("calls resolve(null) when Cancel clicked", async () => {
        const resolve = vi.fn();
        render(PromptDialog);
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await tick();
        await fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
        expect(resolve).toHaveBeenCalledWith(null);
        expect(screen.queryByRole("dialog")).toBeNull();
    });

    it("resolves the previous waiter with null when a second prompt opens", async () => {
        const first = vi.fn();
        const second = vi.fn();
        render(PromptDialog);
        const showFn = promptHandler();
        showFn({ message: "First?", defaultValue: "a", resolve: first });
        await tick();
        showFn({ message: "Second?", defaultValue: "b", resolve: second });
        await tick();
        expect(first).toHaveBeenCalledWith(null);
        expect(screen.getByText("Second?")).toBeTruthy();
        expect(second).not.toHaveBeenCalled();
    });

    it("cancels on window Escape", async () => {
        const resolve = vi.fn();
        render(PromptDialog);
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await tick();
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        expect(resolve).toHaveBeenCalledWith(null);
        expect(screen.queryByRole("dialog")).toBeNull();
    });

    it("does not submit while an IME composition Enter is in progress", async () => {
        const resolve = vi.fn();
        render(PromptDialog);
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await tick();
        const input = screen.getByRole("textbox");
        await fireEvent.keyDown(input, { key: "Enter", isComposing: true });
        expect(resolve).not.toHaveBeenCalled();
        expect(screen.getByRole("dialog")).toBeTruthy();
    });

    it("cancels the pending waiter when a confirm opens", async () => {
        const resolve = vi.fn();
        render(PromptDialog);
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await tick();
        confirmHandler()();
        expect(resolve).toHaveBeenCalledWith(null);
        expect(screen.queryByRole("dialog")).toBeNull();
    });

    it("resolves null when unmounted while open", async () => {
        const resolve = vi.fn();
        const { unmount } = render(PromptDialog);
        promptHandler()({ message: "Name?", defaultValue: "a", resolve });
        await tick();
        unmount();
        expect(resolve).toHaveBeenCalledWith(null);
    });
});

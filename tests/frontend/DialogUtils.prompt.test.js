import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils.js";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

describe("DialogUtils.confirm", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.emit).mockClear();
        delete window.electron;
    });

    it("uses the in-app confirm dialog even when electron is present", async () => {
        window.electron = {
            confirm: vi.fn().mockResolvedValue(true),
        };
        const pending = DialogUtils.confirm("Delete this?");
        expect(window.electron.confirm).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "confirm",
            expect.objectContaining({
                message: "Delete this?",
                resolve: expect.any(Function),
            })
        );
        const payload = GlobalEmitter.emit.mock.calls.find((c) => c[0] === "confirm")[1];
        payload.resolve(false);
        await expect(pending).resolves.toBe(false);
    });

    it("passes an optional title to the in-app dialog", async () => {
        const pending = DialogUtils.confirm("All messages will be lost.", "Delete conversations");
        const payload = GlobalEmitter.emit.mock.calls.find((c) => c[0] === "confirm")[1];
        expect(payload.title).toBe("Delete conversations");
        payload.resolve(true);
        await expect(pending).resolves.toBe(true);
    });

    it("aliases confirmCustom to the same in-app dialog", async () => {
        const pending = DialogUtils.confirmCustom("Leave room?");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "confirm",
            expect.objectContaining({
                message: "Leave room?",
                resolve: expect.any(Function),
            })
        );
        const payload = GlobalEmitter.emit.mock.calls.find((c) => c[0] === "confirm")[1];
        payload.resolve(true);
        await expect(pending).resolves.toBe(true);
    });
});

describe("DialogUtils.prompt", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.emit).mockClear();
        delete window.electron;
    });

    it("uses in-app prompt dialog when electron is unavailable", async () => {
        const pending = DialogUtils.prompt("Enter version", "upload-1");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "prompt",
            expect.objectContaining({
                message: "Enter version",
                defaultValue: "upload-1",
                resolve: expect.any(Function),
            })
        );
        const payload = GlobalEmitter.emit.mock.calls.find((c) => c[0] === "prompt")[1];
        payload.resolve("named");
        await expect(pending).resolves.toBe("named");
    });

    it("falls back to in-app dialog when electron.prompt throws", async () => {
        window.electron = {
            prompt: vi.fn().mockRejectedValue(new Error("prompt() is not supported.")),
        };
        const pending = DialogUtils.prompt("Enter version", "fallback");
        await Promise.resolve();
        expect(window.electron.prompt).toHaveBeenCalledWith("Enter version", "fallback");
        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "prompt",
            expect.objectContaining({
                message: "Enter version",
                defaultValue: "fallback",
            })
        );
        const payload = GlobalEmitter.emit.mock.calls.find((c) => c[0] === "prompt")[1];
        payload.resolve(null);
        await expect(pending).resolves.toBeNull();
    });

    it("uses in-app password prompt and skips electron.prompt for password type", async () => {
        window.electron = {
            prompt: vi.fn().mockResolvedValue("should-not-use"),
        };
        const pending = DialogUtils.prompt("Room key", "", { inputType: "password" });
        expect(window.electron.prompt).not.toHaveBeenCalled();
        expect(GlobalEmitter.emit).toHaveBeenCalledWith(
            "prompt",
            expect.objectContaining({
                message: "Room key",
                defaultValue: "",
                inputType: "password",
                resolve: expect.any(Function),
            })
        );
        const payload = GlobalEmitter.emit.mock.calls.find((c) => c[0] === "prompt")[1];
        payload.resolve("secret");
        await expect(pending).resolves.toBe("secret");
    });
});

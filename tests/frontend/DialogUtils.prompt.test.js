import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../meshchatx/src/frontend/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn(), listenerCount: vi.fn(() => 1) },
}));

import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils.js";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

describe("DialogUtils.confirm", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.emit).mockClear();
        vi.mocked(GlobalEmitter.listenerCount).mockClear();
        vi.mocked(GlobalEmitter.listenerCount).mockReturnValue(1);
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

    it("resolves false when no confirm host is mounted", async () => {
        vi.mocked(GlobalEmitter.listenerCount).mockReturnValue(0);
        await expect(DialogUtils.confirm("Delete this?")).resolves.toBe(false);
        expect(GlobalEmitter.emit).not.toHaveBeenCalled();
    });
});

describe("DialogUtils.prompt", () => {
    beforeEach(() => {
        vi.mocked(GlobalEmitter.emit).mockClear();
        vi.mocked(GlobalEmitter.listenerCount).mockClear();
        vi.mocked(GlobalEmitter.listenerCount).mockReturnValue(1);
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

    it("uses the in-app prompt even when electron.prompt exists", async () => {
        window.electron = {
            prompt: vi.fn().mockResolvedValue("should-not-use"),
        };
        const pending = DialogUtils.prompt("Enter version", "fallback");
        expect(window.electron.prompt).not.toHaveBeenCalled();
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

    it("resolves null when no prompt host is mounted", async () => {
        vi.mocked(GlobalEmitter.listenerCount).mockReturnValue(0);
        await expect(DialogUtils.prompt("Enter version")).resolves.toBeNull();
        expect(GlobalEmitter.emit).not.toHaveBeenCalled();
    });
});

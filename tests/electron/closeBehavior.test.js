import { createRequire } from "module";
import path from "path";
import fs from "fs";
import os from "os";
import { afterEach, describe, expect, it } from "vitest";

const require = createRequire(import.meta.url);
const {
    defaultCloseSettings,
    normalizeCloseSettings,
    resolveCloseAction,
    loadCloseSettings,
    saveCloseSettings,
    rememberedCloseSettings,
    createCloseRequestGuard,
} = require("../../electron/closeBehavior.js");

describe("electron/closeBehavior", () => {
    const tempDirs = [];

    afterEach(() => {
        for (const dir of tempDirs.splice(0)) {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    });

    it("defaults to ask with tray enabled", () => {
        expect(defaultCloseSettings()).toEqual({
            closeBehavior: "ask",
            trayEnabled: true,
        });
    });

    it("normalizes invalid values", () => {
        expect(
            normalizeCloseSettings({
                closeBehavior: "nope",
                trayEnabled: "yes",
            })
        ).toEqual(defaultCloseSettings());
    });

    it("resolveCloseAction maps background to minimize when tray is off", () => {
        expect(resolveCloseAction({ closeBehavior: "ask", trayEnabled: true })).toBe("ask");
        expect(resolveCloseAction({ closeBehavior: "quit", trayEnabled: true })).toBe("quit");
        expect(resolveCloseAction({ closeBehavior: "background", trayEnabled: true })).toBe("background");
        expect(resolveCloseAction({ closeBehavior: "background", trayEnabled: false })).toBe("minimize");
    });

    it("persists and reloads settings from storage dir", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-close-"));
        tempDirs.push(dir);
        const saved = saveCloseSettings(dir, { closeBehavior: "quit", trayEnabled: false });
        expect(saved).toEqual({ closeBehavior: "quit", trayEnabled: false });
        expect(loadCloseSettings(dir)).toEqual({ closeBehavior: "quit", trayEnabled: false });
        expect(fs.existsSync(path.join(dir, "desktop-close-settings.json"))).toBe(true);
    });

    it("rememberedCloseSettings maps minimize/background to background", () => {
        expect(rememberedCloseSettings("quit", true)).toEqual({ closeBehavior: "quit" });
        expect(rememberedCloseSettings("background", true)).toEqual({ closeBehavior: "background" });
        expect(rememberedCloseSettings("minimize", true)).toEqual({ closeBehavior: "background" });
        expect(rememberedCloseSettings("quit", false)).toBeNull();
    });

    it("createCloseRequestGuard blocks re-entrant close handling", () => {
        const guard = createCloseRequestGuard();
        expect(guard.tryEnter()).toBe(true);
        expect(guard.tryEnter()).toBe(false);
        guard.leave();
        expect(guard.tryEnter()).toBe(true);
        guard.leave();
    });
});

// SPDX-License-Identifier: 0BSD

import { createRequire } from "module";
import fs from "fs";
import os from "os";
import path from "path";
import { afterEach, describe, expect, it } from "vitest";

const require = createRequire(import.meta.url);
const {
    loadUiThemePreference,
    saveUiThemePreference,
    resolveEffectiveUiTheme,
    normalizeUiThemePreference,
    shellBackgroundColor,
} = require("../../electron/uiTheme.js");

describe("electron/uiTheme", () => {
    const tempDirs = [];

    afterEach(() => {
        for (const dir of tempDirs.splice(0)) {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    });

    function tempDir() {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-ui-theme-"));
        tempDirs.push(dir);
        return dir;
    }

    it("defaults to system when missing", () => {
        expect(loadUiThemePreference(tempDir())).toBe("system");
    });

    it("persists dark preference for shell pages", () => {
        const dir = tempDir();
        expect(saveUiThemePreference(dir, "dark")).toBe("dark");
        expect(loadUiThemePreference(dir)).toBe("dark");
        expect(resolveEffectiveUiTheme("dark", false)).toBe("dark");
        expect(shellBackgroundColor("dark")).toBe("#09090b");
    });

    it("normalizes invalid values to system", () => {
        expect(normalizeUiThemePreference("neon")).toBe("system");
        expect(resolveEffectiveUiTheme("system", true)).toBe("dark");
        expect(resolveEffectiveUiTheme("system", false)).toBe("light");
    });
});

"use strict";

import fs from "fs";
import os from "os";
import path from "path";
import { describe, expect, it } from "vitest";
import { isAllowedShellPath } from "../../electron/shellPathGuard.js";

function fakeApp() {
    const home = os.homedir();
    return {
        getPath(name) {
            if (name === "userData") {
                return path.join(home, ".meshchatx-test-userdata");
            }
            if (name === "temp") {
                return os.tmpdir();
            }
            if (name === "downloads") {
                return path.join(home, "Downloads");
            }
            if (name === "documents") {
                return path.join(home, "Documents");
            }
            throw new Error(`unexpected getPath ${name}`);
        },
    };
}

describe("shellPathGuard", () => {
    const home = os.homedir();
    const storage = path.join(home, ".reticulum-meshchat");
    const reticulum = path.join(home, ".reticulum");
    const ctx = {
        app: fakeApp(),
        getDefaultStorageDir: () => storage,
        getDefaultReticulumConfigDir: () => reticulum,
        getUserProvidedArguments: () => [],
    };

    it("allows paths under default storage", () => {
        const p = path.join(storage, "rncp_received", "file.bin");
        expect(isAllowedShellPath(p, ctx)).toBe(true);
    });

    it("denies paths outside allowed roots", () => {
        const p = process.platform === "win32" ? "C:\\Windows\\System32\\drivers\\etc\\hosts" : "/etc/passwd";
        expect(isAllowedShellPath(p, ctx)).toBe(false);
    });

    it("allows temp directory files", () => {
        const p = path.join(os.tmpdir(), `meshchatx-shell-guard-${process.pid}.txt`);
        fs.writeFileSync(p, "x");
        try {
            expect(isAllowedShellPath(p, ctx)).toBe(true);
        } finally {
            fs.unlinkSync(p);
        }
    });
});

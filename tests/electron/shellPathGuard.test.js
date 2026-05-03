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
    const storage = path.join(home, ".reticulum-meshchatx");
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

    it("allows paired legacy storage directory", () => {
        const legacy = path.join(home, ".reticulum-meshchat");
        const p = path.join(legacy, "identities", "abc", "database.db");
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

    it("fuzz: paths under default storage stay allowed", () => {
        for (let i = 0; i < 200; i++) {
            const seg = Array.from({ length: 10 }, () => String.fromCharCode(Math.floor(Math.random() * 94) + 33)).join(
                ""
            );
            const p = path.join(storage, "fuzz-shell", seg);
            expect(() => isAllowedShellPath(p, ctx)).not.toThrow();
            expect(isAllowedShellPath(p, ctx)).toBe(true);
        }
    });

    it("fuzz: random absolute-looking paths return boolean without throw", () => {
        for (let i = 0; i < 200; i++) {
            let s = process.platform === "win32" ? "C:\\" : "/";
            const n = Math.floor(Math.random() * 24) + 4;
            for (let j = 0; j < n; j++) {
                s += String.fromCharCode(Math.floor(Math.random() * 96) + 32);
            }
            expect(() => isAllowedShellPath(s, ctx)).not.toThrow();
            expect(typeof isAllowedShellPath(s, ctx)).toBe("boolean");
        }
    });
});

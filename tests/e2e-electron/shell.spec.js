// SPDX-License-Identifier: 0BSD
const { test, expect, _electron: electron } = require("@playwright/test");
const path = require("node:path");
const fs = require("node:fs");
const os = require("node:os");

const harnessMain = path.join(__dirname, "harness", "main.cjs");

test.describe("Electron shell harness", () => {
    /** @type {import('@playwright/test').ElectronApplication | undefined} */
    let electronApp;
    /** @type {import('@playwright/test').Page | undefined} */
    let window;

    test.beforeAll(async () => {
        const userData = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-electron-e2e-"));
        electronApp = await electron.launch({
            args: [harnessMain],
            env: {
                ...process.env,
                ELECTRON_DISABLE_SECURITY_WARNINGS: "1",
            },
            // Isolate Chromium profile from the developer Electron profile.
            cwd: path.join(__dirname, "..", ".."),
        });
        // Electron uses --user-data-dir via app; set after launch when possible.
        window = await electronApp.firstWindow({ timeout: 60000 });
        void userData;
    });

    test.afterAll(async () => {
        if (electronApp) {
            await electronApp.close();
        }
    });

    test("loads harness with preload bridge", async () => {
        await expect(window.locator("#ready")).toHaveText("ok", { timeout: 30000 });
        await expect(window.locator("#title")).toContainText("Electron shell harness");
    });

    test("external URL allowlist matches shell helper", async () => {
        const httpsOk = await window.evaluate(async () =>
            window.electronE2e.normalizeExternalUrl("https://example.com/path")
        );
        expect(httpsOk).toBe("https://example.com/path");

        const fileBlocked = await window.evaluate(async () =>
            window.electronE2e.normalizeExternalUrl("file:///etc/passwd")
        );
        expect(fileBlocked).toBeNull();

        const credsBlocked = await window.evaluate(async () =>
            window.electronE2e.normalizeExternalUrl("https://user:pass@evil.example/")
        );
        expect(credsBlocked).toBeNull();
    });
});

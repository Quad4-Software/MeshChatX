// SPDX-License-Identifier: 0BSD

const { test, expect } = require("@playwright/test");
const { E2E_BACKEND_ORIGIN, prepareE2eSession } = require("./helpers");

/**
 * Browser permission / chooser regressions for Calls mic and RNode Bluetooth.
 * Real OS prompts cannot be driven reliably in CI, so these tests install
 * controlled navigator.mediaDevices / navigator.bluetooth shims and assert the
 * product code asks the browser the right way.
 */

async function installMicProbe(page, { secure = true } = {}) {
    await page.addInitScript((isSecure) => {
        Object.defineProperty(window, "isSecureContext", {
            configurable: true,
            get() {
                return isSecure;
            },
        });
        window.__meshchatxGumCalls = [];
        const stop = () => {};
        const fakeStream = {
            getTracks() {
                return [{ stop, kind: "audio", stopTrack: stop }];
            },
        };
        const getUserMedia = async (constraints) => {
            window.__meshchatxGumCalls.push(constraints);
            return fakeStream;
        };
        const enumerateDevices = async () => [
            { kind: "audioinput", deviceId: "mic-1", label: "Fake Mic", groupId: "g1" },
            { kind: "audiooutput", deviceId: "spk-1", label: "Fake Speaker", groupId: "g1" },
        ];
        Object.defineProperty(navigator, "mediaDevices", {
            configurable: true,
            value: { getUserMedia, enumerateDevices },
        });
    }, secure);
}

async function enableWebAudioBridge(page) {
    await page.goto("/#/call");
    await expect(page.getByRole("button", { name: "Phone", exact: true })).toBeVisible({ timeout: 30000 });
    const refresh = page.getByRole("button", { name: "Refresh Devices", exact: true });
    if (
        (await refresh.count()) === 0 ||
        !(await refresh
            .first()
            .isVisible()
            .catch(() => false))
    ) {
        const label = page.locator('label[for="web-audio-toggle"]');
        await expect(label).toBeVisible({ timeout: 20000 });
        const input = page.locator("#web-audio-toggle");
        const checked = await input.isChecked().catch(() => false);
        const disabled = await input.isDisabled().catch(() => false);
        if (!checked && !disabled) {
            await label.click();
        }
    }
    await expect(refresh).toBeVisible({ timeout: 15000 });
}

async function dismissViteOverlay(page) {
    await page.evaluate(() => {
        document.querySelectorAll("vite-error-overlay").forEach((el) => el.remove());
    });
}

test.describe("Browser mic permission prompt path", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("Refresh Devices prompts getUserMedia with bare audio first", async ({ page }) => {
        await installMicProbe(page, { secure: true });
        await enableWebAudioBridge(page);
        await page.evaluate(() => {
            window.__meshchatxGumCalls = [];
        });
        await page.getByRole("button", { name: "Refresh Devices", exact: true }).click();
        await expect.poll(async () => page.evaluate(() => window.__meshchatxGumCalls.length)).toBeGreaterThan(0);
        const calls = await page.evaluate(() => window.__meshchatxGumCalls);
        expect(calls[0]).toEqual({ audio: true });
    });

    test("Refresh Devices refuses insecure contexts without calling getUserMedia", async ({ page }) => {
        await installMicProbe(page, { secure: false });
        await enableWebAudioBridge(page);
        await page.evaluate(() => {
            window.__meshchatxGumCalls = [];
        });
        await page.getByRole("button", { name: "Refresh Devices", exact: true }).click();
        await expect(page.getByText(/Microphone access needs HTTPS|secure URL/i).first()).toBeVisible({
            timeout: 10000,
        });
        const calls = await page.evaluate(() => window.__meshchatxGumCalls);
        expect(calls).toEqual([]);
    });
});

test.describe("RNode flasher Web Bluetooth chooser path", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("Brave without Web Bluetooth shows Try Bluetooth and flag guidance", async ({ page }) => {
        await page.addInitScript(() => {
            Object.defineProperty(window, "isSecureContext", {
                configurable: true,
                get() {
                    return true;
                },
            });
            Object.defineProperty(navigator, "userAgent", {
                configurable: true,
                get() {
                    return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Brave/1.70 Chrome/120.0.0.0 Safari/537.36";
                },
            });
            Object.defineProperty(navigator, "brave", {
                configurable: true,
                value: { isBrave: async () => true },
            });
            try {
                delete navigator.bluetooth;
            } catch {
                Object.defineProperty(navigator, "bluetooth", {
                    configurable: true,
                    value: undefined,
                });
            }
        });
        await page.goto("/#/tools/rnode-flasher");
        await expect(page.getByText("Bluetooth is unavailable").first()).toBeVisible({ timeout: 30000 });
        await expect(page.getByText(/brave:\/\/flags\/#brave-web-bluetooth-api/i).first()).toBeVisible();
        await dismissViteOverlay(page);
        const tryBtn = page.getByRole("button", { name: /Try Bluetooth/i });
        const recheckBtn = page.getByRole("button", { name: /Recheck Bluetooth/i });
        await expect(tryBtn).toBeVisible();
        await expect(recheckBtn).toBeVisible();
        await tryBtn.click({ force: true });
        await expect(page.getByText(/Brave disables Web Bluetooth|brave:\/\/flags/i).first()).toBeVisible({
            timeout: 10000,
        });
    });

    test("Try Bluetooth calls requestDevice when Web Bluetooth becomes available", async ({ page }) => {
        await page.addInitScript(() => {
            Object.defineProperty(window, "isSecureContext", {
                configurable: true,
                get() {
                    return true;
                },
            });
            Object.defineProperty(navigator, "userAgent", {
                configurable: true,
                get() {
                    return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Brave/1.70 Chrome/120.0.0.0 Safari/537.36";
                },
            });
            Object.defineProperty(navigator, "brave", {
                configurable: true,
                value: { isBrave: async () => true },
            });
            try {
                delete navigator.bluetooth;
            } catch {
                Object.defineProperty(navigator, "bluetooth", {
                    configurable: true,
                    value: undefined,
                });
            }
            window.__meshchatxBtRequests = 0;
            window.__meshchatxInstallBluetooth = () => {
                Object.defineProperty(navigator, "bluetooth", {
                    configurable: true,
                    value: {
                        requestDevice: async () => {
                            window.__meshchatxBtRequests += 1;
                            return {
                                gatt: {
                                    connected: false,
                                    disconnect() {},
                                },
                            };
                        },
                        getAvailability: async () => true,
                    },
                });
            };
        });
        await page.goto("/#/tools/rnode-flasher");
        const tryBtn = page.getByRole("button", { name: /Try Bluetooth/i });
        await expect(tryBtn).toBeVisible({ timeout: 30000 });
        await dismissViteOverlay(page);
        await page.evaluate(() => window.__meshchatxInstallBluetooth());
        await tryBtn.click({ force: true });
        await expect.poll(async () => page.evaluate(() => window.__meshchatxBtRequests)).toBeGreaterThan(0);
        await expect(
            page.getByText(/Bluetooth device chooser worked|Bluetooth transport is ready/i).first()
        ).toBeVisible({
            timeout: 10000,
        });
    });

    test("Permissions-Policy from backend allows bluetooth for flasher origin", async ({ request }) => {
        const index = await request.get(`${E2E_BACKEND_ORIGIN}/`);
        expect(index.ok()).toBeTruthy();
        const policy = index.headers()["permissions-policy"] || "";
        expect(policy).toContain("bluetooth=(self)");
        expect(policy).toContain("microphone=(self)");
        expect(policy).toContain("autoplay=(self)");
        expect(policy).toContain("speaker-selection=(self)");
        expect(policy).toContain("serial=(self)");
        expect(policy).toContain("usb=(self)");
        expect(index.headers()["feature-policy"] || "").toBe("");
    });
});

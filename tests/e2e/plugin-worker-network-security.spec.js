// SPDX-License-Identifier: 0BSD
const { test, expect } = require("@playwright/test");

test("plugin workers cannot fetch same-origin API data directly", async ({ page }) => {
    let probeRequests = 0;
    await page.route("**/api/v1/**", async (route) => {
        if (new URL(route.request().url()).pathname === "/api/v1/plugins/csp-probe") {
            probeRequests += 1;
        }
        await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
    });

    await page.goto("/");
    const outcome = await page.evaluate(
        () =>
            new Promise((resolve, reject) => {
                const worker = new Worker("/js/plugins/pluginWorker.js", { type: "module" });
                const timeout = setTimeout(() => {
                    worker.terminate();
                    reject(new Error("plugin worker did not report fetch result"));
                }, 5000);
                worker.onerror = (event) => {
                    clearTimeout(timeout);
                    worker.terminate();
                    reject(new Error(event.message || "plugin worker failed"));
                };
                worker.onmessage = (event) => {
                    if (event.data?.type !== "toast") {
                        return;
                    }
                    clearTimeout(timeout);
                    worker.terminate();
                    resolve(event.data.message);
                };
                worker.postMessage({
                    type: "init",
                    pluginId: "csp-probe",
                    labels: {},
                    permissions: {},
                    grantedPermissions: ["network:fetch"],
                    source: `export async function activate(api) {
                        if (!api.hasPermission("network:fetch")) {
                            api.toast("grant-missing");
                            return;
                        }
                        try {
                            await fetch("/api/v1/plugins/csp-probe");
                            api.toast("fetch-allowed");
                        } catch {
                            api.toast("fetch-blocked");
                        }
                    }`,
                });
            })
    );

    expect(outcome).toBe("fetch-blocked");
    expect(probeRequests).toBe(0);
});

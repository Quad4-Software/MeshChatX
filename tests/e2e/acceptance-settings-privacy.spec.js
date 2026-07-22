// SPDX-License-Identifier: 0BSD
/**
 * Acceptance: Settings privacy surface is reachable and shows expected controls.
 */
const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

test.describe("Acceptance: Settings privacy", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("privacy tab shows data controls and privacy mode", async ({ page }) => {
        await page.goto("/#/settings");
        await expect(page).toHaveURL(/#\/settings/);
        await expect(page.getByText("Profile", { exact: true }).first()).toBeVisible({
            timeout: 30000,
        });

        const privacyTab = page.getByRole("button", { name: /^Privacy$/i }).first();
        await expect(privacyTab).toBeVisible({ timeout: 20000 });
        await privacyTab.click();

        await expect(page.getByText("Data & device", { exact: true }).first()).toBeVisible({
            timeout: 20000,
        });
        await expect(page.getByText("Privacy mode (block external HTTP/HTTPS)", { exact: true }).first()).toBeVisible({
            timeout: 20000,
        });
        await expect(page.getByText("Warn when multiple sessions are connected", { exact: true }).first()).toBeVisible({
            timeout: 20000,
        });
    });
});

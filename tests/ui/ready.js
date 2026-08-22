const { expect } = require("@playwright/test");

/**
 * Wait until the static boot splash is removed after /api/v1/status is ready.
 * @param {import('@playwright/test').Page} page
 */
async function waitForBootReady(page) {
    const splash = page.locator("#meshchatx-boot-splash");
    await expect(splash).toHaveCount(0, { timeout: 120000 });
}

/**
 * Wait until a catalog page has painted its ready signal.
 * @param {import('@playwright/test').Page} page
 * @param {import('./pages').UiPage} entry
 */
async function waitForPageReady(page, entry) {
    const timeout = 60000;
    const kind = entry.readyKind || "text";

    if (kind === "heading") {
        await expect(page.getByRole("heading", { name: entry.ready, exact: true })).toBeVisible({
            timeout,
        });
        return;
    }
    if (kind === "placeholder") {
        await expect(page.getByPlaceholder(entry.ready)).toBeVisible({ timeout });
        return;
    }
    if (kind === "role") {
        await expect(page.getByRole(entry.ready, { name: entry.readyName })).toBeVisible({
            timeout,
        });
        return;
    }
    await expect(page.getByText(entry.ready, { exact: true }).first()).toBeVisible({ timeout });
}

/**
 * @param {import('@playwright/test').Page} page
 * @param {import('./pages').UiPage} entry
 * @param {string} baseURL
 */
async function gotoUiPage(page, entry, baseURL) {
    const url = `${baseURL.replace(/\/$/, "")}/#${entry.path}`;
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(new RegExp(`#${entry.path.replace(/\//g, "\\/")}`));
    await waitForBootReady(page);
    await waitForPageReady(page, entry);
}

module.exports = {
    waitForBootReady,
    waitForPageReady,
    gotoUiPage,
};

const { expect } = require("@playwright/test");

const E2E_BACKEND_PORT = process.env.E2E_BACKEND_PORT || "8000";
const E2E_BACKEND_ORIGIN = `http://127.0.0.1:${E2E_BACKEND_PORT}`;

const PALETTE_PLACEHOLDER = "Search commands, navigate, or find peers...";

/**
 * Marks tutorial and changelog as seen on the E2E backend so first-load modals
 * (v-overlay scrim) do not block pointer clicks on the shell.
 */
async function prepareE2eSession(request) {
    const tutorial = await request.post(`${E2E_BACKEND_ORIGIN}/api/v1/app/tutorial/seen`);
    expect(tutorial.ok()).toBeTruthy();
    const changelog = await request.post(`${E2E_BACKEND_ORIGIN}/api/v1/app/changelog/seen`, {
        data: { version: "999.999.999" },
    });
    expect(changelog.ok()).toBeTruthy();
}

async function openCommandPalette(page) {
    await page.keyboard.press("Control+K");
    let input = page.getByPlaceholder(PALETTE_PLACEHOLDER);
    if ((await input.count()) === 0) {
        await page.evaluate(() => {
            window.dispatchEvent(
                new KeyboardEvent("keydown", {
                    key: "k",
                    code: "KeyK",
                    ctrlKey: true,
                    bubbles: true,
                    cancelable: true,
                }),
            );
        });
        input = page.getByPlaceholder(PALETTE_PLACEHOLDER);
    }
    await expect(input).toBeVisible({ timeout: 15000 });
}

module.exports = { E2E_BACKEND_ORIGIN, PALETTE_PLACEHOLDER, openCommandPalette, prepareE2eSession };

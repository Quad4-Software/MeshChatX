const { test, expect } = require("@playwright/test");
const { prepareE2eSession, dismissMapOnboardingTooltip } = require("./helpers");

test.describe("Keyboard shortcuts (global)", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("Alt+2 opens Nomad Network", async ({ page }) => {
        await page.goto("/#/messages");
        await expect(page).toHaveURL(/#\/messages/);
        await page.keyboard.press("Alt+2");
        await expect(page).toHaveURL(/#\/nomadnetwork/, { timeout: 15000 });
    });

    test("Alt+3 opens Map", async ({ page }) => {
        await page.goto("/#/messages");
        await page.evaluate(() => {
            localStorage.setItem("map_onboarding_seen", "true");
        });
        await page.keyboard.press("Alt+3");
        await expect(page).toHaveURL(/#\/map/, { timeout: 15000 });
        await dismissMapOnboardingTooltip(page);
    });

    test("Alt+4 opens Archives", async ({ page }) => {
        await page.goto("/#/messages");
        await page.keyboard.press("Alt+4");
        await expect(page).toHaveURL(/#\/archives/, { timeout: 15000 });
    });

    test("Alt+5 opens Calls", async ({ page }) => {
        await page.goto("/#/messages");
        await page.keyboard.press("Alt+5");
        await expect(page).toHaveURL(/#\/call/, { timeout: 15000 });
    });

    test("Alt+P opens Paper Message tool", async ({ page }) => {
        await page.goto("/#/messages");
        await page.keyboard.press("Alt+p");
        await expect(page).toHaveURL(/#\/tools\/paper-message/, { timeout: 15000 });
        await expect(page.getByRole("heading", { name: "Paper Message Generator", exact: true })).toBeVisible({
            timeout: 20000,
        });
    });

    test("Alt+N goes to Messages (compose flow)", async ({ page }) => {
        await page.goto("/#/settings");
        await expect(page).toHaveURL(/#\/settings/);
        await page.keyboard.press("Alt+n");
        await expect(page).toHaveURL(/#\/messages/, { timeout: 15000 });
    });

    test("Ctrl+B toggles sidebar collapsed width", async ({ page }) => {
        await page.goto("/#/messages");
        const classBefore = await page.evaluate(() => {
            const ul = document.querySelector("ul.py-3");
            const el = ul && ul.closest(".fixed");
            return el ? el.className : "";
        });
        expect(classBefore).toMatch(/w-80|md:max-lg:w-64|lg:w-80/);

        await page.keyboard.press("Control+b");
        const classAfterCollapse = await page.evaluate(() => {
            const ul = document.querySelector("ul.py-3");
            const el = ul && ul.closest(".fixed");
            return el ? el.className : "";
        });
        expect(classAfterCollapse).toContain("w-16");

        await page.keyboard.press("Control+b");
        const classAfterExpand = await page.evaluate(() => {
            const ul = document.querySelector("ul.py-3");
            const el = ul && ul.closest(".fixed");
            return el ? el.className : "";
        });
        expect(classAfterExpand).toMatch(/w-80|md:max-lg:w-64|lg:w-80/);
    });
});

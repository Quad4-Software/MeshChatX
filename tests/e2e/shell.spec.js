const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

function topChrome(page) {
    return page.locator("div.sticky.top-0.z-\\[100\\]").first();
}

test.describe("Shell: sidebar, theme, notifications, call, search", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("desktop sidebar collapse toggle changes width", async ({ page }) => {
        await page.goto("/#/messages");
        const sidebar = page.locator("div.fixed.inset-y-0.left-0").filter({ has: page.locator("ul.py-3") });
        const toggleButton = sidebar.locator("div.hidden.sm\\:flex button").first();
        await expect(sidebar).toHaveClass(/w-80/);
        await toggleButton.click();
        await expect(sidebar).toHaveClass(/w-16/);
        await toggleButton.click();
        await expect(sidebar).toHaveClass(/w-80/);
    });

    test("header theme button toggles dark mode on root shell", async ({ page }) => {
        await page.goto("/#/messages");
        const shell = page.locator("#app > div.h-screen.w-full.flex.flex-col").first();
        await expect(shell).toBeVisible({ timeout: 30000 });
        const themeBtn = page.getByTitle(/Switch to (light|dark) mode/);
        await expect(themeBtn).toBeVisible({ timeout: 20000 });
        const initialDark = await shell.evaluate((el) => el.classList.contains("dark"));
        await themeBtn.click();
        await expect.poll(async () => shell.evaluate((el) => el.classList.contains("dark"))).not.toBe(initialDark);
        await themeBtn.click();
        await expect.poll(async () => shell.evaluate((el) => el.classList.contains("dark"))).toBe(initialDark);
    });

    test("notification bell opens panel and closes from header", async ({ page }) => {
        await page.goto("/#/messages");
        await topChrome(page)
            .locator("button")
            .filter({ has: page.locator('svg[aria-label="bell"]') })
            .click();
        await expect(page.getByRole("heading", { name: "Notifications", exact: true })).toBeVisible({
            timeout: 15000,
        });
        await expect(page.getByText("No new notifications", { exact: true })).toBeVisible({ timeout: 10000 });
        const panel = page.locator("div.fixed").filter({ hasText: "Notifications" }).first();
        await panel.locator('svg[aria-label="close"]').click();
        await expect(page.getByRole("heading", { name: "Notifications", exact: true })).toBeHidden({
            timeout: 5000,
        });
    });

    test("call route shows Phone tab", async ({ page }) => {
        await page.goto("/#/call");
        await expect(page).toHaveURL(/#\/call/);
        await expect(page.getByRole("button", { name: "Phone", exact: true })).toBeVisible({ timeout: 20000 });
    });

    test("messages Announces tab search input accepts text", async ({ page }) => {
        await page.goto("/#/messages");
        await page.locator("div.-mb-px.flex").getByText("Announces", { exact: true }).click();
        const input = page.getByPlaceholder(/Search \d+ recent announces/);
        await expect(input).toBeVisible({ timeout: 15000 });
        await input.fill("e2e-filter");
        await expect(input).toHaveValue("e2e-filter");
    });

    test("NomadNet favourites and announces search inputs accept text", async ({ page }) => {
        await page.goto("/#/nomadnetwork");
        const favSearch = page.getByPlaceholder(/Search \d+ favourites/);
        await expect(favSearch).toBeVisible({ timeout: 20000 });
        await favSearch.fill("fav-q");
        await expect(favSearch).toHaveValue("fav-q");

        await page.locator("button.sidebar-tab").filter({ hasText: "Announces" }).click();
        const nodeSearch = page.getByPlaceholder(/Search \d+ recent announces/);
        await expect(nodeSearch).toBeVisible({ timeout: 15000 });
        await nodeSearch.fill("node-q");
        await expect(nodeSearch).toHaveValue("node-q");
    });
});

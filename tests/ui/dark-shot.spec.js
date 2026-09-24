const { test } = require("@playwright/test");
const { seedUiDemoData } = require("./seed");
const { gotoUiPage, waitForBootReady, waitForPageReady } = require("./ready");
const { resolveShots, VIEWPORTS } = require("./screenshots");
const { e2ePost, E2E_BACKEND_ORIGIN, prepareE2eSession } = require("../e2e/helpers");

const entries = resolveShots({ ids: ["conversation"] });

test.describe("dark shots", () => {
    test.beforeAll(async ({ request }) => {
        await seedUiDemoData(request);
        const csrf = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/auth/csrf`);
        const token = (await csrf.json()).csrf_token;
        const res = await request.patch(`${E2E_BACKEND_ORIGIN}/api/v1/config`, {
            headers: { "X-CSRF-Token": token },
            data: { theme: "dark" },
        });
        console.log("theme patch", res.status());
    });
    for (const entry of entries) {
        test(`${entry.id} dark`, async ({ page, baseURL }) => {
            await page.addInitScript(() => {
                try { window.localStorage.setItem("meshchatx_ui_theme", "dark"); } catch (e) {}
            });
            await page.setViewportSize(VIEWPORTS.desktop);
            await gotoUiPage(page, entry, baseURL);
            await page.waitForTimeout(600);
            await page.screenshot({ path: "/tmp/mcx-shots/conversation-dark.png" });
        });
    }
});

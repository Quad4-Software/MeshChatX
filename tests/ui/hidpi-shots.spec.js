const { test } = require("@playwright/test");
const { seedUiDemoData } = require("./seed");
const { gotoUiPage } = require("./ready");
const { resolveShots, VIEWPORTS } = require("./screenshots");
const { E2E_BACKEND_ORIGIN } = require("../e2e/helpers");

const entries = resolveShots({ ids: ["conversation"] });

test.use({ deviceScaleFactor: 2 });

test.describe("hidpi shots", () => {
    test.beforeAll(async ({ request }) => {
        await seedUiDemoData(request);
    });
    for (const theme of ["light", "dark"]) {
        for (const entry of entries) {
            test(`${entry.id} ${theme} @2x`, async ({ page, baseURL }) => {
                const csrf = await page.request.get(`${E2E_BACKEND_ORIGIN}/api/v1/auth/csrf`);
                const token = (await csrf.json()).csrf_token;
                await page.request.patch(`${E2E_BACKEND_ORIGIN}/api/v1/config`, {
                    headers: { "X-CSRF-Token": token },
                    data: { theme },
                });
                await page.addInitScript((t) => {
                    try { window.localStorage.setItem("meshchatx_ui_theme", t); } catch (e) {}
                }, theme);
                await page.setViewportSize(VIEWPORTS.desktop);
                await gotoUiPage(page, entry, baseURL);
                await page.waitForTimeout(600);
                await page.screenshot({ path: `/tmp/mcx-shots/conversation-${theme}-2x.png` });
            });
        }
    }
});

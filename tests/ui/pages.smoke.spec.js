const { test, expect } = require("@playwright/test");
const { dismissMapOnboardingTooltip } = require("../e2e/helpers");
const { resolvePages } = require("./pages");
const { seedUiSimulatedData } = require("./seed");
const { gotoUiPage } = require("./ready");

const pages = resolvePages({
    ciOnly: process.env.MESHCHAT_UI_CI === "1",
    ids: process.env.MESHCHAT_UI_PAGES
        ? process.env.MESHCHAT_UI_PAGES.split(",")
              .map((s) => s.trim())
              .filter(Boolean)
        : null,
});

test.describe("UI pages with simulated data", () => {
    test.beforeAll(async ({ request }) => {
        await seedUiSimulatedData(request);
    });

    for (const entry of pages) {
        test(`ready: ${entry.id}`, async ({ page, baseURL }) => {
            await gotoUiPage(page, entry, baseURL);
            if (entry.id === "map") {
                await dismissMapOnboardingTooltip(page);
            }
            await expect(page.locator("body")).toBeVisible();
        });
    }
});

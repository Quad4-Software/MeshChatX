const path = require("path");
const fs = require("fs");
const { test } = require("@playwright/test");
const { dismissMapOnboardingTooltip } = require("../e2e/helpers");
const { resolveShots, VIEWPORTS } = require("./screenshots");
const { seedUiDemoData } = require("./seed");
const { gotoUiPage, waitForBootReady, waitForPageReady } = require("./ready");

const OUT_DIR = process.env.MESHCHAT_SCREENSHOTS_DIR
    ? path.resolve(process.env.MESHCHAT_SCREENSHOTS_DIR)
    : path.resolve(__dirname, "../../screenshots");

const shots = resolveShots({
    ids: process.env.MESHCHAT_SCREENSHOT_PAGES
        ? process.env.MESHCHAT_SCREENSHOT_PAGES.split(",")
              .map((s) => s.trim())
              .filter(Boolean)
        : null,
});

const formFactors = process.env.MESHCHAT_SCREENSHOT_MOBILE === "0" ? ["desktop"] : ["desktop", "mobile"];

test.describe("screenshots", () => {
    test.beforeAll(async ({ request }) => {
        await seedUiDemoData(request);
        fs.mkdirSync(OUT_DIR, { recursive: true });
        fs.mkdirSync(path.join(OUT_DIR, "mobile"), { recursive: true });
    });

    for (const entry of shots) {
        for (const factor of formFactors) {
            if (factor === "mobile" && !entry.mobile) {
                continue;
            }
            test(`${entry.id} [${factor}]`, async ({ page, baseURL }) => {
                await page.setViewportSize(VIEWPORTS[factor]);
                if (entry.id === "map") {
                    const url = `${baseURL.replace(/\/$/, "")}/#${entry.path}`;
                    await page.goto(url, { waitUntil: "domcontentloaded" });
                    await waitForBootReady(page);
                    await dismissMapOnboardingTooltip(page);
                    await waitForPageReady(page, entry);
                } else {
                    await gotoUiPage(page, entry, baseURL);
                }
                if (entry.settleMs) {
                    await page.waitForTimeout(entry.settleMs);
                }
                const file =
                    factor === "mobile"
                        ? path.join(OUT_DIR, "mobile", `${entry.id}.png`)
                        : path.join(OUT_DIR, `${entry.id}.png`);
                await page.screenshot({ path: file, fullPage: false });
            });
        }
    }
});

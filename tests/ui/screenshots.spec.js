const path = require("path");
const fs = require("fs");
const { test } = require("@playwright/test");
const { dismissMapOnboardingTooltip } = require("../e2e/helpers");
const { resolveShots, VIEWPORTS } = require("./screenshots");
const { seedUiDemoData, setUiTheme } = require("./seed");
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
const themes = (process.env.MESHCHAT_SCREENSHOT_THEMES || "light,dark")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

test.describe("screenshots", () => {
    test.describe.configure({ mode: "serial" });
    test.beforeAll(async ({ request }) => {
        await seedUiDemoData(request);
        // Remove the legacy flat layout (screenshots/*.png, screenshots/mobile/*.png)
        // so stale captures never linger next to the factor/theme matrix. The
        // mobile directory itself is a valid factor dir in the new layout, so
        // only flat image files get removed, not the theme subtrees.
        for (const f of fs.readdirSync(OUT_DIR)) {
            const p = path.join(OUT_DIR, f);
            const stat = fs.statSync(p);
            if (stat.isFile() && /\.(png|jpe?g)$/i.test(f)) {
                fs.unlinkSync(p);
            } else if (stat.isDirectory() && f === "mobile") {
                for (const m of fs.readdirSync(p)) {
                    const mp = path.join(p, m);
                    if (fs.statSync(mp).isFile() && /\.(png|jpe?g)$/i.test(m)) {
                        fs.unlinkSync(mp);
                    }
                }
            }
        }
        for (const factor of formFactors) {
            for (const theme of themes) {
                fs.mkdirSync(path.join(OUT_DIR, factor, theme), { recursive: true });
            }
        }
    });

    // Switch the persisted theme once per theme block, then shoot every page.
    for (const theme of themes) {
        for (const entry of shots) {
            for (const factor of formFactors) {
                if (factor === "mobile" && !entry.mobile) {
                    continue;
                }
                test(`${entry.id} [${factor}/${theme}]`, async ({ page, baseURL, request }) => {
                    await page.setViewportSize(VIEWPORTS[factor]);
                    await setUiTheme(request, theme);
                    if (entry.id === "map") {
                        const url = `${baseURL.replace(/\/$/, "")}/#${entry.path}`;
                        await page.goto(url, { waitUntil: "domcontentloaded" });
                        await waitForBootReady(page);
                        await dismissMapOnboardingTooltip(page);
                        await waitForPageReady(page, entry);
                    } else {
                        await gotoUiPage(page, entry, baseURL);
                    }
                    // Let the theme engine settle after config-driven repaint.
                    await page.waitForTimeout(150);
                    if (entry.settleMs) {
                        await page.waitForTimeout(entry.settleMs);
                    }
                    const file = path.join(OUT_DIR, factor, theme, `${entry.id}.webp`);
                    // Per-shot cap: a wedged canvas/rAF loop can stall CDP
                    // captureScreenshot, so fail this test instead of the run.
                    await page.screenshot({ path: file, fullPage: false, type: "webp", quality: 95, timeout: 45000 });
                });
            }
        }
    }
});

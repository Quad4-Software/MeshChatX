const path = require("path");
const fs = require("fs");
const { test } = require("@playwright/test");
const { dismissMapOnboardingTooltip } = require("../e2e/helpers");
const { VIEWPORTS } = require("./screenshots");
const { seedUiDemoData, setUiTheme } = require("./seed");
const { gotoUiPage, waitForBootReady, waitForPageReady } = require("./ready");
const { applyGuideAnnotations, clearGuideAnnotations } = require("./guide/annotate");
const { startGuideRecording } = require("./guide/recorder");
const { GUIDES } = require("./guide/guides");

const OUT_DIR = process.env.MESHCHAT_GUIDE_DIR
    ? path.resolve(process.env.MESHCHAT_GUIDE_DIR)
    : path.resolve(__dirname, "../../docs/assets/guides");

const guides = (() => {
    const filter = process.env.MESHCHAT_GUIDE_IDS;
    if (!filter) return GUIDES;
    const want = new Set(filter.split(",").map((s) => s.trim()));
    return GUIDES.filter((g) => want.has(g.id));
})();

test.describe("guide captures", () => {
    test.describe.configure({ mode: "serial" });
    test.beforeAll(async ({ request }) => {
        await seedUiDemoData(request);
        fs.mkdirSync(OUT_DIR, { recursive: true });
    });

    for (const guide of guides) {
        for (const theme of guide.themes || ["dark"]) {
            const factor = guide.factor || "desktop";
            test(`${guide.id} [${factor}/${theme}]`, async ({ page, baseURL, request }) => {
                await page.setViewportSize(VIEWPORTS[factor]);
                await setUiTheme(request, theme);
                const url = `${baseURL.replace(/\/$/, "")}/#${guide.path}`;
                await page.goto(url, { waitUntil: "domcontentloaded" });
                await waitForBootReady(page);
                if (guide.path.startsWith("/map")) {
                    await dismissMapOnboardingTooltip(page);
                }
                await waitForPageReady(page, guide);
                await page.waitForTimeout(300);

                const dir = path.join(OUT_DIR, guide.id);
                fs.mkdirSync(dir, { recursive: true });

                for (const shot of guide.shots || []) {
                    if (shot.actions) {
                        await shot.actions(page);
                    }
                    const missing = await applyGuideAnnotations(page, shot.annotations || []);
                    if (missing.length) {
                        console.warn(`guide ${guide.id}/${shot.name}: selectors not found: ${missing.join("; ")}`);
                    }
                    await page.waitForTimeout(120);
                    const file = path.join(dir, `${shot.name}-${theme}.webp`);
                    await page.screenshot({ path: file, type: "webp", quality: 95, timeout: 45000 });
                    await clearGuideAnnotations(page);
                }

                for (const clip of guide.clips || []) {
                    const rec = await startGuideRecording(page);
                    try {
                        await clip.actions(page);
                        await rec.stop();
                        const fmt = clip.format || "webp";
                        const file = path.join(dir, `${clip.name}-${theme}.${fmt}`);
                        await rec.save(file, { fps: clip.fps || 8 });
                    } finally {
                        await rec.cleanup();
                    }
                }
            });
        }
    }
});

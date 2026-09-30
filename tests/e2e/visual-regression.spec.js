const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

// Visual regression baselines for a small set of content-rich routes.
// Baselines live in tests/e2e/__screenshots__/ via the snapshotPathTemplate
// in playwright.visual.config.js. Generate or refresh them with:
//   playwright test --config playwright.visual.config.js --update-snapshots
// The png directory is gitignored: baselines are local machine artifacts,
// regenerate them per environment rather than committing renders.
//
// Under the default playwright.config.js the snapshot template points at
// per-spec -snapshots/ dirs, so these tests skip there instead of writing
// stray baselines or failing on missing ones.

const SHOTS = [
    { route: "/", name: "dashboard" },
    { route: "/messages", name: "messages" },
    { route: "/contacts", name: "contacts" },
    { route: "/settings", name: "settings" },
    { route: "/relay-chat", name: "relay-chat" },
    { route: "/interfaces", name: "interfaces" },
    { route: "/map", name: "map", extraMask: ["canvas", ".ol-viewport"] },
    { route: "/archives", name: "archives" },
    { route: "/identities", name: "identities" },
    { route: "/tools", name: "tools" },
];

// Dynamic regions that shift every run: timestamps, relative times, live
// counters and badges. Masked elements get a solid overlay in the baseline.
const MASK_SELECTORS = [
    "time",
    "[class*='timestamp']",
    "[class*='relative-time']",
    "[class*='counter']",
    "[class*='badge']",
];

const STABILIZE_CSS = `
    *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
        caret-color: transparent !important;
    }
`;

test.describe("Visual regression", () => {
    test.setTimeout(300000);
    test.describe.configure({ mode: "serial" });
    test.use({ viewport: { width: 1280, height: 800 } });

    test.beforeEach(async ({ request }, testInfo) => {
        const underVisualConfig = (testInfo.config.configFile || "").endsWith("playwright.visual.config.js");
        test.skip(
            !underVisualConfig,
            "run via: playwright test --config playwright.visual.config.js --update-snapshots"
        );
        await prepareE2eSession(request);
    });

    for (const shot of SHOTS) {
        test(`route ${shot.route} matches baseline`, async ({ page }) => {
            await page.goto(`/#${shot.route}`, { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(1500);
            await page.addStyleTag({ content: STABILIZE_CSS });

            const mask = MASK_SELECTORS.concat(shot.extraMask || []).map((sel) => page.locator(sel));
            await expect(page).toHaveScreenshot(`${shot.name}.png`, {
                animations: "disabled",
                caret: "hide",
                mask,
                maxDiffPixelRatio: 0.01,
            });
        });
    }
});

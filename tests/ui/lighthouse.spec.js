const { test } = require("@playwright/test");
const { dismissMapOnboardingTooltip } = require("../e2e/helpers");
const { resolvePages, budgetsFor } = require("./pages");
const { seedUiSimulatedData } = require("./seed");
const { gotoUiPage } = require("./ready");
const {
    LH_DEBUG_PORT,
    runLighthouseAudit,
    scoresFromLhr,
    assertBudgets,
    writeReports,
} = require("./lighthouse-helper");

const pages = resolvePages({
    ciOnly: process.env.MESHCHAT_UI_CI === "1",
    ids: process.env.MESHCHAT_UI_PAGES
        ? process.env.MESHCHAT_UI_PAGES.split(",")
              .map((s) => s.trim())
              .filter(Boolean)
        : null,
});

test.describe("Lighthouse page scores (simulated data)", () => {
    test.describe.configure({ mode: "serial", timeout: 180000 });

    test.beforeAll(async ({ request }) => {
        await seedUiSimulatedData(request);
    });

    for (const entry of pages) {
        test(`lighthouse: ${entry.id}`, async ({ page, baseURL }) => {
            await gotoUiPage(page, entry, baseURL);
            if (entry.id === "map") {
                await dismissMapOnboardingTooltip(page);
            }

            const url = page.url();
            const runnerResult = await runLighthouseAudit(url, { port: LH_DEBUG_PORT });
            const scores = scoresFromLhr(runnerResult.lhr);
            const paths = writeReports(entry.id, runnerResult);

            // eslint-disable-next-line no-console
            console.log(
                `LH ${entry.id}: perf=${scores.performance} a11y=${scores.accessibility} bp=${scores["best-practices"]} report=${paths.htmlPath}`
            );

            assertBudgets(scores, budgetsFor(entry), entry.id);
        });
    }
});

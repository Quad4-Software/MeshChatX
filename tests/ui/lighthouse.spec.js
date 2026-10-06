const { test } = require("@playwright/test");
const { dismissMapOnboardingTooltip } = require("../e2e/helpers");
const { resolvePages, budgetsFor } = require("./pages");
const { seedUiSimulatedData } = require("./seed");
const { gotoUiPage } = require("./ready");
const {
    LH_DEBUG_PORT,
    runLighthouseAudit,
    scoresFromLhr,
    vitalsFromLhr,
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
    test.describe.configure({ mode: "serial", timeout: 240000 });

    test.beforeAll(async ({ request }) => {
        await seedUiSimulatedData(request);
    });

    for (const entry of pages) {
        test(`lighthouse: ${entry.id}`, async ({ page, baseURL, context }) => {
            // Freeze app-driven navigations on every document this target
            // loads. Lighthouse navigates the shared CDP target itself to
            // gather the measured page, and pages such as messages
            // reactively router.replace on mount or when data lands, which
            // kills the gatherer with "Inspected target navigated or
            // closed". An init script no-ops the History API before app code
            // runs on each load, including the load the audit performs.
            const preparePage = async (target) => {
                await target.addInitScript(() => {
                    history.pushState = () => undefined;
                    history.replaceState = () => undefined;
                });
                // Keep the service worker out of the audited page entirely:
                // re-navigations in the retry loop would re-register it, and
                // a SW-served document is what kills Network.getResponseBody
                // and nulls whole category scores.
                await target.route("**/service-worker.js", (route) => route.abort());
                await gotoUiPage(target, entry, baseURL);
                if (entry.id === "map") {
                    await dismissMapOnboardingTooltip(target);
                }
                // The service worker registered by the initial page load can
                // serve the audited navigation from cache, which makes CDP
                // unable to read the document body (Network.getResponseBody:
                // no resource with given identifier) and nulls whole category
                // scores. Unregister so audits measure the raw network page.
                await target.evaluate(async () => {
                    const regs = await navigator.serviceWorker.getRegistrations();
                    await Promise.all(regs.map((r) => r.unregister()));
                });
                // Let post-mount work settle (router redirects, ws handshakes)
                // before the audit takes over the target. A mid-audit navigation
                // kills the perf gatherer with "Inspected target navigated or
                // closed".
                await target.waitForTimeout(2500);
                return target;
            };

            let auditPage = await preparePage(page);
            const url = auditPage.url();
            // Lighthouse navigates the shared CDP target itself. a concurrent
            // evaluate or teardown can race it into "Inspected target
            // navigated or closed". Retry only that transient protocol error.
            // If the app navigated the tab mid-audit (router redirect after a
            // session event), re-open the target first so retries audit the
            // intended page rather than wherever the tab ended up.
            let runnerResult;
            for (let attempt = 1; ; attempt++) {
                try {
                    runnerResult = await runLighthouseAudit(url, { port: LH_DEBUG_PORT });
                    break;
                } catch (err) {
                    const msg = String((err && err.message) || err);
                    if (attempt >= 5 || !/navigated or closed|Protocol error|missing category scores/.test(msg)) {
                        throw err;
                    }
                    // eslint-disable-next-line no-console
                    console.log(`LH ${entry.id}: retrying audit after transient error: ${msg.split("\n")[0]}`);
                    // Re-navigate on retry, and on persistent failure move to
                    // a fresh page: a crashed renderer leaves the old target
                    // closed and every subsequent gather would die the same
                    // way on it.
                    try {
                        if (attempt >= 3) {
                            auditPage = await preparePage(await context.newPage());
                        } else {
                            await gotoUiPage(auditPage, entry, baseURL);
                            await auditPage.waitForTimeout(2500);
                        }
                    } catch {
                        // The next audit attempt fails on its own if the
                        // re-navigation itself is broken.
                    }
                }
            }
            const scores = scoresFromLhr(runnerResult.lhr);
            const vitals = vitalsFromLhr(runnerResult.lhr);
            const paths = writeReports(entry.id, runnerResult);

            // eslint-disable-next-line no-console
            console.log(
                `LH ${entry.id}: perf=${scores.performance} a11y=${scores.accessibility} bp=${scores["best-practices"]} ` +
                    `FCP=${vitals.fcp} LCP=${vitals.lcp} TBT=${vitals.tbt} CLS=${vitals.cls} SI=${vitals.si} ` +
                    `report=${paths.htmlPath}`
            );

            assertBudgets(scores, budgetsFor(entry), entry.id);
        });
    }
});

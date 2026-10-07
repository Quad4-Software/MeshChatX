const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");
const { readFileSync } = require("fs");
const { join } = require("path");

// axe-core accessibility audit over the full route crawl. axe is injected
// per route via addScriptTag and run against the whole document. Violations
// with impact "serious" or "critical" fail the test. "Moderate" and "minor"
// are logged as warnings so they can be triaged without blocking the suite.

const ROUTES = [
    "/",
    "/about",
    "/interfaces",
    "/interfaces/add",
    "/messages",
    "/contacts",
    "/map",
    "/network-visualiser",
    "/relay-chat",
    "/archives",
    "/propagation-nodes",
    "/ping",
    "/rncp",
    "/rns-filesync",
    "/rnsh",
    "/rnx",
    "/rnstatus",
    "/rnpath",
    "/rnpath-trace",
    "/rnprobe",
    "/translator",
    "/bots",
    "/bots/new",
    "/forwarder",
    "/micron-editor",
    "/tools/reticulum-config-editor",
    "/mesh-server",
    "/documentation",
    "/profile/icon",
    "/settings",
    "/identities",
    "/blocked",
    "/tools",
    "/licenses",
    "/tools/paper-message",
    "/tools/nearby",
    "/tools/sieve-filters",
    "/tools/message-blocklist",
    "/tools/rnode-flasher",
    "/tools/repository-server",
    "/debug/logs",
    "/changelog",
    "/tutorial",
    "/call",
    "/nomadnetwork",
];

const FAIL_IMPACTS = new Set(["serious", "critical"]);

// Known a11y debt, keyed as route|rule. New violations outside this
// baseline fail the run. paying down entries is welcome. Regenerate
// after fixing a batch by recording the live violation keys.
const BASELINE = new Set(JSON.parse(readFileSync(join(__dirname, "a11y-baseline.json"), "utf8")));

test.describe("Accessibility audit (axe-core)", () => {
    test.setTimeout(900000);
    test.describe.configure({ mode: "serial" });

    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("no new serious or critical axe violations beyond baseline", async ({ page }) => {
        const failures = [];
        const summary = [];

        for (const route of ROUTES) {
            await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(1200);

            await page.addScriptTag({ path: require.resolve("axe-core") });
            let results;
            try {
                results = await page.evaluate(async () => await window.axe.run());
            } catch (e) {
                failures.push(`${route}: axe.run threw: ${e.message}`);
                continue;
            }

            const violations = results.violations || [];
            for (const v of violations) {
                const targets = (v.nodes || [])
                    .slice(0, 3)
                    .map((n) => (n.target || []).join(" "))
                    .join(" | ");
                const line = `${route} [${v.impact}] ${v.id}: ${v.help} (${(v.nodes || []).length} nodes) ${targets}`;
                if (FAIL_IMPACTS.has(v.impact)) {
                    if (!BASELINE.has(`${route}|${v.id}`)) {
                        failures.push(line);
                    }
                } else {
                    console.warn(`a11y warning ${line}`);
                }
            }
            summary.push(`${route}:${violations.length}`);
        }

        console.log(`axe violations per route: ${summary.join(", ")}`);
        expect(failures).toEqual([]);
    });
});

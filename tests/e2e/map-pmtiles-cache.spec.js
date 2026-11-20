const { test, expect } = require("@playwright/test");
const { dismissMapOnboardingTooltip, prepareE2eSession } = require("./helpers");

const { buildArchive } = require("./pmtilesFixture");

const ARCHIVE = buildArchive([
    { z: 0, x: 0, y: 0 },
    { z: 1, x: 0, y: 0 },
    { z: 1, x: 1, y: 0 },
    { z: 1, x: 0, y: 1 },
    { z: 1, x: 1, y: 1 },
    { z: 2, x: 0, y: 0 },
    { z: 2, x: 1, y: 0 },
    { z: 2, x: 0, y: 1 },
    { z: 2, x: 1, y: 1 },
    { z: 2, x: 2, y: 0 },
    { z: 2, x: 2, y: 1 },
    { z: 2, x: 3, y: 0 },
    { z: 2, x: 0, y: 2 },
    { z: 2, x: 3, y: 1 },
    { z: 2, x: 0, y: 3 },
    { z: 2, x: 3, y: 3 },
]);

const ARCHIVE_HOST = "https://s3.quad4.io/pmtiles/planet.pmtiles";

test.describe("PMTiles basemap range caching", () => {
    test("repeated pan and zoom dedupe range requests, warm reload hits cache", async ({ page }) => {
        test.setTimeout(120000);
        const rangeRequests = [];
        await page.route(`${ARCHIVE_HOST}**`, async (route) => {
            const req = route.request();
            const range = req.headers()["range"] || "";
            rangeRequests.push(range);
            const m = /bytes=(\d+)-(\d+)/.exec(range);
            if (!m) {
                return route.fulfill({ status: 200, body: ARCHIVE });
            }
            const start = parseInt(m[1], 10);
            const end = Math.min(parseInt(m[2], 10), ARCHIVE.length - 1);
            return route.fulfill({
                status: 206,
                body: ARCHIVE.subarray(start, end + 1),
                headers: {
                    "content-range": `bytes ${start}-${end}/${ARCHIVE.length}`,
                    "content-length": String(end - start + 1),
                    "accept-ranges": "bytes",
                    "cache-control": "public, max-age=3600",
                    "last-modified": "Thu, 20 Nov 2025 00:00:00 GMT",
                    // Deliberately no access-control-expose-headers: the live
                    // server has the same gap, ETag must stay unreadable.
                    "access-control-allow-origin": "*",
                    etag: '"synthetic-v1"',
                },
            });
        });
        // Glyph/sprite fetches are irrelevant to range accounting. Satisfy
        // them with inert bytes so style application cannot stall the test.
        await page.route("https://protomaps.github.io/**", (route) =>
            route.fulfill({ status: 200, body: Buffer.alloc(16) })
        );
        // Offline mode is the backend default. Opt into online for this spec.
        await page.addInitScript(() => localStorage.setItem("meshchatx.map.offlineMode", "0"));

        await prepareE2eSession(page.request);
        await page.goto("/#/map");
        await page.evaluate(() => localStorage.setItem("map_onboarding_seen", "true"));
        await dismissMapOnboardingTooltip(page);
        await page.waitForSelector("canvas", { timeout: 60000 });
        await page.waitForTimeout(3000);

        const firstPass = rangeRequests.slice();
        expect(firstPass.length).toBeGreaterThan(0);

        // Pan twice and zoom in/out: every repeated range would mean the
        // shared source failed to cache.
        const box = await page.locator("canvas").first().boundingBox();
        const cx = box.x + box.width / 2;
        const cy = box.y + box.height / 2;
        for (let i = 0; i < 3; i++) {
            await page.mouse.move(cx, cy);
            await page.mouse.down();
            await page.mouse.move(cx + 200, cy + 100, { steps: 6 });
            await page.mouse.up();
            await page.waitForTimeout(700);
        }
        await page.mouse.move(cx, cy);
        await page.mouse.wheel(0, -480);
        await page.waitForTimeout(1000);
        await page.mouse.wheel(0, 480);
        await page.waitForTimeout(1000);
        for (let i = 0; i < 3; i++) {
            await page.mouse.move(cx, cy);
            await page.mouse.down();
            await page.mouse.move(cx - 200, cy - 100, { steps: 6 });
            await page.mouse.up();
            await page.waitForTimeout(700);
        }

        const all = rangeRequests.slice();
        const seen = new Set();
        const duplicates = all.filter((r) => (seen.has(r) ? true : (seen.add(r), false)));
        expect(duplicates).toEqual([]);

        // Warm reload: persisted entries serve everything, so the archive
        // should see at most a cheap revalidation probe, no tile refetch.
        rangeRequests.length = 0;
        await page.reload();
        await page.evaluate(() => localStorage.setItem("map_onboarding_seen", "true"));
        await dismissMapOnboardingTooltip(page);
        await page.waitForSelector("canvas", { timeout: 60000 });
        await page.waitForTimeout(3000);
        const tileRefetches = rangeRequests.filter((r) => r !== "bytes=0-126");
        expect(tileRefetches).toEqual([]);
    });
});

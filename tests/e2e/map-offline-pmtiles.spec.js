const { test, expect } = require("@playwright/test");
const { dismissMapOnboardingTooltip, prepareE2eSession } = require("./helpers");
const { buildArchive } = require("./pmtilesFixture");

// Local .pmtiles offline flow on the real backend: upload through the
// UI, tiles served 206 from the local endpoint with all external hosts
// blocked, warm reload revalidates cheaply, delete removes it.

const ARCHIVE = buildArchive([
    { z: 0, x: 0, y: 0 },
    { z: 1, x: 0, y: 0 },
    { z: 1, x: 1, y: 0 },
    { z: 1, x: 0, y: 1 },
    { z: 1, x: 1, y: 1 },
    { z: 2, x: 0, y: 0 },
    { z: 2, x: 1, y: 0 },
    { z: 2, x: 2, y: 0 },
    { z: 2, x: 3, y: 0 },
]);

const EXTERNAL = /s3\.quad4\.io|protomaps\.github\.io|tile\.openstreetmap|cartocdn|openfreemap/;

test.describe("local PMTiles offline basemap", () => {
    test("upload via UI, serve tiles locally with no external traffic, delete", async ({ page, request }) => {
        test.setTimeout(120000);
        const external = [];
        const localTileResponses = [];
        await page.route(EXTERNAL, (route) => {
            external.push(route.request().url());
            return route.abort();
        });
        page.on("response", (r) => {
            if (r.url().includes("/api/v1/map/pmtiles/")) {
                localTileResponses.push({ url: r.url(), status: r.status() });
            }
        });

        await page.addInitScript(() => {
            localStorage.setItem("meshchatx.map.offlineMode", "1");
            localStorage.setItem("map_onboarding_seen", "true");
        });
        await prepareE2eSession(request);
        await page.goto("/#/map");
        await dismissMapOnboardingTooltip(page);
        await page.waitForSelector(".ol-viewport", { timeout: 60000 });

        // Upload the fixture through the real UI file input.
        const fileInput = page.locator('input[type="file"][accept*=".pmtiles"]');
        await fileInput.setInputFiles({
            name: "e2e-region.pmtiles",
            mimeType: "application/octet-stream",
            buffer: ARCHIVE,
        });

        // The file list lives in the Maps side panel on the Offline tab.
        await page.locator('button[title="Maps"]').first().click();
        await page
            .locator("button", { hasText: /^Offline$/ })
            .first()
            .click();
        const fileRow = page.locator("text=e2e-region.pmtiles").first();
        await expect(fileRow).toBeVisible({ timeout: 15000 });
        await page
            .locator("button", { hasText: /^Offline$/ })
            .first()
            .click();
        await page.locator('button[title="Maps"]').first().click(); // close panel

        // Tiles must come from the local range endpoint as 206 partial
        // content; wait for at least one tile fetch then check traffic.
        await expect.poll(() => localTileResponses.length, { timeout: 30000 }).toBeGreaterThan(0);
        const bad = localTileResponses.filter((r) => r.status !== 206 && r.status !== 304);
        expect(bad, "non-range local tile responses").toEqual([]);
        expect(
            external.filter((u) => !u.includes("glyphs") || true),
            "external tile/glyph traffic"
        ).toEqual([]);

        // Warm reload: repeat views revalidate with 304 or serve without
        // a request; they must never hit the network outside localhost.
        const before = localTileResponses.length;
        await page.reload();
        await dismissMapOnboardingTooltip(page);
        await page.waitForSelector(".ol-viewport", { timeout: 60000 });
        await page.waitForTimeout(5000);
        const after = localTileResponses.slice(before);
        const fullRefetches = after.filter((r) => r.status === 200);
        expect(fullRefetches, "warm reload did a full tile refetch").toEqual([]);
        expect(external).toEqual([]);

        // Delete through the panel.
        await page.locator('button[title="Maps"]').first().click();
        await page
            .locator("button", { hasText: /^Offline$/ })
            .first()
            .click();
        const name = page.locator("text=e2e-region.pmtiles").first();
        await expect(name).toBeVisible({ timeout: 15000 });
        const row = name.locator("xpath=ancestor::div[contains(@class,'rounded-lg')][1]");
        await row
            .locator("button", { hasText: /delete/i })
            .first()
            .click();
        // Confirm the deletion dialog.
        const confirmBtn = page.locator("button", { hasText: /^(delete|confirm|ok|yes)$/i }).last();
        if (await confirmBtn.count()) await confirmBtn.click();
        await expect(page.locator("text=e2e-region.pmtiles")).toHaveCount(0, { timeout: 15000 });
    });
});

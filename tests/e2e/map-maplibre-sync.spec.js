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
]);

const ARCHIVE_HOST = "https://s3.quad4.io/pmtiles/planet.pmtiles";

test.describe("MapLibre basemap view sync", () => {
    test("maplibre.project matches OpenLayers pixels across zooms and rotations", async ({ page }) => {
        test.setTimeout(120000);
        await page.route(`${ARCHIVE_HOST}**`, async (route) => {
            const range = route.request().headers()["range"] || "";
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
                    "access-control-allow-origin": "*",
                    etag: '"sync-v1"',
                },
            });
        });
        await page.route("https://protomaps.github.io/**", (route) => {
            const url = route.request().url();
            if (url.endsWith(".json")) {
                return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
            }
            if (url.endsWith(".png")) {
                return route.fulfill({ status: 200, body: Buffer.alloc(16) });
            }
            return route.fulfill({ status: 200, body: Buffer.alloc(0) });
        });
        await page.addInitScript(() => {
            localStorage.setItem("meshchatx.map.offlineMode", "0");
            localStorage.setItem("mcx.map-basemap-renderer", "gpu");
            localStorage.setItem("map_onboarding_seen", "true");
        });

        await prepareE2eSession(page.request);
        await page.goto("/#/map");
        await dismissMapOnboardingTooltip(page);
        // The MapLibre canvas proves the GPU path was actually selected.
        await page.waitForSelector(".mcx-maplibre-basemap canvas", { timeout: 60000 });
        await page.waitForFunction(() => window.__mcxMap, { timeout: 30000 });
        await page.waitForTimeout(3000);

        const lonLat = [0, 0];
        for (const zoom of [3, 5, 7]) {
            for (const rotation of [0, 0.5, -0.7]) {
                await page.evaluate(
                    async ([z, r]) => {
                        const view = window.__mcxMap.getView();
                        view.setZoom(z);
                        view.setRotation(r);
                        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                    },
                    [zoom, rotation]
                );
                const diff = await page.evaluate(([lon, lat]) => {
                    // fromLonLat via proj4-free conversion: EPSG:4326 -> 3857
                    const x = (lon * 20037508.34) / 180;
                    const y = Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / 180);
                    const yMerc = (y * 20037508.34) / 180;
                    const olPx = window.__mcxMap.getPixelFromCoordinate([x, yMerc]);
                    const mlMap = document.querySelector(".mcx-maplibre-basemap").__mlMap;
                    const mlPx = mlMap.project([lon, lat]);
                    return { dx: olPx[0] - mlPx.x, dy: olPx[1] - mlPx.y };
                }, lonLat);
                expect(
                    Math.hypot(diff.dx, diff.dy),
                    `view drift at zoom ${zoom} rotation ${rotation}: ${JSON.stringify(diff)}`
                ).toBeLessThan(1.5);
            }
        }
    });
});

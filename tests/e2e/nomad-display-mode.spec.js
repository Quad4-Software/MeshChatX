const { test, expect } = require("@playwright/test");

// The sandboxed nomad renderer frame honors "display-mode" messages on its
// postMessage channel. Top-level loads treat window as its own parent, so
// posting to self exercises the same code path the app uses.
const CHANNEL = "nomad-crash-tab";

async function injectWideAscii(page) {
    await page.evaluate(() => {
        const wide = "X".repeat(220);
        const mid = "Y".repeat(110);
        document.getElementById("root").innerHTML =
            `<pre><span id="line-a">${wide}</span>\n<span id="line-b">${mid}</span></pre>`;
    });
}

function sendMode(page, mode) {
    return page.evaluate(
        ([channel, m]) => window.postMessage({ channel, type: "display-mode", mode: m }, "*"),
        [CHANNEL, mode]
    );
}

async function widths(page) {
    return page.evaluate(() => {
        const rect = (id) => document.getElementById(id).getBoundingClientRect().width;
        return { a: rect("line-a"), b: rect("line-b") };
    });
}

for (const width of [360, 390]) {
    test(`fit mode scales wide ASCII with no overflow at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 640 });
        await page.goto("/nomad-crash-tab.html");
        await page.waitForSelector("#root");
        await injectWideAscii(page);

        const natural = await widths(page);
        expect(natural.a).toBeGreaterThan(width);

        await sendMode(page, "fit");
        await page.evaluate(() => (document.fonts ? document.fonts.ready : Promise.resolve()));
        await page.waitForTimeout(300);

        const fit = await page.evaluate(() => {
            const root = document.getElementById("root");
            return {
                docScroll: document.documentElement.scrollWidth,
                win: window.innerWidth,
                rootZoom: getComputedStyle(root).zoom,
                rootTransform: getComputedStyle(root).transform,
            };
        });
        expect(fit.docScroll, "page scrolls sideways in fit mode").toBeLessThanOrEqual(fit.win + 1);
        const scaled = await widths(page);
        expect(scaled.a).toBeLessThanOrEqual(width + 1);
        // Lines keep proportional alignment: the ratio of rendered widths
        // matches the natural ratio, so the art is not distorted.
        expect(Math.abs(scaled.a / scaled.b - natural.a / natural.b)).toBeLessThan(0.05);
    });

    test(`scroll mode scrolls only the content at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 640 });
        await page.goto("/nomad-crash-tab.html");
        await page.waitForSelector("#root");
        await injectWideAscii(page);
        await sendMode(page, "scroll");
        await page.waitForTimeout(300);

        const sc = await page.evaluate(() => ({
            bodyOverflowX: getComputedStyle(document.body).overflowX,
            bodyScroll: document.body.scrollWidth,
            bodyClient: document.body.clientWidth,
            docScroll: document.documentElement.scrollWidth,
            win: window.innerWidth,
        }));
        expect(sc.bodyOverflowX).toBe("auto");
        // The frame body is the content scroll container. It scrolls, the
        // surrounding document does not grow past the viewport.
        expect(sc.bodyScroll).toBeGreaterThan(sc.bodyClient);
        expect(sc.docScroll).toBeLessThanOrEqual(sc.win + 1);

        const before = await page.evaluate(() => document.body.scrollLeft);
        await page.evaluate(() => {
            document.body.scrollLeft = 200;
        });
        const after = await page.evaluate(() => document.body.scrollLeft);
        expect(before).toBe(0);
        expect(after).toBeGreaterThan(0);
    });

    test(`off mode restores the clipped layout at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 640 });
        await page.goto("/nomad-crash-tab.html");
        await page.waitForSelector("#root");
        await injectWideAscii(page);
        await sendMode(page, "scroll");
        await page.waitForTimeout(200);
        await sendMode(page, "off");
        await page.waitForTimeout(200);
        const st = await page.evaluate(() => ({
            bodyOverflowX: getComputedStyle(document.body).overflowX,
            rootZoom: getComputedStyle(document.getElementById("root")).zoom,
        }));
        expect(st.bodyOverflowX).toBe("hidden");
        expect(st.rootZoom === "" || st.rootZoom === "normal" || parseFloat(st.rootZoom) === 1).toBe(true);
    });
}

const { chromium } = require("playwright");
(async () => {
    const pages = [
        "/",
        "/download/",
        "/roadmap/",
        "/changelog/",
        "/interfaces/",
        "/docs/overview/",
        "/branding/",
        "/git/",
    ];
    const browser = await chromium.launch({ executablePath: "/usr/bin/chromium" });
    for (const theme of ["dark", "light"]) {
        const ctx = await browser.newContext({
            viewport: { width: 1440, height: 900 },
            deviceScaleFactor: 2,
            colorScheme: theme,
        });
        const page = await ctx.newPage();
        for (const p of pages) {
            const name = p === "/" ? "home" : p.replace(/\//g, "");
            await page.goto(`http://127.0.0.1:4377${p}`, { waitUntil: "networkidle" });
            await page.waitForTimeout(600);
            await page.screenshot({
                path: `/run/media/user1/projects/site-shots/${theme}-${name}.png`,
                fullPage: false,
            });
        }
        await ctx.close();
    }
    await browser.close();
    console.log("done");
})();

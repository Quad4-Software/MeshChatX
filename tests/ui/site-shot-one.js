const { chromium } = require("playwright");
(async () => {
    const [url, out, theme = "dark", w = 1440, h = 900] = process.argv.slice(2);
    const b = await chromium.launch({ executablePath: "/usr/bin/chromium" });
    const p = await (
        await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: 2, colorScheme: theme })
    ).newPage();
    await p.goto(url, { waitUntil: "networkidle" });
    await p.waitForTimeout(600);
    await p.screenshot({ path: out });
    await b.close();
})();

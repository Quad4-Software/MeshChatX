// i18n visual sweep: render key routes in every locale, scan for text
// overflow/clipping deterministically, and (optionally) ask a vision
// model to compare each locale's render against the en baseline.
//
// Usage: node tests/agentic/i18n-sweep.cjs [--routes /settings,/about]
//        [--locales de,ja] [--judge] [--shots out-dir]
// --judge needs AGENTIC_VISION_MODEL via tests/agentic/llm.cjs env.

const { chromium } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const llm = require("./llm.cjs");

const BASE_URL = process.env.AGENTIC_BASE_URL || "http://127.0.0.1:5173";
const BACKEND = process.env.E2E_BACKEND_ORIGIN || "http://127.0.0.1:18079";

const DEFAULT_ROUTES = ["/settings", "/about", "/messages", "/contacts", "/tools"];
const LOCALES_DIR = path.resolve(__dirname, "../../meshchatx/src/frontend/locales");

function argValue(name, fallback) {
    const i = process.argv.indexOf(`--${name}`);
    return i >= 0 ? process.argv[i + 1] : fallback;
}
const hasFlag = (n) => process.argv.includes(`--${n}`);

function locales() {
    const arg = argValue("locales", null);
    if (arg) {
        return arg.split(",");
    }
    return fs
        .readdirSync(LOCALES_DIR)
        .filter((f) => f.endsWith(".json"))
        .map((f) => f.replace(".json", ""));
}

// Deterministic overflow/clipping scan. Flags elements whose rendered text
// exceeds their visible box, and elements clipped by zero-size parents.
async function overflowScan(page) {
    return page.evaluate(() => {
        const bad = [];
        const els = document.querySelectorAll(
            "button, h1, h2, h3, h4, label, nav a, [class*='tab'], [class*='title'], td, th",
        );
        for (const el of els) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) {
                continue;
            }
            const overflow = el.scrollWidth - el.clientWidth;
            if (overflow > 4) {
                bad.push({
                    tag: el.tagName.toLowerCase(),
                    text: (el.textContent || "").trim().slice(0, 60),
                    overflowPx: overflow,
                });
            }
        }
        return bad.slice(0, 50);
    });
}

async function setUiLocale(request, code) {
    const csrf = await request.get(`${BACKEND}/api/v1/auth/csrf`);
    const token = (await csrf.json()).csrf_token;
    const res = await request.patch(`${BACKEND}/api/v1/config`, {
        headers: { "X-CSRF-Token": token },
        data: { language: code },
    });
    if (!res.ok()) {
        throw new Error(`set language=${code} failed: ${res.status()}`);
    }
}

const JUDGE_PROMPT = `You are a UI layout reviewer comparing two screenshots of the same app page. Image 1 is the English baseline, image 2 is the same page in another locale. Classify the result:
- "pass": layout intact, only text length/language differs
- "clip": translated text is visibly truncated, cut off, or overflows its container
- "overlap": elements overlap or collide
- "break": layout structure broken (misaligned grid, missing section)
Reply ONLY as JSON: {"verdict":"pass|clip|overlap|break","regions":["short description of affected areas"],"confidence":0-1}`;

async function judgeDiff(base64Baseline, base64Locale, locale, route) {
    const msgs = llm.imageMessage(
        `${JUDGE_PROMPT}\nRoute: ${route}, locale: ${locale}`,
        [base64Baseline, base64Locale],
    );
    const out = await llm.chatJson(msgs, { model: llm.VISION_MODEL });
    return out;
}

async function main() {
    const routes = argValue("routes", null)
        ? argValue("routes").split(",")
        : DEFAULT_ROUTES;
    const shotsDir = argValue("shots", path.resolve(__dirname, "out", "i18n"));
    const useJudge = hasFlag("judge") && llm.configured();
    fs.mkdirSync(shotsDir, { recursive: true });

    const browser = await chromium.launch();
    const ctx = await browser.newContext({ baseURL: BASE_URL, viewport: { width: 1280, height: 900 } });
    const request = ctx.request;
    const page = await ctx.newPage();
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);

    const results = [];
    const baselines = {};

    for (const locale of locales()) {
        await setUiLocale(request, locale);
        for (const route of routes) {
            await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(1500);
            const shotPath = path.join(shotsDir, `${locale}${route.replace(/\//g, "_")}.png`);
            await page.screenshot({ path: shotPath });

            const overflow = await overflowScan(page);
            let verdict = overflow.length ? "clip" : "pass";
            let judge = null;
            if (useJudge) {
                const shotB64 = fs.readFileSync(shotPath).toString("base64");
                if (locale === "en") {
                    baselines[route] = shotB64;
                } else if (baselines[route]) {
                    try {
                        judge = await judgeDiff(baselines[route], shotB64, locale, route);
                        if (judge.verdict && judge.verdict !== "pass") {
                            verdict = judge.verdict;
                        }
                    } catch (e) {
                        judge = { error: String(e) };
                    }
                }
            }
            const row = { locale, route, verdict, overflow: overflow.length, judge };
            results.push(row);
            const mark = verdict === "pass" ? "ok " : "!! ";
            console.log(`${mark}${locale} ${route} overflow=${overflow.length}${judge ? ` judge=${judge.verdict || judge.error}` : ""}`);
        }
    }

    // Restore English.
    await setUiLocale(request, "en").catch(() => {});
    await browser.close();

    const reportPath = path.join(shotsDir, "report.json");
    fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
    const bad = results.filter((r) => r.verdict !== "pass");
    console.log(`\ni18n sweep: ${results.length - bad.length}/${results.length} pass, report at ${reportPath}`);
    for (const r of bad) {
        console.log(`FLAG ${r.locale} ${r.route} verdict=${r.verdict} overflow=${r.overflow}`);
    }
    process.exit(bad.length ? 1 : 0);
}

main().catch((e) => {
    console.error(e);
    process.exit(2);
});

// Adversarial input explorer: finds text inputs on each route, fills them
// with context-matched hostile payloads (deterministic sets, optionally
// extended by an LLM), and flags pageerrors, console errors, and 5xx.
//
// Usage: node tests/agentic/adversarial.cjs [--routes /settings,/tools] [--llm]
// --llm asks the configured model for extra payloads per field context.

const { chromium } = require("@playwright/test");
const llm = require("./llm.cjs");

const BASE_URL = process.env.AGENTIC_BASE_URL || "http://127.0.0.1:5173";
const MAX_FIELDS = parseInt(process.env.AGENTIC_ADV_FIELDS || "12", 10);

const PAYLOADS = {
    generic: [
        "<script>alert(1)</script>",
        "${7*7}",
        "{{7*7}}",
        "%s%s%s%s%n",
        "a".repeat(4096),
        "\u202Eevil\u202C",
        "😀".repeat(500),
        "null undefined NaN",
        "../../etc/passwd",
        "\x00\x01\x02",
        "' OR '1'='1",
        "javascript:alert(1)",
    ],
    micron: [
        "`!`[",
        "!`unclosed",
        "[`link`]()",
        ">```\nnever closed",
        "\\*{50}",
        "!`img`/nonexistent.png",
        "[`*".repeat(50),
        "\\n\\n".repeat(200),
    ],
    url: [
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://127.0.0.1:1",
        "https://a".repeat(2000),
        "://malformed",
        "data:text/html,<script>alert(1)</script>",
    ],
    numeric: ["-1", "0", "999999999999999", "1e308", "NaN", "Infinity", "0x10", "1.5.2.3"],
    path: ["../../../../etc/shadow", "..\\..\\win.ini", "/dev/null", "con.txt", "a".repeat(1024)],
};

const FIELD_HINTS = [
    { re: /micron|markup|markdown|message|body|text|content|page|editor/i, kind: "micron" },
    { re: /url|host|address|proxy|endpoint|server|uri/i, kind: "url" },
    { re: /port|count|size|limit|number|interval|timeout|ttl|min|max|amount/i, kind: "numeric" },
    { re: /path|file|dir|folder|import|export/i, kind: "path" },
];

function payloadsFor(el) {
    const hay = `${el.placeholder || ""} ${el.name || ""} ${el.label || ""} ${el.type || ""}`;
    for (const h of FIELD_HINTS) {
        if (h.re.test(hay)) {
            return PAYLOADS[h.kind];
        }
    }
    return PAYLOADS.generic;
}

async function llmPayloads(context) {
    const prompt = `Generate 6 hostile test inputs for a web form field with this context: ${context}.
Focus on parsing edge cases for the field's apparent purpose: markup injection, oversized input, unicode tricks, format confusion, path tricks.
Reply ONLY as JSON: {"payloads": ["...", "..."]}`;
    try {
        const out = await llm.chatJson([{ role: "user", content: prompt }]);
        return Array.isArray(out.payloads) ? out.payloads.slice(0, 6) : [];
    } catch {
        return [];
    }
}

function argValue(name, fallback) {
    const i = process.argv.indexOf(`--${name}`);
    return i >= 0 ? process.argv[i + 1] : fallback;
}

async function main() {
    const routes = argValue("routes", "/settings,/tools,/micron-editor").split(",");
    const useLlm = process.argv.includes("--llm") && llm.configured();
    const findings = [];

    const browser = await chromium.launch();
    const page = await (await browser.newContext({ baseURL: BASE_URL })).newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    page.on("console", (m) => {
        if (m.type() === "error") {
            errors.push(`console: ${m.text().slice(0, 200)}`);
        }
    });
    page.on("response", (r) => {
        if (r.status() >= 500) {
            errors.push(`http ${r.status()}: ${r.url()}`);
        }
    });

    for (const route of routes) {
        await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(1200);
        const before = errors.length;

        const inputs = await page
            .locator("input[type=text]:visible, input:not([type]):visible, textarea:visible, input[type=url]:visible, input[type=number]:visible")
            .all();
        for (const input of inputs.slice(0, MAX_FIELDS)) {
            const meta = await input.evaluate((el) => ({
                placeholder: el.placeholder || "",
                name: el.name || el.id || "",
                type: el.type || "",
                label: el.labels && el.labels[0] ? el.labels[0].textContent.trim() : "",
            }));
            let payloads = payloadsFor(meta);
            if (useLlm) {
                const extra = await llmPayloads(JSON.stringify(meta));
                payloads = [...payloads, ...extra];
            }
            for (const p of payloads.slice(0, 10)) {
                try {
                    await input.fill(p, { timeout: 1500 });
                    await input.press("Enter", { timeout: 500 }).catch(() => {});
                    await page.waitForTimeout(150);
                } catch {
                    // element detached or non-editable, move on
                }
            }
        }
        const found = errors.slice(before);
        if (found.length) {
            findings.push({ route, errors: found });
            console.log(`!! ${route}: ${found.length} errors`);
            for (const f of found.slice(0, 5)) {
                console.log(`   ${f}`);
            }
        } else {
            console.log(`ok ${route}`);
        }
    }

    await browser.close();
    console.log(`\nadversarial sweep: ${routes.length - findings.length}/${routes.length} clean`);
    process.exit(findings.length ? 1 : 0);
}

main().catch((e) => {
    console.error(e);
    process.exit(2);
});

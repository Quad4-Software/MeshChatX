/* eslint-disable security/detect-non-literal-regexp, security/detect-unsafe-regex */
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const REPO_ROOT = process.cwd();
const FRONTEND_DIR = join(REPO_ROOT, "meshchatx", "src", "frontend");
const INVENTORY_PATH = join(REPO_ROOT, "tests", "frontend", "fixtures", "theme_color_inventory.json");
const BASELINE_PATH = join(REPO_ROOT, "tests", "frontend", "fixtures", "theme_color_baseline.json");

const PALETTE = [
    "gray",
    "zinc",
    "slate",
    "neutral",
    "stone",
    "red",
    "orange",
    "amber",
    "yellow",
    "lime",
    "green",
    "emerald",
    "teal",
    "cyan",
    "sky",
    "blue",
    "indigo",
    "violet",
    "purple",
    "fuchsia",
    "pink",
    "rose",
];

const RAW_COLOR_RE = new RegExp(
    `\\b(?:bg|text|border|ring|accent|caret|outline|placeholder|shadow|decoration|from|via|to)-(?!sem-)(?:${PALETTE.join("|")})-(?:\\d{2,3}|[\\w-]+)\\b`,
    "g"
);

const FOCUS_RAW_RE =
    /\b(?:focus:ring|focus:border|peer-focus:ring|focus-visible:ring|dark:focus:ring|dark:focus:border)-(?!sem-)[\w-]+(?:\/[\d.]+)?/g;

const DARK_RAW_RE = /\bdark:(?:bg|text|border|ring)-(?!sem-)[\w-]+(?:\/[\d.]+)?/g;

const WHITE_BLACK_RE = /\b(?:bg|text|border|ring)-(?:white|black)\b/g;

const RAW_ACCENT_RE = /\baccent-(?:teal|blue|green|red|purple|violet|amber|cyan|sky|indigo|pink|orange)-[\d\w]+\b/g;

function walk(dir, out = []) {
    for (const name of readdirSync(dir)) {
        if (name === "public" || name === "node_modules") {
            continue;
        }
        const p = join(dir, name);
        const s = statSync(p);
        if (s.isDirectory()) {
            walk(p, out);
        } else if (s.isFile() && (name.endsWith(".vue") || name.endsWith(".css"))) {
            out.push(p);
        }
    }
    return out;
}

function matches(body) {
    return {
        raw_color: (body.match(RAW_COLOR_RE) || []).length,
        focus_raw: (body.match(FOCUS_RAW_RE) || []).length,
        dark_raw: (body.match(DARK_RAW_RE) || []).length,
        white_black: (body.match(WHITE_BLACK_RE) || []).length,
        accent_raw: (body.match(RAW_ACCENT_RE) || []).length,
    };
}

function main() {
    const files = walk(FRONTEND_DIR);
    const perFile = {};
    const totals = { raw_color: 0, focus_raw: 0, dark_raw: 0, white_black: 0, accent_raw: 0 };

    for (const p of files) {
        const body = readFileSync(p, "utf8");
        const m = matches(body);
        const rel = relative(REPO_ROOT, p);
        if (Object.values(m).some((n) => n > 0)) {
            perFile[rel] = m;
            for (const k of Object.keys(totals)) {
                totals[k] += m[k];
            }
        }
    }

    const inventory = {
        generated: new Date().toISOString(),
        totals,
        perFile,
        topFiles: Object.entries(perFile)
            .map(([path, counts]) => ({ path, total: Object.values(counts).reduce((a, b) => a + b, 0) }))
            .sort((a, b) => b.total - a.total)
            .slice(0, 50),
    };

    writeFileSync(INVENTORY_PATH, JSON.stringify(inventory, null, 2));

    const baseline = {
        generated: new Date().toISOString(),
        totals,
    };
    writeFileSync(BASELINE_PATH, JSON.stringify(baseline, null, 2));

    console.log(JSON.stringify({ totals, topFiles: inventory.topFiles.slice(0, 10) }, null, 2));
}

main();

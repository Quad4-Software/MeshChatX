#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD
/**
 * Fail when formatDate / meshDate(...).format patterns use unsupported tokens.
 * Keeps meshchatx/src/frontend/libs/datetime.js as the single source of truth.
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const FRONTEND_ROOT = path.join(ROOT, "meshchatx", "src", "frontend");
const DATETIME_LIB = path.join(FRONTEND_ROOT, "libs", "datetime.js");

const SCAN_EXTENSIONS = new Set([".js", ".mjs", ".cjs", ".vue", ".ts", ".tsx"]);

/** @type {RegExp[]} */
const PATTERN_EXTRACTORS = [
    /\bformatDate\s*\(\s*[^,]+?\s*,\s*(['"`])([^'"`]+?)\1/g,
    /\bmeshDate\s*\(\s*[^)]*?\)\s*\.\s*format\s*\(\s*(['"`])([^'"`]+?)\1/g,
    /\bdayjs\s*\(\s*[^)]*?\)\s*\.\s*format\s*\(\s*(['"`])([^'"`]+?)\1/g,
];

/**
 * @param {string} source
 * @returns {string[]}
 */
function readSupportedTokens(source) {
    const match = source.match(/export const SUPPORTED_FORMAT_TOKENS = Object\.freeze\(\[([\s\S]*?)\]\)/);
    if (!match) {
        return [];
    }
    return Array.from(match[1].matchAll(/"([^"]+)"/g), (m) => m[1]);
}

/**
 * @param {string} dir
 * @param {(filePath: string) => void} visit
 */
function walk(dir, visit) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.name === "node_modules" || entry.name === "public" || entry.name.startsWith(".")) {
            continue;
        }
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            walk(full, visit);
            continue;
        }
        if (SCAN_EXTENSIONS.has(path.extname(entry.name))) {
            visit(full);
        }
    }
}

/**
 * @param {string} pattern
 * @param {ReadonlySet<string>} supported
 * @returns {string[]}
 */
function unsupportedTokens(pattern, supported) {
    const tokenRe = /YYYY|MMM|MM|M|DD|D|HH|H|hh|h|mm|A|a|ss|SSS|Z|z|X|x|Do|ddd|dddd/g;
    const found = pattern.match(tokenRe) || [];
    return [...new Set(found.filter((token) => !supported.has(token)))];
}

function main() {
    const datetimeSource = fs.readFileSync(DATETIME_LIB, "utf8");
    const supportedList = readSupportedTokens(datetimeSource);
    if (supportedList.length === 0) {
        console.error("check-format-tokens: SUPPORTED_FORMAT_TOKENS missing from datetime.js");
        process.exit(1);
    }
    const supported = new Set(supportedList);

    /** @type {{ file: string, pattern: string, tokens: string[] }[]} */
    const failures = [];
    /** @type {{ file: string, pattern: string }[]} */
    const dayjsHits = [];

    walk(FRONTEND_ROOT, (filePath) => {
        const rel = path.relative(ROOT, filePath).replace(/\\/g, "/");
        if (rel.endsWith("libs/datetime.js")) {
            return;
        }
        const text = fs.readFileSync(filePath, "utf8");
        for (const extractor of PATTERN_EXTRACTORS) {
            extractor.lastIndex = 0;
            let match;
            while ((match = extractor.exec(text)) !== null) {
                const pattern = match[2];
                if (extractor.source.includes("dayjs")) {
                    dayjsHits.push({ file: rel, pattern });
                }
                const bad = unsupportedTokens(pattern, supported);
                if (bad.length > 0) {
                    failures.push({ file: rel, pattern, tokens: bad });
                }
            }
        }
    });

    if (dayjsHits.length > 0) {
        console.error("check-format-tokens: dayjs(...).format still used in frontend sources:");
        for (const hit of dayjsHits) {
            console.error(`  ${hit.file}: ${hit.pattern}`);
        }
        process.exit(1);
    }

    if (failures.length > 0) {
        console.error("check-format-tokens: unsupported format tokens:");
        for (const failure of failures) {
            console.error(`  ${failure.file}: "${failure.pattern}" -> ${failure.tokens.join(", ")}`);
        }
        console.error(`Supported tokens: ${supportedList.join(" ")}`);
        process.exit(1);
    }

    console.log("check-format-tokens: ok");
}

main();

import { readdirSync, readFileSync, statSync } from "fs";
import { join, relative } from "path";
import { describe, it, expect } from "vitest";

const ROOT = process.cwd();
const FRONTEND = join(ROOT, "meshchatx/src/frontend");
const STYLE_CSS = join(FRONTEND, "style.css");

const CLASS_ATTR_RE = /\bclass\s*=\s*"([^"]*)"/i;
const OPTION_RULE_RE = /(?:^|[}\s])((?:select\s+)?option)\s*\{([^}]*)\}/g;

const EXPLICIT_TEXT_MARKERS = [
    "text-sem-fg",
    "text-gray-900",
    "text-zinc-100",
    "dark:text-zinc-100",
    "dark:text-gray-100",
    "input-field",
    "rnf-input",
    "rnf-config-input",
];

function walkFiles(dir, exts, out = []) {
    for (const name of readdirSync(dir)) {
        if (name === "node_modules" || (name === "public" && dir === FRONTEND)) {
            continue;
        }
        const full = join(dir, name);
        const st = statSync(full);
        if (st.isDirectory()) {
            walkFiles(full, exts, out);
            continue;
        }
        if (exts.some((ext) => name.endsWith(ext))) {
            out.push(full);
        }
    }
    return out;
}

function extractSelects(filePath, source) {
    const rel = relative(ROOT, filePath);
    const found = [];
    let searchFrom = 0;
    const lower = source.toLowerCase();
    while (searchFrom < source.length) {
        const start = lower.indexOf("<select", searchFrom);
        if (start < 0) {
            break;
        }
        let depth = 0;
        let inQuote = null;
        let end = start + 7;
        for (; end < source.length; end++) {
            const ch = source[end];
            if (inQuote) {
                if (ch === inQuote && source[end - 1] !== "\\") {
                    inQuote = null;
                }
                continue;
            }
            if (ch === '"' || ch === "'") {
                inQuote = ch;
                continue;
            }
            if (ch === "{") {
                depth += 1;
                continue;
            }
            if (ch === "}") {
                depth = Math.max(0, depth - 1);
                continue;
            }
            if (ch === ">" && depth === 0) {
                break;
            }
        }
        const attrs = source.slice(start + 7, end);
        const classMatch = CLASS_ATTR_RE.exec(attrs);
        const classes = classMatch ? classMatch[1] : "";
        const line = source.slice(0, start).split("\n").length;
        found.push({ rel, line, classes, attrs });
        searchFrom = end + 1;
    }
    return found;
}

function hasExplicitText(classes) {
    return EXPLICIT_TEXT_MARKERS.some((marker) => classes.includes(marker));
}

function collectOptionRules(css) {
    const rules = [];
    for (const match of css.matchAll(OPTION_RULE_RE)) {
        rules.push({
            selector: match[1].replace(/\s+/g, " ").trim(),
            body: match[2],
        });
    }
    return rules;
}

describe("native select option theming", () => {
    const styleCss = readFileSync(STYLE_CSS, "utf8");
    const uiFiles = [
        ...walkFiles(join(FRONTEND, "features"), [".svelte"]),
        ...walkFiles(join(FRONTEND, "ui"), [".svelte"]),
    ];
    const allSelects = uiFiles.flatMap((file) => extractSelects(file, readFileSync(file, "utf8")));

    it("themes every native option via global select option rules", () => {
        expect(styleCss).toMatch(/select\s+option\s*\{[^}]*background-color:\s*var\(--mc-surface\)/s);
        expect(styleCss).toMatch(/select\s+option\s*\{[^}]*color:\s*var\(--mc-text\)/s);
        expect(styleCss).not.toMatch(/select\.input-field\s+option\s*\{/);
    });

    it("does not ship component option rules that force unthemed white surfaces", () => {
        const offenders = [];
        for (const file of uiFiles) {
            const source = readFileSync(file, "utf8");
            const styleBlocks = [...source.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]);
            for (const block of styleBlocks) {
                for (const rule of collectOptionRules(block)) {
                    const body = rule.body.toLowerCase();
                    const forcesWhite =
                        /background(?:-color)?\s*:\s*(#fff(?:fff)?|white|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))/i.test(
                            body
                        );
                    const missingSemanticText = !/--mc-text|text-sem-fg|var\(--mc-text\)/.test(body);
                    if (forcesWhite || (missingSemanticText && /color\s*:/.test(body) === false && forcesWhite)) {
                        offenders.push(`${relative(ROOT, file)} (${rule.selector})`);
                    }
                }
            }
        }
        expect(offenders).toEqual([]);
    });

    it("finds native selects across the Svelte UI", () => {
        expect(allSelects.length).toBeGreaterThan(20);
    });

    it("gives every native select an explicit text color class", () => {
        const missing = allSelects
            .filter((sel) => !hasExplicitText(sel.classes))
            .map((sel) => `${sel.rel}:${sel.line} class=${JSON.stringify(sel.classes)}`);
        expect(missing).toEqual([]);
    });

    it("keeps transparent selects covered by global option colors", () => {
        const transparent = allSelects.filter((sel) => sel.classes.includes("bg-transparent"));
        expect(transparent.length).toBeGreaterThan(0);
        expect(transparent.some((sel) => sel.rel.includes("ThemePresetPicker.svelte"))).toBe(true);
        for (const sel of transparent) {
            expect(hasExplicitText(sel.classes), `${sel.rel}:${sel.line}`).toBe(true);
        }
        expect(styleCss).toMatch(/select\s+option\s*\{[^}]*background-color:\s*var\(--mc-surface\)/s);
    });

    it("uses semantic dropdown-panel colors for floating menus", () => {
        const visualiserMenu = readFileSync(
            join(FRONTEND, "features/network-visualiser/components/NetworkVisualiserToolbarEngineSelect.svelte"),
            "utf8"
        );
        const language = readFileSync(join(FRONTEND, "ui/svelte/LanguageSelector.svelte"), "utf8");
        expect(visualiserMenu).toContain("bg-sem-surface");
        expect(visualiserMenu).toContain('role="listbox"');
        expect(visualiserMenu).not.toMatch(/bg-white[\s\S]{0,400}role="listbox"/);
        expect(language).toContain("bg-sem-surface");
        expect(language).toContain('role="menu"');
        expect(styleCss).toMatch(/\.dropdown-panel\s*\{[^}]*bg-sem-surface/s);
    });
});

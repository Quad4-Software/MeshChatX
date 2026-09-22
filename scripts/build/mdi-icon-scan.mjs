// SPDX-License-Identifier: 0BSD
//
// Shared icon-literal scanner used by the mdi subset generator and the
// vitest gate that keeps it fresh.

import fs from "node:fs";
import path from "node:path";

export const MDI_KEY_ALIASES = {
    mdiRoute: "mdiRoutes",
    mdiEmailSendOutline: "mdiSendOutline",
};

export const MATERIAL_SYMBOL_ALIASES = {
    "bug-report": "bug-outline",
    "smart-toy": "robot-outline",
    "robot-2": "robot-outline",
    "emoji-objects": "lightbulb-on",
};

// Dynamic names that never appear as source literals: backend defaults,
// fallbacks, and icons referenced through user data.
export const CURATED_EXTRA_ICON_NAMES = [
    "account",
    "account-outline",
    "alarm",
    "chat",
    "forum",
    "forum-outline",
    "help-circle-outline",
    "loading",
    "note-text",
    "progress-question",
    "robot",
    "robot-outline",
];

const SOURCE_EXTENSIONS = new Set([".svelte", ".ts", ".js", ".mjs", ".cjs"]);
const SKIP_DIRS = new Set(["node_modules", "public", "dist", "generated", ".git"]);

const LITERAL_PATTERNS = [
    // markup attributes and object fields: iconName="x", icon-name="x", icon: "x"
    /(?:iconName|icon-name|icon_name|icon)\s*(?:=|:)\s*["']([a-z0-9][a-z0-9_-]{1,60})["']/g,
    // direct resolver calls with a literal: getMdiIconPath("x")
    /(?:getMdiIconPath|resolveMdiIconKey|resolveMdiKebabIconName|normalizeMdiIconName|isValidMdiIconName|normalizeIconNameForLookup)\(\s*["']([^"']{1,64})["']/g,
];

export function kebabToMdiKey(kebab) {
    return (
        "mdi" +
        String(kebab)
            .split(/[-_]/)
            .filter((word) => word.length > 0)
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join("")
    );
}

export function mdiKeyToListName(key) {
    return String(key)
        .replace(/^mdi/, "")
        .replace(/([a-z])([A-Z])/g, "$1-$2")
        .toLowerCase();
}

export function isKebabCaseIconName(name) {
    if (!name || name.length > 64) {
        return false;
    }
    if (name.startsWith("-") || name.endsWith("-") || name.includes("--")) {
        return false;
    }
    for (let i = 0; i < name.length; i++) {
        const c = name.charCodeAt(i);
        if (c === 45) {
            continue;
        }
        if ((c >= 48 && c <= 57) || (c >= 97 && c <= 122)) {
            continue;
        }
        return false;
    }
    return true;
}

function walk(dir, out) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (entry.isDirectory()) {
            if (!SKIP_DIRS.has(entry.name)) {
                walk(path.join(dir, entry.name), out);
            }
            continue;
        }
        if (SOURCE_EXTENSIONS.has(path.extname(entry.name))) {
            out.push(path.join(dir, entry.name));
        }
    }
    return out;
}

/** Collect literal icon names referenced in frontend source files. */
export function collectLiteralIconNames(frontendRoot) {
    const files = walk(frontendRoot, []);
    const found = new Set();
    for (const file of files) {
        const text = fs.readFileSync(file, "utf8");
        for (const pattern of LITERAL_PATTERNS) {
            pattern.lastIndex = 0;
            for (const match of text.matchAll(pattern)) {
                const raw = match[1].trim().toLowerCase().replace(/_/g, "-");
                if (isKebabCaseIconName(raw)) {
                    found.add(raw);
                }
            }
        }
    }
    return found;
}

/**
 * Resolve a kebab-case icon name to its canonical @mdi/js export key, or null
 * when no such icon exists. Mirrors the runtime resolver in mdiIconNames.ts.
 */
export function resolveMdiExportKey(kebabName, mdi) {
    const normalized = String(kebabName).trim().toLowerCase().replace(/_/g, "-");
    const direct = MDI_KEY_ALIASES[kebabToMdiKey(normalized)] || kebabToMdiKey(normalized);
    if (mdi[direct]) {
        return direct;
    }
    const aliased = MATERIAL_SYMBOL_ALIASES[normalized];
    if (aliased) {
        const k = MDI_KEY_ALIASES[kebabToMdiKey(aliased)] || kebabToMdiKey(aliased);
        if (mdi[k]) {
            return k;
        }
    }
    const stripped = normalized.replace(/-\d+$/, "");
    if (stripped !== normalized) {
        const k = MDI_KEY_ALIASES[kebabToMdiKey(stripped)] || kebabToMdiKey(stripped);
        if (mdi[k]) {
            return k;
        }
    }
    return null;
}

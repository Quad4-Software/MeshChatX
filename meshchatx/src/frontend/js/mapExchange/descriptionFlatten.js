// SPDX-License-Identifier: 0BSD

const NULLISH_RE = /^(?:&lt;null&gt;|<null>|null|n\/?a|undefined|none|-)$/i;
const TABLE_ROW_RE = /<tr\b[^>]*>([\s\S]*?)<\/tr\s*>/gi;
const CELL_RE = /<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]\s*>/gi;
const BLOCK_BREAK_RE = /<\/(?:p|div|li|h[1-6]|br|tr)\s*>/gi;
const BR_RE = /<br\s*\/?>/gi;
const TAG_RE = /<[^>]+>/g;
const WS_RE = /\s+/g;
const ENTITY_RE = /&(#x?[0-9a-f]+|[a-z]+);/gi;

/**
 * @param {string} value
 * @returns {boolean}
 */
export function isNullishMapValue(value) {
    const t = String(value ?? "")
        .trim()
        .replace(/\u00a0/g, " ");
    if (!t) {
        return true;
    }
    return NULLISH_RE.test(t);
}

/**
 * @param {string} html
 * @returns {string}
 */
function decodeBasicEntities(html) {
    return String(html).replace(ENTITY_RE, (full, name) => {
        const n = String(name).toLowerCase();
        if (n === "amp") {
            return "&";
        }
        if (n === "lt") {
            return "<";
        }
        if (n === "gt") {
            return ">";
        }
        if (n === "quot") {
            return '"';
        }
        if (n === "apos" || n === "#39") {
            return "'";
        }
        if (n === "nbsp") {
            return " ";
        }
        if (n.startsWith("#x")) {
            const code = Number.parseInt(n.slice(2), 16);
            return Number.isFinite(code) ? String.fromCodePoint(code) : full;
        }
        if (n.startsWith("#")) {
            const code = Number.parseInt(n.slice(1), 10);
            return Number.isFinite(code) ? String.fromCodePoint(code) : full;
        }
        return full;
    });
}

/**
 * Drop script and style nodes before flattening to plain text.
 * Uses the DOM when available so nested or malformed tags are not left behind
 * by a single-pass regex replace.
 * @param {string} html
 * @returns {string}
 */
function dropScriptAndStyle(html) {
    const s = String(html || "");
    if (!s || typeof DOMParser === "undefined") {
        return s;
    }
    const doc = new DOMParser().parseFromString(s, "text/html");
    for (const el of doc.querySelectorAll("script, style")) {
        el.remove();
    }
    return doc.body ? doc.body.innerHTML : s;
}

/**
 * @param {string} cellHtml
 * @returns {string}
 */
function cellPlain(cellHtml) {
    return decodeBasicEntities(String(cellHtml).replace(TAG_RE, " ").replace(WS_RE, " ").trim());
}

/**
 * Turn ArcGIS / balloon HTML descriptions into readable plain text.
 * Drops script and style blocks. Prefer table rows as "Key: Value" lines.
 * Output is plain text (callers XML-escape when writing markup).
 * @param {string} html
 * @returns {string}
 */
export function flattenHtmlDescription(html) {
    let s = String(html || "");
    if (!s.trim()) {
        return "";
    }
    s = dropScriptAndStyle(s);
    const rows = [];
    s.replace(TABLE_ROW_RE, (_full, rowInner) => {
        const cells = [];
        String(rowInner).replace(CELL_RE, (_c, cellInner) => {
            const plain = cellPlain(cellInner);
            if (plain) {
                cells.push(plain);
            }
            return "";
        });
        if (cells.length >= 2) {
            const key = cells[0];
            const val = cells.slice(1).join(" ");
            if (key && !isNullishMapValue(val)) {
                rows.push(`${key}: ${val}`);
            }
        } else if (cells.length === 1 && !isNullishMapValue(cells[0])) {
            rows.push(cells[0]);
        }
        return "";
    });
    if (rows.length) {
        return rows.join("\n");
    }
    s = s.replace(BR_RE, "\n").replace(BLOCK_BREAK_RE, "\n");
    s = decodeBasicEntities(s.replace(TAG_RE, " "));
    return s
        .split(/\n+/)
        .map((line) => line.replace(WS_RE, " ").trim())
        .filter((line) => line && !isNullishMapValue(line))
        .join("\n");
}

/**
 * Split "Key: Value" lines out of a flattened description.
 * Rejects URL-like keys so "See https://host:port/path" stays as description text.
 * @param {string} description
 * @returns {{ leftover: string, pairs: { key: string, value: string }[] }}
 */
export function extractKeyedDescriptionLines(description) {
    const pairs = [];
    const leftover = [];
    for (const rawLine of String(description || "").split(/\n+/)) {
        const line = rawLine.trim();
        if (!line) {
            continue;
        }
        const m = line.match(/^([^:]{1,80}):\s*(.+)$/);
        if (m) {
            const key = m[1].trim();
            const value = m[2].trim();
            if (key && !isNullishMapValue(value) && isPlausiblePropertyKey(key, value)) {
                pairs.push({ key, value });
                continue;
            }
        }
        if (!isNullishMapValue(line)) {
            leftover.push(line);
        }
    }
    return { leftover: leftover.join("\n"), pairs };
}

/**
 * @param {string} key
 * @param {string} value
 * @returns {boolean}
 */
function isPlausiblePropertyKey(key, value) {
    const k = String(key || "").trim();
    if (!k || k.length > 64) {
        return false;
    }
    if (/https?/i.test(k) || k.includes("/") || k.includes("\\")) {
        return false;
    }
    const v = String(value || "").trim();
    if (v.startsWith("//") || /^https?:\/\//i.test(v)) {
        if (!/^[A-Za-z_][\w.-]{0,63}$/.test(k)) {
            return false;
        }
    }
    return /^[A-Za-z_][\w\s.-]{0,63}$/.test(k);
}

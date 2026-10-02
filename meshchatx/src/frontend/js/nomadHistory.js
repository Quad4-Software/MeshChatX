// SPDX-License-Identifier: 0BSD

/**
 * In-memory + localStorage-backed NomadNet browsing history.
 * Tracks visited node/page pairs for the tab-strip history dropdown.
 */

const STORAGE_KEY = "meshchatx.nomad.history";
const MAX_ENTRIES = 50;

const FORBIDDEN_KEYS = new Set(["__proto__", "constructor", "prototype"]);

let entries = [];

function load() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw == null) return;
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
            entries = parsed.filter(
                (e) =>
                    e &&
                    typeof e.destinationHash === "string" &&
                    typeof e.path === "string" &&
                    !FORBIDDEN_KEYS.has(e.destinationHash)
            );
        }
    } catch {
        entries = [];
    }
}

function persist() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    } catch {
        // persistence is best-effort
    }
}

/**
 * Record a page visit.
 * @param {string} destinationHash
 * @param {string} path
 * @param {string|null} title
 * @param {boolean} isPrivate
 */
export function recordNomadVisit(destinationHash, path, title = null, isPrivate = false) {
    if (isPrivate || !destinationHash || !path) return;
    load();
    // Dedupe consecutive identical visits
    const last = entries[entries.length - 1];
    if (last && last.destinationHash === destinationHash && last.path === path) return;
    entries.push({
        destinationHash,
        path,
        title: typeof title === "string" ? title.slice(0, 200) : null,
        ts: Date.now(),
    });
    if (entries.length > MAX_ENTRIES) {
        entries.splice(0, entries.length - MAX_ENTRIES);
    }
    persist();
}

/**
 * Get the history list, newest first.
 * @returns {Array<{destinationHash: string, path: string, title: string|null, ts: number}>}
 */
export function getNomadHistory() {
    load();
    return [...entries].reverse();
}

/**
 * Clear all history.
 */
export function clearNomadHistory() {
    entries = [];
    persist();
}

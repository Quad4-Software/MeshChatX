// SPDX-License-Identifier: 0BSD

/**
 * In-memory + localStorage-backed NomadNet browsing history.
 * Tracks visited node/page pairs for the tab-strip history dropdown.
 */

const STORAGE_KEY = "meshchatx.nomad.history";
const MAX_ENTRIES = 50;

const FORBIDDEN_KEYS = new Set(["__proto__", "constructor", "prototype"]);

export interface NomadHistoryEntry {
    destinationHash: string;
    path: string;
    title: string | null;
    ts: number;
}

let entries: NomadHistoryEntry[] = [];

function load(): void {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw == null) return;
        const parsed: unknown = JSON.parse(raw);
        if (Array.isArray(parsed)) {
            entries = parsed.filter(
                (e): e is NomadHistoryEntry =>
                    typeof e === "object" &&
                    e !== null &&
                    typeof (e as NomadHistoryEntry).destinationHash === "string" &&
                    typeof (e as NomadHistoryEntry).path === "string" &&
                    !FORBIDDEN_KEYS.has((e as NomadHistoryEntry).destinationHash)
            );
        }
    } catch {
        entries = [];
    }
}

function persist(): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    } catch {
        // persistence is best-effort
    }
}

export function recordNomadVisit(
    destinationHash: string,
    path: string,
    title: string | null = null,
    isPrivate = false
): void {
    if (isPrivate || !destinationHash || !path) return;
    load();
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

export function getNomadHistory(): NomadHistoryEntry[] {
    load();
    return [...entries].reverse();
}

export function clearNomadHistory(): void {
    entries = [];
    persist();
}

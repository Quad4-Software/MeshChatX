// SPDX-License-Identifier: 0BSD

/**
 * Persist which post-install / existing-user prompts have been dismissed.
 * Each prompt has an id and a revision. Bump the revision in the registry
 * to show that prompt again to users who already dismissed an older revision.
 */

export const POST_INSTALL_PROMPTS_STORAGE_KEY = "meshchatx.post_install_prompts_seen";

/**
 * localStorage access itself can throw (privacy modes, disabled storage),
 * so resolve it defensively once per call.
 * @returns {Storage | null}
 */
function getSafeLocalStorage() {
    try {
        if (typeof window === "undefined") {
            return null;
        }
        return window.localStorage || null;
    } catch {
        return null;
    }
}

/**
 * @returns {Record<string, number>}
 */
export function readSeenMap() {
    const storage = getSafeLocalStorage();
    if (!storage) {
        return {};
    }
    try {
        const raw = storage.getItem(POST_INSTALL_PROMPTS_STORAGE_KEY);
        if (!raw) {
            return {};
        }
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            return {};
        }
        /** @type {Record<string, number>} */
        const out = {};
        for (const [id, revision] of Object.entries(parsed)) {
            const n = Number(revision);
            if (Number.isFinite(n) && n >= 0) {
                out[id] = Math.floor(n);
            }
        }
        return out;
    } catch {
        return {};
    }
}

/**
 * @param {Record<string, number>} map
 */
export function writeSeenMap(map) {
    const storage = getSafeLocalStorage();
    if (!storage) {
        return;
    }
    try {
        storage.setItem(POST_INSTALL_PROMPTS_STORAGE_KEY, JSON.stringify(map || {}));
    } catch {
        // Storage may be unavailable or full — prompts simply re-appear.
    }
}

/**
 * @param {string} id
 * @returns {number}
 */
export function getSeenRevision(id) {
    if (!id) {
        return 0;
    }
    const map = readSeenMap();
    const n = Number(map[id]);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
}

/**
 * @param {string} id
 * @param {number} revision
 */
export function markPromptSeen(id, revision) {
    if (!id) {
        return;
    }
    const nextRevision = Math.max(0, Math.floor(Number(revision) || 0));
    const map = readSeenMap();
    const prev = getSeenRevision(id);
    if (nextRevision <= prev) {
        return;
    }
    map[id] = nextRevision;
    writeSeenMap(map);
}

/**
 * @param {string} id
 * @param {number} revision
 * @returns {boolean}
 */
export function shouldShowPrompt(id, revision) {
    const target = Math.max(0, Math.floor(Number(revision) || 0));
    if (!id || target <= 0) {
        return false;
    }
    return getSeenRevision(id) < target;
}

/**
 * Test helper.
 */
export function clearPromptSeenState() {
    const storage = getSafeLocalStorage();
    if (!storage) {
        return;
    }
    try {
        storage.removeItem(POST_INSTALL_PROMPTS_STORAGE_KEY);
    } catch {
        // ignore
    }
}

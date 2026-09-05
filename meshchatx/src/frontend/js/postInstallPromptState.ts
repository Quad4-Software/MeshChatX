// SPDX-License-Identifier: 0BSD

/**
 * Persist which post-install / existing-user prompts have been dismissed.
 * Each prompt has an id and a revision. Bump the revision in the registry
 * to show that prompt again to users who already dismissed an older revision.
 */

export const POST_INSTALL_PROMPTS_STORAGE_KEY = "meshchatx.post_install_prompts_seen";

/**
 * @returns {Record<string, number>}
 */
export function readSeenMap() {
    if (typeof window === "undefined" || !window.localStorage) {
        return {};
    }
    try {
        const raw = window.localStorage.getItem(POST_INSTALL_PROMPTS_STORAGE_KEY);
        if (!raw) {
            return {};
        }
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            return {};
        }
        /** @type {Record<string, number>} */
        const out: any = {};
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
    if (typeof window === "undefined" || !window.localStorage) {
        return;
    }
    window.localStorage.setItem(POST_INSTALL_PROMPTS_STORAGE_KEY, JSON.stringify(map || {}));
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
    if (typeof window === "undefined" || !window.localStorage) {
        return;
    }
    window.localStorage.removeItem(POST_INSTALL_PROMPTS_STORAGE_KEY);
}

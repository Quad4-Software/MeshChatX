// SPDX-License-Identifier: 0BSD

/**
 * Persist which post-install / existing-user prompts have been dismissed.
 * Each prompt has an id and a revision. Bump the revision in the registry
 * to show that prompt again to users who already dismissed an older revision.
 */

export const POST_INSTALL_PROMPTS_STORAGE_KEY = "meshchatx.post_install_prompts_seen";

export type PostInstallSeenMap = Record<string, number>;

export function readSeenMap(): PostInstallSeenMap {
    if (typeof window === "undefined" || !window.localStorage) {
        return {};
    }
    try {
        const raw = window.localStorage.getItem(POST_INSTALL_PROMPTS_STORAGE_KEY);
        if (!raw) {
            return {};
        }
        const parsed: unknown = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            return {};
        }
        const out: PostInstallSeenMap = {};
        for (const [id, revision] of Object.entries(parsed as Record<string, unknown>)) {
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

export function writeSeenMap(map: PostInstallSeenMap): void {
    if (typeof window === "undefined" || !window.localStorage) {
        return;
    }
    window.localStorage.setItem(POST_INSTALL_PROMPTS_STORAGE_KEY, JSON.stringify(map || {}));
}

export function getSeenRevision(id: string): number {
    if (!id) {
        return 0;
    }
    const map = readSeenMap();
    const n = Number(map[id]);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
}

export function markPromptSeen(id: string, revision: number): void {
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

export function shouldShowPrompt(id: string, revision: number): boolean {
    const target = Math.max(0, Math.floor(Number(revision) || 0));
    if (!id || target <= 0) {
        return false;
    }
    return getSeenRevision(id) < target;
}

/** Test helper. */
export function clearPromptSeenState(): void {
    if (typeof window === "undefined" || !window.localStorage) {
        return;
    }
    window.localStorage.removeItem(POST_INSTALL_PROMPTS_STORAGE_KEY);
}

/* SPDX-License-Identifier: 0BSD */

const STORAGE_KEY = "meshchatx.paper_ingested_hashes";
const MAX_HASHES_PER_IDENTITY = 500;

/**
 * @param {unknown} identityKey
 * @returns {string}
 */
export function normalizePaperIngestIdentityKey(identityKey) {
    return typeof identityKey === "string" && identityKey ? identityKey : "_";
}

/**
 * @param {unknown} messageHash
 * @returns {string}
 */
export function normalizePaperIngestMessageHash(messageHash) {
    return typeof messageHash === "string" ? messageHash.trim().toLowerCase() : "";
}

/**
 * @returns {Record<string, string[]>}
 */
function readRoot() {
    try {
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
        if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
            return {};
        }
        return raw;
    } catch {
        return {};
    }
}

/**
 * @param {Record<string, string[]>} root
 */
function writeRoot(root) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(root));
    } catch {
        /* ignore quota / private mode */
    }
}

/**
 * @param {unknown} identityKey
 * @returns {string[]}
 */
export function listIngestedPaperMessageHashes(identityKey) {
    const key = normalizePaperIngestIdentityKey(identityKey);
    const root = readRoot();
    const list = root[key];
    if (!Array.isArray(list)) {
        return [];
    }
    return list.filter((h) => typeof h === "string" && h);
}

/**
 * @param {unknown} identityKey
 * @param {unknown} messageHash
 * @returns {boolean}
 */
export function isPaperMessageIngested(identityKey, messageHash) {
    const hash = normalizePaperIngestMessageHash(messageHash);
    if (!hash) {
        return false;
    }
    return listIngestedPaperMessageHashes(identityKey).includes(hash);
}

/**
 * @param {unknown} identityKey
 * @param {unknown} messageHash
 * @returns {string[]} updated list for that identity
 */
export function markPaperMessageIngested(identityKey, messageHash) {
    const key = normalizePaperIngestIdentityKey(identityKey);
    const hash = normalizePaperIngestMessageHash(messageHash);
    if (!hash) {
        return listIngestedPaperMessageHashes(identityKey);
    }
    const root = readRoot();
    const prev = Array.isArray(root[key]) ? root[key].filter((h) => typeof h === "string" && h) : [];
    if (prev.includes(hash)) {
        return prev;
    }
    const next = [...prev, hash];
    while (next.length > MAX_HASHES_PER_IDENTITY) {
        next.shift();
    }
    root[key] = next;
    writeRoot(root);
    return next;
}

/**
 * Whether an ingest_uri result should mark the source bubble as ingested.
 * @param {unknown} status
 * @returns {boolean}
 */
export function shouldMarkPaperIngestFromResultStatus(status) {
    return status === "success" || status === "info";
}

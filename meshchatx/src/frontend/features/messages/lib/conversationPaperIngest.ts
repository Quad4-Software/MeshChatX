// SPDX-License-Identifier: 0BSD

import { PAPER_INGESTED_HASHES_MAX_PER_IDENTITY, PAPER_INGESTED_HASHES_STORAGE_KEY } from "./constants.js";

const STORAGE_KEY = PAPER_INGESTED_HASHES_STORAGE_KEY;
const MAX_HASHES_PER_IDENTITY = PAPER_INGESTED_HASHES_MAX_PER_IDENTITY;

export function normalizePaperIngestIdentityKey(identityKey: unknown): string {
    return typeof identityKey === "string" && identityKey ? identityKey : "_";
}

export function normalizePaperIngestMessageHash(messageHash: unknown): string {
    return typeof messageHash === "string" ? messageHash.trim().toLowerCase() : "";
}

function readRoot(): Record<string, string[]> {
    try {
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
        if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
            return {};
        }
        return raw as Record<string, string[]>;
    } catch {
        return {};
    }
}

function writeRoot(root: Record<string, string[]>): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(root));
    } catch {
        /* ignore quota / private mode */
    }
}

export function listIngestedPaperMessageHashes(identityKey: unknown): string[] {
    const key = normalizePaperIngestIdentityKey(identityKey);
    const root = readRoot();
    const list = root[key];
    if (!Array.isArray(list)) {
        return [];
    }
    return list.filter((h) => typeof h === "string" && h);
}

export function isPaperMessageIngested(identityKey: unknown, messageHash: unknown): boolean {
    const hash = normalizePaperIngestMessageHash(messageHash);
    if (!hash) {
        return false;
    }
    return listIngestedPaperMessageHashes(identityKey).includes(hash);
}

export function markPaperMessageIngested(identityKey: unknown, messageHash: unknown): string[] {
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

export function shouldMarkPaperIngestFromResultStatus(status: unknown): boolean {
    return status === "success" || status === "info";
}

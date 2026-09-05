// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import { t } from "../../../js/i18n.js";
import type { AclRow, AclRules, FilesyncPeer, FilesyncProgressPayload } from "./types.js";

export function formatFileSize(bytes: number | null | undefined): string {
    return Utils.formatBytes(bytes || 0);
}

export function formatProgressLabel(payload: FilesyncProgressPayload | null | undefined): string {
    if (!payload) {
        return "";
    }
    if (typeof payload === "string") {
        return payload;
    }
    const path = payload.path || payload.file || payload.name || "";
    const status = payload.status || payload.state || payload.phase || "";
    const bytes = (payload.bytes ?? payload.transferred ?? payload.done) as number | undefined;
    const total = (payload.total ?? payload.size) as number | undefined;
    const parts: string[] = [];
    if (path) {
        parts.push(String(path));
    }
    if (status) {
        parts.push(String(status));
    }
    if (bytes != null && total != null) {
        parts.push(`${formatFileSize(bytes)} / ${formatFileSize(total)}`);
    } else if (bytes != null) {
        parts.push(formatFileSize(bytes));
    }
    if (parts.length === 0) {
        try {
            return JSON.stringify(payload);
        } catch {
            return String(payload);
        }
    }
    return parts.join(" · ");
}

export function peerStatusLabel(peer: FilesyncPeer | null | undefined): string {
    const raw = peer?.status;
    if (raw === 1 || raw === "connected" || raw === true) {
        return t("rns_filesync.peer_connected");
    }
    if (raw === 0 || raw === "disconnected" || raw === false) {
        return t("rns_filesync.peer_disconnected");
    }
    return raw != null ? String(raw) : t("rns_filesync.peer_unknown");
}

export function formatAclRows(rules: AclRules | null | undefined): AclRow[] {
    const r = rules || {};
    const byHash: Record<string, Set<string>> = {};
    for (const perm of ["read", "write", "delete"]) {
        const targets = Array.isArray(r[perm]) ? (r[perm] as string[]) : [];
        for (const hash of targets) {
            if (!byHash[hash]) {
                byHash[hash] = new Set();
            }
            byHash[hash].add(perm);
        }
    }
    const labelMap: Record<string, string> = {
        read: t("rns_filesync.perm_read"),
        write: t("rns_filesync.perm_write"),
        delete: t("rns_filesync.perm_delete"),
    };
    return Object.keys(byHash)
        .sort()
        .map((hash) => ({
            hash,
            permsLabel: ["read", "write", "delete"]
                .filter((p) => byHash[hash].has(p))
                .map((p) => labelMap[p])
                .join(", "),
        }));
}

export function joinPath(base: string, name: string): string {
    const left = String(base || "").replace(/\/+$/, "");
    const right = String(name || "").replace(/^\/+/, "");
    if (!left) {
        return right;
    }
    if (!right) {
        return left;
    }
    return `${left}/${right}`;
}

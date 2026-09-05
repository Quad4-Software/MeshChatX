// SPDX-License-Identifier: 0BSD

import { MIN_VIRTUAL_DISPLAY_GROUPS, VIRTUAL_ROW_HEIGHT } from "./constants.js";

export { MIN_VIRTUAL_DISPLAY_GROUPS };

export function displayGroupsOldestFirst(displayGroups: unknown[] | null | undefined): unknown[] {
    if (!displayGroups?.length) {
        return [];
    }
    return displayGroups.slice().reverse();
}

export function estimateGroupHeight(entry: unknown): number {
    if (!entry || typeof entry !== "object") {
        return VIRTUAL_ROW_HEIGHT.default;
    }
    const e = entry as {
        type?: string;
        chatItem?: { lxmf_message?: { content?: string; fields?: Record<string, unknown> } };
    };
    if (e.type === "dateDivider") {
        return VIRTUAL_ROW_HEIGHT.dateDivider;
    }
    if (e.type === "imageGroup") {
        return VIRTUAL_ROW_HEIGHT.imageGroup;
    }
    const msg = e.chatItem?.lxmf_message;
    const fields = msg?.fields as
        | {
              image?: unknown;
              file_attachments?: unknown[];
              audio?: unknown;
              telemetry?: unknown;
              telemetry_stream?: unknown;
              commands?: unknown[];
          }
        | undefined;
    if (fields?.image && !fields?.file_attachments?.length && !fields?.audio) {
        return VIRTUAL_ROW_HEIGHT.imageOnly;
    }
    let height = VIRTUAL_ROW_HEIGHT.base;
    const content = (msg?.content || "").trim();
    if (content) {
        height += Math.min(160, Math.ceil(content.length / 40) * 18);
    }
    const fileCount = Array.isArray(fields?.file_attachments) ? fields.file_attachments.length : 0;
    if (fileCount > 0) {
        height += fileCount * 56;
    }
    if (fields?.audio) {
        height += 72;
    }
    if (fields?.telemetry || fields?.telemetry_stream || fields?.commands?.length) {
        height += 48;
    }
    return height;
}

export function findDisplayGroupIndexForMessageHash(groupsOldestFirst: unknown[], hash: string): number {
    if (!groupsOldestFirst?.length || !hash) {
        return -1;
    }
    for (let i = 0; i < groupsOldestFirst.length; i++) {
        const g = groupsOldestFirst[i] as {
            type?: string;
            items?: Array<{ lxmf_message?: { hash?: string } }>;
            chatItem?: { lxmf_message?: { hash?: string } };
        };
        if (!g || typeof g !== "object") {
            continue;
        }
        if (g.type === "dateDivider") {
            continue;
        }
        if (g.type === "imageGroup" && Array.isArray(g.items)) {
            if (g.items.some((it) => it?.lxmf_message?.hash === hash)) {
                return i;
            }
        } else if (g.type === "single" && g.chatItem?.lxmf_message?.hash === hash) {
            return i;
        }
    }
    return -1;
}

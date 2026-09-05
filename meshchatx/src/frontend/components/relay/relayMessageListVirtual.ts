// SPDX-License-Identifier: 0BSD

export const MIN_VIRTUAL_RELAY_ENTRIES = 150;

interface RelayMessage {
    text?: string;
    [key: string]: unknown;
}

interface RelayEntry {
    type?: string;
    msg?: RelayMessage;
    [key: string]: unknown;
}

export function estimateRelayEntryHeight(entry: unknown): number {
    if (!entry || typeof entry !== "object") {
        return 28;
    }
    const relayEntry = entry as RelayEntry;
    if (relayEntry.type === "dateDivider") {
        return 44;
    }
    if (relayEntry.type === "presenceGroup") {
        return 28;
    }
    const text = typeof relayEntry.msg?.text === "string" ? relayEntry.msg.text : "";
    let height = 32;
    if (text) {
        const lines = text.split("\n").reduce((sum, line) => sum + Math.max(1, Math.ceil(line.length / 72)), 0);
        height += Math.max(0, lines - 1) * 20;
    }
    return height;
}

export function findRelayEntryIndexForMessageKey(
    entries: RelayEntry[],
    key: string,
    keyFn: (msg: RelayMessage) => string
): number {
    if (!entries?.length || !key || typeof keyFn !== "function") {
        return -1;
    }
    for (let i = 0; i < entries.length; i++) {
        const entry = entries[i];
        if (entry?.type === "message" && entry.msg && keyFn(entry.msg) === key) {
            return i;
        }
    }
    return -1;
}

// SPDX-License-Identifier: 0BSD AND MIT

/**
 * Unjoined public rooms for the Available Rooms sidebar.
 *
 * Oracle: entries in availableRooms whose names are not in knownRooms,
 * sorted by room name.
 */
export function unjoinedAvailableRooms(availableRooms, knownRooms, keyedRooms) {
    if (!availableRooms || typeof availableRooms !== "object") {
        return [];
    }
    const known = new Set(Array.isArray(knownRooms) ? knownRooms : []);
    const keyed = new Set(Array.isArray(keyedRooms) ? keyedRooms : []);
    return Object.entries(availableRooms)
        .filter(([name]) => typeof name === "string" && name && !known.has(name))
        .map(([name, topic]) => ({
            name,
            topic: typeof topic === "string" && topic ? topic : null,
            has_key: keyed.has(name),
        }))
        .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Diff two available_rooms snapshots after a hub /list refresh.
 *
 * A full list reply replaces the map. This oracle describes that replace
 * as added, removed, and topic-updated room names.
 */
export function diffAvailableRooms(previous, next) {
    const prev = previous && typeof previous === "object" && !Array.isArray(previous) ? previous : {};
    const nxt = next && typeof next === "object" && !Array.isArray(next) ? next : {};
    const prevKeys = new Set(Object.keys(prev));
    const nextKeys = new Set(Object.keys(nxt));
    const added = [];
    const removed = [];
    const updated = [];
    for (const name of nextKeys) {
        if (!prevKeys.has(name)) {
            added.push(name);
        } else if ((prev[name] || null) !== (nxt[name] || null)) {
            updated.push(name);
        }
    }
    for (const name of prevKeys) {
        if (!nextKeys.has(name)) {
            removed.push(name);
        }
    }
    added.sort();
    removed.sort();
    updated.sort();
    return { added, removed, updated };
}

/**
 * Apply a refreshed hub room-list snapshot.
 *
 * Oracle: the next map fully replaces previous (add, remove, and topic update).
 */
export function applyAvailableRoomsSnapshot(_previous, next) {
    if (!next || typeof next !== "object" || Array.isArray(next)) {
        return {};
    }
    const out: any = {};
    for (const [name, topic] of Object.entries(next)) {
        if (typeof name !== "string" || !name) {
            continue;
        }
        out[name] = typeof topic === "string" && topic ? topic : null;
    }
    return out;
}

// SPDX-License-Identifier: 0BSD AND MIT

export function countRelayMentions(hubs) {
    if (!Array.isArray(hubs)) {
        return 0;
    }
    let total = 0;
    for (const hub of hubs) {
        const rooms = hub?.mention_rooms;
        if (Array.isArray(rooms)) {
            total += rooms.length;
        }
    }
    return total;
}

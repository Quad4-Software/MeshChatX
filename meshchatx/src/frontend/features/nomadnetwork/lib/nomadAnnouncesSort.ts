// SPDX-License-Identifier: 0BSD

import type { NomadNode } from "./types.js";

function parseTs(value: string | undefined | null): number {
    if (!value) return 0;
    const ts = Date.parse(value);
    return Number.isFinite(ts) ? ts : 0;
}

interface SortableNode {
    node: NomadNode;
    name: string;
    created: number;
    updated: number;
    count: number;
}

function toSortable(n: NomadNode): SortableNode {
    return {
        node: n,
        name: n.custom_display_name || n.display_name || "",
        created: parseTs(n.created_at) || parseTs(n.updated_at),
        updated: parseTs(n.updated_at),
        count: Number(n.announce_count) || 0,
    };
}

/** Order announces list nodes by the persisted sidebar sort mode. */
export function sortAnnouncesNodes(nodes: Record<string, NomadNode>, sort: string): NomadNode[] {
    const keyed = Object.values(nodes).map(toSortable);
    if (sort === "name") {
        keyed.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sort === "most_announced") {
        keyed.sort((a, b) => b.count - a.count || b.created - a.created);
    } else if (sort === "newest_discovered") {
        // first-seen wins, so a re-announce of a known node does not jump back to the top.
        keyed.sort((a, b) => b.created - a.created);
    } else {
        // last_announced
        keyed.sort((a, b) => b.updated - a.updated);
    }
    return keyed.map((k) => k.node);
}

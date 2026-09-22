// SPDX-License-Identifier: 0BSD

import type { NomadNode } from "./types.js";

function createdTs(n: NomadNode): number {
    const ts = new Date(n.created_at || n.updated_at || "").getTime();
    return Number.isFinite(ts) ? ts : 0;
}

/** Order announces list nodes by the persisted sidebar sort mode. */
export function sortAnnouncesNodes(nodes: Record<string, NomadNode>, sort: string): NomadNode[] {
    const list = Object.values(nodes).slice();
    if (sort === "name") {
        return list.sort((a, b) =>
            (a.custom_display_name || a.display_name || "").localeCompare(b.custom_display_name || b.display_name || "")
        );
    }
    if (sort === "most_announced") {
        return list.sort(
            (a, b) => (Number(b.announce_count) || 0) - (Number(a.announce_count) || 0) || createdTs(b) - createdTs(a)
        );
    }
    if (sort === "newest_discovered") {
        // first-seen wins, so a re-announce of a known node does not jump back to the top.
        return list.sort((a, b) => createdTs(b) - createdTs(a));
    }
    // last_announced
    return list.sort((a, b) => {
        const ta = a.updated_at ? new Date(a.updated_at).getTime() : 0;
        const tb = b.updated_at ? new Date(b.updated_at).getTime() : 0;
        return tb - ta;
    });
}

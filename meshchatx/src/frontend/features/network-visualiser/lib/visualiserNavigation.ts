// SPDX-License-Identifier: 0BSD

/**
 * Open a visualiser announce node in the matching app surface.
 * lxmf.delivery goes to messages. nomadnetwork.node opens NomadNet.
 */

import { navigate } from "../../../shell/hashRouter.js";
import type { AnnounceEntry } from "./types.js";

export type AnnounceLike = {
    destination_hash?: string | null;
    destinationHash?: string | null;
    aspect?: string | null;
    [key: string]: unknown;
};

export function resolveAnnounceDestinationHash(announce: AnnounceLike | null | undefined, fallbackHash = ""): string {
    if (!announce) {
        return String(fallbackHash || "").trim();
    }
    const fromAnnounce = announce.destination_hash || announce.destinationHash || "";
    return String(fromAnnounce || fallbackHash || "").trim();
}

/**
 * Attach announce payloads onto graph nodes so click/activate handlers can read aspect.
 */
export function attachAnnounceMetaToNodes(
    nodes: Array<{ id?: string; _announce?: AnnounceEntry | null; [key: string]: unknown }>,
    announces: Record<string, AnnounceEntry | undefined> | null | undefined
): void {
    if (!Array.isArray(nodes) || !announces) {
        return;
    }
    for (const node of nodes) {
        if (!node?.id) {
            continue;
        }
        const announce = announces[node.id];
        if (announce) {
            node._announce = announce;
        }
    }
}

/**
 * Navigate from a visualiser announce activation (WebGL click or vis double-click).
 */
export function openAnnounceDestination(announce: AnnounceLike | null | undefined, fallbackHash = ""): void {
    const destinationHash = resolveAnnounceDestinationHash(announce, fallbackHash);
    if (!destinationHash) {
        return;
    }
    const aspect = String(announce?.aspect || "");
    if (aspect === "lxmf.delivery") {
        void navigate({ name: "messages", params: { destinationHash } });
        return;
    }
    if (aspect === "nomadnetwork.node") {
        void navigate({
            name: "nomadnetwork",
            params: { destinationHash },
            query: { newTab: "1" },
        });
    }
}

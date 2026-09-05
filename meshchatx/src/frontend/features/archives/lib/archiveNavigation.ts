// SPDX-License-Identifier: 0BSD

import { handleRichHtmlLinkClick } from "../../../js/NomadRichHtmlLinks.js";
import type { ArchiveItem } from "./types.js";

/** Router abstraction allowing Vue router or hash location fallback */
export interface RouterLike {
    push?: (location: {
        name: string;
        params?: Record<string, unknown>;
        query?: Record<string, unknown>;
    }) => void;
}

/** Open archive in NomadNet browser view */
export function openInNomadnet(archive: ArchiveItem, router?: RouterLike): void {
    if (router?.push) {
        router.push({
            name: "nomadnetwork",
            params: { destinationHash: archive.destination_hash },
            query: {
                path: archive.page_path,
                archive_id: archive.id,
            },
        });
        return;
    }
    const params = new URLSearchParams();
    if (archive.page_path) {
        params.set("path", archive.page_path);
    }
    if (archive.id != null) {
        params.set("archive_id", String(archive.id));
    }
    const qs = params.toString() ? `?${params.toString()}` : "";
    window.location.hash = `#/nomadnetwork/${encodeURIComponent(archive.destination_hash)}${qs}`;
}

/** Intercept clicks on rendered Nomad archive content */
export function handleArchiveContentClick(event: MouseEvent, router?: RouterLike): void {
    handleRichHtmlLinkClick(event, {
        onNomadUrl: (url: string) => {
            const [hash, ...pathParts] = url.split(":");
            const path = pathParts.join(":");
            if (router?.push) {
                router.push({
                    name: "nomadnetwork",
                    params: { destinationHash: hash },
                    query: { path: path },
                });
                return;
            }
            const params = new URLSearchParams(path ? { path } : {});
            const qs = params.toString() ? `?${params.toString()}` : "";
            window.location.hash = `#/nomadnetwork/${encodeURIComponent(hash)}${qs}`;
        },
        onOpenNode: (destination: string) => {
            const [hash, ...pathParts] = destination.split(":");
            const path = pathParts.join(":") || "/page/index.mu";
            if (router?.push) {
                router.push({
                    name: "nomadnetwork",
                    params: { destinationHash: hash },
                    query: { path: path },
                });
                return;
            }
            const params = new URLSearchParams({ path });
            window.location.hash = `#/nomadnetwork/${encodeURIComponent(hash)}?${params.toString()}`;
        },
    });
}

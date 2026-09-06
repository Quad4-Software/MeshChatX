// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import type { NomadFavourite, NomadNode } from "./types.js";

export type NomadNodesFetchResult = {
    nodes: Record<string, NomadNode>;
    totalNodesCount: number;
    hasMoreNodes: boolean;
};

export async function fetchNomadNodes(options: {
    append?: boolean;
    existingNodes: Record<string, NomadNode>;
    searchTerm?: string;
}): Promise<NomadNodesFetchResult | null> {
    const api = (window as any).api;
    if (!api) return null;
    const append = options.append === true;
    try {
        const offset = append ? Object.keys(options.existingNodes).length : 0;
        const res = await api.get("/api/v1/announces", {
            params: {
                aspect: "nomadnetwork.node",
                limit: 50,
                offset,
                search: options.searchTerm || undefined,
            },
        });
        const list: NomadNode[] = res.data?.announces || res.data?.nodes || res.data || [];
        const map: Record<string, NomadNode> = append ? { ...options.existingNodes } : {};
        for (const n of list) {
            if (n.destination_hash) map[n.destination_hash] = n;
        }
        return {
            nodes: map,
            totalNodesCount: Number(res.data?.total_count ?? Object.keys(map).length),
            hasMoreNodes: list.length >= 50,
        };
    } catch {
        return null;
    }
}

export async function fetchNomadFavourites(): Promise<NomadFavourite[]> {
    const api = (window as any).api;
    if (!api) return [];
    try {
        const res = await api.get("/api/v1/favourites");
        return res.data?.favourites || res.data || [];
    } catch {
        return [];
    }
}

export async function addNomadFavourite(node: NomadNode): Promise<boolean> {
    const api = (window as any).api;
    if (!api || !node.destination_hash) return false;
    try {
        await api.post("/api/v1/favourites", {
            destination_hash: node.destination_hash,
            display_name: node.custom_display_name || node.display_name,
            aspect: "nomadnetwork.node",
        });
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message ?? t("nomadnet.add_favourite"));
        return false;
    }
}

export async function removeNomadFavourite(fav: NomadFavourite): Promise<boolean> {
    const api = (window as any).api;
    if (!api || !fav.destination_hash) return false;
    if (!(await DialogUtils.confirm(t("nomadnet.remove_favourite_confirm", { name: fav.display_name })))) {
        return false;
    }
    try {
        await api.delete(`/api/v1/favourites/${fav.destination_hash}`);
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message ?? t("nomadnet.remove_favourite"));
        return false;
    }
}

export async function renameNomadFavourite(fav: NomadFavourite): Promise<boolean> {
    const api = (window as any).api;
    if (!api || !fav.destination_hash) return false;
    const newName = await DialogUtils.prompt(
        t("nomadnet.rename_favourite_prompt"),
        fav.custom_display_name || fav.display_name || ""
    );
    if (newName === null) return false;
    try {
        await api.put(`/api/v1/favourites/${fav.destination_hash}`, {
            custom_display_name: newName.trim() || null,
        });
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message ?? t("nomadnet.rename_favourite_prompt"));
        return false;
    }
}

export async function toggleNomadIdentifyOnConnect(hash: string, favourites: NomadFavourite[]): Promise<boolean> {
    if (!hash) return false;
    const api = (window as any).api;
    if (!api) return false;
    const existing = favourites.find((f) => f.destination_hash === hash);
    const currentlyOn = Boolean(existing?.identify_on_connect);
    const enable = !currentlyOn;
    try {
        if (enable) {
            if (!(await DialogUtils.confirm(t("nomadnet.identify_confirm")))) {
                return false;
            }
        }
        await api.post(`/api/v1/favourites/${hash}/identify-on-connect`, {
            enabled: enable,
            display_name: existing?.custom_display_name || existing?.display_name || t("nomadnet.unknown_node"),
            aspect: "nomadnetwork.node",
        });
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message ?? t("nomadnet.identify_on_connect_failed"));
        return false;
    }
}

export function mergeNomadAnnounceIntoNodes(
    nodes: Record<string, NomadNode>,
    json: Record<string, unknown>
): Record<string, NomadNode> | null {
    const announce = (json.announce || json) as NomadNode & { aspect?: string };
    if (announce?.aspect !== "nomadnetwork.node" || !announce.destination_hash) {
        return null;
    }
    return {
        ...nodes,
        [announce.destination_hash]: {
            ...nodes[announce.destination_hash],
            ...announce,
        },
    };
}

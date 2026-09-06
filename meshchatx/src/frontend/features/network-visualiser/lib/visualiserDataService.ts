// SPDX-License-Identifier: 0BSD

import {
    ANNOUNCE_HASH_CHUNK_SIZE,
    VIZ_ANNOUNCE_ASPECTS,
    VIZ_ANNOUNCE_SOFT_CAP,
    VIZ_PATH_TABLE_SOFT_CAP,
    pathHashesWithinHopFilter,
    pickAdaptiveFetchConcurrency,
} from "../../../js/networkVisualiserPerf.js";
import { loadVisualiserCache, saveVisualiserCache } from "../../../js/networkVisualiserCache.js";
import type {
    PathTableEntry,
    AnnounceEntry,
    InterfaceEntry,
    DiscoveredInterfaceEntry,
    DiscoveredActiveEntry,
    ConversationEntry,
    VisualiserConfig,
} from "./types.js";

export interface BasicVisualiserData {
    config: VisualiserConfig | null;
    interfaces: InterfaceEntry[];
    discoveredInterfaces: DiscoveredInterfaceEntry[];
    conversations: Record<string, ConversationEntry>;
}

export interface PathTableFetchResult {
    pathTable: PathTableEntry[];
    totalCount: number;
}

export interface VisualiserDataState {
    interfaces: InterfaceEntry[];
    discoveredInterfaces: DiscoveredInterfaceEntry[];
    discoveredActive: DiscoveredActiveEntry[];
    announces: AnnounceEntry[];
    paths: PathTableEntry[];
    conversations: ConversationEntry[];
    config: VisualiserConfig | null;
    isLoading: boolean;
    hasLoadedInitially: boolean;
}

export async function fetchBasicVisualiserData(signal?: AbortSignal): Promise<BasicVisualiserData> {
    if (typeof window === "undefined" || !window.api) {
        return {
            config: null,
            interfaces: [],
            discoveredInterfaces: [],
            conversations: {},
        };
    }

    try {
        const [cfgRes, ifaceRes, convRes, discRes] = await Promise.all([
            window.api.get("/api/v1/config", { signal }).catch(() => null),
            window.api.get("/api/v1/reticulum/interfaces", { signal }).catch(() => null),
            window.api.get("/api/v1/lxmf/conversations", { signal, params: { limit: 2000 } }).catch(() => null),
            window.api.get("/api/v1/reticulum/discovered-interfaces", { signal }).catch(() => null),
        ]);

        const config = (cfgRes as { data?: { config?: VisualiserConfig } } | null)?.data?.config || null;
        const interfaces = (ifaceRes as { data?: { interfaces?: InterfaceEntry[] } } | null)?.data?.interfaces || [];
        const discoveredInterfaces =
            (discRes as { data?: { interfaces?: DiscoveredInterfaceEntry[] } } | null)?.data?.interfaces || [];
        const rawConvs =
            (convRes as { data?: { conversations?: ConversationEntry[] } } | null)?.data?.conversations || [];

        const conversations: Record<string, ConversationEntry> = {};
        for (const c of rawConvs) {
            if (c?.destination_hash) {
                conversations[c.destination_hash] = c;
            }
        }

        return {
            config,
            interfaces,
            discoveredInterfaces,
            conversations,
        };
    } catch (e) {
        if (window.api?.isCancel?.(e)) {
            return { config: null, interfaces: [], discoveredInterfaces: [], conversations: {} };
        }
        console.error("Failed to fetch basic visualiser data", e);
        return { config: null, interfaces: [], discoveredInterfaces: [], conversations: {} };
    }
}

export async function fetchPathTableBatches(options: {
    signal?: AbortSignal;
    hopMaxFilter?: number | null;
    onProgress?: (loaded: number, total: number, batch: number, totalBatches: number) => void;
}): Promise<PathTableFetchResult> {
    if (typeof window === "undefined" || !window.api) {
        return { pathTable: [], totalCount: 0 };
    }

    const { signal, hopMaxFilter, onProgress } = options;
    const limit = 500;
    const softCap = VIZ_PATH_TABLE_SOFT_CAP;
    const pathTable: PathTableEntry[] = [];

    try {
        const res = (await window.api.get("/api/v1/path-table", {
            signal,
            params: { offset: 0, limit, max_hops: hopMaxFilter ?? undefined },
        })) as { data?: { path_table?: PathTableEntry[]; total_count?: number } } | null;

        const initialRows = res?.data?.path_table || [];
        pathTable.push(...initialRows);
        const totalCount = res?.data?.total_count || initialRows.length;
        const remaining = Math.max(0, totalCount - limit);
        const totalBatches = Math.ceil(remaining / limit);
        let currentBatch = 0;

        onProgress?.(pathTable.length, totalCount, currentBatch, totalBatches);

        if (totalCount > limit) {
            for (let i = limit; i < totalCount && i < softCap; i += limit) {
                if (signal?.aborted) {
                    return { pathTable, totalCount };
                }
                currentBatch++;
                const batchRes = (await window.api.get("/api/v1/path-table", {
                    signal,
                    params: { offset: i, limit, max_hops: hopMaxFilter ?? undefined },
                })) as { data?: { path_table?: PathTableEntry[] } } | null;

                const rows = batchRes?.data?.path_table || [];
                const room = softCap - pathTable.length;
                if (room <= 0) {
                    break;
                }
                pathTable.push(...rows.slice(0, room));
                onProgress?.(pathTable.length, totalCount, currentBatch, totalBatches);
            }
        }

        return { pathTable, totalCount };
    } catch (e) {
        if (window.api?.isCancel?.(e)) {
            return { pathTable, totalCount: pathTable.length };
        }
        console.error("Failed to fetch path table batch", e);
        return { pathTable, totalCount: pathTable.length };
    }
}

export async function fetchAnnouncesForHashes(options: {
    hashes: string[];
    signal?: AbortSignal;
    concurrency?: number;
    onAnnouncesReceived?: (announces: AnnounceEntry[]) => void;
}): Promise<AnnounceEntry[]> {
    const { hashes, signal, concurrency = pickAdaptiveFetchConcurrency(), onAnnouncesReceived } = options;
    if (!Array.isArray(hashes) || hashes.length === 0 || typeof window === "undefined" || !window.api) {
        return [];
    }

    const collected: AnnounceEntry[] = [];
    for (let i = 0; i < hashes.length; i += ANNOUNCE_HASH_CHUNK_SIZE * concurrency) {
        if (signal?.aborted) {
            return collected;
        }
        const offsets: number[] = [];
        for (let j = 0; j < concurrency && i + j * ANNOUNCE_HASH_CHUNK_SIZE < hashes.length; j++) {
            offsets.push(i + j * ANNOUNCE_HASH_CHUNK_SIZE);
        }
        const promises = offsets.map((start) => {
            const chunk = hashes.slice(start, start + ANNOUNCE_HASH_CHUNK_SIZE);
            return window.api.post(
                "/api/v1/announces/query",
                {
                    destination_hashes: chunk,
                    aspects: VIZ_ANNOUNCE_ASPECTS,
                },
                { signal }
            );
        });

        const responses = (await Promise.all(promises)) as Array<{
            data?: { announces?: AnnounceEntry[] };
        } | null>;
        for (const resp of responses) {
            const rows = resp?.data?.announces || [];
            collected.push(...rows);
            onAnnouncesReceived?.(rows);
        }
    }
    return collected;
}

export async function ensureAnnouncesForPathHashes(options: {
    pathTable: PathTableEntry[];
    hopMaxFilter: number | null;
    announces: Record<string, AnnounceEntry>;
    signal?: AbortSignal;
    concurrency?: number;
    reset?: boolean;
    onProgress?: (count: number) => void;
}): Promise<Record<string, AnnounceEntry>> {
    const { pathTable, hopMaxFilter, signal, concurrency, reset = false, onProgress } = options;
    let targetAnnounces: Record<string, AnnounceEntry> = reset ? {} : { ...options.announces };

    const needed = pathHashesWithinHopFilter(pathTable, hopMaxFilter);
    const missing = needed.filter((hash) => !targetAnnounces[hash]);

    if (missing.length > 0) {
        await fetchAnnouncesForHashes({
            hashes: missing,
            signal,
            concurrency,
            onAnnouncesReceived: (rows) => {
                for (const announce of rows) {
                    if (announce?.destination_hash) {
                        targetAnnounces[announce.destination_hash] = announce;
                    }
                }
                onProgress?.(Object.keys(targetAnnounces).length);
            },
        });
    }

    if (needed.length > 0) {
        const neededSet = new Set(needed);
        for (const hash of Object.keys(targetAnnounces)) {
            if (!neededSet.has(hash)) {
                delete targetAnnounces[hash];
            }
        }
    }

    const announceKeys = Object.keys(targetAnnounces);
    if (announceKeys.length > VIZ_ANNOUNCE_SOFT_CAP) {
        const neededSet = new Set(needed);
        const extras = announceKeys.filter((hash) => !neededSet.has(hash));
        const overflow = announceKeys.length - VIZ_ANNOUNCE_SOFT_CAP;
        for (const hash of extras.slice(0, overflow)) {
            delete targetAnnounces[hash];
        }
    }

    return targetAnnounces;
}

export async function loadCachedVisualiserGraph(identityHash: string) {
    if (!identityHash) {
        return null;
    }
    return loadVisualiserCache(identityHash);
}

export async function saveCachedVisualiserGraph(
    identityHash: string,
    pathTable: PathTableEntry[],
    announces: Record<string, AnnounceEntry>,
    positions: Record<string, { x: number; y: number }>
): Promise<boolean> {
    if (!identityHash) {
        return false;
    }
    return saveVisualiserCache({
        identityHash,
        pathTable,
        announces,
        positions,
        pathSoftCap: VIZ_PATH_TABLE_SOFT_CAP,
        announceSoftCap: VIZ_ANNOUNCE_SOFT_CAP,
    });
}

export async function fetchVisualiserData(): Promise<Omit<VisualiserDataState, "isLoading" | "hasLoadedInitially">> {
    if (typeof window === "undefined" || !window.api) {
        return {
            interfaces: [],
            discoveredInterfaces: [],
            discoveredActive: [],
            announces: [],
            paths: [],
            conversations: [],
            config: null,
        };
    }

    const [interfacesRes, discoveredRes, announcesRes, pathTableRes, conversationsRes, configRes] = await Promise.all([
        window.api.get("/api/v1/reticulum/interfaces").catch(() => null),
        window.api.get("/api/v1/reticulum/discovered-interfaces").catch(() => null),
        window.api.get("/api/v1/announces", { params: { limit: 500 } }).catch(() => null),
        window.api.get("/api/v1/path-table").catch(() => null),
        window.api.get("/api/v1/lxmf/conversations").catch(() => null),
        window.api.get("/api/v1/config").catch(() => null),
    ]);

    const interfaces: InterfaceEntry[] =
        (interfacesRes as { data?: { interfaces?: InterfaceEntry[] } } | null)?.data?.interfaces || [];
    const discoveredInterfaces: DiscoveredInterfaceEntry[] =
        (discoveredRes as { data?: { interfaces?: DiscoveredInterfaceEntry[] } } | null)?.data?.interfaces || [];
    const discoveredActive: DiscoveredActiveEntry[] = [];
    const announces: AnnounceEntry[] =
        (announcesRes as { data?: { announces?: AnnounceEntry[] } } | null)?.data?.announces || [];
    const paths: PathTableEntry[] =
        (pathTableRes as { data?: { path_table?: PathTableEntry[] } } | null)?.data?.path_table || [];
    const conversations: ConversationEntry[] =
        (conversationsRes as { data?: { conversations?: ConversationEntry[] } } | null)?.data?.conversations || [];
    const config: VisualiserConfig | null =
        (configRes as { data?: { config?: VisualiserConfig } } | null)?.data?.config || null;

    return {
        interfaces,
        discoveredInterfaces,
        discoveredActive,
        announces,
        paths,
        conversations,
        config,
    };
}

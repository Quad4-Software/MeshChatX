// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import {
    DEFAULT_REMOTE_TIMEOUT,
    PATH_STATE_RESPONSIVE,
    PATH_STATE_UNRESPONSIVE,
    DESTINATION_HASH_HEX_LENGTH,
} from "./constants.js";
import type { PathEntry, RateEntry, RemoteQueryParams, PathQueryOptions } from "./types.js";

/** Build remote query params if a remote hash is provided */
export function buildRemoteQueryParams(
    remoteHash?: string,
    identityPath?: string,
    remoteTimeout?: number
): RemoteQueryParams {
    const remote = (remoteHash || "").trim();
    if (!remote) {
        return {};
    }
    const params: RemoteQueryParams = { remote };
    if (identityPath) {
        params.identity_path = identityPath;
    }
    if (remoteTimeout != null && remoteTimeout > 0) {
        params.timeout = remoteTimeout;
    }
    return params;
}

/** Parse and validate hops filter value */
export function parseHops(filterHops: unknown): number | undefined {
    if (filterHops === null || filterHops === undefined || filterHops === "") {
        return undefined;
    }
    const parsed = Number(filterHops);
    if (!Number.isFinite(parsed)) {
        throw new Error("Invalid hops");
    }
    return parsed;
}

/** Build full path table query parameters */
export function buildPathQueryParams(options: PathQueryOptions): Record<string, unknown> {
    const hops = parseHops(options.filterHops);
    const remoteParams = buildRemoteQueryParams(
        options.remoteHash,
        options.identityPath,
        options.remoteTimeout ?? DEFAULT_REMOTE_TIMEOUT
    );
    const params: Record<string, unknown> = {
        page: options.currentPage,
        limit: options.itemsPerPage,
        ...remoteParams,
    };
    if (options.searchQuery && options.searchQuery.trim()) {
        params.search = options.searchQuery.trim();
    }
    if (options.filterInterface) {
        params.interface = options.filterInterface;
    }
    if (hops !== undefined) {
        params.hops = hops;
    }
    return params;
}

/** Extract sorted unique interface names from local and discovered interfaces */
export function extractInterfaceNames(
    interfacesRes?: { interfaces?: Record<string, unknown> } | null,
    discRes?: { active?: Array<{ name?: string }>; interfaces?: Array<{ name?: string } | string> } | null
): string[] {
    const nameSet = new Set<string>();
    const ifaces = interfacesRes?.interfaces;
    if (ifaces && typeof ifaces === "object") {
        for (const name of Object.keys(ifaces)) {
            if (name) {
                nameSet.add(name);
            }
        }
    }
    for (const row of discRes?.active || []) {
        if (row?.name) {
            nameSet.add(String(row.name));
        }
    }
    for (const d of discRes?.interfaces || []) {
        if (d && typeof d === "object" && d.name) {
            nameSet.add(String(d.name));
        } else if (typeof d === "string" && d) {
            nameSet.add(d);
        }
    }
    return Array.from(nameSet).sort();
}

/** Calculate hourly announce rate */
export function calculateRate(rate?: Partial<RateEntry> | null): string {
    const timestamps = rate?.timestamps || [];
    if (timestamps.length === 0) {
        return "0.00";
    }
    const startTs = timestamps[0];
    const span = Math.max(Date.now() / 1000 - startTs, 3600.0);
    const spanHours = span / 3600.0;
    return (timestamps.length / spanHours).toFixed(2);
}

/** Return CSS badge classes for path responsive state */
export function getStateColor(state?: number): string {
    if (state === PATH_STATE_RESPONSIVE) {
        return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300";
    }
    if (state === PATH_STATE_UNRESPONSIVE) {
        return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
    }
    return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";
}

/** Return text label for path responsive state */
export function getStateText(state?: number): string {
    if (state === PATH_STATE_RESPONSIVE) {
        return "RESPONSIVE";
    }
    if (state === PATH_STATE_UNRESPONSIVE) {
        return "UNRESPONSIVE";
    }
    return "UNKNOWN";
}

/** Format unix timestamp in seconds as local date string */
export function formatDate(ts?: number): string {
    if (!ts) {
        return "Unknown";
    }
    return new Date(ts * 1000).toLocaleString();
}

/** Format unix timestamp in seconds as relative elapsed time */
export function formatTimeAgo(ts?: number): string {
    if (!ts) {
        return "Unknown";
    }
    const secondsAgo = Math.max(0, Math.floor(Date.now() / 1000 - ts));
    return Utils.formatSeconds(secondsAgo);
}

/** Truncate hash for compact display */
export function shortHash(hash?: string): string {
    if (!hash || hash.length < 10) {
        return hash || "";
    }
    return `${hash.slice(0, 8)}…`;
}

/** Validate whether string is a 32 char hex hash */
export function isValidDestinationHash(hash?: string): boolean {
    if (!hash || typeof hash !== "string") {
        return false;
    }
    const trimmed = hash.trim();
    return trimmed.length === DESTINATION_HASH_HEX_LENGTH && /^[0-9a-fA-F]{32}$/.test(trimmed);
}

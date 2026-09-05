// SPDX-License-Identifier: 0BSD

/** Path entry in the Reticulum path table */
export type PathEntry = {
    hash: string;
    hops: number;
    via: string;
    interface: string;
    timestamp?: number;
    expires?: number;
    announce_hash?: string;
    state?: number;
    [key: string]: unknown;
};

/** Announce rate tracking entry */
export type RateEntry = {
    hash: string;
    last: number;
    timestamps: number[];
    rate_violations: number;
    blocked_until: number;
    [key: string]: unknown;
};

/** Management identity record */
export type ManagementIdentity = {
    name: string;
    hash: string;
    path: string;
    [key: string]: unknown;
};

/** Remote query parameters */
export type RemoteQueryParams = {
    remote?: string;
    identity_path?: string;
    timeout?: number;
};

/** Options for querying path table */
export type PathQueryOptions = {
    searchQuery?: string;
    filterInterface?: string;
    filterHops?: number | string | null;
    currentPage: number;
    itemsPerPage: number;
    remoteHash?: string;
    identityPath?: string;
    remoteTimeout?: number;
};

/** Path table API response */
export type PathTableResponse = {
    table: PathEntry[];
    total: number;
    responsive: number;
    unresponsive: number;
    remote?: string;
    [key: string]: unknown;
};

/** Announce rates API response */
export type RateTableResponse = {
    rates: RateEntry[];
    remote?: string;
    [key: string]: unknown;
};

/** Active tab selection */
export type RNPathTab = "table" | "rates" | "actions";

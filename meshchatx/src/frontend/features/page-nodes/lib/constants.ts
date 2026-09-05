// SPDX-License-Identifier: 0BSD

/** Default periodic announce interval in seconds (15 minutes) */
export const DEFAULT_ANNOUNCE_INTERVAL_SECONDS = 900;

/** Minimum allowed announce interval in minutes */
export const ANNOUNCE_INTERVAL_MIN_MINUTES = 1;

/** Maximum allowed announce interval in minutes (24 hours) */
export const ANNOUNCE_INTERVAL_MAX_MINUTES = 1440;

/** API base endpoint for page nodes */
export const PAGE_NODES_API_BASE = "/api/v1/page-nodes";

/** Detail sub-tabs */
export const PAGE_NODE_TABS = {
    PAGES: "pages",
    FILES: "files",
} as const;

export type PageNodeDetailTab = (typeof PAGE_NODE_TABS)[keyof typeof PAGE_NODE_TABS];

// SPDX-License-Identifier: 0BSD

/** Performance and traffic statistics for a hosted page node */
export interface PageNodeStats {
    pages_served: number;
    files_served: number;
    links_established: number;
}

/** Page document descriptor */
export interface PageNodePageItem {
    name: string;
    executable?: boolean;
}

/** Static file descriptor */
export interface PageNodeFileItem {
    name: string;
    size: number;
}

/** Hosted Reticulum page node */
export interface PageNode {
    node_id: string;
    name: string;
    running: boolean;
    destination_hash?: string | null;
    announce_enabled?: boolean;
    announce_interval_seconds?: number | null;
    executable_pages_enabled?: boolean;
    uptime_seconds?: number | null;
    unique_connections?: number;
    last_announced_at?: number | null;
    stats?: PageNodeStats;
    pages: PageNodePageItem[];
    files: PageNodeFileItem[];
}

/** Announce and runtime execution settings form */
export interface AnnounceSettingsForm {
    announce_enabled: boolean;
    announce_interval_seconds: number;
    executable_pages_enabled: boolean;
}

/** Page content response from backend */
export interface PageContentResponse {
    name: string;
    content: string;
    executable?: boolean;
}

/** Node start action response */
export interface PageNodeStartResponse {
    destination_hash?: string;
    message?: string;
}

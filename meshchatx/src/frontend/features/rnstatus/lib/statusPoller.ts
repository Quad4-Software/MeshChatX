// SPDX-License-Identifier: 0BSD

import type { ManagementIdentityItem, RNStatusQueryParams, RNStatusResponse } from "./types.js";

/**
 * Fetch Reticulum network status from backend API.
 */
export async function fetchRNStatus(params: RNStatusQueryParams): Promise<RNStatusResponse> {
    const queryParams: Record<string, unknown> = {
        include_link_stats: params.include_link_stats,
        show_all: params.show_all,
    };
    if (params.sorting) {
        queryParams.sorting = params.sorting;
    }
    const remote = (params.remote || "").trim();
    if (remote) {
        queryParams.remote = remote;
        if (params.identity_path) {
            queryParams.identity_path = params.identity_path;
        }
        if (params.timeout) {
            queryParams.timeout = params.timeout;
        }
    }
    const response = await window.api.get("/api/v1/rnstatus", { params: queryParams });
    return (response?.data || {}) as RNStatusResponse;
}

/**
 * Fetch management identities list.
 */
export async function fetchManagementIdentities(): Promise<ManagementIdentityItem[]> {
    const response = await window.api.get("/api/v1/reticulum/management-identities");
    const data = response?.data as { identities?: ManagementIdentityItem[] } | undefined;
    const list = data?.identities;
    return Array.isArray(list) ? list : [];
}

/**
 * Create a new management identity.
 */
export async function createManagementIdentity(name: string): Promise<ManagementIdentityItem | null> {
    const response = await window.api.post("/api/v1/reticulum/management-identities", {
        name: name.trim(),
    });
    const data = response?.data as { identity?: ManagementIdentityItem } | undefined;
    return (data?.identity as ManagementIdentityItem) || null;
}

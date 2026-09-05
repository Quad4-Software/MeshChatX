// SPDX-License-Identifier: 0BSD

import { postDestinationPath } from "../../../js/reticulumPathfinding.js";
import {
    ANNOUNCE_API_ENDPOINT,
    CONFIG_API_ENDPOINT,
    PATH_TIMEOUT_SECONDS,
    PROPAGATION_NODE_RESTART_ENDPOINT,
    PROPAGATION_NODE_STOP_ENDPOINT,
    PROPAGATION_NODES_API_BASE,
} from "./constants.js";
import type { NodePathInfo, PropagationNodeItem, PropagationNodesConfig } from "./types.js";

/**
 * Fetch current application configuration.
 */
export async function fetchPropagationConfig(): Promise<PropagationNodesConfig> {
    const response = await window.api.get(CONFIG_API_ENDPOINT);
    const data = response.data as { config?: PropagationNodesConfig } | undefined;
    return (data?.config || {}) as PropagationNodesConfig;
}

/**
 * Patch application configuration.
 */
export async function updatePropagationConfig(patch: Partial<PropagationNodesConfig>): Promise<PropagationNodesConfig> {
    const response = await window.api.patch(CONFIG_API_ENDPOINT, patch);
    const data = response.data as { config?: PropagationNodesConfig } | undefined;
    return (data?.config || {}) as PropagationNodesConfig;
}

/**
 * Fetch discovered propagation nodes.
 */
export async function fetchPropagationNodes(limit = 500): Promise<PropagationNodeItem[]> {
    const response = await window.api.get(PROPAGATION_NODES_API_BASE, {
        params: { limit },
    });
    const data = response.data as { lxmf_propagation_nodes?: PropagationNodeItem[] } | undefined;
    return Array.isArray(data?.lxmf_propagation_nodes) ? data.lxmf_propagation_nodes : [];
}

/**
 * Request path for a destination hash.
 */
export async function requestNodePath(hash: string): Promise<NodePathInfo | null> {
    const clean = (hash || "").trim();
    if (!clean) return null;
    try {
        const response = await postDestinationPath(window.api, clean, {
            timeout: PATH_TIMEOUT_SECONDS,
        });
        const data = response.data as { path?: NodePathInfo } | undefined;
        return data?.path || null;
    } catch {
        return null;
    }
}

/**
 * Trigger immediate reticulum announce.
 */
export async function triggerAnnounce(): Promise<void> {
    await window.api.get(ANNOUNCE_API_ENDPOINT);
}

/**
 * Stop local propagation node.
 */
export async function stopLocalNode(): Promise<void> {
    await window.api.post(PROPAGATION_NODE_STOP_ENDPOINT);
}

/**
 * Restart local propagation node.
 */
export async function restartLocalNode(): Promise<void> {
    await window.api.post(PROPAGATION_NODE_RESTART_ENDPOINT);
}

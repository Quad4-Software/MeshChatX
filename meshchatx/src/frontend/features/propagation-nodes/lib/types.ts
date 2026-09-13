// SPDX-License-Identifier: 0BSD

export interface PropagationNodeStats {
    is_running?: boolean;
    uptime_seconds?: number;
    total_peers?: number;
    messagestore_count?: number;
    client_messages_received?: number;
    client_messages_served?: number;
    messagestore_bytes?: number;
    messagestore_limit_bytes?: number;
    rx_bytes?: number;
    tx_bytes?: number;
}

export interface PropagationNodeItem {
    destination_hash: string;
    operator_display_name?: string;
    updated_at?: string;
    is_local_node?: boolean;
    is_propagation_enabled?: boolean;
    local_node_stats?: PropagationNodeStats;
}

export interface PropagationNodesConfig {
    display_name?: string;
    lxmf_preferred_propagation_node_destination_hash?: string | null;
    lxmf_preferred_propagation_node_auto_select?: boolean;
    lxmf_local_propagation_node_address_hash?: string | null;
    lxmf_local_propagation_node_enabled?: boolean;
    lxmf_delivery_transfer_limit_in_bytes?: number;
    lxmf_propagation_transfer_limit_in_bytes?: number;
    lxmf_propagation_sync_limit_in_bytes?: number;
    lxmf_propagation_node_stamp_cost?: number;
}

export interface NodePathInfo {
    hops?: number;
    next_hop_interface?: string;
}

export type PropagationSortBy = "preferred" | "recent" | "oldest" | "name" | "name-desc";

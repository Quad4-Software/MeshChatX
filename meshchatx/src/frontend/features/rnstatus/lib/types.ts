// SPDX-License-Identifier: 0BSD

export interface RNStatusTrafficStats {
    rx_bytes_str?: string;
    tx_bytes_str?: string;
    rx_speed_str?: string;
    tx_speed_str?: string;
}

export interface RNStatusTotals extends RNStatusTrafficStats {
    announces?: RNStatusTrafficStats;
    path_requests?: RNStatusTrafficStats;
}

export interface RNStatusQueueItem {
    name: string;
    pressure?: string;
    packets?: number;
    dropped?: number;
}

export interface RNStatusQueues {
    queues?: RNStatusQueueItem[];
}

export interface RNStatusAirtime {
    short: number | string;
    long: number | string;
}

export interface RNStatusInterface {
    name: string;
    status?: string;
    discovered?: boolean;
    type?: string;
    mode?: string;
    bitrate?: string;
    rx_bytes_str?: string;
    tx_bytes_str?: string;
    rx_speed_str?: string;
    tx_speed_str?: string;
    clients?: number;
    peers?: number;
    noise_floor?: string | number;
    interference?: string | number;
    interference_last?: string | number;
    cpu_load?: string | number;
    cpu_temp?: string | number;
    mem_load?: string | number;
    battery_percent?: number;
    battery_state?: string;
    network_name?: string;
    incoming_announce_frequency?: number;
    outgoing_announce_frequency?: number;
    incoming_pr_frequency?: number;
    outgoing_pr_frequency?: number;
    held_announces?: number | string;
    announce_queue?: number | string;
    announce_totals?: number | string;
    path_request_totals?: number | string;
    announce_rx_bytes_str?: string;
    announce_tx_bytes_str?: string;
    path_rx_bytes_str?: string;
    path_tx_bytes_str?: string;
    announce_flow_rx_pct?: number | string;
    announce_flow_tx_pct?: number | string;
    path_flow_rx_pct?: number | string;
    path_flow_tx_pct?: number | string;
    announce_rate_limits?: string;
    violations?: number | string;
    filter_hits?: number | string;
    blocked_ip_list?: string[];
    airtime?: RNStatusAirtime;
    channel_load?: RNStatusAirtime;
    i2p_b32?: string;
    i2p_connectable?: boolean;
    i2p_tunnel_state?: string;
    switch_id?: string;
    endpoint_id?: string;
    via_switch_id?: string;
    ifac_access?: string;
    parent_interface?: string;
    autoconnect_source?: string;
    blocked_ips?: string | number;
    burst?: string | number;
    path_burst?: string | number;
}

export interface RNStatusResponse {
    interfaces?: RNStatusInterface[];
    link_count?: number | null;
    active_link_count?: number | null;
    blackhole_enabled?: boolean | null;
    blackhole_sources?: string[];
    blackhole_count?: number;
    remote?: string;
    transport_id?: string;
    network_id?: string;
    probe_responder?: string;
    transport_uptime_str?: string;
    totals?: RNStatusTotals;
    queues?: RNStatusQueues;
    rns_version?: string;
    rss_str?: string;
}

export interface RNStatusQueryParams {
    include_link_stats: boolean;
    show_all: boolean;
    sorting?: string;
    remote?: string;
    identity_path?: string;
    timeout?: number;
}

export interface ManagementIdentityItem {
    name: string;
    path: string;
    hash: string;
}

export interface InterfaceStatRow {
    key: string;
    label: string;
    value: string | number;
}

export interface QueueDisplayRow {
    key: string;
    label: string;
    pressure?: string;
    packets?: number;
    dropped?: number;
}

// SPDX-License-Identifier: 0BSD

export interface InterfaceStats {
    interface_name?: string;
    short_name?: string;
    status?: boolean | string;
    connected?: boolean;
    online?: boolean;
    bitrate?: number;
    gravity?: number;
    txb?: number;
    rxb?: number;
    noise_floor?: number;
    clients?: number;
    ifac_signature?: string;
    ifac_size?: number;
    ifac_netname?: string;
    target_host?: string;
    remote?: string;
    listen_ip?: string;
    target_port?: number | string;
    listen_port?: number | string;
    transport_id?: string;
    autoconnect_source?: string;
}

export interface ConfiguredInterface {
    _name: string;
    _stats?: InterfaceStats;
    _restart_required?: boolean;
    type: string;
    enabled?: boolean;
    interface_enabled?: boolean;
    discoverable?: boolean | string;
    target_host?: string;
    target_port?: number | string;
    remote?: string;
    listen_ip?: string;
    listen_port?: number | string;
    listen_host?: string;
    forward_ip?: string;
    forward_port?: number | string;
    port?: string;
    frequency?: number;
    bandwidth?: number;
    spreadingfactor?: number;
    codingrate?: number;
    txpower?: number;
    speed?: number | string;
    mode?: string;
    server_url?: string;
    description?: string;
    passphrase?: string;
    network_name?: string;
    ifac_netname?: string;
    ifac_netkey?: string;
    [key: string]: unknown;
}

export interface DiscoveredInterface {
    name?: string;
    type?: string;
    reachable_on?: string;
    target_host?: string;
    remote?: string;
    listen_ip?: string;
    port?: number | string;
    target_port?: number | string;
    listen_port?: number | string;
    transport_id?: string;
    network_id?: string;
    discovery_hash?: string;
    network_name?: string;
    ifac_netname?: string;
    passphrase?: string;
    ifac_netkey?: string;
    publish_ifac?: boolean;
    config_entry?: string;
    value?: number;
    hops?: number;
    status?: string;
    last_heard?: number;
    is_blacklisted?: boolean;
    is_allowed?: boolean;
    latitude?: number | null;
    longitude?: number | null;
    height?: number | null;
    frequency?: number | null;
    bandwidth?: number | null;
    sf?: number | null;
    spreadingfactor?: number | null;
    cr?: number | null;
    codingrate?: number | null;
    discoverable?: boolean | string | null;
    __isNew?: boolean;
}

export interface DiscoveredActiveInterface {
    name?: string;
    target_host?: string;
    remote?: string;
    listen_ip?: string;
    target_port?: number | string;
    listen_port?: number | string;
    transport_id?: string;
    autoconnect_source?: string;
    status?: boolean | string;
    connected?: boolean;
    online?: boolean;
    txb?: number;
    rxb?: number;
}

export interface DiscoveryConfig {
    discover_interfaces: boolean;
    interface_discovery_sources?: string;
    interface_discovery_whitelist?: string;
    interface_discovery_blacklist?: string;
    required_discovery_value?: number | null;
    autoconnect_discovered_interfaces?: number | null;
    default_gravity?: number | null;
    autoconnect_interface_mode?: string;
    autoconnect_interface_gravity?: number | null;
    autoconnect_announces_to_internal?: boolean;
    default_bootstrap_only?: boolean;
    network_identity?: string;
    autodiscover_allow_all?: boolean;
    autodiscover_list?: string;
    autodiscover_blacklist?: string;
    autodiscover_default_bootstrap_only?: boolean;
    [key: string]: unknown;
}

export type DiscoveryFields = {
    discover_interfaces?: boolean;
    interface_discovery_sources?: string;
    interface_discovery_whitelist?: string;
    interface_discovery_blacklist?: string;
    required_discovery_value?: number | null;
    autoconnect_discovered_interfaces?: number | null;
    default_gravity?: number | null;
    autoconnect_interface_mode?: string;
    autoconnect_interface_gravity?: number | null;
    autoconnect_announces_to_internal?: boolean;
    default_bootstrap_only?: boolean;
    network_identity?: string;
    autodiscover_allow_all?: boolean;
    autodiscover_list?: string;
    autodiscover_blacklist?: string;
    autodiscover_default_bootstrap_only?: boolean;
    discoverable?: boolean | string | null;
    discovery_name?: string | null;
    announce_interval?: number | string | null;
    reachable_on?: string | null;
    latitude?: number | string | null;
    longitude?: number | string | null;
    height?: number | string | null;
    location_cmd?: string | null;
    discovery_stamp_value?: number | string | null;
    discovery_encrypt?: boolean | string | null;
    publish_ifac?: boolean | string | null;
    [key: string]: unknown;
};

export type SharedInterfaceSettings = Record<string, unknown>;
export type ReticulumDiscovery = DiscoveryFields;

export interface RNodeLoRaParameters {
    antennaGain: number;
    noiseFloor: number;
    sensitivity: string | null;
    dataRate: string | null;
    linkBudget: string | null;
}

export interface InterfaceModule {
    type: string;
    filename: string;
    size?: number;
    name?: string;
}

export interface KernelInterface {
    name: string;
    addresses?: string[];
}

export interface Comport {
    device: string;
    product?: string;
    description?: string;
}

export interface CommunityInterface {
    name: string;
    type: string;
    target_host?: string;
    target_port?: number | string;
    online?: boolean;
    description?: string;
    [key: string]: unknown;
}

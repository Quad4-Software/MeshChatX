// SPDX-License-Identifier: 0BSD

import { buildRNodeTcpPort } from "./addInterfaceState.js";
import type { DiscoveryFields, SharedInterfaceSettings } from "./types.js";

export interface AddInterfaceFormState {
    targetHost?: string | null;
    targetPort?: number | string | null;
    transportIdentity?: string | null;
    kissFraming?: boolean;
    i2pTunneled?: boolean;
    bootstrapOnly?: boolean;
    connectTimeout?: number | string | null;
    maxReconnectTries?: number | string | null;
    fixedMtu?: number | string | null;
    backboneListenMode?: boolean;
    listenIp?: string | null;
    listenPort?: number | string | null;
    listenDevice?: string | null;
    preferIPv6?: boolean;
    blockFastFlapping?: boolean;
    fastFlappingBlockTime?: number | string | null;
    fastFlappingThreshold?: number | string | null;
    fastFlappingGrace?: number | string | null;
    forwardIp?: string | null;
    forwardPort?: number | string | null;
    udpDevice?: string | null;
    i2pConnectable?: boolean;
    i2pPeers?: string[];
    rnodeTransport?: "serial" | "tcp" | "bluetooth" | "ble";
    rnodePort?: string | null;
    rnodeTcpHost?: string | null;
    rnodeTcpPort?: number | string | null;
    rnodeFrequency?: number | string | null;
    rnodeBandwidth?: number | string | null;
    rnodeSpreadingFactor?: number | string | null;
    rnodeCodingRate?: number | string | null;
    rnodeTxpower?: number | string | null;
    rnodeFlowControl?: boolean;
    rnodeAutotune?: boolean;
    rnodeIdCallsign?: string | null;
    rnodeIdInterval?: number | string | null;
    rnodeAirtimeLimitLong?: number | string | null;
    rnodeAirtimeLimitShort?: number | string | null;
    serialSpeed?: number | string | null;
    serialDatabits?: number | string | null;
    serialParity?: string | null;
    serialStopbits?: number | string | null;
    ax25Callsign?: string | null;
    ax25Ssid?: number | string | null;
    kissPreamble?: number | string | null;
    kissTxtail?: number | string | null;
    kissPersistence?: number | string | null;
    kissSlottime?: number | string | null;
    kissFlowControl?: boolean;
    kissIdCallsign?: string | null;
    kissIdInterval?: number | string | null;
    autoGroupId?: string | null;
    autoMulticastType?: string | null;
    autoDevices?: string | null;
    autoIgnoredDevices?: string | null;
    autoDiscoveryScope?: string | null;
    autoDiscoveryPort?: number | string | null;
    autoDataPort?: number | string | null;
    autoConfiguredBitrate?: number | string | null;
    httpMode?: "client" | "server";
    httpServerUrl?: string | null;
    httpPollInterval?: number | string | null;
    httpListenHost?: string | null;
    httpListenPort?: number | string | null;
    httpMtu?: number | string | null;
    httpVersion?: number | string | null;
    httpUserAgent?: string | null;
    httpCheckUserAgent?: boolean;
    httpTlsVerify?: boolean;
    httpTlsCertfile?: string | null;
    httpTlsKeyfile?: string | null;
    customTypeName?: string;
    customOptionsJson?: string;
}

export function buildSavePayload(
    interfaceType: string,
    sharedSettings: SharedInterfaceSettings,
    form: AddInterfaceFormState,
    discovery: DiscoveryFields
): Record<string, any> {
    const payload: Record<string, any> = {
        type: interfaceType,
        ...sharedSettings,
    };

    if (interfaceType === "TCPClientInterface") {
        payload.target_host = form.targetHost ?? null;
        payload.target_port = form.targetPort != null ? Number(form.targetPort) : null;
        if (form.kissFraming !== undefined) payload.kiss_framing = form.kissFraming;
        if (form.i2pTunneled !== undefined) payload.i2p_tunneled = form.i2pTunneled;
        if (form.bootstrapOnly !== undefined) payload.bootstrap_only = form.bootstrapOnly;
        if (form.connectTimeout != null) payload.connect_timeout = Number(form.connectTimeout);
        if (form.maxReconnectTries != null) payload.max_reconnect_tries = Number(form.maxReconnectTries);
        if (form.fixedMtu != null) payload.fixed_mtu = Number(form.fixedMtu);
    } else if (interfaceType === "TCPServerInterface") {
        payload.listen_ip = form.listenIp || "0.0.0.0";
        payload.listen_port = form.listenPort != null ? Number(form.listenPort) : 4242;
        if (form.listenDevice || form.udpDevice) payload.device = form.listenDevice || form.udpDevice;
        if (form.preferIPv6 !== undefined) payload.prefer_ipv6 = form.preferIPv6;
        if (form.i2pTunneled !== undefined) payload.i2p_tunneled = form.i2pTunneled;
        if (form.fixedMtu != null) payload.fixed_mtu = Number(form.fixedMtu);
    } else if (interfaceType === "BackboneInterface") {
        if (form.backboneListenMode) {
            payload.listen_ip = form.listenIp || "0.0.0.0";
            payload.listen_port = form.listenPort != null ? Number(form.listenPort) : 5151;
            if (form.listenDevice) payload.device = form.listenDevice;
            if (form.preferIPv6 !== undefined) payload.prefer_ipv6 = form.preferIPv6;
            payload.target_host = null;
            payload.target_port = null;
            if (form.blockFastFlapping !== undefined) payload.block_fast_flapping = form.blockFastFlapping;
            if (form.fastFlappingBlockTime != null)
                payload.fast_flapping_block_time = Number(form.fastFlappingBlockTime);
            if (form.fastFlappingThreshold != null)
                payload.fast_flapping_threshold = Number(form.fastFlappingThreshold);
            if (form.fastFlappingGrace != null) payload.fast_flapping_grace = Number(form.fastFlappingGrace);
        } else {
            payload.target_host = form.targetHost ?? null;
            payload.target_port = form.targetPort != null ? Number(form.targetPort) : null;
            if (form.transportIdentity) payload.transport_identity = form.transportIdentity;
            if (form.bootstrapOnly !== undefined) payload.bootstrap_only = form.bootstrapOnly;
        }
        if (form.connectTimeout != null) payload.connect_timeout = Number(form.connectTimeout);
        if (form.maxReconnectTries != null) payload.max_reconnect_tries = Number(form.maxReconnectTries);
        if (form.fixedMtu != null) payload.fixed_mtu = Number(form.fixedMtu);
    } else if (interfaceType === "UDPInterface") {
        payload.listen_ip = form.listenIp ?? null;
        payload.listen_port = form.listenPort != null ? Number(form.listenPort) : null;
        payload.forward_ip = form.forwardIp ?? null;
        payload.forward_port = form.forwardPort != null ? Number(form.forwardPort) : null;
        if (form.udpDevice) payload.device = form.udpDevice;
    } else if (interfaceType === "I2PInterface") {
        payload.connectable = Boolean(form.i2pConnectable);
        payload.peers = Array.isArray(form.i2pPeers) ? form.i2pPeers.filter(Boolean) : [];
        if (form.connectTimeout != null) payload.connect_timeout = Number(form.connectTimeout);
        if (form.fixedMtu != null) payload.fixed_mtu = Number(form.fixedMtu);
    } else if (interfaceType === "RNodeInterface" || interfaceType === "RNodeIPInterface") {
        if (form.rnodeTransport === "tcp") {
            payload.port = buildRNodeTcpPort(form.rnodeTcpHost || "127.0.0.1");
        } else {
            payload.port = form.rnodePort ?? null;
        }
        if (form.rnodeFrequency != null) payload.frequency = Number(form.rnodeFrequency);
        if (form.rnodeBandwidth != null) payload.bandwidth = Number(form.rnodeBandwidth);
        if (form.rnodeSpreadingFactor != null) payload.spreadingfactor = Number(form.rnodeSpreadingFactor);
        if (form.rnodeCodingRate != null) payload.codingrate = Number(form.rnodeCodingRate);
        if (form.rnodeTxpower != null) payload.txpower = Number(form.rnodeTxpower);
        if (form.rnodeFlowControl !== undefined) payload.flow_control = form.rnodeFlowControl;
        if (form.rnodeAutotune !== undefined) payload.autotune = form.rnodeAutotune;
        if (form.rnodeIdCallsign) payload.id_callsign = form.rnodeIdCallsign;
        if (form.rnodeIdInterval != null) payload.id_interval = Number(form.rnodeIdInterval);
        if (form.rnodeAirtimeLimitLong != null) payload.airtime_limit_long = Number(form.rnodeAirtimeLimitLong);
        if (form.rnodeAirtimeLimitShort != null) payload.airtime_limit_short = Number(form.rnodeAirtimeLimitShort);
    } else if (["SerialInterface", "KISSInterface", "AX25KISSInterface"].includes(interfaceType)) {
        payload.port = form.rnodePort ?? null;
        if (form.serialSpeed != null) payload.speed = Number(form.serialSpeed);
        if (form.serialDatabits != null) payload.databits = Number(form.serialDatabits);
        if (form.serialParity) payload.parity = form.serialParity;
        if (form.serialStopbits != null) payload.stopbits = Number(form.serialStopbits);
        if (interfaceType === "AX25KISSInterface") {
            if (form.ax25Callsign) payload.callsign = form.ax25Callsign;
            if (form.ax25Ssid != null) payload.ssid = Number(form.ax25Ssid);
        }
        if (form.kissPreamble != null) payload.preamble = Number(form.kissPreamble);
        if (form.kissTxtail != null) payload.txtail = Number(form.kissTxtail);
        if (form.kissPersistence != null) payload.persistence = Number(form.kissPersistence);
        if (form.kissSlottime != null) payload.slottime = Number(form.kissSlottime);
        if (form.kissFlowControl !== undefined) payload.flow_control = form.kissFlowControl;
        else if (form.rnodeFlowControl !== undefined) payload.flow_control = form.rnodeFlowControl;
        const callsign = form.kissIdCallsign || form.rnodeIdCallsign;
        if (callsign) payload.id_callsign = callsign;
        const interval = form.kissIdInterval ?? form.rnodeIdInterval;
        if (interval != null) payload.id_interval = Number(interval);
    } else if (interfaceType === "AutoInterface") {
        if (form.autoGroupId) payload.group_id = form.autoGroupId;
        if (form.autoMulticastType) payload.multicast_address_type = form.autoMulticastType;
        if (form.autoDevices) payload.devices = form.autoDevices;
        if (form.autoIgnoredDevices) payload.ignored_devices = form.autoIgnoredDevices;
        if (form.autoDiscoveryScope) payload.discovery_scope = form.autoDiscoveryScope;
        if (form.autoDiscoveryPort != null) payload.discovery_port = Number(form.autoDiscoveryPort);
        if (form.autoDataPort != null) payload.data_port = Number(form.autoDataPort);
        if (form.autoConfiguredBitrate != null) payload.configured_bitrate = Number(form.autoConfiguredBitrate);
    } else if (interfaceType === "HTTPInterface") {
        payload.type = "HTTPInterface";
        payload.mode = form.httpMode || "client";
        payload.http_tunnel_mode = form.httpMode || "client";
        if (form.httpMode === "server") {
            payload.listen_host = form.httpListenHost || "0.0.0.0";
            if (form.httpListenPort != null) payload.listen_port = Number(form.httpListenPort);
        } else {
            payload.server_url = form.httpServerUrl || "";
            if (form.httpPollInterval != null) payload.poll_interval = Number(form.httpPollInterval);
        }
        if (form.httpMtu != null) payload.mtu = Number(form.httpMtu);
        if (form.httpVersion != null) payload.http_version = Number(form.httpVersion);
        if (form.httpUserAgent) payload.user_agent = form.httpUserAgent;
        if (form.httpCheckUserAgent !== undefined) payload.check_user_agent = form.httpCheckUserAgent;
        if (form.httpTlsVerify !== undefined) payload.tls_verify = form.httpTlsVerify;
        if (form.httpTlsCertfile) payload.tls_certfile = form.httpTlsCertfile;
        if (form.httpTlsKeyfile) payload.tls_keyfile = form.httpTlsKeyfile;
    } else if (interfaceType === "__external__") {
        payload.custom_type_name = form.customTypeName || "";
        payload.custom_options = JSON.parse(form.customOptionsJson || "{}");
    }

    if (discovery.discoverable) {
        payload.discoverable = "yes";
        payload.discovery_name = discovery.discovery_name || null;
        payload.announce_interval = discovery.announce_interval != null ? Number(discovery.announce_interval) : 360;
        payload.reachable_on = discovery.reachable_on || null;
        payload.latitude = discovery.latitude != null ? Number(discovery.latitude) : null;
        payload.longitude = discovery.longitude != null ? Number(discovery.longitude) : null;
        payload.height = discovery.height != null ? Number(discovery.height) : null;
        payload.location_cmd = discovery.location_cmd || null;
        if (discovery.discovery_stamp_value != null)
            payload.discovery_stamp_value = Number(discovery.discovery_stamp_value);
        if (discovery.discovery_encrypt !== undefined) payload.discovery_encrypt = discovery.discovery_encrypt;
        if (discovery.publish_ifac !== undefined) payload.publish_ifac = discovery.publish_ifac;
    } else {
        payload.discoverable = null;
        payload.discovery_name = null;
        payload.latitude = null;
    }

    return payload;
}

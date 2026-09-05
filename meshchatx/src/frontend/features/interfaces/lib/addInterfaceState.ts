// SPDX-License-Identifier: 0BSD

import { numOrNull, parseRNodeFrequencyHz } from "../../../js/interfaceDiscoveryUtils.js";
import { parseBool } from "./interfacesFormat.js";
import type { DiscoveryFields, RNodeLoRaParameters, SharedInterfaceSettings } from "./types.js";

export { numOrNull, parseRNodeFrequencyHz };

export function buildRNodeTcpPort(host: string): string {
    let h = String(host ?? "").trim();
    while (h.endsWith(":")) {
        h = h.slice(0, -1);
    }
    if (!h) {
        return "";
    }
    return `tcp://${h}`;
}

export function parseRnodeTcpHostFromPort(portStr: string): string {
    const s = String(portStr || "");
    if (!s.startsWith("tcp://")) {
        return "localhost";
    }
    let rest = s.slice(6);
    while (rest.endsWith(":")) {
        rest = rest.slice(0, -1);
    }
    if (!rest) {
        return "";
    }
    if (rest.startsWith("[")) {
        const close = rest.indexOf("]");
        if (close !== -1 && rest[close + 1] === ":") {
            return rest.slice(0, close + 1);
        }
        return rest;
    }
    if (rest.includes(":") && rest.indexOf(":") === rest.lastIndexOf(":")) {
        const idx = rest.indexOf(":");
        const tail = rest.slice(idx + 1);
        if (/^\d{1,5}$/.test(tail) && Number(tail) <= 65535) {
            return rest.slice(0, idx);
        }
    }
    return rest;
}

export function effectiveRNodeBlePort(peer: string): string {
    const p = (peer || "").trim();
    if (!p) {
        return "ble://";
    }
    if (p.toLowerCase().startsWith("ble://")) {
        return p;
    }
    return `ble://${p}`;
}

export function calculateRNodeParameters(
    bandwidth: number,
    spreadingFactor: number,
    codingRate: number,
    noiseFloor: number,
    antennaGain: number,
    transmitPower: number
): Partial<RNodeLoRaParameters> {
    if (!bandwidth || !spreadingFactor || !codingRate) {
        return {};
    }
    const crn: Record<number, number> = { 5: 1, 6: 2, 7: 3, 8: 4 };
    const cr = crn[codingRate] ?? 1;
    const sfn: Record<number, number> = { 5: -2.5, 6: -5, 7: -7.5, 8: -10, 9: -12.5, 10: -15, 11: -17.5, 12: -20 };
    const dataRate = spreadingFactor * (4 / (4 + cr) / (Math.pow(2, spreadingFactor) / (bandwidth / 1000))) * 1000;
    let sensitivity = -174 + 10 * Math.log10(bandwidth) + noiseFloor + (sfn[spreadingFactor] || 0);
    if (bandwidth === 203125 || bandwidth === 406250 || bandwidth > 500000) {
        sensitivity = -165.6 + 10 * Math.log10(bandwidth) + noiseFloor + (sfn[spreadingFactor] || 0);
    }
    const linkBudget = transmitPower - sensitivity + antennaGain;
    return {
        dataRate: dataRate < 1000 ? `${dataRate.toFixed(0)} bps` : `${(dataRate / 1000).toFixed(2)} kbps`,
        linkBudget: `${linkBudget.toFixed(1)} dB`,
        sensitivity: `${sensitivity.toFixed(1)} dBm`,
    };
}

export function calculateLoRaParameters(
    bandwidth: number,
    spreadingFactor: number,
    codingRate: number,
    noiseFloor: number,
    antennaGain: number,
    transmitPower: number
): Partial<RNodeLoRaParameters> {
    return calculateRNodeParameters(bandwidth, spreadingFactor, codingRate, noiseFloor, antennaGain, transmitPower);
}

export function parseRawConfig(rawConfigInput: string): Record<string, any>[] {
    if (!rawConfigInput.trim()) {
        return [];
    }

    const configs: Record<string, any>[] = [];
    const sections = rawConfigInput.split(/\[\[(.*?)\]\]/);

    for (let i = 1; i < sections.length; i += 2) {
        const name = sections[i].trim();
        const content = sections[i + 1] || "";
        const config: Record<string, any> = { name };

        const lines = content.split("\n");
        for (const line of lines) {
            const match = line.match(/^\s*(\w+)\s*=\s*(.*?)\s*$/);
            if (match) {
                const key = match[1].trim();
                let value = match[2].trim();

                if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
                    value = value.substring(1, value.length - 1);
                    config[key] = value;
                } else if (/^-?\d+$/.test(value)) {
                    config[key] = parseInt(value, 10);
                } else if (/^-?\d+\.\d+$/.test(value)) {
                    config[key] = parseFloat(value);
                } else {
                    config[key] = value;
                }
            }
        }

        if (config.type) {
            configs.push(config);
        }
    }

    return configs;
}

export function buildPayloadFromImportedConfig(config: Record<string, any>): Record<string, any> {
    const discoveryEnabled =
        config.discoverable !== undefined && config.discoverable !== null && config.discoverable !== ""
            ? parseBool(config.discoverable)
            : false;
    const backboneConnector =
        config.type === "BackboneInterface" &&
        Boolean(config.remote || config.target_host) &&
        !(config.listen_port != null && String(config.listen_port).trim() !== "");
    let bootstrapOnlyPayload: boolean | undefined;
    if (config.type === "TCPClientInterface" || backboneConnector) {
        if (config.bootstrap_only !== undefined && config.bootstrap_only !== null && config.bootstrap_only !== "") {
            bootstrapOnlyPayload = parseBool(config.bootstrap_only);
        }
    }
    const i2pPeers =
        config.type === "I2PInterface"
            ? Array.isArray(config.i2p_peers)
                ? config.i2p_peers.map((p: unknown) => String(p).trim()).filter(Boolean)
                : Array.isArray(config.peers)
                  ? config.peers.map((p: unknown) => String(p).trim()).filter(Boolean)
                  : []
            : undefined;

    return {
        allow_overwriting_interface: false,
        name: config.name,
        type: config.type,
        target_host: config.target_host || config.remote || null,
        target_port: numOrNull(config.target_port),
        transport_identity: config.transport_identity || null,
        peers: i2pPeers,
        listen_ip: config.listen_ip || null,
        listen_port: numOrNull(config.listen_port),
        port: config.port || null,
        frequency: parseRNodeFrequencyHz(config.frequency) ?? numOrNull(config.frequency),
        bandwidth: numOrNull(config.bandwidth),
        txpower: numOrNull(config.txpower),
        spreadingfactor: numOrNull(config.spreadingfactor),
        codingrate: numOrNull(config.codingrate),
        command: config.command || null,
        respawn_delay: numOrNull(config.respawn_delay),
        discoverable: discoveryEnabled ? "yes" : null,
        discovery_name: discoveryEnabled ? config.discovery_name || config.name || null : null,
        announce_interval: discoveryEnabled ? (numOrNull(config.announce_interval) ?? 360) : null,
        reachable_on: discoveryEnabled ? config.reachable_on || config.target_host || null : null,
        discovery_stamp_value: discoveryEnabled ? (numOrNull(config.discovery_stamp_value) ?? 14) : null,
        discovery_encrypt: discoveryEnabled
            ? config.discovery_encrypt !== undefined
                ? parseBool(config.discovery_encrypt)
                : false
            : null,
        publish_ifac: discoveryEnabled
            ? config.publish_ifac !== undefined
                ? parseBool(config.publish_ifac)
                : false
            : null,
        latitude: discoveryEnabled ? numOrNull(config.latitude) : null,
        longitude: discoveryEnabled ? numOrNull(config.longitude) : null,
        height: discoveryEnabled ? numOrNull(config.height) : null,
        location_cmd: discoveryEnabled
            ? config.location_cmd
                ? String(config.location_cmd).trim() || null
                : null
            : null,
        discovery_frequency: discoveryEnabled ? numOrNull(config.discovery_frequency) : null,
        discovery_bandwidth: discoveryEnabled ? numOrNull(config.discovery_bandwidth) : null,
        discovery_modulation: discoveryEnabled ? numOrNull(config.discovery_modulation) : null,
        mode: config.mode || null,
        recursive_prs:
            config.recursive_prs !== undefined && config.recursive_prs !== null && config.recursive_prs !== ""
                ? parseBool(config.recursive_prs)
                : false,
        announces_from_internal:
            config.announces_from_internal !== undefined &&
            config.announces_from_internal !== null &&
            config.announces_from_internal !== ""
                ? parseBool(config.announces_from_internal)
                : true,
        announces_to_internal:
            config.announces_to_internal !== undefined &&
            config.announces_to_internal !== null &&
            config.announces_to_internal !== ""
                ? parseBool(config.announces_to_internal)
                : false,
        gravity:
            config.gravity !== undefined && config.gravity !== null && config.gravity !== ""
                ? numOrNull(config.gravity)
                : null,
        bitrate: numOrNull(config.bitrate),
        network_name: config.network_name || null,
        passphrase: config.passphrase || null,
        forward_ip: config.forward_ip || null,
        forward_port: numOrNull(config.forward_port),
        device: config.device || null,
        prefer_ipv6:
            config.prefer_ipv6 !== undefined && config.prefer_ipv6 !== null && config.prefer_ipv6 !== ""
                ? parseBool(config.prefer_ipv6)
                : null,
        block_fast_flapping:
            config.type === "BackboneInterface" &&
            config.listen_port != null &&
            String(config.listen_port).trim() !== ""
                ? config.block_fast_flapping !== undefined &&
                  config.block_fast_flapping !== null &&
                  config.block_fast_flapping !== ""
                    ? parseBool(config.block_fast_flapping)
                    : true
                : null,
        fast_flapping_block_time:
            config.type === "BackboneInterface" &&
            config.listen_port != null &&
            String(config.listen_port).trim() !== ""
                ? numOrNull(config.fast_flapping_block_time)
                : null,
        fast_flapping_threshold:
            config.type === "BackboneInterface" &&
            config.listen_port != null &&
            String(config.listen_port).trim() !== ""
                ? numOrNull(config.fast_flapping_threshold)
                : null,
        fast_flapping_grace:
            config.type === "BackboneInterface" &&
            config.listen_port != null &&
            String(config.listen_port).trim() !== ""
                ? numOrNull(config.fast_flapping_grace)
                : null,
        kiss_framing:
            config.kiss_framing !== undefined && config.kiss_framing !== null && config.kiss_framing !== ""
                ? parseBool(config.kiss_framing)
                : null,
        i2p_tunneled:
            config.i2p_tunneled !== undefined && config.i2p_tunneled !== null && config.i2p_tunneled !== ""
                ? parseBool(config.i2p_tunneled)
                : null,
        connect_timeout: numOrNull(config.connect_timeout),
        max_reconnect_tries: numOrNull(config.max_reconnect_tries),
        fixed_mtu: numOrNull(config.fixed_mtu),
        connectable:
            config.type === "I2PInterface"
                ? config.connectable !== undefined && config.connectable !== null && config.connectable !== ""
                    ? parseBool(config.connectable)
                    : false
                : null,
        group_id: config.group_id || null,
        multicast_address_type: config.multicast_address_type || null,
        devices: config.devices || null,
        ignored_devices: config.ignored_devices || null,
        discovery_scope: config.discovery_scope || null,
        discovery_port: numOrNull(config.discovery_port),
        data_port: numOrNull(config.data_port),
        configured_bitrate: numOrNull(config.configured_bitrate),
        callsign: config.callsign || null,
        id_callsign: config.id_callsign || null,
        id_interval: numOrNull(config.id_interval),
        ssid: numOrNull(config.ssid),
        airtime_limit_long: numOrNull(config.airtime_limit_long),
        airtime_limit_short: numOrNull(config.airtime_limit_short),
        speed: numOrNull(config.speed),
        databits: numOrNull(config.databits),
        parity: config.parity || null,
        stopbits: numOrNull(config.stopbits),
        preamble: numOrNull(config.preamble),
        txtail: numOrNull(config.txtail),
        persistence: numOrNull(config.persistence),
        slottime: numOrNull(config.slottime),
        flow_control:
            config.flow_control !== undefined && config.flow_control !== null && config.flow_control !== ""
                ? parseBool(config.flow_control)
                : null,
        bootstrap_only: bootstrapOnlyPayload,
    };
}

export interface InterfaceFormState {
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
    serialSpeed?: number | string | null;
    serialDatabits?: number | string | null;
    serialParity?: string | null;
    serialStopbits?: number | string | null;
    ax25Callsign?: string | null;
    ax25Ssid?: number | string | null;
    kissPreamble?: number | string | null;
    kissTxtail?: number | string | null;
    autoGroupId?: string | null;
    autoMulticastType?: string | null;
    autoDevices?: string | null;
    autoIgnoredDevices?: string | null;
    autoDiscoveryScope?: string | null;
    autoDiscoveryPort?: number | string | null;
    autoDataPort?: number | string | null;
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

export function buildInterfaceSavePayload(
    interfaceType: string,
    sharedSettings: SharedInterfaceSettings,
    discovery: DiscoveryFields,
    form: InterfaceFormState
): Record<string, any> {
    const payload: Record<string, any> = {
        type: interfaceType,
        ...sharedSettings,
    };

    if (interfaceType === "TCPClientInterface") {
        payload.target_host = form.targetHost;
        payload.target_port = form.targetPort;
        payload.kiss_framing = form.kissFraming;
        payload.i2p_tunneled = form.i2pTunneled;
        payload.bootstrap_only = form.bootstrapOnly;
        if (form.connectTimeout) payload.connect_timeout = Number(form.connectTimeout);
        if (form.maxReconnectTries) payload.max_reconnect_tries = Number(form.maxReconnectTries);
        if (form.fixedMtu) payload.fixed_mtu = Number(form.fixedMtu);
    } else if (interfaceType === "BackboneInterface") {
        if (form.backboneListenMode) {
            payload.listen_ip = form.listenIp || "0.0.0.0";
            payload.listen_port = Number(form.listenPort) || 4242;
            if (form.listenDevice) payload.listen_device = form.listenDevice;
            payload.block_fast_flapping = form.blockFastFlapping;
            if (form.fastFlappingBlockTime) payload.fast_flapping_block_time = Number(form.fastFlappingBlockTime);
            if (form.fastFlappingThreshold) payload.fast_flapping_threshold = Number(form.fastFlappingThreshold);
            if (form.fastFlappingGrace) payload.fast_flapping_grace = Number(form.fastFlappingGrace);
        } else {
            payload.target_host = form.targetHost;
            payload.target_port = form.targetPort;
            if (form.transportIdentity) payload.transport_identity = form.transportIdentity;
            payload.bootstrap_only = form.bootstrapOnly;
        }
        if (form.connectTimeout) payload.connect_timeout = Number(form.connectTimeout);
        if (form.maxReconnectTries) payload.max_reconnect_tries = Number(form.maxReconnectTries);
        if (form.fixedMtu) payload.fixed_mtu = Number(form.fixedMtu);
    } else if (interfaceType === "UDPInterface") {
        payload.listen_ip = form.listenIp;
        payload.listen_port = form.listenPort;
        payload.forward_ip = form.forwardIp;
        payload.forward_port = form.forwardPort;
        if (form.udpDevice) payload.device = form.udpDevice;
    } else if (interfaceType === "I2PInterface") {
        payload.connectable = form.i2pConnectable;
        payload.peers = (form.i2pPeers || []).filter(Boolean);
        if (form.connectTimeout) payload.connect_timeout = Number(form.connectTimeout);
        if (form.fixedMtu) payload.fixed_mtu = Number(form.fixedMtu);
    } else if (interfaceType === "RNodeInterface" || interfaceType === "RNodeIPInterface") {
        if (form.rnodeTransport === "tcp") {
            payload.port = buildRNodeTcpPort(form.rnodeTcpHost || "127.0.0.1");
        } else {
            payload.port = form.rnodePort;
        }
        payload.frequency = form.rnodeFrequency;
        payload.bandwidth = form.rnodeBandwidth;
        payload.spreadingfactor = form.rnodeSpreadingFactor;
        payload.codingrate = form.rnodeCodingRate;
        payload.txpower = form.rnodeTxpower;
        payload.flow_control = form.rnodeFlowControl;
        payload.autotune = form.rnodeAutotune;
        if (form.rnodeIdCallsign) payload.id_callsign = form.rnodeIdCallsign;
        if (form.rnodeIdInterval) payload.id_interval = Number(form.rnodeIdInterval);
    } else if (["SerialInterface", "KISSInterface", "AX25KISSInterface"].includes(interfaceType)) {
        payload.port = form.rnodePort;
        payload.speed = Number(form.serialSpeed);
        payload.databits = Number(form.serialDatabits);
        payload.parity = form.serialParity;
        payload.stopbits = Number(form.serialStopbits);
        if (interfaceType === "AX25KISSInterface") {
            payload.callsign = form.ax25Callsign;
            payload.ssid = Number(form.ax25Ssid);
        }
        if (form.kissPreamble) payload.preamble = Number(form.kissPreamble);
        if (form.kissTxtail) payload.txtail = Number(form.kissTxtail);
    } else if (interfaceType === "AutoInterface") {
        if (form.autoGroupId) payload.group_id = form.autoGroupId;
        if (form.autoMulticastType) payload.multicast_address_type = form.autoMulticastType;
        if (form.autoDevices) payload.devices = form.autoDevices;
        if (form.autoIgnoredDevices) payload.ignored_devices = form.autoIgnoredDevices;
        if (form.autoDiscoveryScope) payload.discovery_scope = form.autoDiscoveryScope;
        if (form.autoDiscoveryPort) payload.discovery_port = Number(form.autoDiscoveryPort);
        if (form.autoDataPort) payload.data_port = Number(form.autoDataPort);
    } else if (interfaceType === "HTTPInterface") {
        payload.http_tunnel_mode = form.httpMode;
        if (form.httpMode === "client") {
            payload.server_url = form.httpServerUrl;
            payload.poll_interval = Number(form.httpPollInterval);
        } else {
            payload.listen_host = form.httpListenHost;
            payload.listen_port = Number(form.httpListenPort);
        }
        payload.mtu = Number(form.httpMtu);
        payload.http_version = Number(form.httpVersion);
        payload.user_agent = form.httpUserAgent;
        payload.check_user_agent = form.httpCheckUserAgent;
        payload.tls_verify = form.httpTlsVerify;
        if (form.httpTlsCertfile) payload.tls_certfile = form.httpTlsCertfile;
        if (form.httpTlsKeyfile) payload.tls_keyfile = form.httpTlsKeyfile;
    } else if (interfaceType === "__external__") {
        payload.custom_type_name = form.customTypeName;
        payload.custom_options = JSON.parse(form.customOptionsJson || "{}");
    }

    if (discovery.discoverable) {
        Object.assign(payload, discovery);
    }

    return payload;
}

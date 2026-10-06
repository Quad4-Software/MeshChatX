// SPDX-License-Identifier: 0BSD

/** Community preset type grouping for the add-interface quick start list. */

const TYPE_TO_GROUP = Object.freeze({
    TCPClientInterface: "tcp",
    BackboneInterface: "backbone",
    I2PInterface: "i2p",
    YggdrasilInterface: "yggdrasil",
});

export const COMMUNITY_FILTER_OPTIONS = Object.freeze([
    { id: "all", icon: "format-list-bulleted", labelKey: "interfaces.community_filter_all" },
    { id: "tcp", icon: "lan-connect", labelKey: "interfaces.community_filter_tcp" },
    { id: "backbone", icon: "sitemap", labelKey: "interfaces.community_filter_backbone" },
    { id: "i2p", icon: "eye", labelKey: "interfaces.community_filter_i2p" },
    { id: "yggdrasil", icon: "earth", labelKey: "interfaces.community_filter_yggdrasil" },
    { id: "other", icon: "dots-horizontal", labelKey: "interfaces.community_filter_other" },
]);

export function communityPresetGroup(iface) {
    const type = String((iface && iface.type) || "");
    return TYPE_TO_GROUP[type] || "other";
}

export function filterCommunityInterfaces(interfaces, group) {
    const list = Array.isArray(interfaces) ? interfaces : [];
    if (!group || group === "all") {
        return list;
    }
    return list.filter((iface) => communityPresetGroup(iface) === group);
}

/** Single-line address label for a preset row (peer for I2P, host:port otherwise). */
export function communityPresetAddress(iface) {
    if (!iface || typeof iface !== "object") {
        return "";
    }
    if (iface.type === "I2PInterface") {
        const peers = Array.isArray(iface.i2p_peers) ? iface.i2p_peers : [];
        return String(peers[0] || iface.target_host || "");
    }
    const host = String(iface.target_host || "");
    const port = iface.target_port;
    return port !== null && port !== undefined && port !== "" ? `${host}:${port}` : host;
}

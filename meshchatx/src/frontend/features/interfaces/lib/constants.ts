// SPDX-License-Identifier: 0BSD

export const INTERFACES_FEATURE_ID = "interfaces";
export const INTERFACES_ROUTE_NAME = "interfaces";
export const INTERFACES_ROUTE_PATH = "/interfaces";

export const INTERFACES_ADD_ROUTE_NAME = "interfaces.add";
export const INTERFACES_ADD_ROUTE_PATH = "/interfaces/add";

export const INTERFACES_EDIT_ROUTE_NAME = "interfaces.edit";
export const INTERFACES_EDIT_ROUTE_PATH = "/interfaces/edit";

export const RETICULUM_MIN_FIXED_MTU = 500;

export const RNODE_DEFAULTS = {
    bandwidths: [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000, 1625000],
    codingrates: [5, 6, 7, 8],
    spreadingfactors: [5, 6, 7, 8, 9, 10, 11, 12],
    txpowerMin: 0,
    txpowerMax: 37,
} as const;

export interface TransportTypeOption {
    id: string;
    name: string;
    icon: string;
    color: string;
}

export const TRANSPORT_TYPE_OPTIONS: TransportTypeOption[] = [
    {
        id: "TCPClientInterface",
        name: "TCP Client",
        icon: "lan-connect",
        color: "text-blue-500",
    },
    {
        id: "BackboneInterface",
        name: "Backbone",
        icon: "transit-connection-variant",
        color: "text-sky-500",
    },
    {
        id: "TCPServerInterface",
        name: "TCP Server",
        icon: "server-network",
        color: "text-indigo-500",
    },
    {
        id: "UDPInterface",
        name: "UDP",
        icon: "broadcast",
        color: "text-cyan-500",
    },
    {
        id: "RNodeInterface",
        name: "RNode (LoRa)",
        icon: "radio-handheld",
        color: "text-emerald-500",
    },
    {
        id: "I2PInterface",
        name: "I2P Tunnel",
        icon: "tunnel",
        color: "text-purple-500",
    },
    {
        id: "SerialInterface",
        name: "Serial (Generic)",
        icon: "serial-port",
        color: "text-amber-500",
    },
    {
        id: "KISSInterface",
        name: "KISS (TNC)",
        icon: "radio-tower",
        color: "text-orange-500",
    },
    {
        id: "AutoInterface",
        name: "Auto (Local)",
        icon: "auto-fix",
        color: "text-pink-500",
    },
    {
        id: "HTTPInterface",
        name: "HTTP Tunnel",
        icon: "web",
        color: "text-teal-500",
    },
];

export const DEDICATED_FORM_INTERFACE_TYPES = new Set([
    "TCPClientInterface",
    "BackboneInterface",
    "I2PInterface",
    "TCPServerInterface",
    "UDPInterface",
    "RNodeInterface",
    "RNodeIPInterface",
    "RNodeMultiInterface",
    "SerialInterface",
    "KISSInterface",
    "AX25KISSInterface",
    "PipeInterface",
    "AutoInterface",
    "LocalInterface",
    "HTTPInterface",
]);

// SPDX-License-Identifier: 0BSD

interface DiscoveredInterfaceDescriptor {
    type?: string;
    interface_type?: string;
    port?: string | number;
}

export function getDiscoveredIconName(node: DiscoveredInterfaceDescriptor | null | undefined): string {
    if (!node) return "map-marker-radius";
    const type = node.type || node.interface_type || "";
    switch (type) {
        case "AutoInterface":
            return "home-automation";
        case "RNodeInterface":
            return node.port && node.port.toString().startsWith("tcp://") ? "lan-connect" : "radio-tower";
        case "RNodeMultiInterface":
            return "access-point-network";
        case "TCPClientInterface":
        case "BackboneInterface":
            return "lan-connect";
        case "TCPServerInterface":
            return "lan";
        case "UDPInterface":
            return "wan";
        case "SerialInterface":
            return "usb-port";
        case "KISSInterface":
        case "AX25KISSInterface":
            return "antenna";
        case "I2PInterface":
            return "eye";
        case "PipeInterface":
            return "pipe";
        case "HTTPInterface":
            return "web";
        default:
            return "server-network";
    }
}

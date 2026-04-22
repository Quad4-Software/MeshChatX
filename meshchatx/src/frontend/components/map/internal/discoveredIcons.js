/**
 * Map a discovered/announce-style interface descriptor to an MDI icon name.
 *
 * Mirrors the icon mapping used in the Interfaces page so that the map view
 * stays visually consistent with the rest of the app.
 *
 * @param {object|null} node - discovered node or interface descriptor.
 * @returns {string} an mdi icon name (without the "mdi-" prefix).
 */
export function getDiscoveredIconName(node) {
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
        default:
            return "server-network";
    }
}

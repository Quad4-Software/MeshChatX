# Reticulum interfaces

Interfaces connect your MeshChatX node to the Reticulum mesh. Manage them from the **Interfaces** page.

## What an interface does

Each interface is a Reticulum transport definition. Examples include TCP over the internet, UDP discovery, LoRa through an RNode, serial KISS devices, I2P tunnels, and automatic LAN discovery.

MeshChatX reads and writes interface configuration in your Reticulum config directory (default `~/.reticulum`).

## Supported interface types

The **Add interface** flow includes:

| Type                  | Typical use                                   |
| --------------------- | --------------------------------------------- |
| TCPClientInterface    | Connect outbound to a known TCP peer          |
| TCPServerInterface    | Accept inbound TCP connections                |
| BackboneInterface     | High-throughput backbone link                 |
| UDPInterface          | UDP transport with discovery helpers          |
| RNodeInterface        | LoRa via RNode (serial, BLE, or IP transport) |
| RNodeIPInterface      | RNode reached over IP                         |
| SerialInterface       | Direct serial devices                         |
| KISSInterface         | KISS TNC devices                              |
| I2PInterface          | I2P-based Reticulum transport                 |
| AutoInterface         | Automatic discovery on local networks         |
| HTTPInterface         | HTTP/S tunnel (bundled RNS-over-HTTP)         |
| Custom external types | Advanced setups                               |

Community-curated suggestions come from bundled `community_interfaces.json`, built from [directory.rns.recipes](https://directory.rns.recipes) at release time. An optional `public/community_interfaces.json` override can replace that list locally. The app does not fetch the directory over the network at runtime.

## Interface discovery

Discovery can automatically connect to peers on your LAN or configured networks. You can maintain allowlists and blocklists, set autoconnect behaviour, and assign a network identity for discovered peers.

## Import and export

Export your interface set for backup or clone it to another machine. Import validates entries before applying them.

## RNode tools

LoRa setups often need firmware management. **Tools → RNode Flasher** opens the bundled flasher at `/rnode-flasher/`. Configure frequency, bandwidth, spreading factor, and TX power when adding an RNode interface.

## Websocket server interface

MeshChatX includes a custom `WebsocketServerInterface` for WebSocket-based Reticulum transport. Use it when bridging to web-friendly gateways.

## HTTP tunnel interface

MeshChatX vendors [RNS-over-HTTP](https://github.com/Quad4-Software/RNS-over-HTTP) and installs `HTTPInterface.py` into your Reticulum `interfacepath` on startup. Use **Add interface → HTTP Tunnel** for client or server mode when only HTTP/S egress is available. Default transport is HTTP/1.1. HTTP/2 and HTTP/3 need TLS and optional extra packages on the server side.

## Getting onto the mesh

A minimal path for a new node:

```
Install MeshChatX
    |
    v
Add interface (TCP client, community suggestion, or RNode)
    |
    v
Reticulum establishes transport
    |
    v
Paths and announces populate in the UI
    |
    v
LXMF, LXST, and Nomad features become reachable
```

1. Pick a community interface or ask your mesh operator for TCP endpoint details.
2. Add the interface and enable it.
3. Watch the path table (**Tools → RNPath**) if connectivity fails.
4. Enable **auto-announce** so your services are visible.

## I2P

I2P uses the local router's SAM API (usually `127.0.0.1:7656`). Enable SAM in the router. Do not run Java I2P and i2pd at the same time.

MeshChatX allows one I2P interface, last in the list, with Transport Mode on. New interfaces default `connectable` off. Turn it on only if this node should accept inbound I2P peers. That makes the node an I2P transport. At least one `b32.i2p` peer is required.

## Bundled documentation hints

The Interfaces UI links into the Reticulum manual sections on interface options. Open **Documentation → Reticulum** and search for `interfaces` if you need field-by-field reference.

## Tips

- Run only the interfaces you need. Each open port or radio adds attack surface and power draw.
- On Raspberry Pi and Android, prefer a single well-known TCP uplink if LoRa hardware is not attached.
- After editing Reticulum config externally, use the reload controls or restart MeshChatX so changes apply cleanly.
- Keep firmware on RNodes current using the flasher tool before debugging RF issues.

## See also

- **Installation and setup** for Reticulum config directory flags
- **Tools and utilities** for RNPath, RNProbe, and Ping
- Reticulum manual **Interfaces** chapter for protocol-level detail

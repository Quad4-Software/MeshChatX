# Reticulum interfaces

Interfaces connect your MeshChatX node to the Reticulum mesh. Manage them from the **Interfaces** page.

## What an interface does

Each interface is a Reticulum transport definition. Examples include TCP over the internet, UDP discovery, LoRa through an RNode, serial KISS devices, I2P tunnels, and automatic LAN discovery.

MeshChatX reads and writes interface configuration in your Reticulum config directory (default ~/.reticulum).

## Supported interface types

The **Add interface** flow includes:

| Type                  | Typical use                                   |
| --------------------- | --------------------------------------------- |
| TCPClientInterface    | Connect outbound to a known TCP peer          |
| TCPServerInterface    | Accept inbound TCP connections                |
| BackboneInterface     | High-throughput backbone link                 |
| UDPInterface          | UDP transport with discovery helpers          |
| DNS tunnel (iodine)   | UDPInterface preset riding an iodine tunnel   |
| RNodeInterface        | LoRa via RNode (serial, BLE, or IP transport) |
| RNodeIPInterface      | RNode reached over IP                         |
| SerialInterface       | Direct serial devices                         |
| KISSInterface         | KISS TNC devices                              |
| I2PInterface          | I2P-based Reticulum transport                 |
| AutoInterface         | Automatic discovery on local networks         |
| HTTPInterface         | HTTP/S tunnel (bundled RNS-over-HTTP)         |
| AwareInterface        | WiFi Aware peer links (bundled, Android)      |
| Custom external types | Advanced setups                               |

Community-curated suggestions come from bundled community_interfaces.json, built from [meshchatx.com/api/mcx-interfaces](https://meshchatx.com/api/mcx-interfaces) at release time. Browse listings at [meshchatx.com/interfaces](https://meshchatx.com/interfaces). An optional public/community_interfaces.json override can replace that list locally. The app does not fetch the directory over the network at runtime.

## Interface discovery

Discovery can automatically connect to peers on your LAN or configured networks. You can maintain allowlists and blocklists, set autoconnect behaviour, and assign a network identity for discovered peers.

## Import and export

Export your interface set for backup or clone it to another machine. Import validates entries before applying them.

## RNode tools

LoRa setups often need firmware management. **Tools -> RNode Flasher** opens the bundled flasher at /rnode-flasher/. Configure frequency, bandwidth, spreading factor, and TX power when adding an RNode interface.

## Websocket server interface

MeshChatX includes a custom WebsocketServerInterface for WebSocket-based Reticulum transport. Use it when bridging to web-friendly gateways.

## HTTP tunnel interface

MeshChatX vendors [RNS-over-HTTP](https://github.com/Quad4-Software/RNS-over-HTTP) and installs HTTPInterface.py into your Reticulum interfacepath on startup. Use **Add interface -> HTTP Tunnel** for client or server mode when only HTTP/S egress is available. Default transport is HTTP/1.1. HTTP/2 and HTTP/3 need TLS and optional extra packages on the server side.

## Iodine DNS tunnel

**Add interface -> DNS tunnel (iodine)** is a preset, not a new transport. It fills in a UDPInterface that rides an existing iodine DNS tunnel. MeshChatX does not ship or start iodine. Install it yourself and run it with root privileges, then point the interface at the tunnel IPs.

On the server host:

```
sudo iodined -f -c -P <password> 10.0.0.1 tunnel.example.com
```

This creates the dns0 device at 10.0.0.1 and answers tunnel queries on UDP 53. Add the interface with role **server**. The preset writes a UDPInterface in access_point mode listening on 10.0.0.1 port 6969 and forwarding to the subnet broadcast 10.0.0.255.

On each client:

```
sudo iodine -f -P <password> tunnel.example.com
```

iodine assigns the client a tunnel IP in the same subnet (for example 10.0.0.2). Add the interface with role **client**. The preset writes a UDPInterface in roaming mode listening on 0.0.0.0 port 6969 and forwarding to the server at 10.0.0.1. Any UDP port works; the preset uses 6969 and it stays inside the tunnel, separate from iodine's own DNS traffic.

The tunnel domain field in the UI is a label for your reference only. It is not written to Reticulum config. The delegation that makes iodine work lives in your DNS zone: give the server host an A record, then delegate the tunnel subdomain to it.

```
t1ns.example.com.     A   <server public IP>
tunnel.example.com.   NS  t1ns.example.com.
```

Throughput is low and round trips are long because every packet travels inside DNS queries. The preset caps bitrate at 20000 bps, which matches typical iodine upstream rates; downstream can run faster when the resolver path allows larger record types. Captive portals and some corporate resolvers block or rate-limit the long lookups iodine relies on, so a tunnel that works on one network can stall on another.

On Android there is no bundled iodine client. Run an external app such as AndIodine, which registers as the device VPN service. Android allows one VPN at a time, so the tunnel cannot run alongside another VPN app.

## WiFi Aware interface

On Android, the bundled AwareInterface.py installs into the Reticulum interfacepath alongside HTTPInterface. It drives the same WiFi Aware session as the Nearby page and spawns one interface per established data path. A stanza looks like:

```
[[WiFi Aware]]
  type = AwareInterface
  enabled = yes
  mode = subscribe
  peers = 4
```

`mode` is `publish` (be found, waits for initiators) or `subscribe` (find publishers). `peers` caps concurrent data paths and defaults to 4. The interface only works while the Android local-link bridge is available, so it stays an Android feature. On supported Android builds you can add it from **Add interface -> WiFi Aware**; the tile stays greyed out on desktop and web. For ad-hoc sessions, Tools -> Nearby drives the same underlying session without touching the config.

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
3. Watch the path table (**Tools -> RNPath**) if connectivity fails.
4. Enable **auto-announce** so your services are visible.

## I2P

I2P uses the local router's SAM API (usually 127.0.0.1:7656). Enable SAM in the router. Do not run Java I2P and i2pd at the same time.

MeshChatX allows one I2P interface, last in the list, with Transport Mode on. New interfaces default connectable off. Turn it on only if this node should accept inbound I2P peers. That makes the node an I2P transport. At least one b32.i2p peer is required.

## Bundled documentation hints

The Interfaces UI links into the Reticulum manual sections on interface options. Open **Documentation -> Reticulum** and search for interfaces if you need field-by-field reference.

## Tips

- Run only the interfaces you need. Each open port or radio adds attack surface and power draw.
- On Raspberry Pi and Android, prefer a single well-known TCP uplink if LoRa hardware is not attached.
- After editing Reticulum config externally, use the reload controls or restart MeshChatX so changes apply cleanly.
- Keep firmware on RNodes current using the flasher tool before debugging RF issues.

## See also

- **Installation and setup** for Reticulum config directory flags
- **Tools and utilities** for RNPath, RNProbe, and Ping
- Reticulum manual **Interfaces** chapter for protocol-level detail

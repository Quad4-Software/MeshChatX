# Nearby transports (Android)

The **Nearby** page in Tools links devices that are physically close, so Reticulum peers can find each other without a router, an internet connection, or any account. It is Android-only. On desktop, join the same WiFi network as your peer and an enabled AutoInterface handles discovery the same way.

The page reports what your hardware can do up top: hotspot, specifier join, WiFi Aware, WiFi Direct, NFC, and satellite support. Cards that need hardware your device lacks stay disabled.

## Hotspot join

One device hosts a temporary local hotspot and shows a WiFi QR code on demand. The other device scans the code (or types the credentials) and joins through the Android network picker. Once both share the link-local network, an enabled Auto Interface discovers the peer automatically and normal mesh traffic flows. Nothing routes through the internet.

To host:

1. Open Tools, then Nearby.
2. Grant the Nearby devices permission if asked.
3. Tap **Start hotspot**. Android creates an isolated hotspot with a random name and password.
4. Show the QR code to the other device, or read the credentials out.

The QR code and password are bearer credentials: anyone who sees them can join your hotspot. Show the code only when the peer is ready, use **Rotate credentials** if the code may have leaked, and tap **Stop** when you are done. The hotspot is local-only and gives joined devices no internet access.

To join:

1. On the peer device, open Tools, then Nearby.
2. Tap **Scan join QR** and point the camera at the host's code, or expand manual entry.
3. Confirm the network name in the dialog. Android may also show a system picker. Accept it.

While joined, this app's internet access pauses because its traffic is bound to the local network. The rest of the device is unaffected. Tap **Leave** to return to normal connectivity.

## WiFi Direct group

The **WiFi Direct group** card creates a named group (SSID starts with `DIRECT-mc-`) with a random passphrase. Unlike the temporary hotspot, the group stays up until you stop it and the credentials do not change on restart, which makes it better for a recurring pair of devices. Join it from the other device exactly like the hotspot: the same QR format, the same join flow, the same AutoInterface discovery afterwards.

## WiFi Aware

WiFi Aware (Neighbor Awareness Networking) links two devices directly with no network at all. One side publishes, the other subscribes, and matching devices pair automatically in radio range.

1. Pick **Be found (publish)** on one device and tap **Start Aware**.
2. Pick **Find peers (subscribe)** on the other and tap **Start Aware**.
3. The status line shows discovered peers and established links.

Each session uses a fresh random passphrase, and links carry ordinary Reticulum traffic framed the same way as TCP interfaces. There is also a bundled `AwareInterface` module if you want Aware inside your normal interface configuration: it installs into the Reticulum interfacepath on startup and takes `mode = publish|subscribe` plus a `peers` cap in its stanza. The UI card and the config interface drive the same underlying session.

Aware is a presence signal while it runs: nearby radios can see the service name. Keep sessions short if that matters to you.

## NFC tap

The **NFC tap** card shares the active join credentials between two phones held back to back.

- To share, start a hotspot or WiFi Direct group first, then tap **Share credentials by tap**. The payload is emitted only while the Nearby page is open, and only when a reader actually selects the app. Leave the page or tap **Stop sharing** to end it.
- To receive, tap **Read from device** and hold the phones together. When a payload arrives it appears in the card, and a **Join this network** button runs it through the same confirm dialog as a scanned QR code.

NFC payloads are the same `WIFI:` join codes the QR shows. They contain the network name and password and nothing else. No identity data goes over the tap.

## Satellite posture

On devices with satellite connectivity, MeshChatX declares itself optimized for constrained satellite data so the system may route mesh traffic during a satellite attach. The badge row shows whether the feature exists and whether a satellite link is currently enabled.

Satellite is just another IP path, not a new medium. Existing TCP, backbone, or I2P interfaces ride it unchanged. It is slow and metered though, so on links that might use satellite keep interface bitrate and announce caps low. Satellite traffic is carrier-visible at the metadata level exactly like cellular: Reticulum encryption protects content, not the fact that you are connected.

## Permissions

- Both hotspot host and join need the Nearby devices permission (Android 13+). Older Android versions use the location permission because the OS groups WiFi discovery under location. MeshChatX declares `neverForLocation`, so the nearby grant does not expose your location.
- WiFi Direct groups need the same Nearby devices permission and Android 10 or later.
- WiFi Aware needs Android 8 or later plus hardware support. Check the capability badges.
- NFC needs hardware support. Nothing is emitted unless you start sharing on this screen.

## Security notes

- Never scan a join code or accept an NFC payload from someone you do not trust: joining an unknown network exposes your device to that network's operator.
- The MeshChatX web interface stays bound to loopback on Android, so devices that join your hotspot cannot reach it.
- Credentials are never logged. QR and NFC payloads contain only the network name and password.
- Aware sessions advertise a generic service name with no identity data. Reticulum authenticates peers after the link is up.

## Manual test protocol

The radio paths need real hardware. With two Android devices:

1. Host a hotspot on device A, scan the QR on device B, confirm the join prompt, and verify the connected state on both. Check that Reticulum announces arrive once an Auto Interface is enabled.
2. Start a WiFi Direct group on A, join it from B using the shown credentials, and confirm peers appear.
3. Start Aware publish on A and subscribe on B. Confirm a link count appears on both sides and mesh traffic flows. Stop both and confirm clean teardown.
4. Share credentials over NFC from A to B and confirm B offers the join dialog for the received payload.
5. Rotate hotspot credentials and confirm the old QR no longer joins.
6. Kill and reopen the app mid-session on each transport and confirm status cards reflect reality after refresh.

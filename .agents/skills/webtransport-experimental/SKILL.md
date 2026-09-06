---
name: webtransport-experimental
description: Experimental WebTransport dual-stack for UI live channel. Use when changing LiveTransport, webtransport_sidecar, or live_transport_mode.
---

# Skill: webtransport-experimental

Keep aiohttp for HTTP and WSS. Optional WebTransport is advertised via webtransport_sidecar and client LiveTransport with automatic WebSocket fallback.

## Rules

- Do not replace aiohttp with Hypercorn for this feature.
- Do not move /ws/telephone/audio onto WebTransport datagrams yet.
- Self-signed WebTransport needs a separate short-lived P-256 cert and serverCertificateHashes (webtransport_cert.py).
- Default install keeps sidecar off. WSS must keep working when aioquic is missing.
- Auth/Origin/CSRF boundaries stay the same as /ws.
- Pages that cache live state must REST-resync on websocket-reconnected (gap recovery does not replay events).
- Call sites that still use WebSocketConnection.send ride WT via setLiveSendBridge when LiveTransport is on WebTransport.

## Key files

- meshchatx/src/backend/webtransport_sidecar.py
- meshchatx/src/backend/webtransport_cert.py
- meshchatx/src/frontend/js/liveTransport.js
- meshchatx/src/frontend/js/wsLiveSync.js
- meshchatx/src/frontend/js/WebSocketConnection.js (setLiveSendBridge)

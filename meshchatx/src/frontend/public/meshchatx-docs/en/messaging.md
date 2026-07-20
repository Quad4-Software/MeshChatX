# LXMF messaging

MeshChatX uses LXMF (LXMF Message Format) for direct and store-and-forward messaging over Reticulum. Each identity has an `LXMRouter` registered under aspect `lxmf.delivery`.

## Conversations

Open **Messages** to see your conversation list. Each row is a peer destination you have exchanged traffic with or selected from announces.

The Messages sidebar icon shows a red count when you have unread LXMF conversations. Opening a thread marks it read. If a new message arrives while that thread is already open, it is marked read without needing to switch away and back.

From a conversation you can:

- Send and receive text messages
- Attach images, audio clips, and files
- Reply with quotes and add reactions
- Organise threads into folders and pin important chats
- Run bulk operations on multiple conversations

Incoming messages arrive over the WebSocket as `lxmf_message` events. The UI updates without a full page reload.

## Attachments and rich content

The composer supports:

- **Images** via LXMF image fields
- **Audio** via LXMF audio fields
- **Files** as LXMF file attachments
- **Stickers and GIFs** when enabled in settings
- **User icons** stored as LXMF app data

Large payloads follow LXMF sizing and stamp rules configured in settings.

## Propagation nodes

When a peer is not reachable directly, LXMF can store messages on propagation nodes.

MeshChatX can:

- Run a **local propagation node** on your identity
- **Sync** with remote propagation nodes you trust
- **Auto-select** a preferred node via `AutoPropagationManager`
- **Retry** failed direct deliveries through propagation when configured

Manage nodes from **Tools → Propagation nodes** or related settings entries.

## Stamp costs and stranger protection

LXMF uses work proofs (stamps) to limit abuse. Settings let you tune:

- Outbound stamp costs for your messages
- Inbound stamp requirements for unknown senders
- **Stranger protection** options such as blocking strangers, attachments, or links from unknown peers
- **Flood protection** with dynamic inbound stamp costs based on rate

Raise inbound costs when you operate a public-facing node. Lower them on trusted private meshes.

## Filtering and blocking

- **Blocked** destinations stop traffic from specific hashes.
- **Sieve filters** (beta) drop inbound messages by pattern.
- **Message blocklist** (beta) complements sieve rules for known bad content.
- **Spam reporting** helps you mark unwanted conversations.

## Paper messages

**Tools → Paper message** generates LXMF URIs you can share as QR codes. Another MeshChatX user can ingest the URI to receive the payload. Useful for offline handoff when no live path exists yet.

## Forwarding

`ForwardingManager` supports alias identities that forward messages between peers according to rules you define. Configure forwarding from **Tools → Forwarder**.

## Import and export

You can import and export messages and folder structures for backup or migration. Operations go through the API and respect identity boundaries.

## Local retention

**Local message auto-delete** removes old messages after a configured retention period. Tune this in settings if you operate on storage-constrained hardware.

## Messaging flow

```
Composer in UI
    |
    v
POST /api/v1/lxmf-messages/send
    |
    v
LXMRouter (identity-local)
    |
    +--> Direct path to peer destination
    |
    +--> Propagation node (when direct delivery fails or policy requires it)
    |
    v
Peer LXMF router
    |
    v
WebSocket lxmf_message event on recipient UI
```

## Tips

- Set a **display name** in settings so announces show a friendly label.
- Enable **auto-announce** so your `lxmf.delivery` aspect stays visible on the mesh.
- Check **Interfaces** if messages stall. No path to the peer means LXMF cannot deliver.
- Review stamp settings before joining busy public meshes.

## See also

- **Reticulum interfaces** for connectivity
- **Identities, privacy, and security** for auth and HTTPS
- Reticulum manual section on LXMF for protocol detail

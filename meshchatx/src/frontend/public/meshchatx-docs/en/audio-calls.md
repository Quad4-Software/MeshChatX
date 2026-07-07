# Audio calls (LXST)

MeshChatX uses LXST for voice telephony over Reticulum. Telephone functionality is optional and controlled per identity in settings.

## Enable telephony

Turn on **telephone** in settings before using the **Call** page. MeshChatX announces your callable destination under aspect `lxst.telephony` when announcing is enabled.

Peers who announce the same aspect appear as callable contacts.

## Placing and receiving calls

From **Call** or a contact entry you can:

- **Dial** another identity by hash
- **Answer** or **decline** inbound rings
- **Hang up** an active session
- **Mute** transmit or receive paths

Call state changes arrive over the WebSocket (`telephone_ringing`, `telephone_call_established`, `telephone_call_ended`, and related events).

## Audio path

The frontend loads Codec2 assets for voice encoding (`Codec2Loader.js`). Browser and Electron builds use a Web Audio bridge at `/ws/telephone/audio`. Packaged desktop builds bundle the backend that negotiates LXST sessions.

## Voicemail

When you miss a call, voicemail may be offered depending on settings:

- Record a custom greeting
- Upload or generate greeting audio
- Play back messages left for you

Voicemail events surface as `new_voicemail` on the WebSocket.

## Call history and recordings

The **Call** area keeps history of placed, received, and missed calls. You can record calls when the feature is enabled and policy allows storage on your device.

## Ringtones

Upload custom ringtones and assign them per contact. Default sounds are used when no override exists.

## Do not disturb and contacts-only

Settings support:

- **Do not disturb** to silence inbound rings
- **Contacts-only** mode to reject calls from unknown hashes

Combine these with the **Blocked** list for finer control.

## Telephone contacts

Import and export telephone contacts separately from LXMF conversation peers. Contacts drive caller display names and ringtone overrides.

## Call setup flow

```
Caller UI: initiate call
    |
    v
GET /api/v1/telephone/call/{identity_hash}
    |
    v
LXST Telephone session over Reticulum
    |
    +--> Signalling and media via LXST
    |
    +--> /ws/telephone/audio (browser audio bridge)
    |
    v
Callee UI: ring, answer, or decline
```

## Tips

- Verify **Interfaces** and paths before troubleshooting audio quality. Packet loss on the mesh affects voice.
- Use headphones on mobile and Quest builds to prevent echo.
- Review microphone permissions in Electron or the Android system settings if the UI shows no input level.
- Keep LXST and Reticulum versions aligned with MeshChatX release notes when upgrading.

## See also

- **LXMF messaging** for text conversations with the same peers
- **Identities, privacy, and security** for HTTPS and local access controls
- LXST project documentation for codec and session details

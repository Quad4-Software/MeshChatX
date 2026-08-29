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
- **Mute** microphone (transmit) or speaker (receive)
- Switch **full duplex** or **half duplex** during a live call
- Use **push-to-talk** while in half duplex (hold the PTT control or Space)

Half duplex uses LXST packetizer squelch so idle airtime stays low on constrained links. Full duplex keeps both directions open.

Call state changes arrive over the WebSocket (`telephone_ringing`, `telephone_call_established`, `telephone_call_ended`, and related events).

While connected, the Call screen shows link stats (packets, bytes, approximate bitrates, path hops, and interface).

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

Unread missed calls show as a red count on the Calls sidebar icon and the header phone button. Opening the Call page clears that count. Desktop and Android still show a one-shot missed-call notification when the event happens.

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

## Windows microphone (Electron, Windows 10 / 11)

Calls and voice attachments use the mic through Chromium. If the UI has no access or `getUserMedia` fails, check Windows privacy first. That is a common miss for Win32 apps, Electron included.

1. Win+R, paste `ms-settings:privacy-microphone`, Enter.
2. Turn Microphone access on.
3. Enable Let desktop apps access your microphone (wording varies by Windows version).
4. If a per-app list appears, make sure MeshChatX is not denied.

Also check Settings, System, Sound so the app is not muted and a working input device is selected.

## Tips

- Verify **Interfaces** and paths before troubleshooting audio quality. Packet loss on the mesh affects voice.
- Use headphones on mobile and Quest builds to prevent echo.
- Review microphone permissions in Electron or the Android system settings if the UI shows no input level.
- Keep LXST and Reticulum versions aligned with MeshChatX release notes when upgrading.
- **Docker / headless web**: containers have no PulseAudio host devices. MeshChatX forces the web audio bridge (`MESHCHAT_FORCE_WEB_AUDIO=1`) and installs hostless LXST backends so calls can use the browser mic/speaker. Enable telephone in settings, then place a call from the web UI over HTTPS.
- **Android Codec2**: native `libcodec2.so` must be preloaded before `pycodec2`. If Codec2 profiles are hidden, check `/api/v1/telephone/codec2/status` and rebuild with vendor wheels that bundle `pycodec2/libcodec2.so`.

## See also

- **LXMF messaging** for text conversations with the same peers
- **Identities, privacy, and security** for HTTPS and local access controls
- LXST project documentation for codec and session details

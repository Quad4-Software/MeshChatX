# Skill: lxst-telephony

Change LXST telephony or call audio without treating MeshChatX as a cloud PBX or leaking identity-scoped call state.

## When to use

- TelephoneManager, call setup/teardown, ringing, voicemail
- `/ws/telephone/audio` or related audio bridges
- Adversarial or security tests for telephony
- UI call screens and permissions

## Intent

LXST runs over Reticulum Links. Address callees by identity/destination hash. No mandatory TURN/SIP cloud for core calls. Local HTTPS UI is control plane for this device only.

## Key paths

| Area               | Path                                                              |
| ------------------ | ----------------------------------------------------------------- |
| Telephony managers | `meshchatx/src/backend/` telephone / ringtone / voicemail modules |
| Identity wiring    | `meshchatx/src/backend/identity_context.py`                       |
| Adversarial tests  | `tests/backend/test_lxst_telephony_adversarial.py`                |
| Frontend call UI   | telephone-related Vue components under `meshchatx/src/frontend/`  |

## Gates

1. Tear down call and audio resources on identity switch.
2. Do not block the whole UI on real-time ACK over constrained links. Show recoverable call states.
3. Auth-guard WS mutators that start or answer calls when password auth is enabled.
4. Keep audio paths identity-scoped. No shared in-memory call tables across identities.
5. Prefer half duplex + PTT (LXST packetizer squelch) on scarce links instead of always full duplex.

## Verification

```bash
uv run pytest tests/backend/test_lxst_telephony_adversarial.py tests/backend/test_telephone_duplex_ptt.py -q --tb=short
```

Also: `reticulum-design-gates`, `auth-csrf-ws-security`, `identity-switch-teardown`.

## LXST 0.5 duplex / PTT

| Control            | LXST API                                   | MeshChatX surface                                    |
| ------------------ | ------------------------------------------ | ---------------------------------------------------- |
| Full / half duplex | `Telephone.switch_mode`, `Profiles.MODE_*` | `POST /api/v1/telephone/switch-call-mode/{mode_id}`  |
| PTT (half duplex)  | `squelch_transmit` / `unsquelch_transmit`  | `POST /api/v1/telephone/ptt` with `{"active": bool}` |
| Mute mic / speaker | `mute_transmit` / `mute_receive`           | existing mute endpoints                              |
| Live stats         | RNS Link counters on `active_call`         | `/api/v1/telephone/status` `tx_*` / `rx_*` / `*_bps` |

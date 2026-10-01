# pair-messaging

Two real MeshChatX instances exchange LXMF traffic over a live link.
Alice runs the dev stack on http://127.0.0.1:5173, Bob runs on
http://127.0.0.1:18081. Both announce before the scenario starts.

Shared state lives in tests/agentic/out/pairshare/pair.json:
{ "alice": {"url","api","lxmf_address"}, "bob": {"url","lxmf_address"} }

Rules for both agents:
- Drive the UI with your browser tools (navigate, snapshot, click, fill).
- Never send real API calls outside the UI unless the step says so.
- A message counts as delivered only when it renders in the peer's
  conversation view, not when the send button stops spinning.
- Record every pageerror, console error, and 5xx you observe.

## Steps

alice.ready: read pair.json, load your /#/messages page, confirm it renders.
alice.sent: open the conversation with Bob's lxmf_address, type
  "PAIR-HELLO-<unix seconds>", send it, confirm it shows in the thread.
bob.reply: wait for alice.sent, find the PAIR-HELLO message in your
  conversations, open the thread, reply with "PAIR-PONG-<unix seconds>".
alice.reply: wait for bob.reply, confirm the PAIR-PONG reply rendered in
  the same conversation.
alice.attach: send Bob a small file through the composer attachment
  control if one exists; if not, send "ATTACHMENT-SKIP" and note it.
bob.attach: wait for alice.attach, confirm the attachment card (or the
  ATTACHMENT-SKIP message) renders, try to open/download the file.
alice.call: look for a call/dial control in the conversation; if found,
  click it, wait a few seconds, snapshot, then hang up or dismiss.
bob.call: wait for alice.call, report whether an incoming-call UI
  appeared (banner, ring screen, accept/decline). Accept or decline.

```agentic
{
  "pair": true,
  "global_timeout_s": 1500,
  "agents": {
    "alice": { "browser": "chromium", "tools": "playwright" },
    "bob":   { "browser": "firefox",  "tools": "playwright-firefox" }
  },
  "markers": [
    { "id": "alice.ready",  "owner": "alice", "timeout_s": 120 },
    { "id": "bob.ready",    "owner": "bob",   "timeout_s": 120 },
    { "id": "alice.sent",   "owner": "alice", "after": ["alice.ready", "bob.ready"], "timeout_s": 240 },
    { "id": "bob.reply",    "owner": "bob",   "after": ["alice.sent"],   "timeout_s": 300 },
    { "id": "alice.reply",  "owner": "alice", "after": ["bob.reply"],    "timeout_s": 300 },
    { "id": "alice.attach", "owner": "alice", "after": ["alice.reply"],  "timeout_s": 240 },
    { "id": "bob.attach",   "owner": "bob",   "after": ["alice.attach"], "timeout_s": 300 },
    { "id": "alice.call",   "owner": "alice", "after": ["bob.attach"],   "timeout_s": 240 },
    { "id": "bob.call",     "owner": "bob",   "after": ["alice.call"],   "timeout_s": 300 }
  ]
}
```

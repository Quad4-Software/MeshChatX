# pair-features

Two real MeshChatX instances exercise the mesh features end to end:
file sync, remote copy, remote shell, and propagation-node delivery.
Alice runs the dev stack on http://127.0.0.1:5173 (backend API
http://127.0.0.1:18079), Bob runs on http://127.0.0.1:18081.

Shared state lives in tests/agentic/out/pairshare/pair.json:
{ "alice": {"url","api","lxmf_address"}, "bob": {"url","lxmf_address"} }

Both agents may use fetch() in the browser console against their own
backend API when a step calls for an API action; remember CSRF requires
a session cookie plus the X-CSRF-Token header from /api/v1/auth/csrf.
Feature work otherwise happens through the UI where a page exists.

## Steps

alice.ready / bob.ready: read pair.json, load your app root, confirm it
  renders without console errors.

bob.filesync-host: on Bob's /#/rns-filesync page, start file sync (or
  POST /api/v1/filesync/start), upload a small text file named
  pair-note.txt with content "pair filesync <ts>", then announce
  (POST /api/v1/filesync/announce). Record your filesync peer/destination
  hash if the status endpoint reports one.
alice.filesync-get: wait for bob.filesync-host. Browse Bob's share via
  POST /api/v1/filesync/browse {"peer_id": "<bob peer or dest hash>"}
  then POST /api/v1/filesync/download {"peer_id": ..., "path":
  "pair-note.txt"}. Confirm the content matches.

bob.rncp-listen: POST /api/v1/rncp/listen {"fetch_allowed": true} and
  record the destination_hash it returns into your marker content.
alice.rncp-send: wait for bob.rncp-listen; read the destination hash
  from Bob's marker file, write a small file through the UI download
  area or POST /api/v1/rncp/send {"destination_hash": ...,
  "file_path": <path under out/pairshare>} and confirm completion.

bob.propnode: on Bob, enable the local propagation node
  (POST /api/v1/lxmf/propagation-node/start) and confirm status reports
  it running.
alice.propnode-send: wait for bob.propnode. Set Bob as the outbound
  propagation node (PATCH config lxmf_preferred_propagation_node or via
  the propagation UI), send Bob a message containing "PROP-<ts>", and
  confirm Bob received it via propagation rather than direct link.
bob.propsync: wait for alice.propnode-send. Trigger inbound sync
  (POST /api/v1/lxmf/propagation-node/sync) and confirm the PROP message
  is present in the conversation with Alice.

bob.rnsh-listen: POST /api/v1/rnsh/sessions with listen mode (no
  destination) and read the listener destination hash from the session
  output tail; put it in your marker content.
alice.rnsh: wait for bob.rnsh-listen; read the listener hash from Bob's
  marker, POST /api/v1/rnsh/sessions {"destination": <hash>,
  "remote_command": "echo pair-rnsh-ok"}, then poll the session output
  endpoint until "pair-rnsh-ok" appears.

```agentic
{
  "pair": true,
  "global_timeout_s": 2400,
  "agents": {
    "alice": { "browser": "chromium", "tools": "playwright" },
    "bob":   { "browser": "firefox",  "tools": "playwright-firefox" }
  },
  "markers": [
    { "id": "alice.ready",          "owner": "alice", "timeout_s": 120 },
    { "id": "bob.ready",            "owner": "bob",   "timeout_s": 120 },
    { "id": "bob.filesync-host",    "owner": "bob",   "after": ["bob.ready"], "timeout_s": 300 },
    { "id": "alice.filesync-get",   "owner": "alice", "after": ["bob.filesync-host"], "timeout_s": 300 },
    { "id": "bob.rncp-listen",      "owner": "bob",   "after": ["bob.ready"], "timeout_s": 240 },
    { "id": "alice.rncp-send",      "owner": "alice", "after": ["bob.rncp-listen"], "timeout_s": 300 },
    { "id": "bob.propnode",         "owner": "bob",   "after": ["bob.ready"], "timeout_s": 240 },
    { "id": "alice.propnode-send",  "owner": "alice", "after": ["bob.propnode"], "timeout_s": 300 },
    { "id": "bob.propsync",         "owner": "bob",   "after": ["alice.propnode-send"], "timeout_s": 300 },
    { "id": "bob.rnsh-listen",      "owner": "bob",   "after": ["bob.ready"], "timeout_s": 240 },
    { "id": "alice.rnsh",           "owner": "alice", "after": ["bob.rnsh-listen"], "timeout_s": 300 }
  ]
}
```

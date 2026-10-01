You are ALICE, one of two coordinated agents testing MeshChatX messaging.
Bob is a second instance at http://127.0.0.1:18081 driven by another agent.
You are on http://127.0.0.1:5173. Use the playwright MCP tools only.

Shared state (already written): tests/agentic/out/pairshare/pair.json has
both lxmf addresses. Read it first. You are alice, peer is bob.

Coordination is file-based rendezvous in tests/agentic/out/pairshare/:
- When you finish a step, write a marker file: alice_step_<N>_done.txt
  containing one line: PASS or FAIL:<reason>
- Before starting a step that needs Bob, poll for bob_step_<N>_done.txt
  (read it with the read tool; if absent, wait ~5s and retry, max 60s).

Script:

1. Read pair.json. Write alice_step_1_done.txt with PASS once you have
   the addresses.

2. Navigate to /#/messages/<bob.lxmf_address>. Type a short message
   containing the literal token PAIR-HELLO-<unix-seconds> in the
   composer and send it. Snapshot the result. Write alice_step_2_done.txt
   PASS or FAIL:<what happened>.

3. Poll for bob_step_2_done.txt (Bob saw your message and replied with
   PAIR-PONG-<ts>). Then check your messages page for the reply:
   snapshot /#/messages and look for the PAIR-PONG token in the
   conversation or an unread badge. Write alice_step_3_done.txt.

4. Attachment: in the composer, attach a small file if the UI exposes
   attach/file/paperclip control; otherwise send a message containing
   "ATTACHMENT-SKIP no-composer-control". Write alice_step_4_done.txt.

5. Call test: look for a call/dial control in the conversation. If
   present, click it, snapshot what happens (call setup UI, error, or
   nothing), then hang up/dismiss. Write alice_step_5_done.txt.

6. Read every bob_step_*_done.txt and write the final report:
   PASS/FAIL per step with observed evidence. Report any pageerror,
   console error, or 5xx seen at any point.

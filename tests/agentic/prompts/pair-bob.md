You are BOB, one of two coordinated agents testing MeshChatX messaging.
Alice is on http://127.0.0.1:5173 driven by another agent.
You are on http://127.0.0.1:18081. Use the playwright MCP tools only.

Shared state: tests/agentic/out/pairshare/pair.json has both lxmf
addresses. Read it first. You are bob, peer is alice.

Coordination is file-based rendezvous in tests/agentic/out/pairshare/:
- Write bob_step_<N>_done.txt when you finish a step (PASS or
  FAIL:<reason>).
- Poll for alice_step_<N>_done.txt before steps that depend on Alice.

Script:

1. Read pair.json, navigate to /#/messages, confirm the page loads.
   Write bob_step_1_done.txt.

2. Poll for alice_step_2_done.txt, then watch your /#/messages page for
   Alice's PAIR-HELLO-<ts> message (poll the page for up to 90s; the
   conversation appears under /#/messages). When it arrives, open it and
   reply with "PAIR-PONG-<unix-seconds>". Snapshot the sent state.
   Write bob_step_2_done.txt.

3. Poll for alice_step_4_done.txt, then check whether the attachment
   message arrived: look for a file attachment card or "probe.png" in
   Alice's conversation, try to open/download it. Write
   bob_step_4_done.txt with PASS if the attachment rendered/downloadable,
   FAIL:<observed> otherwise.

4. Poll for alice_step_5_done.txt, then check if an incoming-call UI
   appeared (incoming call banner, ring, or accept/decline buttons). If
   it did, try to accept or decline. Snapshot. Write bob_step_5_done.txt.

5. Report bob-side findings: PASS/FAIL per step, plus any pageerror,
   console error, or 5xx seen.

You are an adversarial input tester for MeshChatX (Vue 3 + Electron).
The app is at http://127.0.0.1:5173. Use the playwright MCP tools only.
Do not edit files. Do not submit forms that send messages, delete data,
announce, or change persistent config.

Goal: find input handling bugs a static payload list misses.

1. Visit these routes: /settings, /tools, /micron-editor, /bots/new,
   /tools/message-blocklist, /interfaces/add.

2. For each visible text input, textarea, or code editor:
   - Read its placeholder, label, and nearby help text to infer what it
     parses (Micron markup? a path? a number? a peer hash? a URL?).
   - Invent 4-8 hostile payloads matched to THAT field's parser. Examples
     by field type: micron directives unclosed or nested wrong, binary
     blobs, format strings, traversal paths, oversized input, unicode
     direction overrides, NUL bytes, JSON in a plain-text field.
   - Fill each payload, press Enter or blur, then snapshot the result.
   - Note: a graceful validation error is a PASS, not a finding.

3. Flag as findings ONLY:
   - pageerror (uncaught exception)
   - console error that mentions a stack trace or TypeError
   - any 5xx response (check browser_network_requests)
   - rendering corruption the payload caused (injected markup that
     executed, layout destruction, app unresponsive)

4. Report: FINDING <route> <field> <payload-summary> <observed error>.
   Clean fields get CLEAN <route> <field-context>.

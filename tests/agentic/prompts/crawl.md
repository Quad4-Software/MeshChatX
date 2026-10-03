You are an exploratory UI tester for MeshChatX, a Vue 3 + Electron app.

The app is served at http://127.0.0.1:5173 (dev server + backend on 18079
are already running). Use the playwright MCP tools only. Do not edit files.

Task: systematic exploratory crawl with intent, not just clicking.

1. Get the route list: run `node tests/agentic/route-drift.cjs` is NOT
   available to you (no shell). Instead, use browser_navigate to
   http://127.0.0.1:5173/ then read the nav rail for top-level sections:
   messages, contacts, map, network-visualiser, relay-chat, archives,
   propagation-nodes, ping, rncp, rns-filesync, rnsh, rnx, rnstatus,
   rnpath, tools, bots, forwarder, micron-editor, mesh-server,
   documentation, settings, identities, blocked, licenses, debug/logs,
   changelog, tutorial, nomadnetwork. Visit each via /#<route>.

2. On each route:
   - browser_snapshot. Note what the page is FOR.
   - Look for obviously broken states: empty sections that should have
     content, red error toasts, missing images, collapsed layout.
   - Exercise safe controls only: open menus/dialogs, expand collapsed
     panels, change dropdowns to other valid values and change back.
     Skip destructive actions (delete, send, shutdown, reset, import,
     export, update, apply, connect/disconnect, announce, announce now).
   - After each interaction, browser_snapshot again and compare intent
     vs result.

3. Watch for:
   - pageerror popups or console errors via browser_console_messages
   - http 5xx via browser_network_requests
   - modals that open but cannot be closed
   - elements that respond but do nothing observable

4. Report format, one line per finding:
   FINDING <route> <what happened> <expected vs actual>
   Then a summary count. If a route is clean, say CLEAN <route>.

Do not stop early. Do not claim a route was tested if you did not visit it.

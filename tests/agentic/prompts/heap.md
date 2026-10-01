You are investigating heap growth in MeshChatX, a Vue 3 app.

The deterministic profiler ran first:
  node tests/agentic/heap-profiler.cjs --json tests/agentic/out/heap.json

1. Read tests/agentic/out/heap.json. It lists per-route retained heap
   before/after clicking safe buttons with GC in between. Routes where
   delta exceeds the budget are the suspects.

2. For each OVER route, correlate the growth with what the route does:
   - Look at the clicked buttons and what they open (menus, dialogs,
     lazy components).
   - In the running app, redo the interaction manually via the
     playwright MCP: snapshot before, click, snapshot after, and use
     browser_evaluate to read performance.memory.usedJSHeapSize before
     and after each single click to isolate which control leaks.
   - Common leak shapes: event listeners on detached nodes, watchers on
     unmounted components, cached blobs in vue refs, wsEventRegistry
     handlers not unsubscribed.

3. For each confirmed leak, report:
   - route, control, heap delta per click (bytes)
   - the likely owner (component or composable name, file path)
   - whether it grows per-click (listener leak) or once (lazy init cache)

4. Do not fix code. Output findings only.

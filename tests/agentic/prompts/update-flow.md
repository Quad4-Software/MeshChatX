You are verifying the MeshChatX signed update apply path end to end.

What is true about the system under test (do not re-derive it):
- The backend stages verified artifacts under <storage>/updates/pending/
  and writes <storage>/updates/pending.json with file, sha256, size,
  kind, platform, arch, version.
- Electron main reads that marker itself in the update-apply IPC handler
  and swaps the payload over process.env.APPIMAGE, backs up to .bak,
  clears the marker, and relaunches.
- The renderer (Updates settings section) calls window.electron.applyUpdate()
  with NO arguments. Any renderer-supplied path must be ignored.

Your task, in order:

1. Run the deterministic check first:
   `node tests/agentic/electron-update-flow.cjs`
   (you may use the shell tool for this; it needs a built frontend and
   xvfb on headless Linux. If it cannot launch Electron, report that as
   ENVIRONMENT and continue to step 2.)

2. Drive the UI path in the launched app: navigate to /#/settings,
   Maintenance tab, Updates section. Verify the pending banner shows
   version 99.0.0 and the staged filename. Click Restart to apply.
   The app should relaunch.

3. After relaunch, verify on disk:
   - the fake AppImage content matches the staged payload
   - updates/pending.json is gone
   - <appimage>.bak contains the old bytes

4. Attempt these hostile variants by crafting markers directly:
   - pending.json with file:"../escape.AppImage" -> expect bad_pending_marker
   - marker sha256 that does not match staged bytes -> expect sha256_mismatch
   - kind:"deb" -> expect unsupported_kind
   - path key in the marker pointing outside pending/ -> must be ignored;
     the basename of "file" is the only thing used

Report each step PASS/FAIL with the observed result. The update system
must fail closed: any invalid marker must NOT touch the target file.

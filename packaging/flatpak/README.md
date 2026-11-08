# Flatpak packaging files

This directory holds the AppStream metainfo, desktop entry, and icon for the
Wails desktop shell (`com.meshchatx.app`).

The release pipeline builds the `.flatpak` bundle with `flatpak-builder` via
`scripts/ci/github-build-linux-flatpak.sh`, which expects a source manifest at
`packaging/flatpak/manifest.json` that:

- builds the Go/Wails shell (`desktop/`, `wails3 build`, GTK4 + WebKitGTK 6.0
  runtime),
- bundles the frozen Python backend under `backend/` beside the shell binary,
- installs the metainfo, desktop entry, and icon files from this directory.

Runtime dependencies: `gtk4`, `webkitgtk-6.0`, `libsoup3`.

<!-- SPDX-License-Identifier: 0BSD -->

# Flatpak packaging

This directory holds the AppStream metainfo, desktop entry, and icon used for Flatpak builds. The release pipeline builds the `.flatpak` bundle with `electron-builder` using the `flatpak` target in `package.json`.

## Files

- `com.meshchatx.app.metainfo.xml` — AppStream metadata for app stores and `appstream-compose`.
- `com.meshchatx.app.desktop` — Desktop entry used by manual `flatpak-builder` workflows.
- `com.meshchatx.app.png` — 512x512 icon for hicolor icon themes.

## Release build

The CI pipeline in `.github/workflows/build-release.yml` runs:

```bash
bash scripts/ci/github-build-linux-flatpak.sh
```

This uses `package.json` `build.flatpak` settings and produces `dist/*.flatpak`.

## Manual source build

A full `flatpak-builder` source manifest is not tracked here because the release pipeline uses `electron-builder`. To build from source with `flatpak-builder`, create a manifest that runs the `electron-builder` Flatpak target or repacks a `dist/linux-unpacked` tree, then installs the metainfo, desktop, and icon files from this directory.

## OSTree remote

Release flatpaks are published as an OSTree remote at `https://cdn.quad4.io/flatpak/`:

```bash
flatpak install --from https://cdn.quad4.io/flatpak/meshchatx-stable.flatpakref
flatpak run com.meshchatx.app
```

For details, see `docs/en/installation.md`.

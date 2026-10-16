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

Release flatpaks are published as an OSTree remote on GitHub Pages:

```bash
flatpak install --from https://quad4-software.github.io/MeshChatX/flatpak/meshchatx-stable.flatpakref
flatpak run com.meshchatx.app
```

For details, see `docs/en/installation.md`.

## Publishing

The `flatpak-pages` job in `.github/workflows/build-release.yml` runs
`scripts/ci/github-publish-flatpak-pages.sh` on every release tag except
`nightly-*` and `testing-*`. The job is best effort (`continue-on-error`) and
can be retried without a new tag via the `flatpak-pages` workflow
(`workflow_dispatch`, input: tag).

One-time repository setup:

- Settings > Pages: set source to the `gh-pages` branch, root `/`. The
  workflow creates the branch on first publish.
- Secrets: `FLATPAK_GPG_PRIVATE_KEY` and `FLATPAK_GPG_PASSPHRASE` for signing
  the OSTree commits and summary.
- Optional repository variable `FLATPAK_REPO_BASE_URL` when Pages is served
  from a custom domain; default is
  `https://<owner>.github.io/<repo>/flatpak` derived from
  `GITHUB_REPOSITORY`.

Size limits: GitHub Pages allows about 1 GB per site and 100 MB per file.
The publish script fails when a single file exceeds 95 MB or the site
exceeds 900 MB. The export prunes OSTree history to depth 1 and skips
static deltas to stay under the limit.

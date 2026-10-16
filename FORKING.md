# Forking MeshChatX

## Rebrand

1. Edit `brand.json` at the repo root. It is the single source of truth for
   the product name, slug, app id, repository slug, URLs, container images,
   and security contact.
2. Run `pnpm run brand:check` (or `task brand:check`). It lists every file
   that still carries the old literal value, with the expected replacement.

## What is derived automatically

- CI uses `github.repository` and `github.repository_owner`, so workflow
  release URLs, the flatpak Pages URL, and the torrent webseed API/download
  endpoints follow the fork remote without edits.
- `scripts/ci/make-release-torrent.py`, `scripts/ci/build-apk-package.sh`,
  `scripts/rpi/install_meshchatx.sh`, and `scripts/ci/github-flatpak-ostree-export.sh`
  read `GITHUB_REPOSITORY` or `brand.json`.
- `FLATPAK_REPO_BASE_URL` defaults to `https://<owner>.github.io/<repo>/flatpak`.

## Literal surfaces enforced by brand:check

Dockerfiles' OCI source label (via ARG `OCI_SOURCE`), compose files
(`docker/docker-compose*.yml`), `helm/meshchatx/values.yaml` and
`Chart.yaml`, `ansible/meshchatx/defaults/main.yml`, `proxmox/build-*.sh`,
`packaging/arch/PKGBUILD`, `packaging/flatpak/*`, `pyproject.toml`,
`SECURITY.md`, `android/app/build.gradle`, `package.json`,
`meshchatx/src/frontend/public/manifest.json`, `index.html`, and
`helm/meshchatx/Chart.yaml`. These stay literal; the drift check names any
file that diverges from `brand.json`.

## Secrets and variables a fork must set

Secrets referenced by workflows:

- `FLATPAK_GPG_PRIVATE_KEY`, `FLATPAK_GPG_PASSPHRASE` (Flatpak OSTree signing).
- `ANDROID_SIGNING_KEYSTORE_BASE64`, `ANDROID_SIGNING_KEYSTORE_PASSWORD`,
  `ANDROID_SIGNING_KEY_ALIAS`, `ANDROID_SIGNING_KEY_PASSWORD` (APK signing).
- `COSIGN_PRIVATE_KEY`, `COSIGN_PASSWORD` (repository-key asset signing;
  replace `cosign.pub` to match).
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (Docker Hub publishing).

Variables: `DOCKERHUB_REPOSITORY`, `FLATPAK_REPO_BASE_URL`,
.

## GitHub Pages flatpak repo

Settings > Pages > source: `gh-pages` branch, root `/`. The `flatpak-pages`
job and the `flatpak-pages` retry workflow publish there automatically.

## Not brand strings

These are content, not renames: `cosign.pub`, `openvex.json` purls, GPG keys,
the bundled Reticulum docs, `THIRD_PARTY_NOTICES.txt`, license files, and
contributor credits. Keep authorship, `LICENSE`, and copyright notices.
Upstream project links (Micron-Parser-Go, LXMF, RNS, and other
Quad4-Software repositories that are not this app) stay as they are.

## Runtime endpoints

The app contacts project-operated services at runtime (interface directory,
translation catalog, and similar). They are listed in the codebase and are
the fork's choice to keep or repoint.

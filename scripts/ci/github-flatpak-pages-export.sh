#!/usr/bin/env bash
# SPDX-License-Identifier: 0BSD
# Import a single-file Flatpak bundle into an OSTree archive repo and write
# Pages artifacts (.flatpakref, .flatpakrepo, landing page).
#
# Usage: github-flatpak-pages-export.sh BUNDLE_PATH OUTPUT_DIR
#
# Environment:
#   GITHUB_REPOSITORY  owner/repo (required unless PAGES_URL is set)
#   PAGES_URL          optional override for https://owner.github.io/repo
#   GPG_FINGERPRINT    optional GPG key id for signing commits and summary
set -euo pipefail

BUNDLE="${1:?usage: $0 BUNDLE_PATH OUTPUT_DIR}"
OUT="${2:?usage: $0 BUNDLE_PATH OUTPUT_DIR}"

if [[ ! -f "$BUNDLE" ]]; then
    echo "Bundle not found: $BUNDLE" >&2
    exit 1
fi

if [[ -z "${GITHUB_REPOSITORY:-}" ]] && [[ -z "${PAGES_URL:-}" ]]; then
    echo "Set GITHUB_REPOSITORY or PAGES_URL" >&2
    exit 1
fi

if [[ -n "${PAGES_URL:-}" ]]; then
    pages_url="${PAGES_URL%/}"
else
    owner="${GITHUB_REPOSITORY%%/*}"
    repo="${GITHUB_REPOSITORY#*/}"
    pages_url="https://${owner,,}.github.io/${repo}"
fi

repo_url="${pages_url}/repo"
repo_path="${OUT}/repo"
mkdir -p "$OUT"

if [[ ! -f "${repo_path}/config" ]]; then
    ostree --repo="${repo_path}" init --mode=archive-z2
fi

if curl -sf --max-time 60 -o /dev/null "${repo_url}/summary"; then
    echo "Pulling existing ostree repo from ${repo_url}"
    ostree --repo="${repo_path}" remote-add --if-not-exists --no-gpg-verify meshchatx-prev "${repo_url}" || true
    if ostree --repo="${repo_path}" pull meshchatx-prev --mirror --depth=-1 --commit-only 2>/dev/null; then
        echo "Restored prior ostree commits from live Pages"
    else
        echo "Live summary present but pull failed, continuing with local repo" >&2
    fi
    ostree --repo="${repo_path}" remote-delete meshchatx-prev 2>/dev/null || true
fi

gpg_args=()
update_args=()
if [[ -n "${GPG_FINGERPRINT:-}" ]]; then
    gpg_args=(--gpg-sign="${GPG_FINGERPRINT}")
    update_args=(--gpg-sign="${GPG_FINGERPRINT}")
fi

flatpak build-import-bundle "${gpg_args[@]}" "${repo_path}" "${BUNDLE}"

flatpak build-update-repo \
    "${update_args[@]}" \
    --generate-static-deltas \
    --prune \
    --prune-depth=20 \
    "${repo_path}"

mapfile -t refs < <(ostree --repo="${repo_path}" refs | grep '^app/' || true)
if [[ ${#refs[@]} -eq 0 ]]; then
    echo "No app/ ref found after import" >&2
    exit 1
fi

ref="${refs[0]}"
appid="${ref#app/}"
appid="${appid%%/*}"
arch="${ref#app/"${appid}"/}"
arch="${arch%%/*}"
branch="${ref##*/}"

echo "Imported ref: ${ref}"
echo "appid=${appid}"
echo "arch=${arch}"
echo "branch=${branch}"

touch "${OUT}/.nojekyll"

gpg_key_line=""
if [[ -n "${GPG_FINGERPRINT:-}" ]]; then
    gpg_key_line="GPGKey=$(gpg --export "${GPG_FINGERPRINT}" | base64 -w0)"
fi

cat >"${OUT}/meshchatx.flatpakref" <<EOF
[Flatpak Ref]
Title=Reticulum MeshChatX
Name=${appid}
Branch=${branch}
Url=${repo_url}
SuggestRemoteName=meshchatx
Homepage=https://meshchatx.com
Icon=${appid}
RuntimeRepo=https://dl.flathub.org/repo/flathub.flatpakrepo
IsRuntime=false
${gpg_key_line}
EOF

cat >"${OUT}/meshchatx.flatpakrepo" <<EOF
[Flatpak Repo]
Version=1
Title=MeshChatX
Homepage=https://meshchatx.com
Comment=Reticulum MeshChatX Flatpak repository
Description=Mesh networking chat client powered by the Reticulum Network Stack
Icon=${appid}
Url=${repo_url}
SuggestRemoteName=meshchatx
${gpg_key_line}
EOF

cat >"${OUT}/index.html" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MeshChatX Flatpak</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 44rem; margin: 3rem auto; padding: 0 1rem; line-height: 1.5; }
    code, pre { background: #f4f4f5; border-radius: 6px; }
    code { padding: .1em .35em; }
    pre { padding: 1rem; overflow-x: auto; }
    h1 { margin-bottom: .2rem; }
  </style>
</head>
<body>
  <h1>MeshChatX Flatpak</h1>
  <p>Install once from this repository, then run <code>flatpak update</code> for new releases.</p>
  <h2>Install</h2>
  <pre>flatpak install --from ${pages_url}/meshchatx.flatpakref</pre>
  <p>Then run <code>flatpak run ${appid}</code> or launch from your app menu.</p>
  <h2>Update</h2>
  <pre>flatpak update</pre>
  <p><a href="https://github.com/${GITHUB_REPOSITORY:-Quad4-Software/MeshChatX}">Project on GitHub</a></p>
</body>
</html>
EOF

#!/usr/bin/env bash
# SPDX-License-Identifier: 0BSD
# Import a single-file Flatpak bundle into an OSTree archive-z2 repo and write
# CDN discovery files (.flatpakref, .flatpakrepo, landing page) for BunnyCDN.
#
# Usage: github-flatpak-ostree-export.sh BUNDLE_PATH OUTPUT_DIR [BRANCH]
#
# BRANCH defaults from GITHUB_REF_NAME via github_flatpak_channel.py
# (testing | beta | stable).
#
# Environment:
#   FLATPAK_CDN_BASE_URL  public base (default https://cdn.meshchatx.com/flatpak)
#   GPG_FINGERPRINT       GPG key id for signing commits and summary
#   REQUIRE_GPG           if 1, fail when GPG_FINGERPRINT is empty
#   GITHUB_REPOSITORY     owner/repo for landing page link
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUNDLE="${1:?usage: $0 BUNDLE_PATH OUTPUT_DIR [BRANCH]}"
OUT="${2:?usage: $0 BUNDLE_PATH OUTPUT_DIR [BRANCH]}"
BRANCH_ARG="${3:-}"

if [[ ! -f "$BUNDLE" ]]; then
    echo "Bundle not found: $BUNDLE" >&2
    exit 1
fi

if [[ -n "$BRANCH_ARG" ]]; then
    branch="$BRANCH_ARG"
else
    ref_name="${GITHUB_REF_NAME:-}"
    if [[ -z "$ref_name" ]]; then
        echo "Set BRANCH argument or GITHUB_REF_NAME" >&2
        exit 1
    fi
    branch="$(python3 "${ROOT}/scripts/ci/github_flatpak_channel.py" "$ref_name")"
fi

case "$branch" in
    testing | beta | stable) ;;
    *)
        echo "Invalid Flatpak branch: ${branch}" >&2
        exit 1
        ;;
esac

cdn_base="${FLATPAK_CDN_BASE_URL:-https://cdn.meshchatx.com/flatpak}"
cdn_base="${cdn_base%/}"
repo_url="${cdn_base}/repo"
repo_path="${OUT}/repo"
mkdir -p "$OUT"

if [[ "${REQUIRE_GPG:-0}" == "1" ]] && [[ -z "${GPG_FINGERPRINT:-}" ]]; then
    echo "REQUIRE_GPG=1 but GPG_FINGERPRINT is empty" >&2
    exit 1
fi

if [[ ! -f "${repo_path}/config" ]]; then
    ostree init --repo="${repo_path}" --mode=archive-z2
fi

if curl -sfL --max-time 120 -o /dev/null "${repo_url}/summary"; then
    echo "Pulling existing ostree repo from ${repo_url}"
    ostree remote add --repo="${repo_path}" --if-not-exists --no-gpg-verify meshchatx-prev "${repo_url}" || true
    if ostree pull --repo="${repo_path}" meshchatx-prev --mirror --depth=-1 2>/dev/null; then
        echo "Restored prior ostree commits from live CDN"
    else
        echo "Live summary present but pull failed, continuing with local repo" >&2
    fi
    ostree remote delete --repo="${repo_path}" meshchatx-prev 2>/dev/null || true
fi

gpg_args=()
update_args=()
if [[ -n "${GPG_FINGERPRINT:-}" ]]; then
    gpg_args=(--gpg-sign="${GPG_FINGERPRINT}")
    update_args=(--gpg-sign="${GPG_FINGERPRINT}")
fi

appid="com.quad4.meshchatx"
case "$(uname -m)" in
    x86_64 | amd64) arch="x86_64" ;;
    aarch64 | arm64) arch="aarch64" ;;
    *)
        echo "Unsupported arch for Flatpak export: $(uname -m)" >&2
        exit 1
        ;;
esac
target_ref="app/${appid}/${arch}/${branch}"

echo "Importing bundle (expected ref ${target_ref})"

# Do not pass --ref to rename the branch. Flatpak commits carry
# ostree.ref-binding from build-export; pointing a testing/beta/stable
# ref at a master-bound commit makes clients reject the pull.
flatpak build-import-bundle \
    --no-update-summary \
    "${gpg_args[@]}" \
    "${repo_path}" \
    "${BUNDLE}"

mapfile -t refs < <(ostree refs --repo="${repo_path}" | grep "^app/${appid}/" || true)
if [[ ${#refs[@]} -eq 0 ]]; then
    echo "No app/${appid}/ ref found after import" >&2
    exit 1
fi

if ! ostree rev-parse --repo="${repo_path}" "${target_ref}" >/dev/null 2>&1; then
    echo "Expected ${target_ref} after import, but it is missing." >&2
    echo "Bundle branch must match channel (${branch}). Repo app refs:" >&2
    printf '  %s\n' "${refs[@]}" >&2
    exit 1
fi

commit="$(ostree rev-parse --repo="${repo_path}" "${target_ref}")"
binding="$(ostree show --repo="${repo_path}" --print-metadata-key=ostree.ref-binding "${commit}" 2>/dev/null || true)"
if [[ -n "$binding" ]] && [[ "$binding" != *"${target_ref}"* ]]; then
    echo "ostree.ref-binding does not include ${target_ref}:" >&2
    echo "${binding}" >&2
    exit 1
fi

echo "Target ref: ${target_ref}"
echo "commit=${commit}"
echo "appid=${appid}"
echo "arch=${arch}"
echo "branch=${branch}"
echo "Repo app refs:"
printf '  %s\n' "${refs[@]}"

flatpak build-update-repo \
    "${update_args[@]}" \
    --generate-static-deltas \
    --prune \
    --prune-depth=20 \
    "${repo_path}"

gpg_key_line=""
if [[ -n "${GPG_FINGERPRINT:-}" ]]; then
    gpg_key_line="GPGKey=$(gpg --export "${GPG_FINGERPRINT}" | base64 -w0)"
fi

write_flatpakref() {
    local dest="$1"
    local ref_branch="$2"
    cat >"$dest" <<EOF
[Flatpak Ref]
Title=Reticulum MeshChatX
Name=${appid}
Branch=${ref_branch}
Url=${repo_url}
SuggestRemoteName=meshchatx
Homepage=https://meshchatx.com
Icon=${appid}
RuntimeRepo=https://dl.flathub.org/repo/flathub.flatpakrepo
IsRuntime=false
${gpg_key_line}
EOF
}

write_flatpakref "${OUT}/meshchatx-stable.flatpakref" stable
write_flatpakref "${OUT}/meshchatx-beta.flatpakref" beta
write_flatpakref "${OUT}/meshchatx-testing.flatpakref" testing
write_flatpakref "${OUT}/meshchatx.flatpakref" "$branch"

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
DefaultBranch=stable
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
  <p>Install from the CDN remote, then run <code>flatpak update</code> for new releases on that branch.</p>
  <h2>Stable</h2>
  <pre>flatpak install --from ${cdn_base}/meshchatx-stable.flatpakref</pre>
  <h2>Beta</h2>
  <pre>flatpak install --from ${cdn_base}/meshchatx-beta.flatpakref</pre>
  <h2>Testing</h2>
  <pre>flatpak install --from ${cdn_base}/meshchatx-testing.flatpakref</pre>
  <h2>Remote only</h2>
  <pre>flatpak remote-add --if-not-exists meshchatx ${cdn_base}/meshchatx.flatpakrepo
flatpak install meshchatx ${appid}//stable</pre>
  <p>Then run <code>flatpak run ${appid}</code> or launch from your app menu.</p>
  <p><a href="https://github.com/${GITHUB_REPOSITORY:-Quad4-Software/MeshChatX}">Project on GitHub</a></p>
</body>
</html>
EOF

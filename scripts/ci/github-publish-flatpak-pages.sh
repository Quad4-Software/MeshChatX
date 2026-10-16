#!/usr/bin/env bash
# SPDX-License-Identifier: 0BSD
# Export a .flatpak bundle into the OSTree repo and publish the whole site
# tree (repo + flatpakref + flatpakrepo + landing page) to the gh-pages branch
# of the same repository as a single force-pushed orphan commit.
#
# Usage: github-publish-flatpak-pages.sh BUNDLE_PATH
#
# Environment:
#   FLATPAK_REPO_BASE_URL  public repo base URL. Default:
#                          https://<owner>.github.io/<repo>/flatpak derived
#                          from GITHUB_REPOSITORY (owner lowercased).
#   GPG_FINGERPRINT        GPG key id for signing commits and summary
#   REQUIRE_GPG            if 1, fail when GPG_FINGERPRINT is empty
#   GITHUB_TOKEN           token used to push gh-pages
#   GITHUB_REPOSITORY      owner/repo (required)
#   GITHUB_REF_NAME        tag name for channel selection
#   FLATPAK_PAGES_BRANCH   target branch (default gh-pages)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUNDLE="${1:-}"

if [[ -z "${GITHUB_REPOSITORY:-}" ]]; then
    echo "GITHUB_REPOSITORY is required" >&2
    exit 1
fi

if [[ -z "${FLATPAK_REPO_BASE_URL:-}" ]]; then
    repo_owner="$(echo "${GITHUB_REPOSITORY%%/*}" | tr '[:upper:]' '[:lower:]')"
    repo_name="${GITHUB_REPOSITORY#*/}"
    FLATPAK_REPO_BASE_URL="https://${repo_owner}.github.io/${repo_name}/flatpak"
fi
export FLATPAK_REPO_BASE_URL
echo "Flatpak repo base URL: ${FLATPAK_REPO_BASE_URL}"

if [[ -z "$BUNDLE" || ! -f "$BUNDLE" ]]; then
    echo "Bundle not found: ${BUNDLE:-<unset>}" >&2
    exit 1
fi

if [[ "${REQUIRE_GPG:-0}" == "1" ]] && [[ -z "${GPG_FINGERPRINT:-}" ]]; then
    echo "REQUIRE_GPG=1 but GPG_FINGERPRINT is empty" >&2
    exit 1
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "GITHUB_TOKEN is required to push gh-pages" >&2
    exit 1
fi

branch="${FLATPAK_PAGES_BRANCH:-gh-pages}"
work="$(mktemp -d "${TMPDIR:-/tmp}/flatpak-pages.XXXXXX")"
trap 'rm -rf "$work"' EXIT INT TERM

# Export first: the export restores prior OSTree commits from the live site,
# so nothing under the site tree may be wiped before it runs.
bash "${ROOT}/scripts/ci/github-flatpak-ostree-export.sh" "$BUNDLE" "${work}/flatpak"

site="${work}/site"
mkdir -p "${site}/flatpak"
cp -a "${work}/flatpak/." "${site}/flatpak/"
touch "${site}/.nojekyll"
cat >"${site}/index.html" <<EOF
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=flatpak/"><title>MeshChatX Flatpak</title></head>
<body><p><a href="flatpak/">MeshChatX Flatpak repository</a></p></body>
</html>
EOF

python3 "${ROOT}/scripts/ci/check_pages_size.py" "$site"

publish_dir="${work}/publish"
mkdir -p "$publish_dir"
(
    cd "$publish_dir"
    git init -q -b "$branch" .
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    cp -a "${site}/." .
    git add -A
    git commit -qm "flatpak: publish ${GITHUB_REF_NAME:-local} to gh-pages"
    # Token stays in the process env and in the remote URL passed on the
    # command line; it is never written into .git/config.
    git push --force \
        "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" \
        "HEAD:${branch}"
)

echo "Published ${FLATPAK_REPO_BASE_URL} to ${GITHUB_REPOSITORY}@${branch}"

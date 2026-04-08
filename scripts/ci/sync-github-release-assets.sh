#!/usr/bin/env bash
# Download Windows/macOS build artifacts from GitHub Actions (build-release workflow)
# and attach them to an existing Gitea release. Best-effort: missing platforms are skipped.
#
# Required env: TAG, GITHUB_REPOSITORY, GITHUB_PAT, GITEA_API_URL, GITEA_REPOSITORY, GITEA_TOKEN
set -euo pipefail

TAG="${TAG:?set TAG to the release tag (e.g. v1.2.3)}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:?}"
GITHUB_PAT="${GITHUB_PAT:?}"
GITEA_API_URL="${GITEA_API_URL:?}"
GITEA_REPOSITORY="${GITEA_REPOSITORY:?}"
GITEA_TOKEN="${GITEA_TOKEN:?}"

GITEA_API_URL="${GITEA_API_URL%/}"
GH_API="https://api.github.com/repos/${GITHUB_REPOSITORY}"
AUTH_GH=(-H "Authorization: Bearer ${GITHUB_PAT}" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28")
AUTH_GITEA=(-H "Authorization: token ${GITEA_TOKEN}" -H "Accept: application/json")

WORKDIR=$(mktemp -d)
trap 'rm -rf "${WORKDIR}"' EXIT

enc_tag() {
  printf '%s' "$1" | jq -sRr @uri
}

log() {
  printf '%s\n' "$*" >&2
}

if ! command -v jq >/dev/null 2>&1; then
  log "Error: jq is required."
  exit 1
fi

COMMIT_SHA=""
if COMMIT_JSON=$(curl -sS -f "${AUTH_GH[@]}" "${GH_API}/commits/$(enc_tag "$TAG")" 2>/dev/null); then
  COMMIT_SHA=$(printf '%s' "$COMMIT_JSON" | jq -r '.sha // empty')
fi

TAG_ENC=$(enc_tag "$TAG")
RUNS_URL="${GH_API}/actions/workflows/build-release.yml/runs?event=push&branch=${TAG_ENC}&per_page=30"
RUN_ID=""
if RUNS_JSON=$(curl -sS -f "${AUTH_GH[@]}" "$RUNS_URL" 2>/dev/null); then
  RUN_ID=$(printf '%s' "$RUNS_JSON" | jq -r '
    [.workflow_runs[] | select(.conclusion == "success")]
    | sort_by(.created_at) | reverse | .[0].id // empty
  ')
fi

if [ -z "$RUN_ID" ] && [ -n "$COMMIT_SHA" ]; then
  if RUNS_JSON=$(curl -sS -f "${AUTH_GH[@]}" "${GH_API}/actions/workflows/build-release.yml/runs?per_page=50" 2>/dev/null); then
    RUN_ID=$(printf '%s' "$RUNS_JSON" | jq -r --arg sha "$COMMIT_SHA" '
      [.workflow_runs[] | select(.head_sha == $sha and .conclusion == "success")]
      | sort_by(.created_at) | reverse | .[0].id // empty
    ')
  fi
fi

if [ -z "$RUN_ID" ]; then
  log "No successful GitHub Actions run found for build-release.yml (tag=${TAG}). Skipping GitHub artifact sync."
  exit 0
fi

log "Using GitHub workflow run id=${RUN_ID} for tag ${TAG}"

ART_JSON=$(curl -sS "${AUTH_GH[@]}" "${GH_API}/actions/runs/${RUN_ID}/artifacts?per_page=100" || true)
N=$(printf '%s' "${ART_JSON:-{}}" | jq -r '(.artifacts // []) | length')
if [ "${N:-0}" -eq 0 ]; then
  log "No artifacts on GitHub run ${RUN_ID} (or API error). Nothing to download."
  exit 0
fi

STAGE="${WORKDIR}/stage"
mkdir -p "$STAGE"

printf '%s' "$ART_JSON" | jq -r '.artifacts[] | "\(.id)|\(.name)|\(.archive_download_url)"' | while IFS='|' read -r _art_id art_name dl_url; do
  case "$art_name" in
    meshchatx-windows-*|meshchatx-macos-*) ;;
    *)
      log "Skipping artifact with unexpected name: ${art_name}"
      continue
      ;;
  esac
  ZIP="${WORKDIR}/$(echo "$art_name" | tr '/' '_').zip"
  log "Downloading ${art_name}..."
  if ! curl -sS -fL "${AUTH_GH[@]}" -o "$ZIP" "$dl_url"; then
    log "Warning: failed to download ${art_name}; continuing."
    continue
  fi
  EX="${WORKDIR}/ex-${art_name}"
  mkdir -p "$EX"
  if ! unzip -q -o "$ZIP" -d "$EX" 2>/dev/null; then
    log "Warning: unzip failed for ${art_name}; continuing."
    continue
  fi
  find "$EX" -type f \( -name '*.exe' -o -name '*.dmg' -o -name '*.blockmap' -o -name '*.yml' -o -name '*.yaml' \) -print0 2>/dev/null \
    | while IFS= read -r -d '' f; do
      base=$(basename "$f")
      cp -f "$f" "${STAGE}/${base}"
      log "Staged ${base}"
    done
done

STAGED_N=$(find "$STAGE" -mindepth 1 -maxdepth 1 -type f 2>/dev/null | wc -l)
STAGED_N=${STAGED_N//[[:space:]]/}
if [ "${STAGED_N:-0}" -eq 0 ]; then
  log "No .exe/.dmg (or related) files extracted from GitHub artifacts. Nothing to upload."
  exit 0
fi

REL_JSON=$(curl -sS "${AUTH_GITEA[@]}" "${GITEA_API_URL}/api/v1/repos/${GITEA_REPOSITORY}/releases/tags/${TAG}")
REL_ID=$(printf '%s' "$REL_JSON" | jq -r '.id // empty')
if [ -z "$REL_ID" ] || [ "$REL_ID" = "null" ]; then
  log "Error: No Gitea release for tag '${TAG}'. Create the release first (e.g. push the tag so .gitea/workflows/build.yml runs)."
  exit 1
fi

log "Uploading to Gitea release id=${REL_ID} (${GITEA_REPOSITORY}@${TAG})"

find "$STAGE" -maxdepth 1 -type f -print0 | while IFS= read -r -d '' f; do
  base=$(basename "$f")
  NAME_ENC=$(printf '%s' "$base" | jq -sRr @uri)
  if curl -sS -f "${AUTH_GITEA[@]}" -F "attachment=@${f}" \
    "${GITEA_API_URL}/api/v1/repos/${GITEA_REPOSITORY}/releases/${REL_ID}/assets?name=${NAME_ENC}" >/dev/null; then
    log "Uploaded ${base}"
  else
    log "Warning: upload failed or duplicate for ${base}; continuing."
  fi
done

log "Done."

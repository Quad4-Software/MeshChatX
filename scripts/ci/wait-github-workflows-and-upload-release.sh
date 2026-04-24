#!/usr/bin/env bash
# Wait for successful GitHub Actions runs for TAG, download artifacts from listed workflows,
# then create or update a GitHub release and upload binaries.
#
# Required env: TAG, GH_REPOSITORY (owner/repo), GH_PAT
# Optional: WORKFLOWS (space-separated, default: build-release.yml build-linux-release.yml)
#           TIMEOUT_SEC (default 14400), POLL_INTERVAL (default 60), DRAFT (default false)
#           RELEASE_BODY_FILE (path to markdown; default tries ./release-body.md from cwd)
set -euo pipefail

TAG="${TAG:?set TAG (e.g. v1.2.3 or release_1.2.3)}"
GH_REPOSITORY="${GH_REPOSITORY:?set GH_REPOSITORY to owner/repo on github.com}"
GH_PAT="${GH_PAT:?set GH_PAT (fine-grained or classic PAT with contents:write, actions:read)}"
WORKFLOWS="${WORKFLOWS:-build-release.yml build-linux-release.yml}"
TIMEOUT_SEC="${TIMEOUT_SEC:-14400}"
POLL_INTERVAL="${POLL_INTERVAL:-60}"
DRAFT="${DRAFT:-false}"

GH_API="https://api.github.com/repos/${GH_REPOSITORY}"
AUTH=(-H "Authorization: Bearer ${GH_PAT}" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28")

WORKDIR=$(mktemp -d)
trap 'rm -rf "${WORKDIR}"' EXIT

log() {
    printf '%s\n' "$*" >&2
}

if ! command -v jq >/dev/null 2>&1; then
    log "Error: jq is required."
    exit 1
fi

enc_tag() {
    printf '%s' "$1" | jq -sRr @uri
}

latest_success_run_id() {
    local wf="$1"
    local tag="$2"
    local tag_enc run_id runs_json commit_sha runs_json2

    tag_enc=$(enc_tag "$tag")
    run_id=""
    if runs_json=$(curl -sS -f "${AUTH[@]}" "${GH_API}/actions/workflows/${wf}/runs?event=push&branch=${tag_enc}&per_page=30" 2>/dev/null); then
        run_id=$(printf '%s' "$runs_json" | jq -r '
            [.workflow_runs[] | select(.conclusion == "success")]
            | sort_by(.created_at) | reverse | .[0].id // empty
        ')
    fi

    if [ -z "$run_id" ]; then
        if ! commit_sha=$(curl -sS -f "${AUTH[@]}" "${GH_API}/commits/${tag_enc}" | jq -r '.sha // empty'); then
            commit_sha=""
        fi
        if [ -n "$commit_sha" ] && runs_json2=$(curl -sS -f "${AUTH[@]}" "${GH_API}/actions/workflows/${wf}/runs?per_page=80" 2>/dev/null); then
            run_id=$(printf '%s' "$runs_json2" | jq -r --arg sha "$commit_sha" '
                [.workflow_runs[] | select(.head_sha == $sha and .conclusion == "success")]
                | sort_by(.created_at) | reverse | .[0].id // empty
            ')
        fi
    fi
    printf '%s' "$run_id"
}

deadline=$(( $(date +%s) + TIMEOUT_SEC ))
declare -A RUN_IDS=()

log "Waiting for workflows (${WORKFLOWS}) on tag ${TAG} (timeout ${TIMEOUT_SEC}s)..."

while [ "$(date +%s)" -lt "$deadline" ]; do
    all_set=1
    for wf in $WORKFLOWS; do
        rid=$(latest_success_run_id "$wf" "$TAG")
        if [ -n "$rid" ]; then
            RUN_IDS["$wf"]=$rid
        else
            all_set=0
        fi
    done
    if [ "$all_set" = 1 ]; then
        break
    fi
    log "Not all workflows succeeded yet; sleeping ${POLL_INTERVAL}s..."
    sleep "$POLL_INTERVAL"
done

for wf in $WORKFLOWS; do
    if [ -z "${RUN_IDS[$wf]:-}" ]; then
        log "Timeout or missing successful run for ${wf} (tag=${TAG})."
        exit 1
    fi
    log "Using ${wf} run_id=${RUN_IDS[$wf]}"
done

STAGE="${WORKDIR}/stage"
mkdir -p "$STAGE"

download_and_stage_run() {
    local wf="$1"
    local rid="$2"
    local art_json n

    art_json=$(curl -sS "${AUTH[@]}" "${GH_API}/actions/runs/${rid}/artifacts?per_page=100" || true)
    n=$(printf '%s' "${art_json:-{}}" | jq -r '(.artifacts // []) | length')
    if [ "${n:-0}" -eq 0 ]; then
        log "No artifacts for ${wf} run ${rid}."
        return
    fi

    printf '%s' "$art_json" | jq -r '.artifacts[] | "\(.name)|\(.archive_download_url)"' | while IFS='|' read -r art_name dl_url; do
        case "$wf" in
            build-release.yml)
                case "$art_name" in
                    meshchatx-windows-*|meshchatx-macos-*) ;;
                    *)
                        log "Skipping artifact ${art_name} for ${wf}"
                        continue
                        ;;
                esac
                ;;
            build-linux-release.yml)
                case "$art_name" in
                    meshchatx-linux-release-*) ;;
                    *)
                        log "Skipping artifact ${art_name} for ${wf}"
                        continue
                        ;;
                esac
                ;;
            *)
                log "Unknown workflow file in download filter: ${wf}" >&2
                exit 1
                ;;
        esac

        zip_path="${WORKDIR}/$(echo "$art_name" | tr '/' '_').zip"
        log "Downloading ${art_name}..."
        if ! curl -sS -fL "${AUTH[@]}" -o "$zip_path" "$dl_url"; then
            log "Warning: download failed for ${art_name}"
            continue
        fi
        ex="${WORKDIR}/ex-${art_name}"
        mkdir -p "$ex"
        if ! unzip -q -o "$zip_path" -d "$ex" 2>/dev/null; then
            log "Warning: unzip failed for ${art_name}"
            continue
        fi
        find "$ex" -type f \( \
            -name '*.AppImage' -o -name '*.deb' -o -name '*.rpm' -o -name '*.whl' -o \
            -name '*.exe' -o -name '*.dmg' -o -name '*.blockmap' -o \
            -name 'latest*.yml' -o -name 'latest*.yaml' -o -name '*-linux.yml' -o -name '*-linux.yaml' -o \
            -name 'meshchatx-frontend.zip' -o -name 'sbom.cyclonedx.json' -o -name '*.cosign.bundle' -o -name '*.intoto.jsonl' \
            \) -print0 2>/dev/null | while IFS= read -r -d '' f; do
            cp -f "$f" "${STAGE}/$(basename "$f")"
        done
    done
}

for wf in $WORKFLOWS; do
    download_and_stage_run "$wf" "${RUN_IDS[$wf]}"
done

file_count=$(find "$STAGE" -mindepth 1 -maxdepth 1 -type f 2>/dev/null | wc -l)
file_count=${file_count//[[:space:]]/}
if [ "${file_count:-0}" -eq 0 ]; then
    log "No release files staged after downloads."
    exit 1
fi

BODY_FILE="${RELEASE_BODY_FILE:-}"
if [ -z "$BODY_FILE" ] && [ -f "./release-body.md" ]; then
    BODY_FILE="./release-body.md"
fi
BODY_JSON=$(jq -n '""')
if [ -n "$BODY_FILE" ] && [ -f "$BODY_FILE" ]; then
    BODY_JSON=$(jq -Rs . < "$BODY_FILE")
fi

log "Creating or locating GitHub release for tag ${TAG}..."
REL_GET=$(curl -sS -w '%{http_code}' -o "${WORKDIR}/rel.json" "${AUTH[@]}" "${GH_API}/releases/tags/${TAG}" || true)
HTTP="${REL_GET: -3}"
REL_ID=""
if [ "$HTTP" = "200" ]; then
    REL_ID=$(jq -r '.id // empty' "${WORKDIR}/rel.json")
    UPLOAD_URL=$(jq -r '.upload_url // empty' "${WORKDIR}/rel.json")
    log "Release exists id=${REL_ID}"
else
    if [ "$DRAFT" = "true" ] || [ "$DRAFT" = "1" ]; then
        draft_json="true"
    else
        draft_json="false"
    fi
    payload=$(jq -n \
        --arg tag "$TAG" \
        --arg name "$TAG" \
        --argjson draft "$draft_json" \
        --argjson body "$BODY_JSON" \
        '{tag_name: $tag, name: $name, body: body, draft: draft}')
    if ! curl -sS -f "${AUTH[@]}" -X POST -H "Content-Type: application/json" \
        -d "$payload" "${GH_API}/releases" -o "${WORKDIR}/newrel.json"; then
        log "Failed to create release for ${TAG}"
        exit 1
    fi
    REL_ID=$(jq -r '.id // empty' "${WORKDIR}/newrel.json")
    UPLOAD_URL=$(jq -r '.upload_url // empty' "${WORKDIR}/newrel.json")
    log "Created release id=${REL_ID}"
fi

if [ -z "$REL_ID" ] || [ -z "$UPLOAD_URL" ]; then
    log "Could not resolve release id or upload_url."
    exit 1
fi

BASE_UPLOAD="${UPLOAD_URL%\{*}"

EXISTING_NAMES=$(curl -sS "${AUTH[@]}" "${GH_API}/releases/${REL_ID}/assets" | jq -c '[.[].name]' 2>/dev/null || echo '[]')

while IFS= read -r -d '' f; do
    base=$(basename "$f")
    if jq -n -e --argjson names "$EXISTING_NAMES" --arg n "$base" '$names | index($n) != null' >/dev/null 2>&1; then
        log "Skipping existing asset: ${base}"
        continue
    fi
    enc=$(printf '%s' "$base" | jq -sRr @uri)
    log "Uploading ${base}..."
    if ! curl -sS -f "${AUTH[@]}" -X POST \
        -H "Content-Type: application/octet-stream" \
        --data-binary @"$f" \
        "${BASE_UPLOAD}?name=${enc}" >/dev/null; then
        log "Upload failed for ${base}"
        exit 1
    fi
done < <(find "$STAGE" -maxdepth 1 -type f -print0)

log "Done publishing assets to GitHub release ${TAG}."

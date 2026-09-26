#!/usr/bin/env bash
# Mutation test only the src/backend modules changed vs a base ref.
# Advisory on PRs: a low score means the diff added code that tests cannot
# kill when mutated - usually assertions that assert nothing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE_REF="${MUTMUT_BASE_REF:-}"
if [[ -z "${BASE_REF}" ]]; then
    if git rev-parse --verify origin/dev >/dev/null 2>&1; then
        BASE_REF="origin/dev"
    elif git rev-parse --verify origin/master >/dev/null 2>&1; then
        BASE_REF="origin/master"
    else
        echo "No base ref found; set MUTMUT_BASE_REF" >&2
        exit 2
    fi
fi

MAX_MODULES="${MUTMUT_MAX_MODULES:-3}"
MIN_SCORE="${MUTMUT_MIN_SCORE:-}"

MERGE_BASE="$(git merge-base "${BASE_REF}" HEAD)"
mapfile -t changed < <(
    git diff --name-only "${MERGE_BASE}" HEAD -- 'meshchatx/src/backend/**/*.py' \
        | grep -v '/data/' \
        | grep -v '__pycache__' \
        | grep -v '/__init__.py$' \
        || true
)

if [[ "${#changed[@]}" -eq 0 ]]; then
    echo "No backend Python modules changed vs ${BASE_REF}; skipping."
    exit 0
fi

# Map file paths to mutmut dotted module targets (skip deleted modules).
declare -a targets=()
for path in "${changed[@]}"; do
    [[ -f "${path}" ]] || continue
    mod="${path%.py}"
    mod="${mod//\//.}"
    targets+=("${mod}")
done

if [[ "${#targets[@]}" -eq 0 ]]; then
    echo "All changed backend modules were deleted; skipping."
    exit 0
fi

# Keep the job bounded: mutate at most MAX_MODULES modules, highest churn first.
if [[ "${#targets[@]}" -gt "${MAX_MODULES}" ]]; then
    mapfile -t ranked < <(
        git diff --numstat "${MERGE_BASE}" HEAD -- 'meshchatx/src/backend/**/*.py' \
            | sort -rn -k1,1 \
            | awk '{print $3}' \
            | head -n "${MAX_MODULES}"
    )
    targets=()
    for path in "${ranked[@]}"; do
        [[ -f "${path}" ]] || continue
        mod="${path%.py}"
        mod="${mod//\//.}"
        targets+=("${mod}")
    done
fi

echo "Mutation targets vs ${BASE_REF}:"
printf '  %s\n' "${targets[@]}"

STATS_FILE="mutmut-cicd-stats.json"
: >"${STATS_FILE}"

overall_rc=0
for target in "${targets[@]}"; do
    echo "== mutmut run ${target}"
    MUTMUT_TARGET="${target}" MUTMUT_STATS_FILE="${STATS_FILE}" \
        bash scripts/ci/mutation-backend.sh || overall_rc=$?
    if [[ -n "${MIN_SCORE}" ]]; then
        uv run python scripts/ci/mutation-score-check.py \
            --mutmut-stats "${STATS_FILE}" \
            --min-score "${MIN_SCORE}" || overall_rc=$?
    fi
done

exit "${overall_rc}"

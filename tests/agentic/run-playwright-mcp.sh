#!/usr/bin/env bash
# Resolve the repo's installed Playwright browser and launch the MCP
# against it. @playwright/mcp pins its own browser revision, which rarely
# matches the version the repo's playwright installed; pointing at the
# resolved binary sidesteps the mismatch.
#
#   run-playwright-mcp.sh [chromium|firefox] [extra mcp args...]
#   AGENTIC_BROWSER=firefox run-playwright-mcp.sh
set -euo pipefail

BROWSER="${AGENTIC_BROWSER:-chromium}"
if [[ "${1:-}" == "chromium" || "${1:-}" == "firefox" ]]; then
    BROWSER="$1"
    shift
fi

case "$BROWSER" in
    chromium) NAMES=("headless_shell" "chrome");;
    firefox)  NAMES=("firefox");;
    *) echo "run-playwright-mcp: unsupported browser '$BROWSER'" >&2; exit 2;;
esac

CANDIDATES=(
    "${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
    "$HOME/Library/Caches/ms-playwright"
    "${LOCALAPPDATA:-/nonexistent}/ms-playwright"
)

NAME_EXPR=( -name "${NAMES[0]}" )
for n in "${NAMES[@]:1}"; do
    NAME_EXPR+=( -o -name "$n" )
done

BIN=""
for base in "${CANDIDATES[@]}"; do
    [[ -d "$base" ]] || continue
    # Newest matching build wins.
    BIN="$(find "$base" -type f \( "${NAME_EXPR[@]}" \) \
        -path "*${BROWSER}*" 2>/dev/null | sort -V | tail -1)"
    [[ -n "$BIN" ]] && break
done

if [[ -z "$BIN" ]]; then
    echo "run-playwright-mcp: no $BROWSER found under ${CANDIDATES[*]}." >&2
    echo "run: pnpm exec playwright install $BROWSER" >&2
    exit 1
fi

echo "run-playwright-mcp: $BROWSER at $BIN (headless)" >&2
exec npx -y @playwright/mcp@latest --browser "$BROWSER" --headless --executable-path "$BIN" "$@"

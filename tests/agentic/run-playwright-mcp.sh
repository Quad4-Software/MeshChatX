#!/usr/bin/env bash
# Resolve the repo's installed Playwright chromium and launch the MCP
# against it. @playwright/mcp pins its own browser revision, which rarely
# matches the version the repo's playwright installed; pointing at the
# resolved binary sidesteps the mismatch.
set -euo pipefail

CANDIDATES=(
    "${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
    "$HOME/Library/Caches/ms-playwright"
    "${LOCALAPPDATA:-/nonexistent}/ms-playwright"
)

BIN=""
for base in "${CANDIDATES[@]}"; do
    [[ -d "$base" ]] || continue
    # Newest chromium-headless-shell or chromium build wins.
    BIN="$(find "$base" -type f \( -name "headless_shell" -o -name "chrome" \) \
        -path "*chromium*" 2>/dev/null | sort -V | tail -1)"
    [[ -n "$BIN" ]] && break
done

if [[ -z "$BIN" ]]; then
    echo "run-playwright-mcp: no chromium found under ${CANDIDATES[*]}." >&2
    echo "run: pnpm exec playwright install chromium" >&2
    exit 1
fi

echo "run-playwright-mcp: chromium at $BIN" >&2
exec npx -y @playwright/mcp@latest --browser chromium --executable-path "$BIN" "$@"

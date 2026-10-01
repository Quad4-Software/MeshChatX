#!/usr/bin/env bash
# Generate llms-full.txt: all English docs plus the generated module
# reference in one file for LLM consumers. Called by the docs workflow
# after zensical build. Requires lxmfy to be installed; griffe2md is
# optional and skipped if missing.
set -euo pipefail

cd "$(dirname "$0")/.."
# Written into docs/ before zensical build so the file ships with the
# site sources; works with plain builds and mike versioned deploys.
out="${1:-docs/llms-full.txt}"

{
  printf '# LXMFy documentation\n\n'
  printf '> Python framework for building LXMF bots on the Reticulum Network.\n'
  printf '> Source: https://github.com/Quad4-Software/LXMFy\n'

  for page in index quick-start creating-bots api-reference; do
    printf '\n\n================================================================================\n'
    printf 'docs/%s.md\n' "$page"
    printf '================================================================================\n\n'
    cat "docs/${page}.md"
  done

  modref=""
  if command -v griffe2md >/dev/null 2>&1; then
    modref="$(griffe2md lxmfy 2>/dev/null || true)"
  fi
  if [ -n "$modref" ]; then
    printf '\n\n================================================================================\n'
    printf 'Generated module reference (griffe2md lxmfy)\n'
    printf '================================================================================\n\n'
    printf '%s\n' "$modref"
  else
    printf '\n\nGenerated module reference omitted: griffe2md unavailable or lxmfy not importable.\n'
  fi
} > "$out"

echo "wrote $out"

#!/usr/bin/env bash
# Build release documentation artifacts (PDF, EPUB, plain text) from the
# Markdown sources for every translated language.
# Requires pandoc, weasyprint (PDF engine), and griffe2md.
# Usage: docs/build-release-docs.sh [output-dir]
set -euo pipefail

out="${1:-docs-dist}"
mkdir -p "$out"

pages=(index quick-start creating-bots api-reference)

declare -A titles=(
    [en]="LXMFy Documentation"
    [de]="LXMFy Dokumentation"
    [es]="Documentación de LXMFy"
    [fr]="Documentation LXMFy"
    [pt]="Documentação do LXMFy"
    [uk]="Документація LXMFy"
    [ru]="Документация LXMFy"
    [zh]="LXMFy 文档"
)
langs=(en de es fr pt uk ru zh)

api="$(mktemp)"
work="$(mktemp -d)"
trap 'rm -f "$api"; rm -rf "$work"' EXIT

griffe2md lxmfy 2>/dev/null \
    | sed -E 's/\[([^]]+)\]\(#[^)]*\)/\1/g' > "$api"

prepare() {
    local lang="$1" tmp="$work/$2" i
    mkdir -p "$tmp"
    for i in "${!pages[@]}"; do
        if [[ "$lang" == en ]]; then
            src="docs/${pages[$i]}.md"
        else
            src="docs/$lang/${pages[$i]}.md"
        fi
        sed '/^:::/d' "$src" > "$tmp/$(printf '%02d' "$i")-${pages[$i]}.md"
    done
    cp "$api" "$tmp/90-api-generated.md"
}

render() {
    local tmp="$1" base="$out/lxmfy-docs-$2" title="$3"
    pandoc "$tmp"/*.md --toc --metadata title="$title" -o "$base.epub"
    pandoc "$tmp"/*.md --toc --metadata title="$title" \
        --pdf-engine=weasyprint -o "$base.pdf"
    pandoc "$tmp"/*.md --toc --metadata title="$title" -t plain \
        -o "$base.txt"
}

for lang in "${langs[@]}"; do
    missing=""
    if [[ "$lang" != en ]]; then
        for page in "${pages[@]}"; do
            [[ -f "docs/$lang/$page.md" ]] || missing=1
        done
    fi
    if [[ -n "$missing" ]]; then
        echo "skipping $lang: incomplete docs/$lang" >&2
        continue
    fi
    prepare "$lang" "$lang"
    render "$work/$lang" "$lang" "${titles[$lang]}"
done

ls -lh "$out"

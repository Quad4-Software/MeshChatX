#!/usr/bin/env bash
# Copy per-version root files to the gh-pages branch root after a mike
# deploy, so robots.txt, llms.txt, and llms-full.txt stay reachable at
# the domain root. Writes a sitemap index covering every deployed
# version. Runs inside the docs workflow; expects git credentials.
set -euo pipefail

version="${1:?usage: hoist-root-files.sh <deployed-version> [remote-or-url]}"
remote="${2:-origin}"

cd "$(dirname "$0")/.."
wt=".gh-pages-wt"

git fetch "$remote" gh-pages
git worktree add "$wt" FETCH_HEAD
trap 'git worktree remove "$wt" --force' EXIT

src="$wt/$version"
if [ ! -d "$src" ]; then
  echo "version directory $version not found on gh-pages" >&2
  exit 1
fi

for f in robots.txt llms.txt llms-full.txt; do
  if [ -f "$src/$f" ]; then
    cp "$src/$f" "$wt/$f"
  fi
done

{
  printf '<?xml version="1.0" encoding="UTF-8"?>\n'
  printf '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
  for d in "$wt"/*/; do
    name="$(basename "$d")"
    [ -f "$d/sitemap.xml" ] || continue
    printf '  <sitemap><loc>https://lxmfy.quad4.io/%s/sitemap.xml</loc></sitemap>\n' "$name"
  done
  printf '</sitemapindex>\n'
} > "$wt/sitemap.xml"

cd "$wt"
for f in robots.txt llms.txt llms-full.txt sitemap.xml; do
  if [ -f "$f" ]; then
    git add "$f"
  fi
done
if ! git diff --cached --quiet; then
  git commit -m "Hoist root files for $version"
  git push "$remote" HEAD:gh-pages
else
  echo "root files already up to date"
fi

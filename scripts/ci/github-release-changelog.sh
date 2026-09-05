#!/usr/bin/env bash
# Print a "## Changelog" section for a GitHub release tag.
#
# Usage:
#   sh scripts/ci/github-release-changelog.sh <tag>
#
# Finds the previous tag from TAG^ (stable tags prefer prior vN.* tags so
# nightlies do not become the baseline). Lists commits as:
#   * <full-sha> <subject>.
# Excludes conventional docs:/test:/ci: commit subjects.
#
# SPDX-License-Identifier: 0BSD
set -euo pipefail

TAG="${1:?usage: github-release-changelog.sh <tag>}"

if ! git rev-parse -q --verify "${TAG}^{commit}" >/dev/null 2>&1; then
	echo "github-release-changelog.sh: unknown tag or commit: ${TAG}" >&2
	exit 1
fi

PREV=""
if [[ "$TAG" =~ ^v[0-9] ]]; then
	PREV="$(
		git describe --tags --abbrev=0 --match 'v[0-9]*' --exclude "$TAG" "${TAG}^" 2>/dev/null ||
			true
	)"
else
	PREV="$(
		git describe --tags --abbrev=0 --exclude "$TAG" "${TAG}^" 2>/dev/null ||
			true
	)"
fi

echo "## Changelog"
echo
if [[ -n "$PREV" ]]; then
	# Full hash, subject, trailing period. --no-merges keeps authored commits only.
	git log --pretty=format:'* %H %s.' --no-merges \
		--invert-grep --grep='^docs:' --grep='^test:' --grep='^ci:' \
		"${PREV}..${TAG}"
	echo
else
	echo "_No previous tag found; changelog omitted._"
	echo
fi

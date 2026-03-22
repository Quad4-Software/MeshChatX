#!/bin/sh
# Clone and checkout using Gitea Actions environment variables.
# Source: self-contained, no third-party dependencies.
#
# Usage: checkout.sh [fetch_depth]
#   fetch_depth: number of commits (default 1), or 0 for full history.
#
# Required env: GITEA_SERVER_URL, GITEA_REPOSITORY, GITHUB_SHA
# Optional env: GITEA_TOKEN (for private repos), GITHUB_WORKSPACE
set -eu

FETCH_DEPTH="${1:-1}"
SERVER="${GITEA_SERVER_URL:-${GITHUB_SERVER_URL:?GITEA_SERVER_URL not set}}"
REPO="${GITEA_REPOSITORY:-${GITHUB_REPOSITORY:?GITEA_REPOSITORY not set}}"
SHA="${GITHUB_SHA:?GITHUB_SHA not set}"
TOKEN="${GITEA_TOKEN:-${GITHUB_TOKEN:-}}"
WORKSPACE="${GITHUB_WORKSPACE:-.}"

cd "$WORKSPACE"

if [ -n "$TOKEN" ]; then
    git config --global credential.helper \
        "!f() { echo username=x-access-token; echo \"password=${TOKEN}\"; }; f"
fi

ORIGIN="${SERVER}/${REPO}.git"

if [ "$FETCH_DEPTH" = "0" ]; then
    git clone -q "$ORIGIN" .
else
    git init -q
    git remote add origin "$ORIGIN"
    git fetch -q --depth="$FETCH_DEPTH" origin "$SHA"
fi

git checkout -q "$SHA" 2>/dev/null || git checkout -q FETCH_HEAD

echo "Checked out ${REPO} at $(git rev-parse --short HEAD)"

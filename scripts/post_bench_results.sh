#!/bin/bash
set -e

# Required environment variables:
# GITEA_TOKEN
# GITHUB_REPOSITORY
# GITHUB_EVENT_PATH

if [ -z "$GITEA_TOKEN" ]; then
    echo "GITEA_TOKEN is not set. Skipping PR comment."
    exit 0
fi

if [ ! -f "bench_results.txt" ]; then
    echo "bench_results.txt not found. Nothing to post."
    exit 0
fi

# Extract PR number from the event JSON
PR_NUMBER=$(jq -r '.pull_request.number' "$GITHUB_EVENT_PATH")

if [ "$PR_NUMBER" == "null" ]; then
    echo "Not a pull request. Skipping."
    exit 0
fi

# Filter out progress lines to keep the comment clean
grep -v "Progress:" bench_results.txt > bench_filtered.txt || true

# Construct the message
HEADER="### Benchmark and Integrity Results (automated report)"
RESULTS=$(cat bench_filtered.txt)

# Use jq to construct the JSON payload safely
JSON_PAYLOAD=$(jq -n \
  --arg results "$RESULTS" \
  --arg header "$HEADER" \
  '{body: ($header + "\n\n```text\n" + $results + "\n```"), event: "COMMENT"}')

# Post to Gitea
curl -f -X POST \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" \
  "https://git.quad4.io/api/v1/repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}/reviews"


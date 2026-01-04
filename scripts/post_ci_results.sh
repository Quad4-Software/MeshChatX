#!/bin/bash
set -e

# Required environment variables:
# GITEA_TOKEN
# GITHUB_REPOSITORY
# GITHUB_EVENT_PATH
# GITHUB_SERVER_URL
# GITHUB_RUN_ID

if [ -z "$GITEA_TOKEN" ]; then
    echo "GITEA_TOKEN is not set. Skipping PR comment."
    exit 0
fi

# Extract PR number from the event JSON
if [ -f "$GITHUB_EVENT_PATH" ]; then
    PR_NUMBER=$(jq -r '.pull_request.number' "$GITHUB_EVENT_PATH")
else
    echo "GITHUB_EVENT_PATH not found. Skipping."
    exit 0
fi

if [ "$PR_NUMBER" == "null" ] || [ -z "$PR_NUMBER" ]; then
    echo "Not a pull request. Skipping."
    exit 0
fi

REPORT_TYPE=$1
INPUT_FILE=${2:-ci_results.txt}

if [ ! -f "$INPUT_FILE" ]; then
    echo "$INPUT_FILE not found. Nothing to post."
    exit 0
fi

RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

# Clean up ANSI escape sequences (colors) from the output
# This makes the markdown output readable
sed -i 's/\x1b\[[0-9;]*[mK]//g' "$INPUT_FILE"

if [ "$REPORT_TYPE" == "bench" ]; then
    HEADER="### Benchmark Summary (automated report)"
    # Extract from summary start to the end, removing progress lines
    # We look for the start of the benchmark summary table
    RESULTS=$(sed -n '/==================== BENCHMARK SUMMARY ====================/,$p' "$INPUT_FILE" | grep -v "Progress:")
else
    HEADER="### CI Status Report: $REPORT_TYPE"
    # Check for failures
    if grep -qiE "FAILED|error|❌|exit status|failure" "$INPUT_FILE"; then
        # Try to find a meaningful summary
        if grep -q "short test summary info" "$INPUT_FILE"; then
            RESULTS=$(sed -n '/=========================== short test summary info ============================/,$p' "$INPUT_FILE")
        elif grep -q "Found [0-9]* error" "$INPUT_FILE"; then
            # Ruff/Lint style errors
            RESULTS=$(grep -A 20 -B 2 -E "Found [0-9]* error|::error|❌" "$INPUT_FILE")
        else
            # Extract lines that look like errors, with some context, limited to avoid too long comments
            RESULTS=$(grep -Ci 1 -E "FAILED|::error|❌|exit status|failure" "$INPUT_FILE" | tail -n 40)
        fi
        HEADER="### ❌ CI Failure: $REPORT_TYPE"
    else
        RESULTS="All checks passed! ✅"
    fi
fi

if [ -z "$RESULTS" ]; then
    RESULTS="No detailed results found in $INPUT_FILE"
fi

# Construct the message
# Note: Gitea/GitHub PR reviews use a JSON body where \n is a literal newline
BODY="${HEADER}\n\n"
BODY="${BODY}\`\`\`text\n${RESULTS}\n\`\`\`\n\n"
BODY="${BODY}🔗 [View Full Run](${RUN_URL})"

# Use jq to construct the JSON payload safely
JSON_PAYLOAD=$(jq -n \
  --arg body "$BODY" \
  '{body: $body, event: "COMMENT"}')

# Post to Gitea
curl -f -X POST \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" \
  "https://git.quad4.io/api/v1/repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}/reviews"


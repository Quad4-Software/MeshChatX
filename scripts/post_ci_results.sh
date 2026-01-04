#!/bin/bash
set -e

if [ -z "$GITEA_TOKEN" ]; then
    echo "GITEA_TOKEN is not set. Skipping PR comment."
    exit 0
fi

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

if [[ "$GITHUB_SERVER_URL" == *"github.com"* ]] || [ -z "$GITHUB_SERVER_URL" ]; then
    GITHUB_SERVER_URL="https://git.quad4.io"
    RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
fi

sed -i 's/\x1b\[[0-9;]*[mK]//g' "$INPUT_FILE"

if [ "$REPORT_TYPE" == "bench" ]; then
    HEADER="### Benchmark Summary (automated report)"
    RESULTS=$(sed -n '/==================== BENCHMARK SUMMARY ====================/,$p' "$INPUT_FILE" | grep -v "Progress:")
else
    if grep -qiE "FAILED|error|❌|exit status|failure" "$INPUT_FILE"; then
        HEADER="### ❌ CI Failure: $REPORT_TYPE"
        if grep -q "short test summary info" "$INPUT_FILE"; then
            RESULTS=$(sed -n '/=========================== short test summary info ============================/,$p' "$INPUT_FILE")
        elif grep -qE "Found [0-9]* error" "$INPUT_FILE"; then
            RESULTS=$(grep -A 20 -B 2 -E "Found [0-9]* error|::error|❌" "$INPUT_FILE")
        else
            RESULTS=$(grep -Ci 1 -E "FAILED|::error|❌|exit status|failure" "$INPUT_FILE" | tail -n 40)
        fi
        if [ -z "$RESULTS" ]; then
            RESULTS=$(tail -n 30 "$INPUT_FILE")
        fi
    else
        HEADER="### CI Status Report: $REPORT_TYPE"
        RESULTS="All checks passed! ✅"
    fi
fi

if [ -z "$RESULTS" ]; then
    RESULTS="No detailed results found in $INPUT_FILE. Check full logs."
fi

MARKER="<!-- GITEA_CI_REPORT -->"

NEW_SECTION=$(cat <<EOF
${HEADER}

\`\`\`text
${RESULTS}
\`\`\`
EOF
)

COMMENTS_URL="${GITHUB_SERVER_URL}/api/v1/repos/${GITHUB_REPOSITORY}/issues/${PR_NUMBER}/comments"

EXISTING_COMMENT_JSON=$(curl -s -H "Authorization: token $GITEA_TOKEN" "$COMMENTS_URL" | \
    jq -c ".[] | select(.body | contains(\"$MARKER\"))" | tail -n 1)

if [ -n "$EXISTING_COMMENT_JSON" ] && [ "$EXISTING_COMMENT_JSON" != "null" ]; then
    COMMENT_ID=$(echo "$EXISTING_COMMENT_JSON" | jq -r .id)
    OLD_BODY=$(echo "$EXISTING_COMMENT_JSON" | jq -r .body)
    
    UPDATED_BODY=$(python3 -c "
import sys
import re

old_body = sys.stdin.read()
header = sys.argv[1]
new_section = sys.argv[2]

safe_header = re.escape(header)
pattern = r'(?m)^' + safe_header + r'.*?(?=\n---\n|\Z)'

if re.search(pattern, old_body, re.DOTALL):
    updated = re.sub(pattern, new_section, old_body, flags=re.DOTALL)
else:
    if '[View Full Run]' in old_body:
        updated = old_body.replace('[View Full Run]', f'---\n\n{new_section}\n\n[View Full Run]')
    else:
        updated = old_body + f'\n\n---\n\n{new_section}'

print(updated.strip())
" "$HEADER" "$NEW_SECTION")
    
    JSON_PAYLOAD=$(jq -n --arg body "$UPDATED_BODY" '{body: $body}')
    
    curl -f -X PATCH \
      -H "Authorization: token $GITEA_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$JSON_PAYLOAD" \
      "${GITHUB_SERVER_URL}/api/v1/repos/${GITHUB_REPOSITORY}/issues/comments/${COMMENT_ID}"
else
    NEW_BODY=$(cat <<EOF
${MARKER}
## CI Status Reports

${NEW_SECTION}

[View Full Run](${RUN_URL})
EOF
)
    JSON_PAYLOAD=$(jq -n --arg body "$NEW_BODY" '{body: $body}')
    
    curl -f -X POST \
      -H "Authorization: token $GITEA_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$JSON_PAYLOAD" \
      "$COMMENTS_URL"
fi

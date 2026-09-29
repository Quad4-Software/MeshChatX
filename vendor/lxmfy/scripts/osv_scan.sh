#!/usr/bin/env bash
set -euo pipefail

OSV_VERSION="${OSV_VERSION:-v2.3.1}"

echo "Installing OSV-Scanner ${OSV_VERSION}..."
curl -sSL "https://github.com/google/osv-scanner/releases/download/${OSV_VERSION}/osv-scanner_linux_amd64" -o /tmp/osv-scanner
chmod +x /tmp/osv-scanner
sudo mv /tmp/osv-scanner /usr/local/bin/osv-scanner

echo "Running OSV-Scanner recursively..."
OSV_JSON="$(mktemp)"
trap 'rm -f "$OSV_JSON"' EXIT

osv-scanner --recursive ./ --format json > "$OSV_JSON" || true

if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is not installed. Please install jq to parse OSV results."
    exit 1
fi

VULNS=$(jq -r '
  .results[]? |
  .source as $src |
  .vulns[]? |
  "\(.id) (source: \($src))"
' "$OSV_JSON")

if [ -n "$VULNS" ]; then
    echo "OSV scan found vulnerabilities:"
    echo "$VULNS" | while IFS= read -r line; do
        echo " - $line"
    done
    exit 1
else
    echo "OSV scan: no vulnerabilities found."
fi


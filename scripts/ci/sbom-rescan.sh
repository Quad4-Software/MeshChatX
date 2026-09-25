#!/usr/bin/env bash
# Re-scan the SBOM of the latest shipped release for newly disclosed CVEs.
# Applies the repo's OpenVEX doc so triaged findings stay suppressed.
# Warn-only: results go to the step summary and a JSON report artifact.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
OUT="${GITHUB_STEP_SUMMARY:-/dev/stdout}"
REPORT="${SBOM_RESCAN_REPORT:-reports/sbom-rescan.json}"
mkdir -p "$(dirname "$REPORT")"

TAG="$(gh api "repos/${REPO}/releases/latest" -q .tag_name)"
echo "Re-scanning SBOM from release ${TAG}"

gh release download "${TAG}" \
    -R "${REPO}" \
    -p "sbom.cyclonedx.json" \
    --clobber \
    --dir /tmp/sbom-rescan

VEX_ARGS=()
if [[ -f security/openvex.json ]]; then
    VEX_ARGS+=(--vex security/openvex.json)
fi

grype "sbom:/tmp/sbom-rescan/sbom.cyclonedx.json" \
    "${VEX_ARGS[@]}" \
    -o json > "${REPORT}" || true

python3 - "${TAG}" "${REPORT}" <<'PY' >> "${OUT}"
import json, sys
from collections import Counter

tag, report = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(report, encoding="utf-8"))
except Exception:
    print(f"## SBOM re-scan ({tag})\n\nReport could not be parsed.")
    sys.exit(0)

matches = data.get("matches") or []
sev = Counter()
for m in matches:
    sev[((m.get("vulnerability") or {}).get("severity") or "unknown")] += 1

print(f"## SBOM re-scan ({tag})")
print()
print(f"Total findings after VEX: **{len(matches)}**")
print()
if matches:
    print("| Severity | Count |")
    print("|---|---|")
    for s in ("Critical", "High", "Medium", "Low", "Negligible", "Unknown"):
        if sev.get(s):
            print(f"| {s} | {sev[s]} |")
    print()
    print("Top findings:")
    print()
    print("| CVE | Severity | Package | Installed | Fixed in |")
    print("|---|---|---|---|---|")
    def rank(m):
        order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        return order.get(((m.get("vulnerability") or {}).get("severity") or ""), 9)
    for m in sorted(matches, key=rank)[:25]:
        v = m.get("vulnerability") or {}
        a = m.get("artifact") or {}
        fix = ", ".join((v.get("fix") or {}).get("versions") or []) or "-"
        print(
            f"| {v.get('id','?')} | {v.get('severity','?')} | "
            f"{a.get('name','?')} | {a.get('version','?')} | {fix} |"
        )
else:
    print("No findings.")
PY

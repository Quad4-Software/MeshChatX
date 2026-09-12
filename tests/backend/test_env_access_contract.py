# SPDX-License-Identifier: 0BSD

"""Contract test: process env reads go through env_utils or path_utils.

os.environ.get / os.getenv / os.environ[...] reads are banned outside
the allowlist below so the set of honoured variables stays greppable
and parsing rules stay in one place. Writes (os.environ["X"] = ...,
.pop, .copy for subprocess env construction) are unaffected.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = _REPO_ROOT / "meshchatx"

_ENV_READ_RE = re.compile(
    r"os\.environ\.get\s*\(|os\.getenv\s*\(|os\.environ\s*\[\s*[\"']",
)

# Modules that own environment access. Everything else uses
# meshchatx.src.env_utils helpers or meshchatx.src.env_config.
_ALLOWED = {
    "src/env_utils.py",
    "src/path_utils.py",
}


def _env_read_violations() -> list[str]:
    violations: list[str] = []
    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        rel = path.relative_to(_PACKAGE_ROOT).as_posix()
        if rel in _ALLOWED or "__pycache__" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _ENV_READ_RE.search(line):
                violations.append(f"{rel}:{lineno}: {line.strip()}")
    return violations


def test_no_raw_env_reads_outside_allowlist():
    violations = _env_read_violations()
    assert not violations, (
        "Raw environment reads found outside env_utils/path_utils. "
        "Use meshchatx.src.env_utils (env_bool/env_str/env_int/env_float/"
        "env_path) or the MeshchatEnv snapshot:\n" + "\n".join(violations)
    )

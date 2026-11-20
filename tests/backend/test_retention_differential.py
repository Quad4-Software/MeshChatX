# SPDX-License-Identifier: 0BSD
"""Differential test: Python retention logic vs the JS localMessageRetention module.

The frontend writes {value, unit} into config. The backend reads it with
normalize_unit/retention_window_seconds. Both sides must agree on what the
stored setting means. Known intentional divergences are pinned explicitly:
the backend accepts more unit spellings ("m", "mo", " month ") than the JS
parser, and int() falls back to 1 for non-integer strings where JS truncates.
"""

import json
import subprocess
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.local_message_retention import (
    MAX_VALUE_DAYS,
    MAX_VALUE_MONTHS,
    normalize_unit,
)

JS_MODULE = (
    Path(__file__).resolve().parents[2]
    / "meshchatx/src/frontend/js/localMessageRetention.js"
)

JS_EXPR = (
    f"import('file://{JS_MODULE}').then(m => {{"
    "const cases = JSON.parse(process.argv[1]);"
    "const out = cases.map(c => m.normalizeRetentionValue(c[0], c[1]));"
    "console.log(JSON.stringify(out));})"
)


def js_normalize_batch(cases):
    """Run the real JS module once over a corpus. Returns [{value, unit}]."""
    proc = subprocess.run(
        ["node", "-e", JS_EXPR, json.dumps(cases)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    line = proc.stdout.strip().splitlines()[-1]
    return json.loads(line)


def py_normalize(value, unit):
    """Mirror of the JS return shape using the backend semantics."""
    u = normalize_unit(str(unit) if unit is not None else None)
    # Python clamps inside retention_window_seconds. Expose the clamped int.
    try:
        v = int(value)
    except (TypeError, ValueError):
        v = 1
    cap = MAX_VALUE_MONTHS if u == "months" else MAX_VALUE_DAYS
    return {"value": max(1, min(v, cap)), "unit": u}


class TestDifferentialAgreement:
    def test_frontend_output_corpus_agrees(self):
        """On the domain the frontend actually emits, both sides must agree.

        The JS normalizer is the only writer of the stored config, so its
        outputs are the contract the backend reads.
        """
        emitted = js_normalize_batch(
            [
                [v, u]
                for v in [-5, 0, 1, 2.7, 10000, 99999, "x", None]
                for u in ["days", "months", "weird", None]
            ]
        )
        for out in emitted:
            assert py_normalize(out["value"], out["unit"]) == out

    def test_known_divergences_are_backend_superset_only(self):
        """Backends accepts extra unit spellings and rejects float strings.

        These only differ on inputs the JS writer can never produce.
        """
        assert normalize_unit("mo") == "months"
        assert normalize_unit(" month ") == "months"
        assert js_normalize_batch([["mo", None]])[0]["unit"] == "days"
        # String "3.9": JS truncates to 3, Python int() raises then defaults 1.
        assert js_normalize_batch([["3.9", "days"]])[0]["value"] == 3
        assert py_normalize("3.9", "days")["value"] == 1

    @given(
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        st.sampled_from(["days", "months"]),
    )
    @settings(max_examples=200, derandomize=True, deadline=None)
    def test_clamp_bounds_agree_numeric(self, value, unit):
        js = js_normalize_batch([[value, unit]])[0]
        py = py_normalize(value, unit)
        assert js == py

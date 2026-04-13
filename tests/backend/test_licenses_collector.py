from unittest.mock import patch

from meshchatx.src.backend.licenses_collector import (
    _flatten_pnpm_licenses_json,
    build_licenses_payload,
)


def test_flatten_pnpm_licenses_json_maps_and_sorts():
    data = {
        "MIT": [
            {
                "name": "zebra-pkg",
                "versions": ["2.0.0"],
                "author": "Z",
                "license": "MIT",
            },
        ],
        "Apache-2.0": [
            {"name": "alpha-pkg", "versions": ["1.0.0"], "author": "Alice"},
            {"name": "no-version", "versions": [], "author": "—"},
        ],
    }
    rows = _flatten_pnpm_licenses_json(data)
    assert [r["name"] for r in rows] == ["alpha-pkg", "no-version", "zebra-pkg"]
    alpha = next(r for r in rows if r["name"] == "alpha-pkg")
    assert alpha["version"] == "1.0.0"
    assert alpha["author"] == "Alice"
    assert alpha["license"] == "Apache-2.0"
    nov = next(r for r in rows if r["name"] == "no-version")
    assert nov["version"] == "?"


def test_flatten_pnpm_licenses_json_non_dict_package_skipped():
    data = {"MIT": ["not-a-dict", {"name": "ok", "versions": ["1"], "author": "x"}]}
    rows = _flatten_pnpm_licenses_json(data)
    assert len(rows) == 1
    assert rows[0]["name"] == "ok"


def test_build_licenses_payload_composes_counts_and_meta():
    be = [{"name": "rns", "version": "1", "author": "a", "license": "MIT"}]
    fe = [{"name": "vue", "version": "3", "author": "b", "license": "MIT"}]
    with (
        patch(
            "meshchatx.src.backend.licenses_collector.collect_backend_licenses",
            return_value=be,
        ),
        patch(
            "meshchatx.src.backend.licenses_collector.collect_frontend_licenses",
            return_value=(fe, "pnpm"),
        ),
    ):
        payload = build_licenses_payload()
    assert payload["backend"] == be
    assert payload["frontend"] == fe
    assert payload["meta"]["backend_count"] == 1
    assert payload["meta"]["frontend_count"] == 1
    assert payload["meta"]["frontend_source"] == "pnpm"
    assert payload["meta"]["generated_at"].endswith("Z")

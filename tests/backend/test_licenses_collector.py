from pathlib import Path
from unittest.mock import patch

from meshchatx.src.backend.licenses_collector import (
    _flatten_pnpm_licenses_json,
    build_licenses_payload,
    render_third_party_notices,
    write_embedded_license_artifacts,
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


def test_render_third_party_notices_contains_sections_and_rows():
    payload = {
        "backend": [
            {"name": "rns", "version": "1.0", "author": "Author A", "license": "MIT"}
        ],
        "frontend": [
            {"name": "vue", "version": "3.0", "author": "Author B", "license": "MIT"}
        ],
        "meta": {"generated_at": "2026-01-01T00:00:00Z", "frontend_source": "pnpm"},
    }
    rendered = render_third_party_notices(payload)
    assert "Reticulum MeshChatX - Third-party notices" in rendered
    assert "Python dependencies" in rendered
    assert "Node dependencies" in rendered
    assert "rns 1.0" in rendered
    assert "vue 3.0" in rendered


def test_write_embedded_license_artifacts_writes_files(tmp_path):
    payload = {
        "backend": [{"name": "rns", "version": "1", "author": "a", "license": "MIT"}],
        "frontend": [{"name": "vue", "version": "3", "author": "b", "license": "MIT"}],
        "meta": {"generated_at": "2026-01-01T00:00:00Z", "frontend_source": "pnpm"},
    }
    with patch(
        "meshchatx.src.backend.licenses_collector.build_licenses_payload",
        return_value=payload,
    ):
        result = write_embedded_license_artifacts(repo_root=tmp_path)

    frontend_path = Path(result["frontend_path"])
    notices_path = Path(result["notices_path"])
    assert frontend_path.exists()
    assert notices_path.exists()
    assert '"name": "vue"' in frontend_path.read_text(encoding="utf-8")
    assert "Reticulum MeshChatX - Third-party notices" in notices_path.read_text(
        encoding="utf-8"
    )


def test_write_embedded_license_artifacts_preserves_existing_frontend_when_empty(
    tmp_path,
):
    data_dir = tmp_path / "meshchatx" / "src" / "backend" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    frontend_path = data_dir / "licenses_frontend.json"
    frontend_path.write_text('[{"name":"kept"}]\n', encoding="utf-8")

    payload = {
        "backend": [],
        "frontend": [],
        "meta": {"generated_at": "2026-01-01T00:00:00Z", "frontend_source": "none"},
    }
    with patch(
        "meshchatx.src.backend.licenses_collector.build_licenses_payload",
        return_value=payload,
    ):
        result = write_embedded_license_artifacts(repo_root=tmp_path)

    assert result["frontend_written"] is False
    assert frontend_path.read_text(encoding="utf-8") == '[{"name":"kept"}]\n'

# SPDX-License-Identifier: 0BSD
"""Tests for the brand constants module and the drift check."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _load_brand_module():
    spec = importlib.util.spec_from_file_location(
        "brand", _REPO / "meshchatx" / "src" / "backend" / "brand.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_brand_values_nonempty() -> None:
    brand = _load_brand_module().brand()
    required = [
        "name",
        "product_name",
        "slug",
        "app_id",
        "repository",
        "homepage",
        "container_image",
        "copyright_holder",
        "security_contact",
    ]
    for key in required:
        assert brand.get(key), f"brand field {key} must not be empty"


def test_brand_derives_from_repository() -> None:
    mod = _load_brand_module()
    values = mod._derive(
        {
            "repository": "Some-Org/Fork-App",
            "issues_url": "",
            "flatpak_repo_base_url": "",
        }
    )
    assert values["issues_url"] == "https://github.com/Some-Org/Fork-App/issues"
    assert (
        values["flatpak_repo_base_url"] == "https://some-org.github.io/Fork-App/flatpak"
    )


def test_brand_json_matches_module_defaults() -> None:
    mod = _load_brand_module()
    data = json.loads((_REPO / "brand.json").read_text())
    brand = mod.brand()
    for key, value in data.items():
        if value:
            assert brand[key] == value
        else:
            assert isinstance(brand[key], str)


def test_check_brand_passes_on_repo() -> None:
    proc = subprocess.run(
        ["node", "scripts/check-brand.mjs"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr


def test_check_brand_flags_drift(tmp_path: Path) -> None:
    fake = tmp_path / "brand.json"
    data = json.loads((_REPO / "brand.json").read_text())
    data["security_contact"] = "not-the-real-contact@example.invalid"
    fake.write_text(json.dumps(data))
    proc = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                "import { checkBrand } from './scripts/check-brand.mjs';"
                "import { loadBrand } from './scripts/brand.mjs';"
                f"const f = checkBrand(loadBrand('{fake}'), '{fake}');"
                "console.log(JSON.stringify(f));"
            ),
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    failures = json.loads(proc.stdout.strip())
    assert any("SECURITY.md" in f for f in failures)


def test_check_brand_flags_docker_image_drift(tmp_path: Path) -> None:
    fake = tmp_path / "brand.json"
    data = json.loads((_REPO / "brand.json").read_text())
    data["docker_hub_image"] = "somefork/meshchatx"
    fake.write_text(json.dumps(data))
    proc = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                "import { checkBrand } from './scripts/check-brand.mjs';"
                "import { loadBrand } from './scripts/brand.mjs';"
                f"const f = checkBrand(loadBrand('{fake}'), '{fake}');"
                "console.log(JSON.stringify(f));"
            ),
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    failures = json.loads(proc.stdout.strip())
    assert any("docker-compose.yml" in f for f in failures)
    assert any("helm/meshchatx/values.yaml" in f for f in failures)

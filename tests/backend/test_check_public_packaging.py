# SPDX-License-Identifier: 0BSD
"""scripts/ci/check-public-packaging.py rejects dirty public trees and wheels."""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci" / "check-public-packaging.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("check_public_packaging", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def chk():
    return _load_mod()


def test_clean_tree_ok(chk, tmp_path: Path):
    public = tmp_path / "public"
    assets = public / "assets"
    assets.mkdir(parents=True)
    (public / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (assets / "app-AbCdEfGh.js").write_text("1", encoding="utf-8")
    (assets / "MessagesPage-AbCdEfGh.js").write_text("1", encoding="utf-8")
    # Two hashes for one stem is allowed (app + crash-tab split).
    (assets / "vendor-micron-AaAaAaAa.js").write_text("1", encoding="utf-8")
    (assets / "vendor-micron-BbBbBbBb.js").write_text("1", encoding="utf-8")
    assert chk.check_tree(public) == []


def test_leftover_nerd_font_fails(chk, tmp_path: Path):
    public = tmp_path / "public"
    assets = public / "assets"
    assets.mkdir(parents=True)
    (public / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (assets / "RobotoMonoNerdFont-Regular-DyU2aSNn.ttf").write_bytes(b"font")
    errors = chk.check_tree(public)
    assert errors
    assert any("NerdFont" in e or "leftover" in e for e in errors)


def test_leftover_tailwind_fails(chk, tmp_path: Path):
    public = tmp_path / "public"
    assets = public / "assets" / "js" / "tailwindcss"
    assets.mkdir(parents=True)
    (public / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (assets / "tailwind-v3.4.3-forms-v0.5.7.js").write_text("/* */\n", encoding="utf-8")
    errors = chk.check_tree(public)
    assert errors
    assert any("tailwind" in e or "leftover" in e for e in errors)


def test_hash_pileup_fails(chk, tmp_path: Path):
    public = tmp_path / "public"
    assets = public / "assets"
    assets.mkdir(parents=True)
    (public / "index.html").write_text("<html></html>\n", encoding="utf-8")
    for tag in ("AaAaAaAa", "BbBbBbBb", "CcCcCcCc"):
        (assets / f"MessagesPage-{tag}.js").write_text("1", encoding="utf-8")
    errors = chk.check_tree(public)
    assert errors
    assert any("MessagesPage" in e for e in errors)


def test_wheel_leftover_fails(chk, tmp_path: Path):
    whl = tmp_path / "demo-0-py3-none-any.whl"
    with zipfile.ZipFile(whl, "w") as zf:
        zf.writestr("demo/public/index.html", "<html></html>\n")
        zf.writestr(
            "demo/public/assets/RobotoMonoNerdFont-Regular-DyU2aSNn.ttf",
            b"font",
        )
        zf.writestr(
            "demo/public/assets/js/tailwindcss/tailwind-v3.4.3-forms-v0.5.7.js",
            b"/* */\n",
        )
    errors = chk.check_wheel(whl)
    assert errors
    assert any("leftover" in e for e in errors)


def test_main_exit_codes(chk, tmp_path: Path, capsys):
    public = tmp_path / "public"
    public.mkdir()
    (public / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (public / "assets").mkdir()
    assert chk.main(["--public", str(public)]) == 0
    bad = public / "assets" / "RobotoMonoNerdFont-x.ttf"
    bad.write_bytes(b"x")
    assert chk.main(["--public", str(public)]) == 1
    err = capsys.readouterr().err
    assert "FAIL" in err

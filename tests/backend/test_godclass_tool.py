"""End-to-end checks for scripts/refactor/godclass.py.

The tool must be deterministic and lossless: moved methods are verbatim
source slices, the public surface is unchanged, and the plan/apply/verify
cycle is self-checking.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "refactor"))

import godclass

GOD_SOURCE = """import os
import sys
from collections import OrderedDict

CONSTANT = 42
helper_state = []


def helper_fn(x):
    return x * 2


class God:
    KIND = "god"

    def __init__(self):
        self.a = 1
        self.b = 2

    def alpha_one(self):
        self.a += 1
        return helper_fn(self.a)

    def alpha_two(self):
        self.a += 2
        return self.alpha_one()

    def beta_one(self):
        self.b += os.getpid()
        return self.b

    def beta_two(self):
        self.b -= 1
        return self.beta_one()

    @property
    def total(self):
        return self.a + self.b


def main():
    God().alpha_one()
"""


@pytest.fixture
def god_file(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    src = tmp_path / "god.py"
    src.write_text(GOD_SOURCE)
    return src


def _ns(**kw):
    import argparse

    base = {
        "file": "",
        "klass": "God",
        "max_loc": 60,
        "threshold": 0.5,
        "plan": "",
        "plan_out": "",
        "out_root": "",
        "package": "",
        "in_place": False,
        "original": "",
    }
    base.update(kw)
    return argparse.Namespace(**base)


def test_plan_clusters_cover_movable_methods(god_file, tmp_path):
    plan_path = tmp_path / "plan.json"
    godclass.cmd_plan(_ns(file=str(god_file), plan_out=str(plan_path)))
    plan = json.loads(plan_path.read_text())
    planned = {e["name"] for c in plan["clusters"] for e in c["methods"]}
    # __init__ is pinned; everything else movable.
    assert "__init__" in plan["stay"]
    assert "alpha_one" in planned and "beta_two" in planned
    assert "total" in planned  # property getter is movable


def test_apply_is_byte_identical_and_compiles(god_file, tmp_path):
    plan_path = tmp_path / "plan.json"
    out = tmp_path / "out"
    godclass.cmd_plan(_ns(file=str(god_file), plan_out=str(plan_path)))
    godclass.cmd_apply(
        _ns(
            file=str(god_file),
            plan=str(plan_path),
            out_root=str(out),
            package="fakepkg",
        )
    )
    plan = json.loads(plan_path.read_text())

    # Every moved method slice appears verbatim in its part file.
    orig_lines = GOD_SOURCE.splitlines()
    orig_tree = ast.parse(GOD_SOURCE)
    orig_cls = next(
        n for n in orig_tree.body if isinstance(n, ast.ClassDef) and n.name == "God"
    )
    for c in plan["clusters"]:
        ptext = (out / "god_parts" / c["file"]).read_text()
        for e in godclass._plan_methods(c):
            node = next(
                n
                for n in orig_cls.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == e["name"]
                and n.lineno == e["line"]
            )
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            start = godclass._attached_comment_start(orig_lines, first)
            expected = "\n".join(orig_lines[start - 1 : node.end_lineno])
            assert expected in ptext, f"{e['name']} not verbatim in {c['file']}"

    # Rewritten file and every part compile.
    for f in [out / "god.py", *(out / "god_parts").glob("*.py")]:
        compile(f.read_text(), str(f), "exec")

    # Shared module exists because moved methods use helper_fn/CONSTANT.
    assert (out / "god_shared.py").exists()


def test_verify_passes_on_clean_apply(god_file, tmp_path):
    plan_path = tmp_path / "plan.json"
    out = tmp_path / "out"
    godclass.cmd_plan(_ns(file=str(god_file), plan_out=str(plan_path)))
    godclass.cmd_apply(
        _ns(
            file=str(god_file),
            plan=str(plan_path),
            out_root=str(out),
            package="fakepkg",
        )
    )
    rc = godclass.cmd_verify(
        _ns(
            file=str(god_file),
            plan=str(plan_path),
            out_root=str(out),
            original=str(god_file),
        )
    )
    assert rc == 0


def test_apply_rejects_duplicate_cluster_files(god_file, tmp_path):
    plan_path = tmp_path / "plan.json"
    godclass.cmd_plan(_ns(file=str(god_file), plan_out=str(plan_path)))
    plan = json.loads(plan_path.read_text())
    if len(plan["clusters"]) < 2:
        pytest.skip("need >= 2 clusters")
    plan["clusters"][1]["file"] = plan["clusters"][0]["file"]
    plan_path.write_text(json.dumps(plan))
    with pytest.raises(SystemExit):
        godclass.cmd_apply(
            _ns(
                file=str(god_file),
                plan=str(plan_path),
                out_root=str(tmp_path / "out2"),
            )
        )

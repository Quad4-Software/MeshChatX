#!/usr/bin/env python3
"""Deterministic god-class splitter: extract method clusters into mixins.

Research basis: god-class decomposition via clustering on field-access
coupling (Fokaefs et al.), positional adjacency (ClassSplitter, ICSE'24),
and call-graph edges (Deicide). Methods that share self.<attr> reads or
writes, call each other, or sit adjacent in source tend to belong to the
same responsibility.

Extraction mechanism: each cluster becomes a plain mixin class in its own
module and the god class inherits from all of them. Method source is moved
as verbatim line slices, so semantics cannot drift: self.* still resolves
through the MRO, no call site changes, and the public API is unchanged.
Nothing is regenerated or rewritten, only relocated.

Safety model:
  - only FunctionDef/AsyncFunctionDef class members ever move
  - lifecycle dunders, getattr(self, ...) dynamic dispatch users, and
    methods that name the class directly stay pinned to the core class
  - module-level symbols needed by moved methods are extracted to a
    <stem>_shared.py leaf module that both sides import (no cycles)
  - verify: method name-set equality, byte-identical moved slices, and
    compile() on every emitted file

Subcommands:
    analyze   print cohesion stats and a proposed clustering
    plan      write an editable plan.json (cluster names, membership)
    apply     emit mixin modules plus the rewritten original file
    verify    re-check an applied split against the plan and original

Usage:
    python3 scripts/refactor/godclass.py analyze meshchatx/meshchat.py \
        --class ReticulumMeshChat
    python3 scripts/refactor/godclass.py plan ... --plan-out plan.json
    python3 scripts/refactor/godclass.py apply ... --plan plan.json --in-place
    python3 scripts/refactor/godclass.py verify ... --plan plan.json
"""

from __future__ import annotations

import argparse
import ast
import json
import keyword
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Dunders that participate in object lifecycle/protocol dispatch and must
# stay on the concrete class. Extending the MRO around them is legal but
# keeping them central makes the result easier to reason about.
PINNED_DUNDERS = frozenset(
    {
        "__init__",
        "__new__",
        "__call__",
        "__getattr__",
        "__setattr__",
        "__delattr__",
        "__del__",
        "__init_subclass__",
        "__repr__",
        "__str__",
        "__enter__",
        "__exit__",
        "__aenter__",
        "__aexit__",
        "__getattribute__",
        "__hash__",
        "__eq__",
    }
)

# Clustering weights. Shared attribute access is the strongest cohesion
# signal in the literature; calls come next; adjacency is a weak prior.
W_SHARED_ATTR = 2.0
W_CALL = 3.0
W_ADJACENT = 1.0


@dataclass
class Method:
    node: ast.AST
    name: str
    lineno: int
    end_lineno: int
    slice_start: int  # includes decorators and attached comments
    decorators: list[str]
    kind: str  # method | staticmethod | classmethod | property | setter
    attrs_read: set[str] = field(default_factory=set)
    attrs_write: set[str] = field(default_factory=set)
    calls_self: set[str] = field(default_factory=set)
    free_names: set[str] = field(default_factory=set)
    flags: set[str] = field(default_factory=set)
    order: int = 0

    @property
    def loc(self) -> int:
        return self.end_lineno - self.lineno + 1


def _bound_names(target: ast.AST, out: set[str]) -> None:
    """Collect names bound by an assignment target or loop variable."""
    for node in ast.walk(target):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Starred) and isinstance(node.value, ast.Name):
            out.add(node.value.id)


def _local_names(fn: ast.AST) -> set[str]:
    """Names bound anywhere inside the function body (not args)."""
    bound: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node is not fn:
                bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.comprehension):
            _bound_names(node.target, bound)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.alias):
            pass
    return bound


def _args_names(fn: ast.AST) -> set[str]:
    args = fn.args  # type: ignore[attr-defined]
    names = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


def _selfish(node: ast.AST, receiver: str) -> str | None:
    """Return the attribute name for `self.<attr>` / `cls.<attr>` loads."""
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == receiver
    ):
        return node.attr
    return None


def analyze_method(
    fn: ast.AST, receiver: str, comment_start: int, order: int
) -> Method:
    decorators = [ast.unparse(d) for d in fn.decorator_list]  # type: ignore[attr-defined]
    kind = "method"
    for dec in decorators:
        base = dec.split("(", 1)[0].rsplit(".", 1)[-1]
        if base in ("staticmethod", "classmethod", "property"):
            kind = base
        elif base.endswith(".setter") or base.endswith(".deleter"):
            kind = "property"
    m = Method(
        node=fn,
        name=fn.name,  # type: ignore[attr-defined]
        lineno=fn.lineno,
        end_lineno=fn.end_lineno or fn.lineno,
        slice_start=comment_start,
        decorators=decorators,
        kind=kind,
        order=order,
    )
    locals_ = _local_names(fn) | _args_names(fn)
    globals_declared: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Global):
            globals_declared.update(node.names)
            m.flags.add("global-write")
    locals_ |= globals_declared

    # Free names: loads that are not bound locally.
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in locals_:
                m.free_names.add(node.id)

    # Parent links let us split self.attr into read / write / call.
    for node in ast.walk(fn):
        for child in ast.iter_child_nodes(node):
            child._gc_parent = node  # type: ignore[attr-defined]
    for node in ast.walk(fn):
        attr = _selfish(node, receiver)
        if not attr:
            continue
        parent = getattr(node, "_gc_parent", None)
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            m.attrs_write.add(attr)
            if isinstance(node.ctx, ast.Del):
                m.flags.add("del-attr")
        elif isinstance(parent, ast.Call) and parent.func is node:
            m.calls_self.add(attr)
        else:
            m.attrs_read.add(attr)
    # Dynamic dispatch via getattr(self, name, ...) / self.__dict__.
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == receiver
        ):
            m.flags.add("dynamic-dispatch")
        if isinstance(node, ast.Attribute) and node.attr == "__dict__":
            if isinstance(node.value, ast.Name) and node.value.id == receiver:
                m.flags.add("dict-access")
        if isinstance(node, ast.Name) and node.id == "super":
            m.flags.add("super-call")
    for node in ast.walk(fn):
        for child in ast.iter_child_nodes(node):
            if hasattr(child, "_gc_parent"):
                del child._gc_parent  # type: ignore[attr-defined]
    return m


def _attached_comment_start(lines: list[str], lineno: int) -> int:
    """Walk upward over directly-attached comment lines (no blank gap)."""
    start = lineno
    i = lineno - 2  # line index above the def/decorator (0-based)
    while i >= 0 and lines[i].lstrip().startswith("#"):
        start = i + 1
        i -= 1
    return start


def collect_file(path: Path, class_name: str) -> dict:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)

    module_syms: dict[str, tuple[str, ast.AST]] = {}
    imports: list[ast.AST] = []
    target = None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(node)
            for alias in node.names:
                module_syms[(alias.asname or alias.name).split(".")[0]] = (
                    "import",
                    node,
                )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module_syms[node.name] = ("function", node)
        elif isinstance(node, ast.ClassDef):
            module_syms[node.name] = ("class", node)
            if node.name == class_name:
                target = node
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                _bound_names(tgt, set())  # placeholder no-op
                for n in ast.walk(tgt):
                    if isinstance(n, ast.Name):
                        module_syms[n.id] = ("assign", node)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            module_syms[node.target.id] = ("assign", node)
    if target is None:
        raise SystemExit(f"class {class_name} not found at module level in {path}")

    methods: list[Method] = []
    class_assigns: list[ast.AST] = []
    for i, member in enumerate(target.body):
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            first_line = min(
                [member.lineno] + [d.lineno for d in member.decorator_list]
            )
            start = _attached_comment_start(lines, first_line)
            receiver = "self"
            if any(
                d == "classmethod"
                for d in (ast.unparse(d) for d in member.decorator_list)
            ):
                receiver = "cls"
            m = analyze_method(member, receiver, start, i)
            if receiver == "self":
                # Methods may still reference cls; treat uniformly.
                m2 = analyze_method(member, "cls", start, i)
                m.attrs_read |= m2.attrs_read
                m.attrs_write |= m2.attrs_write
                m.calls_self |= m2.calls_self
                m.flags |= m2.flags
            methods.append(m)
        else:
            class_assigns.append(member)

    # Import statement -> source text (shared bound names share one stmt).
    import_texts: dict[int, str] = {}
    for node in imports:
        seg = ast.get_source_segment(source, node) or ""
        import_texts[id(node)] = seg

    return {
        "path": path,
        "source": source,
        "lines": lines,
        "tree": tree,
        "class": target,
        "methods": methods,
        "class_assigns": class_assigns,
        "module_syms": module_syms,
        "imports": imports,
        "import_texts": import_texts,
    }


def build_graph(methods: list[Method]) -> dict[tuple[int, int], float]:
    """Weighted undirected edges between indexes into `methods`.

    Callers pass the movable list. Edges come from shared self.<attr>
    access, self.<method>() calls, and source adjacency.
    """
    edges: dict[tuple[int, int], float] = {}
    attr_owners: dict[str, list[int]] = {}
    for idx, m in enumerate(methods):
        for a in m.attrs_read | m.attrs_write:
            attr_owners.setdefault(a, []).append(idx)
    for owners in attr_owners.values():
        for i in range(len(owners)):
            for j in range(i + 1, len(owners)):
                key = (owners[i], owners[j])
                edges[key] = edges.get(key, 0.0) + W_SHARED_ATTR
    by_name: dict[str, list[int]] = {}
    for idx, m in enumerate(methods):
        by_name.setdefault(m.name, []).append(idx)
    for i, m in enumerate(methods):
        for callee in m.calls_self:
            for j in by_name.get(callee, []):
                if j != i:
                    key = (min(i, j), max(i, j))
                    edges[key] = edges.get(key, 0.0) + W_CALL
    for i in range(1, len(methods)):
        key = (i - 1, i)
        edges[key] = edges.get(key, 0.0) + W_ADJACENT
    return edges


def movable_ok(m: Method) -> bool:
    if m.name in PINNED_DUNDERS:
        return False
    if "dynamic-dispatch" in m.flags or "dict-access" in m.flags:
        return False
    return True


def cluster_agglomerative(
    methods: list[Method],
    edges: dict[tuple[int, int], float],
    max_loc: int,
    threshold: float,
) -> list[list[int]]:
    """Deterministic single-linkage agglomerative clustering.

    Cluster similarity is the max pairwise edge weight between members
    (single linkage), where edges already encode shared self.attr access,
    self.method() calls, and positional adjacency. Merging is by max gain
    subject to the combined LOC cap. Deterministic: ties break on the
    earliest source position in each cluster.
    """
    n = len(methods)
    loc = [m.loc for m in methods]
    pos = [m.order for m in methods]

    # Similarity matrix over live cluster slots; -1 marks dead slots.
    sim: list[list[float]] = [[0.0] * n for _ in range(n)]
    for (i, j), w in edges.items():
        sim[i][j] = sim[j][i] = w

    alive = [True] * n
    members = [[i] for i in range(n)]
    for _ in range(n - 1):
        best_pair = None
        best = None
        for i in range(n):
            if not alive[i]:
                continue
            for j in range(i + 1, n):
                if not alive[j] or loc[i] + loc[j] > max_loc:
                    continue
                s = sim[i][j]
                cand = (s, -pos[i], -pos[j])
                if best is None or cand > best:
                    best = cand
                    best_pair = (i, j)
        if best_pair is None or best[0] < threshold:
            break
        i, j = best_pair
        for k in range(n):
            if alive[k] and k not in (i, j):
                sim[i][k] = sim[k][i] = max(sim[i][k], sim[j][k])
        loc[i] += loc[j]
        pos[i] = min(pos[i], pos[j])
        alive[j] = False
        members[i] += members[j]

    return [members[i] for i in range(n) if alive[i]]


def suggest_name(methods: list[Method]) -> str:
    """Cluster name from the most common leading snake_case token."""
    from collections import Counter

    tokens: Counter[str] = Counter()
    for m in methods:
        name = m.name.lstrip("_")
        tok = name.split("_", 1)[0]
        if tok:
            tokens[tok] += 1
    if not tokens:
        return "misc"
    return sorted(tokens.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def cmd_analyze(args: argparse.Namespace) -> int:
    info = collect_file(Path(args.file), args.klass)
    methods: list[Method] = info["methods"]
    movable = [m for m in methods if movable_ok(m)]
    pinned = [m for m in methods if not movable_ok(m)]
    edges = build_graph(movable)
    comms = cluster_agglomerative(movable, edges, args.max_loc, args.threshold)

    print(f"{args.file}: class {args.klass}")
    print(
        f"  methods: {len(methods)} total, {len(movable)} movable, "
        f"{len(pinned)} pinned/flagged"
    )
    print(f"  class-level statements kept in place: {len(info['class_assigns'])}")
    total_loc = sum(m.loc for m in movable)
    print(f"  movable LOC: {total_loc}")
    print()
    pinned_names = sorted({m.name for m in pinned})
    if pinned_names:
        print(
            f"  pinned: {', '.join(pinned_names[:12])}"
            + (" ..." if len(pinned_names) > 12 else "")
        )
        print()
    for ci, comm in enumerate(sorted(comms, key=lambda c: -len(c))):
        ms = sorted((movable[i] for i in comm), key=lambda m: m.order)
        name = suggest_name(ms)
        loc = sum(m.loc for m in ms)
        attrs = sorted({a for m in ms for a in (m.attrs_read | m.attrs_write)})
        flagged = sorted({f for m in ms for f in m.flags})
        print(f"  cluster {ci}: '{name}' mixin, {len(ms)} methods, ~{loc} LOC")
        print(
            f"    attrs: {', '.join(attrs[:10])}" + (" ..." if len(attrs) > 10 else "")
        )
        if flagged:
            print(f"    flags: {', '.join(flagged)}")
        print(
            f"    methods: {', '.join(m.name for m in ms[:14])}"
            + (" ..." if len(ms) > 14 else "")
        )
        print()
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    info = collect_file(Path(args.file), args.klass)
    methods: list[Method] = info["methods"]
    movable = [m for m in methods if movable_ok(m)]
    edges = build_graph(movable)
    comms = cluster_agglomerative(movable, edges, args.max_loc, args.threshold)

    plan = {
        "file": str(Path(args.file).resolve()),
        "class": args.klass,
        "stay": sorted(m.name for m in methods if not movable_ok(m)),
        "clusters": [],
    }
    used_names: set[str] = set()
    for ci, comm in enumerate(
        sorted(comms, key=lambda c: min(movable[i].order for i in c))
    ):
        ms = sorted((movable[i] for i in comm), key=lambda m: m.order)
        base = suggest_name(ms)
        if keyword.iskeyword(base) or keyword.issoftkeyword(base):
            base = f"{base}_kw"
        name = base
        suffix = 2
        while name in used_names or keyword.iskeyword(name):
            name = f"{base}_{suffix}"
            suffix += 1
        used_names.add(name)
        mixin = "".join(t.title() for t in name.split("_")) + "Mixin"
        plan["clusters"].append(
            {
                "id": ci,
                "name": name,
                "file": f"{name}.py",
                "mixin": mixin,
                # name + line identifies overloaded members like property
                # getter/setter pairs that share a name.
                "methods": [{"name": m.name, "line": m.lineno} for m in ms],
                "loc": sum(m.loc for m in ms),
                "flags": sorted({f for m in ms for f in m.flags}),
            }
        )
    Path(args.plan_out).write_text(json.dumps(plan, indent=2) + "\n")
    print(
        f"wrote {args.plan_out} ({len(plan['clusters'])} clusters, "
        f"{len(plan['stay'])} pinned methods)"
    )
    print("edit 'name'/'file'/'mixin' and reassign 'methods', then apply.")
    return 0


def _slice(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1 : end]) + "\n"


def _module_symbol_closure(
    free_names: set[str], module_syms: dict[str, tuple[str, ast.AST]]
) -> set[str]:
    """Module-level names (non-import) that the given free names pull in."""
    need = set()
    queue = [n for n in free_names if module_syms.get(n, ("import",))[0] != "import"]
    while queue:
        name = queue.pop()
        if name in need or name not in module_syms:
            continue
        need.add(name)
        _, node = module_syms[name]
        queue.extend(
            dep
            for dep in _free_names_of(node, module_syms)
            if module_syms.get(dep, ("import",))[0] != "import" and dep not in need
        )
    return need


def _free_names_of(node: ast.AST, module_syms: dict) -> set[str]:
    """Free names of a module-level definition (approximate, scope-aware)."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        locals_ = _local_names(node) | _args_names(node)
        return {
            n.id
            for n in ast.walk(node)
            if isinstance(n, ast.Name)
            and isinstance(n.ctx, ast.Load)
            and n.id not in locals_
        }
    return {
        n.id
        for n in ast.walk(node)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    }


def _plan_methods(c: dict) -> list[dict]:
    """Normalize plan method entries to {name, line} dicts."""
    out = []
    for entry in c["methods"]:
        if isinstance(entry, str):
            out.append({"name": entry, "line": None})
        else:
            out.append(entry)
    return out


def cmd_apply(args: argparse.Namespace) -> int:
    plan = json.loads(Path(args.plan).read_text())
    src_path = Path(plan["file"])
    info = collect_file(src_path, plan["class"])
    methods: list[Method] = info["methods"]
    module_syms = info["module_syms"]
    lines: list[str] = info["lines"]

    def find_method(entry: dict) -> Method:
        cands = [m for m in methods if m.name == entry["name"]]
        if entry.get("line") is not None:
            cands = [m for m in cands if m.lineno == entry["line"]]
        if len(cands) != 1:
            raise SystemExit(f"plan entry {entry} resolves to {len(cands)} methods")
        return cands[0]

    # The plan must be internally consistent: unique files and mixin names,
    # and every method resolvable.
    files = [c["file"] for c in plan["clusters"]]
    mixins = [c["mixin"] for c in plan["clusters"]]
    if len(set(files)) != len(files):
        raise SystemExit("plan has duplicate cluster 'file' values")
    if len(set(mixins)) != len(mixins):
        raise SystemExit("plan has duplicate cluster 'mixin' values")
    planned = [find_method(e) for c in plan["clusters"] for e in _plan_methods(c)]
    keys = [(m.name, m.lineno) for m in planned]
    if len(set(keys)) != len(keys):
        raise SystemExit("plan lists the same method in two clusters")
    stay_names = set(plan["stay"])
    overlap = [m.name for m in planned if m.name in stay_names]
    if overlap:
        raise SystemExit(
            f"plan conflict, methods in both stay and clusters: {sorted(set(overlap))}"
        )

    # Shared module-level symbols needed by any moved method.
    moved_free = set()
    per_cluster_free: dict[str, set[str]] = {}
    for c in plan["clusters"]:
        free: set[str] = set()
        for e in _plan_methods(c):
            free |= find_method(e).free_names
        per_cluster_free[c["name"]] = free
        moved_free |= free
    shared_syms = _module_symbol_closure(moved_free, module_syms)
    class_name_ref = plan["class"]
    if class_name_ref in shared_syms:
        raise SystemExit(
            f"moved methods reference {class_name_ref} by name; "
            "keep those methods in 'stay'"
        )

    stem = src_path.stem
    parts_pkg = f"{stem}_parts"
    shared_mod = f"{stem}_shared"

    needed_import_ids: dict[str, set[int]] = {}
    for c in plan["clusters"]:
        ids: set[int] = set()
        for fn_ in per_cluster_free[c["name"]]:
            entry = module_syms.get(fn_)
            if entry and entry[0] == "import":
                ids.add(id(entry[1]))
        needed_import_ids[c["name"]] = ids

    def import_lines_for(ids: set[int]) -> list[str]:
        out = []
        for node in info["imports"]:
            if id(node) in ids:
                seg = info["import_texts"].get(id(node), "")
                if seg:
                    out.append(seg)
        return sorted(set(out))

    out_root = Path(args.out_root) if args.out_root else src_path.parent
    parts_dir = out_root / parts_pkg
    written: list[Path] = []

    header = (
        '"""Extracted mixin for {cls}.\n\n'
        "Generated by scripts/refactor/godclass.py. Method bodies are verbatim\n"
        "slices of the original file; do not edit ordering casually.\n"
        '"""\n\n'
    )

    # Shared leaf module.
    if shared_syms:
        shared_body = []
        shared_ids: set[int] = set()
        for name in sorted(shared_syms, key=lambda n: module_syms[n][1].lineno):
            _, node = module_syms[name]
            for dep in _free_names_of(node, module_syms):
                e2 = module_syms.get(dep)
                if e2 and e2[0] == "import":
                    shared_ids.add(id(e2[1]))
            shared_body.append(_slice(lines, node.lineno, node.end_lineno))
        content = (
            header.replace("{cls}", f"{plan['class']} shared helpers")
            + "\n".join(import_lines_for(shared_ids))
            + "\n\n"
            + "\n".join(shared_body)
        )
        dest = out_root / f"{shared_mod}.py"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        written.append(dest)

    # Mixin modules.
    for c in plan["clusters"]:
        ms = [find_method(e) for e in _plan_methods(c)]
        ms.sort(key=lambda m: m.order)
        body = [_slice(lines, m.slice_start, m.end_lineno) for m in ms]
        shared_needed = sorted(per_cluster_free[c["name"]] & shared_syms)
        imports = import_lines_for(needed_import_ids[c["name"]])
        content = header.replace("{cls}", f"{plan['class']}::{c['name']}")
        if imports:
            content += "\n".join(imports) + "\n"
        if shared_needed:
            # Parts live in <stem>_parts/, the shared module is one level up.
            content += f"from ..{shared_mod} import " + ", ".join(shared_needed) + "\n"
        content += f"\nclass {c['mixin']}:\n" + "\n".join(body)
        dest = parts_dir / c["file"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        written.append(dest)

    # __init__.py for the parts package.
    init_py = parts_dir / "__init__.py"
    init_py.write_text('"""Mixin modules extracted from ' + f"{stem}.py" + '"""\n')
    written.append(init_py)

    # Rewrite the god file: drop moved slices and extracted shared symbols,
    # add mixin bases + imports after the existing import block.
    removed: list[tuple[int, int]] = []
    for c in plan["clusters"]:
        for e in _plan_methods(c):
            m = find_method(e)
            removed.append((m.slice_start, m.end_lineno))
    for name in shared_syms:
        node = module_syms[name][1]
        removed.append((node.lineno, node.end_lineno))
    removed.sort()
    keep_lines = []
    for idx, line in enumerate(lines, start=1):
        if any(s <= idx <= e for s, e in removed):
            continue
        keep_lines.append(line)
    src_lines = keep_lines
    cls = info["class"]

    def removed_before(ln: int) -> int:
        return sum(e - s + 1 for s, e in removed if e < ln)

    new_cls_lineno = cls.lineno - removed_before(cls.lineno)
    header_line_idx = new_cls_lineno - 1
    orig_header = src_lines[header_line_idx]
    mixins = [c["mixin"] for c in plan["clusters"]]
    if "(" in orig_header:
        new_header = orig_header.replace("(", "(" + ", ".join(mixins) + ", ", 1)
    else:
        new_header = orig_header.rstrip()[:-1] + "(" + ", ".join(mixins) + "):"
    src_lines[header_line_idx] = new_header

    pkg = args.package or _guess_package(src_path)
    import_block = [
        f"from {pkg}.{parts_pkg}.{c['file'][:-3]} import {c['mixin']}"
        for c in plan["clusters"]
    ]
    if shared_syms:
        import_block.insert(
            0,
            f"from {pkg}.{shared_mod} import " + ", ".join(sorted(shared_syms)),
        )
    # Insert after the last top-level import so names are bound before any
    # remaining module-level code runs.
    last_import_line = max(
        (n.end_lineno or n.lineno)
        for n in info["tree"].body
        if isinstance(n, (ast.Import, ast.ImportFrom))
    )
    # Guard: retained module-level statements above the insertion point
    # must not reference symbols that moved to the shared module.
    if shared_syms:
        for n in info["tree"].body:
            if n.lineno <= last_import_line and not isinstance(
                n, (ast.Import, ast.ImportFrom)
            ):
                used = {
                    x.id
                    for x in ast.walk(n)
                    if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)
                }
                bad = used & shared_syms
                if bad:
                    raise SystemExit(
                        f"module-level statement at line {n.lineno} uses "
                        f"{sorted(bad)} before the shared import lands; "
                        "keep those symbols in place or move the statement"
                    )
    insert_at = last_import_line - removed_before(last_import_line) - 1
    src_lines[insert_at + 1 : insert_at + 1] = ["", *import_block]

    new_source = "\n".join(src_lines) + "\n"
    dest = out_root / src_path.name
    if args.in_place:
        dest = src_path
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new_source)
    written.append(dest)

    # Patch-target migration map. unittest.mock.patch resolves the name on
    # the target module, so patch("pkg.<stem>.X") call sites must move to
    # wherever X is now looked up.
    patch_map: dict[str, str] = {}
    for c in plan["clusters"]:
        mod = f"{pkg}.{parts_pkg}.{c['file'][:-3]}"
        for fn_ in sorted(per_cluster_free[c["name"]]):
            if fn_ in shared_syms:
                continue  # shared names are re-exported on the original
            entry = module_syms.get(fn_)
            if entry and entry[0] == "import":
                patch_map[f"{pkg}.{stem}.{fn_}"] = f"{mod}.{fn_}"
    for name in sorted(shared_syms):
        patch_map[f"{pkg}.{stem}.{name}"] = f"{pkg}.{shared_mod}.{name}"
    plan["patch_map"] = patch_map
    Path(args.plan).write_text(json.dumps(plan, indent=2) + "\n")

    print("wrote:")
    for p in written:
        print(" ", p)
    print()
    print(f"shared symbols extracted: {sorted(shared_syms) or 'none'}")
    if patch_map:
        print()
        print("patch targets to migrate (patch where the name is looked up):")
        for old, new in sorted(patch_map.items()):
            print(f"  {old} -> {new}")
    return 0


def _guess_package(path: Path) -> str:
    """Derive the dotted package for the file's parent directory."""
    parts = []
    d = path.parent.resolve()
    while (d / "__init__.py").exists():
        parts.append(d.name)
        d = d.parent
    parts.reverse()
    return ".".join(parts) if parts else path.parent.name


def cmd_verify(args: argparse.Namespace) -> int:
    plan = json.loads(Path(args.plan).read_text())
    src_path = Path(plan["file"])
    errors: list[str] = []

    stem = src_path.stem
    root = Path(args.out_root) if args.out_root else src_path.parent
    parts_dir = root / f"{stem}_parts"

    # 1. Every planned method exists in exactly one part file.
    seen: list[tuple[str, int, str]] = []  # (name, line, part)
    for c in plan["clusters"]:
        part = parts_dir / c["file"]
        if not part.exists():
            errors.append(f"missing part file {part}")
            continue
        text = part.read_text()
        ptree = ast.parse(text)
        mixin = [n for n in ptree.body if isinstance(n, ast.ClassDef)]
        members = {
            (n.name, n.lineno)
            for cls_ in mixin
            for n in cls_.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        part_names = {n for n, _ in members}
        for e in _plan_methods(c):
            if e["name"] not in part_names:
                errors.append(f"{e['name']} missing from {part.name}")
            else:
                seen.append((e["name"], e.get("line") or 0, part.name))
        try:
            compile(text, str(part), "exec")
        except SyntaxError as ex:
            errors.append(f"{part.name} does not compile: {ex}")

    # 2. Moved method bodies are byte-identical to the original slices.
    if args.original:
        orig_src = Path(args.original).read_text()
    else:
        import shutil
        import subprocess

        git = shutil.which("git") or "git"
        repo_root = subprocess.run(
            [git, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=src_path.parent,
        ).stdout.strip()
        rel = src_path.resolve().relative_to(Path(repo_root).resolve())
        orig_src = subprocess.run(
            [git, "show", f"HEAD:{rel}"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        ).stdout
        if not orig_src:
            errors.append("could not read original from git; pass --original")
    orig_lines = orig_src.splitlines()
    orig_tree = ast.parse(orig_src)
    orig_cls = next(
        (
            n
            for n in orig_tree.body
            if isinstance(n, ast.ClassDef) and n.name == plan["class"]
        ),
        None,
    )
    if orig_cls is None:
        errors.append(f"class {plan['class']} not found in original source")
        orig_methods = {}
    else:
        orig_methods = {}
        for n in orig_cls.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                first = min([n.lineno] + [d.lineno for d in n.decorator_list])
                orig_methods.setdefault(n.name, []).append(
                    (n, _attached_comment_start(orig_lines, first))
                )

    for name, _line, part in seen:
        cands = orig_methods.get(name, [])
        orig_slice = {"\n".join(orig_lines[s - 1 : n.end_lineno]) for n, s in cands}
        # Re-slice from the part file.
        ptext = (parts_dir / part).read_text()
        ptree = ast.parse(ptext)
        pm = [
            n
            for cls_ in ptree.body
            if isinstance(cls_, ast.ClassDef)
            for n in cls_.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
        ]
        plines = ptext.splitlines()
        new_slices = set()
        for n in pm:
            first = min([n.lineno] + [d.lineno for d in n.decorator_list])
            s = _attached_comment_start(plines, first)
            new_slices.add("\n".join(plines[s - 1 : n.end_lineno]))
        if not (new_slices & orig_slice):
            errors.append(f"{name}: no byte-identical slice match in {part}")

    print(
        f"verify: {len(seen)} moved methods checked, "
        f"{sum(len(v) for v in orig_methods.values())} original methods"
    )
    missing = set(orig_methods) - {name for name, _, _ in seen} - set(plan["stay"])
    if missing:
        errors.append(f"original methods unaccounted for: {sorted(missing)}")

    # 3. Rewritten file compiles and keeps every original method name.
    rewritten = root / src_path.name if args.out_root else src_path
    try:
        compile(rewritten.read_text(), str(rewritten), "exec")
    except SyntaxError as e:
        errors.append(f"rewritten file does not compile: {e}")
    try:
        new_info = collect_file(rewritten, plan["class"])
        new_names = {m.name for m in new_info["methods"]}
        for c in plan["clusters"]:
            ptext = (parts_dir / c["file"]).read_text()
            ptree = ast.parse(ptext)
            for cls_ in ptree.body:
                if isinstance(cls_, ast.ClassDef):
                    new_names |= {
                        n.name
                        for n in cls_.body
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    }
        orig_names = set(orig_methods)
        if orig_names - new_names:
            errors.append(
                f"methods lost across split: {sorted(orig_names - new_names)}"
            )
        if new_names - orig_names:
            errors.append(f"unexpected new methods: {sorted(new_names - orig_names)}")
    except Exception as e:  # verification reports, not raises
        errors.append(f"post-split re-parse failed: {e}")

    for e in errors:
        print("  ERROR:", e)
    if errors:
        return 1
    print("verify: all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("analyze", "plan", "apply", "verify"):
        p = sub.add_parser(name)
        p.add_argument("file")
        p.add_argument("--class", dest="klass", required=True)
        p.add_argument(
            "--max-loc",
            type=int,
            default=900,
            help="cap cluster size in lines of code",
        )
        p.add_argument(
            "--threshold",
            type=float,
            default=1.0,
            help="minimum merge similarity; raise for tighter clusters",
        )
        p.add_argument("--plan", default="godclass-plan.json")
        p.add_argument("--plan-out", default="godclass-plan.json")
        p.add_argument("--out-root", default="")
        p.add_argument("--package", default="")
        p.add_argument("--in-place", action="store_true")
        p.add_argument("--original", default="")
        p.set_defaults(func=globals()[f"cmd_{name}"])
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

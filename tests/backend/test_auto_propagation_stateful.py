# SPDX-License-Identifier: 0BSD
"""RuleBasedStateMachine for AutoPropagationManager node memory."""

from types import SimpleNamespace

from hypothesis import settings
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    invariant,
    rule,
)

from meshchatx.src.backend.auto_propagation_manager import (
    FAILURE_COOLDOWN_SECONDS,
    MAX_MEMORY_NODES,
    REVERIFY_SECONDS,
    UNKNOWN_HOPS,
    AutoPropagationManager,
)


def _mgr():
    cfg = SimpleNamespace(get=lambda *a, **k: None, set=lambda *a, **k: None)
    ctx = SimpleNamespace(config=cfg, database=None, running=True)
    return AutoPropagationManager(SimpleNamespace(), ctx)


def _entry(s=0, f=0, cf=0, ls=0, lf=0, hops=UNKNOWN_HOPS):
    return {
        "successes": s,
        "failures": f,
        "consecutive_failures": cf,
        "last_success_at": ls,
        "last_failure_at": lf,
        "last_hops": hops,
    }


class AutoPropMachine(RuleBasedStateMachine):
    nodes = Bundle("nodes")

    def __init__(self):
        super().__init__()
        self.mgr = _mgr()
        self.model: dict[str, dict] = {}
        self.counter = 0

    @rule(target=nodes)
    def new_node(self):
        self.counter += 1
        return f"{self.counter:032x}"

    @rule(node=nodes)
    def record_success(self, node):
        import time

        self.mgr._record_success(node, 3)
        e = self.model.setdefault(node.lower(), _entry())
        e["successes"] += 1
        e["consecutive_failures"] = 0
        e["last_success_at"] = int(time.time())
        e["last_hops"] = 3

    @rule(node=nodes)
    def record_failure(self, node):
        import time

        self.mgr._record_failure(node)
        e = self.model.setdefault(node.lower(), _entry())
        e["failures"] += 1
        e["consecutive_failures"] += 1
        e["last_failure_at"] = int(time.time())

    @rule()
    def reload_garbage_memory(self):
        import json

        for raw in [
            "not json",
            '{"aa": 5}',
            "1234",
            json.dumps({"zz" * 16: {"successes": "x"}}),
            json.dumps({"ab" * 16: {"successes": -3, "consecutive_failures": "2"}}),
        ]:
            parsed = AutoPropagationManager._parse_memory(raw)
            for k, v in parsed.items():
                assert len(k) == 32
                for field in (
                    "successes",
                    "failures",
                    "consecutive_failures",
                    "last_success_at",
                    "last_failure_at",
                    "last_hops",
                ):
                    assert isinstance(v[field], int)

    @invariant()
    def memory_bounded_and_shaped(self):
        assert len(self.mgr._memory) <= MAX_MEMORY_NODES
        for key, entry in self.mgr._memory.items():
            assert key == key.lower() and len(key) == 32
            assert set(entry) == {
                "successes",
                "failures",
                "consecutive_failures",
                "last_success_at",
                "last_failure_at",
                "last_hops",
            }
            assert entry["consecutive_failures"] >= 0

    @invariant()
    def counters_match_model(self):
        for key, entry in self.mgr._memory.items():
            m = self.model.get(key)
            if m is None:  # trimmed or reloaded entry
                continue
            assert entry["successes"] == m["successes"]
            assert entry["failures"] == m["failures"]
            assert entry["consecutive_failures"] == m["consecutive_failures"]

    @invariant()
    def cooldown_and_verify_consistent(self):
        import time

        now = time.time()
        for key, entry in self.mgr._memory.items():
            cd = self.mgr._in_failure_cooldown(key, now)
            expect_cd = (
                entry["consecutive_failures"] > 0
                and entry["last_failure_at"] > 0
                and now - entry["last_failure_at"] < FAILURE_COOLDOWN_SECONDS
            )
            assert cd == expect_cd
            rv = self.mgr._recently_verified(key, now)
            expect_rv = (
                entry["consecutive_failures"] <= 0
                and entry["last_success_at"] > 0
                and now - entry["last_success_at"] < REVERIFY_SECONDS
            )
            assert rv == expect_rv


TestAutoPropStateful = AutoPropMachine.TestCase
TestAutoPropStateful.settings = settings(
    max_examples=40,
    stateful_step_count=30,
    derandomize=True,
    deadline=None,
)


class TestMemoryParse:
    def test_parse_rejects_garbage(self):
        for raw in [None, "", "{}", "nope", 42, ["x"], '{"' + "ab" * 16 + '": "str"}']:
            assert AutoPropagationManager._parse_memory(raw) == {}

    def test_parse_save_roundtrip(self):
        mgr = _mgr()
        mgr._record_success("ab" * 16, 2)
        cfg = mgr.config
        # _save_memory writes via config.set. Capture it.
        captured = {}
        cfg.set = lambda k, v: captured.update({k: v})
        cfg.get = lambda *a, **k: captured.get("lxmf_preferred_propagation_node_memory")
        mgr._record_success("ab" * 16, 4)
        mgr2 = _mgr()
        mgr2.config.get = cfg.get
        mgr2._load_memory()
        assert mgr2._memory["ab" * 16]["successes"] == 2
        assert mgr2._memory["ab" * 16]["last_hops"] == 4

    def test_trim_keeps_best_ranked(self):
        mem = {f"{i:032x}": _entry(s=i, ls=i) for i in range(MAX_MEMORY_NODES + 5)}
        out = AutoPropagationManager._trim_memory(mem)
        assert len(out) == MAX_MEMORY_NODES
        # Highest last_success_at survive.
        assert f"{MAX_MEMORY_NODES + 4:032x}" in out
        assert f"{0:032x}" not in out

# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.process_resource_breakdown import (
    build_resource_breakdown,
    top_by_cpu,
    top_by_rss,
)


class _Mem:
    def __init__(self, rss):
        self.rss = rss


class _FakeProc:
    def __init__(self, name, rss, cpu=1.0, children=None):
        self._name = name
        self._rss = rss
        self._cpu = cpu
        self._children = children or []
        self.pid = abs(hash(name)) % 100000

    def name(self):
        return self._name

    def memory_info(self):
        return _Mem(self._rss)

    def cpu_percent(self, interval=None):
        return self._cpu

    def children(self, recursive=True):
        return list(self._children)


def test_build_resource_breakdown_orders_by_rss():
    child_big = _FakeProc("bot", 80_000_000, cpu=20.0)
    child_small = _FakeProc("helper", 5_000_000, cpu=2.0)
    parent = _FakeProc("python", 40_000_000, cpu=5.0, children=[child_big, child_small])

    rows = build_resource_breakdown(parent)
    assert rows[0]["name"] == "child:bot"
    assert rows[0]["rss"] == 80_000_000
    assert top_by_rss(rows)["name"] == "child:bot"
    assert top_by_cpu(rows)["name"] == "child:bot"


def test_build_resource_breakdown_handles_none():
    assert build_resource_breakdown(None) == []
    assert top_by_rss([]) is None
    assert top_by_cpu([]) is None

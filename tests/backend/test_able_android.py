# SPDX-License-Identifier: 0BSD

import sys
from pathlib import Path

import pytest

ABLE_ROOT = (
    Path(__file__).resolve().parents[2] / "android" / "app" / "src" / "main" / "python"
)


@pytest.fixture
def able_path(monkeypatch):
    monkeypatch.syspath_prepend(str(ABLE_ROOT))
    for name in list(sys.modules):
        if name == "able" or name.startswith("able."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    yield
    for name in list(sys.modules):
        if name == "able" or name.startswith("able."):
            monkeypatch.delitem(sys.modules, name, raising=False)


def test_able_services_search(able_path):
    from able.structures import Services

    services = Services(
        {
            "service0": {"c1-aa": 0, "aa-c2-aa": 1},
            "service1": {"bb-c3-bb": 2},
        },
    )
    assert services.search("c3") == 2
    assert services.search("c4") is None


def test_able_queue_runs_immediate_tasks(able_path):
    from able.queue import BLEQueue

    seen = []
    queue = BLEQueue(timeout=0)
    queue.enque(lambda: seen.append("ok"))
    assert seen == ["ok"]

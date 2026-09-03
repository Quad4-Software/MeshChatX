# SPDX-License-Identifier: 0BSD

import json

import pytest

from meshchatx.src.backend.bug_report_manager import BugReportManager


def _fake_app(tmp_path):
    class FakeApp:
        storage_dir = str(tmp_path)
        current_context = None

    return FakeApp()


def test_preview_report_uses_database_logs(tmp_path):
    full_hash = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"

    class FakeLogs:
        def get_logs(self, **_kwargs):
            return [
                {
                    "timestamp": 1.0,
                    "level": "ERROR",
                    "module": "meshchat",
                    "message": f"fail at /tmp/x for {full_hash}",
                },
            ]

        def get_total_count(self, **_kwargs):
            return 1

    class FakeDatabase:
        debug_logs = FakeLogs()

    class FakeApp:
        database = FakeDatabase()
        storage_dir = str(tmp_path)
        current_context = None

    manager = BugReportManager(FakeApp())
    preview = manager.preview_report({"limit": 5})
    assert preview["line_count"] == 1
    assert "/tmp/x" not in preview["log_text"]
    assert full_hash not in preview["log_text"]
    assert "[redacted]" in preview["log_text"]
    assert preview["chars"] > 0


def test_preview_report_empty_when_no_logs(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    preview = manager.preview_report({"limit": 10})
    assert preview["line_count"] == 0
    assert preview["chars"] == 0
    assert preview["log_text"] == ""


def test_list_collectors_and_reports_empty(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    assert manager.list_collectors()["collectors"] == []
    assert manager.list_reports()["reports"] == []
    assert manager.status()["collector_running"] is False


def test_delete_and_clear_reports(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    manager._reports = [
        {"received_at": 1000, "title": "A"},
        {"received_at": 2000, "title": "B"},
        {"received_at": 3000, "title": "C"},
    ]
    assert len(manager.list_reports(limit=10)["reports"]) == 3

    result = manager.delete_report(1)
    assert result["ok"] is True
    assert len(manager.list_reports(limit=10)["reports"]) == 2
    titles = [r["title"] for r in manager.list_reports(limit=10)["reports"]]
    assert "B" not in titles

    with pytest.raises(IndexError):
        manager.delete_report(99)

    result = manager.clear_reports()
    assert result["ok"] is True
    assert manager.list_reports()["reports"] == []


def test_collector_name_is_truncated(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    assert manager.status()["collector_name"] == ""

    manager.set_collector_name("Test Node")
    assert manager.status()["collector_name"] == "Test Node"

    manager.set_collector_name("x" * 100)
    assert len(manager.status()["collector_name"]) <= 64


def test_report_receive_and_list(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    response = manager._report_response(
        path="/report",
        data=json.dumps(
            {"title": "test", "description": "desc", "log_text": "log"},
        ).encode("utf-8"),
        request_id=b"",
        link_id=None,
        remote_identity=None,
        requested_at=0,
    )
    assert response["ok"] is True
    reports = manager.list_reports(limit=10)["reports"]
    assert len(reports) == 1
    assert reports[0]["title"] == "test"
    assert "redactions" not in reports[0]


def test_send_report_rejects_invalid_hashes(tmp_path, monkeypatch):
    manager = BugReportManager(_fake_app(tmp_path))
    monkeypatch.setattr("RNS.Identity.recall", lambda _h: None)

    with pytest.raises(ValueError, match="destination_hash is required"):
        manager.send_report(
            {
                "destination_hash": "",
                "title": "t",
                "description": "d",
            },
        )

    invalid_hashes = [
        "local",
        "abc",
        "g" * 64,
        "0" * 30,
        "0" * 31,
        "0" * 65,
        "0" * 66,
        "0" * 33,
    ]
    for h in invalid_hashes:
        with pytest.raises(ValueError, match="Invalid collector hash"):
            manager.send_report(
                {
                    "destination_hash": h,
                    "title": "t",
                    "description": "d",
                },
            )


def test_send_report_accepts_32_and_64_char_hashes(tmp_path, monkeypatch):
    manager = BugReportManager(_fake_app(tmp_path))

    received = []

    def fake_report_response(*args, **kwargs):
        received.append((args, kwargs))
        return {"ok": True}

    monkeypatch.setattr(manager, "_report_response", fake_report_response)

    for length in (32, 64):
        hash_value = "a" * length

        class FakeDestination:
            hash = type("H", (), {"hex": lambda _s, _hash=hash_value: _hash})()

        manager._destination = FakeDestination()

        result = manager.send_report(
            {
                "destination_hash": hash_value,
                "title": f"len{length}",
                "description": "d",
                "limit": 5,
            },
        )
        assert result["ok"] is True

    assert len(received) == 2


def test_send_local_report_bypasses_rns(tmp_path, monkeypatch):
    manager = BugReportManager(_fake_app(tmp_path))
    local_hash = "a" * 64

    class FakeDestination:
        hash = type("H", (), {"hex": lambda _s: local_hash})()

    manager._destination = FakeDestination()

    received = []

    def fake_report_response(*args, **kwargs):
        received.append((args, kwargs))
        return {"ok": True}

    monkeypatch.setattr(manager, "_report_response", fake_report_response)

    result = manager.send_report(
        {
            "destination_hash": local_hash,
            "title": "Local Bug",
            "description": "desc",
            "limit": 5,
        },
    )

    assert result["ok"] is True
    assert result["destination_hash"] == "local"
    assert len(received) == 1
    assert b"Local Bug" in received[0][1]["data"]


def test_send_remote_report_requires_identity_recall(tmp_path, monkeypatch):
    manager = BugReportManager(_fake_app(tmp_path))
    remote_hash = "b" * 64

    monkeypatch.setattr("RNS.Identity.recall", lambda _h: None)

    with pytest.raises(LookupError, match="Could not recall collector identity"):
        manager.send_report(
            {
                "destination_hash": remote_hash,
                "title": "Remote Bug",
                "description": "desc",
            },
        )


def test_status_reflects_local_collector(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    local_hash = "c" * 64

    class FakeDestination:
        hash = type("H", (), {"hex": lambda _s: local_hash})()

    manager._destination = FakeDestination()
    manager._collector_name = "MyCollector"

    status = manager.status()
    assert status["collector_running"] is True
    assert status["destination_hash"] == local_hash
    assert status["collector_name"] == "MyCollector"
    assert status["reports"] == 0
    assert status["collectors"] == 0


def test_build_payload_enforces_size_limit(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    manager._reports = []

    class FakeLogs:
        def get_logs(self, **_kwargs):
            return [
                {"timestamp": 1, "level": "INFO", "module": "m", "message": "x"},
            ] * 10

        def get_total_count(self, **_kwargs):
            return 10

    manager.app = type(
        "A",
        (),
        {"database": type("DB", (), {"debug_logs": FakeLogs()})()},
    )()

    payload, body = manager._build_payload({"limit": 10})
    assert payload["title"] == "MeshChatX bug report"
    assert "log_text" in payload
    assert len(body) > 0


def test_clear_reports_deletes_persisted_files(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    manager._reports = [{"received_at": 1234, "title": "X"}]
    manager._persist_report(manager._reports[0])

    storage = manager._ensure_storage_dir()
    assert any(f.endswith(".json") for f in manager._storage_dir_list(storage))

    manager.clear_reports()
    assert manager.list_reports()["reports"] == []
    assert not any(f.endswith(".json") for f in manager._storage_dir_list(storage))


# helper to avoid listing errors on empty dir


def test_delete_report_deletes_persisted_file(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    manager._reports = [
        {"received_at": 1000, "title": "A"},
        {"received_at": 2000, "title": "B"},
    ]
    manager._persist_report(manager._reports[0])
    manager._persist_report(manager._reports[1])

    result = manager.delete_report(0)
    assert result["ok"] is True
    assert len(manager.list_reports(limit=10)["reports"]) == 1


def test_inbound_redaction_and_fingerprint_merge(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    secret = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
    payload = {
        "v": 2,
        "title": "Boom",
        "description": "desc",
        "log_text": f"fail at /tmp/secret for {secret}",
        "exception": {
            "type": "RuntimeError",
            "value": "nope",
            "stack": 'RuntimeError: nope\n  File "/tmp/x.py", line 1',
        },
    }
    first = manager._report_response(
        path="/report",
        data=json.dumps(payload).encode("utf-8"),
        request_id=b"",
        link_id=None,
        remote_identity=None,
        requested_at=0,
    )
    second = manager._report_response(
        path="/report",
        data=json.dumps(payload).encode("utf-8"),
        request_id=b"",
        link_id=None,
        remote_identity=None,
        requested_at=0,
    )
    assert first["ok"] is True
    assert second["ok"] is True
    assert first["fingerprint"] == second["fingerprint"]
    report = manager.list_reports(limit=1)["reports"][0]
    assert "/tmp/secret" not in report["log_text"]
    assert secret not in report["log_text"]
    assert "[redacted]" in report["log_text"]
    issues = manager.list_issues(limit=10)["issues"]
    assert len(issues) == 1
    assert issues[0]["count"] == 2


def test_record_local_and_reload(tmp_path):
    app = _fake_app(tmp_path)
    manager = BugReportManager(app)
    result = manager.record_local(
        {
            "title": "Local fail",
            "exception": {
                "type": "ValueError",
                "value": "bad",
                "stack": "ValueError: bad\n  at main",
            },
            "source": "frontend",
            "force": True,
        },
    )
    assert result["ok"] is True
    fingerprint = result["fingerprint"]
    assert manager.get_issue(fingerprint)["issue"]["title"] == "Local fail"

    reloaded = BugReportManager(app)
    assert fingerprint in {i["fingerprint"] for i in reloaded.list_issues()["issues"]}


def test_set_issue_status(tmp_path):
    manager = BugReportManager(_fake_app(tmp_path))
    result = manager.record_local(
        {
            "title": "Status test",
            "exception": {"type": "Error", "value": "x", "stack": "Error: x"},
            "force": True,
        },
    )
    fp = result["fingerprint"]
    updated = manager.set_issue_status(fp, "resolved")
    assert updated["issue"]["status"] == "resolved"


# Patch the manager to add a list helper for cross-platform robustness
BugReportManager._storage_dir_list = lambda _self, path: [
    name for name in __import__("os").listdir(path)
]

"""Tests for LXMFy debugger."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from lxmfy.cli import run_debug_command
from lxmfy.debugger import (
    CheckResult,
    Debugger,
    DestinationProbe,
    DoctorReport,
    normalize_destination_hex,
    parse_destination_hash,
    redact_hash,
    redact_path,
    redact_sensitive_text,
)


class TestHashHelpers:
    def test_normalize_strips_separators(self):
        assert normalize_destination_hex("AA:BB-cc") == "aabbcc"

    def test_parse_invalid(self):
        assert parse_destination_hash("not-hex") is None
        assert parse_destination_hash("abcd") is None

    def test_parse_valid_length(self):
        raw = "ab" * 16
        parsed = parse_destination_hash(raw)
        assert parsed is not None
        assert len(parsed) == 16


class TestPrivacyHelpers:
    def test_redact_path_home(self, monkeypatch, tmp_path):
        home = str(tmp_path)
        monkeypatch.setenv("HOME", home)
        full = f"{home}/projects/bot/config"
        assert redact_path(full).startswith("~/")
        assert home not in redact_path(full)

    def test_redact_hash(self):
        h = "ab" * 16
        out = redact_hash(h)
        assert "…" in out
        assert len(out) < len(h)

    def test_redact_sensitive_text_hash_and_home(self, monkeypatch, tmp_path):
        home = str(tmp_path)
        monkeypatch.setenv("HOME", home)
        h = "cd" * 16
        text = f"config at {home}/x hash={h}"
        out = redact_sensitive_text(text)
        assert home not in out
        assert h not in out


class TestDebuggerUnit:
    def test_probe_invalid_hash(self, tmp_path):
        dbg = Debugger(config_path=str(tmp_path))
        probe = dbg.probe_destination("zzz")
        assert probe.valid_hash is False
        assert probe.hints

    def test_check_environment(self, tmp_path):
        dbg = Debugger(config_path=str(tmp_path))
        checks = dbg.check_environment()
        names = {c.name for c in checks}
        assert "os" in names
        assert "python" in names
        assert "lxmfy" in names

    def test_check_disk_permissions(self, tmp_path):
        cfg = tmp_path / "botcfg"
        cfg.mkdir()
        rns = tmp_path / "rns"
        rns.mkdir()
        data = tmp_path / "data"
        data.mkdir()
        (cfg / "config").write_text(
            "[reticulum]\nshare_instance = No\n",
            encoding="utf-8",
        )
        dbg = Debugger(
            config_path=str(cfg),
            reticulum_config_dir=str(rns),
        )
        dbg._storage_path = str(data)
        checks = dbg.check_disk_permissions()
        by_name = {c.name: c for c in checks}
        assert by_name["config_path"].status == "ok"
        assert by_name["reticulum_config_dir"].status == "ok"
        assert by_name["storage_path"].status == "ok"

    def test_check_reticulum_isolated_share_yes(self, tmp_path):
        cfg = tmp_path / "botcfg"
        cfg.mkdir()
        (cfg / "config").write_text(
            "[reticulum]\nshare_instance = Yes\n",
            encoding="utf-8",
        )
        dbg = Debugger(
            config_path=str(cfg),
            reticulum_config_dir=str(cfg),
        )
        checks = dbg.check_instance()
        mode = next(c for c in checks if c.name == "instance_mode")
        assert mode.status == "fail"
        assert "owned" in mode.detail

    def test_check_reticulum_isolated_share_no(self, tmp_path):
        cfg = tmp_path / "botcfg"
        cfg.mkdir()
        (cfg / "config").write_text(
            "[reticulum]\nshare_instance = No\n",
            encoding="utf-8",
        )
        dbg = Debugger(
            config_path=str(cfg),
            reticulum_config_dir=str(cfg),
        )
        checks = dbg.check_instance()
        mode = next(c for c in checks if c.name == "instance_mode")
        assert mode.status == "ok"
        assert mode.detail.startswith("owned")

    def test_bot_hash_from_identity_does_not_register_destination(self, tmp_path):
        """Identity hash lookup must not register lxmf/delivery on Transport."""
        import RNS

        identity = RNS.Identity()
        identity_file = tmp_path / "identity"
        identity.to_file(str(identity_file))
        expected = RNS.Destination.hash(identity, "lxmf", "delivery")

        dbg = Debugger(config_path=str(tmp_path), privacy=False)
        with patch("RNS.Destination", wraps=RNS.Destination) as dest_cls:
            dest_cls.hash = staticmethod(RNS.Destination.hash)
            checks = dbg.check_bot_identity()

        # Constructor must not be used (that registers the destination)
        assert dest_cls.call_count == 0
        by_name = {c.name: c for c in checks}
        assert by_name["bot_delivery_hash"].status == "ok"
        assert (
            RNS.hexrep(expected, delimit=False) in by_name["bot_delivery_hash"].detail
        )

    def test_diagnose_send_with_mock_probe(self, tmp_path):
        dbg = Debugger(config_path=str(tmp_path))
        dest = "ab" * 16
        probe = DestinationProbe(
            destination=dest,
            valid_hash=True,
            identity_known=False,
            has_path=False,
        )
        checks = dbg.diagnose_send(dest, probe=probe)
        by_name = {c.name: c for c in checks}
        assert by_name["identity_known"].status == "fail"
        assert by_name["has_path"].status == "fail"
        assert by_name["send_would_queue"].status == "fail"

    def test_bot_delivery_attempts(self, tmp_path):
        bot = SimpleNamespace(
            config=SimpleNamespace(
                announce_enabled=True,
                announce=600,
                opportunistic_sending=True,
                propagation_fallback_enabled=True,
                propagation_node=None,
                autopeer_propagation=False,
                enable_propagation_node=False,
                direct_delivery_retries=3,
                test_mode=False,
                message_persistence_enabled=True,
                stamp_cost=None,
                require_stamps=False,
                signature_verification_enabled=False,
                require_message_signatures=False,
                storage_path=str(tmp_path / "data"),
                landlock_enabled=True,
            ),
            local=None,
            router=None,
            config_path=str(tmp_path),
            reticulum_config_dir=str(tmp_path),
            delivery_attempts={"aabbccdd" * 2: 2},
            queue=SimpleNamespace(qsize=lambda: 0, maxsize=50),
            storage=SimpleNamespace(
                get=lambda key, default=None: (
                    {"aabbccdd" * 2: 2} if key == "delivery_attempts" else []
                ),
            ),
            get_propagation_node_status=lambda: {
                "current_outbound_node": None,
                "discovered_peers": [],
            },
            get_landlock_status=lambda: {
                "active": False,
                "supported": True,
                "config_enabled": True,
            },
        )
        (tmp_path / "config").write_text(
            "[reticulum]\nshare_instance = No\n",
            encoding="utf-8",
        )
        (tmp_path / "data").mkdir()
        dbg = Debugger(bot=bot, config_path=str(tmp_path))
        checks = dbg.check_storage_history()
        attempts = next(c for c in checks if c.name == "delivery_attempts")
        assert attempts.status == "warn"

    def test_run_doctor_categories_and_save(self, tmp_path):
        cfg = tmp_path / "botcfg"
        cfg.mkdir()
        (cfg / "config").write_text(
            "[reticulum]\nshare_instance = No\n[interfaces]\n",
            encoding="utf-8",
        )
        data = tmp_path / "data"
        data.mkdir()
        dbg = Debugger(
            config_path=str(cfg),
            reticulum_config_dir=str(cfg),
        )
        dbg._storage_path = str(data)
        with patch.object(dbg, "ensure_reticulum", return_value=False):
            with patch.object(
                dbg,
                "check_interfaces",
                return_value=[
                    CheckResult(
                        "interfaces",
                        "fail",
                        "Reticulum not initialized",
                        category="network",
                    ),
                ],
            ):
                report = dbg.run_doctor()
        cats = {c.category for c in report.checks}
        assert "environment" in cats
        assert "instance" in cats
        assert "disk" in cats
        assert "network" in cats
        assert report.send_blockers or report.to_dict()["failures"] >= 1

        out = tmp_path / "report.txt"
        saved = dbg.save_report(report, str(out))
        text = open(saved, encoding="utf-8").read()
        assert "LXMFy Debugger Report" in text
        assert "Environment / OS" in text
        assert "Disk Permissions" in text
        assert "Blockers" in text

        jout = tmp_path / "report.json"
        saved_json = dbg.save_report(report, str(jout), as_json=True)
        import json

        data = json.loads(open(saved_json, encoding="utf-8").read())
        assert "checks" in data
        assert data["privacy"] is True

    def test_print_report_no_crash(self, tmp_path, capsys):
        dbg = Debugger(config_path=str(tmp_path))
        report = DoctorReport(
            reticulum_config_dir=str(tmp_path),
            checks=[
                CheckResult("demo", "ok", "fine", category="environment"),
                CheckResult(
                    "warn_me",
                    "warn",
                    "careful",
                    "fix it",
                    category="send",
                ),
            ],
            tips=["tip one"],
            generated_at="2026-01-01T00:00:00Z",
            lxmfy_version="2.0.2",
            privacy=True,
        )
        dbg.print_report(report)
        out = capsys.readouterr().out
        assert "demo" in out
        assert "tip one" in out


class TestDebugCli:
    def test_tips_exit_zero(self):
        assert run_debug_command(["tips"]) == 0

    def test_probe_requires_hash(self):
        assert run_debug_command(["probe"]) == 1

    def test_probe_invalid_hash(self, tmp_path):
        code = run_debug_command(
            ["probe", "nope", "--json", "--output", str(tmp_path / "p.json")],
        )
        assert code == 2
        assert (tmp_path / "p.json").is_file()

    @patch("lxmfy.debugger.Debugger.run_doctor")
    @patch("lxmfy.debugger.Debugger.save_report")
    def test_doctor_success(self, mock_save, mock_doctor):
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {
            "failures": 0,
            "warnings": 0,
            "checks": [],
            "tips": [],
            "ok": True,
            "probe": None,
            "reticulum_config_dir": "/tmp",
            "bot_hash": None,
            "privacy": True,
            "generated_at": "t",
            "lxmfy_version": "2.0.2",
            "send_blockers": [],
            "receive_blockers": [],
        }
        mock_report.checks = []
        mock_report.probe = None
        mock_report.tips = []
        mock_report.reticulum_config_dir = "/tmp"
        mock_report.bot_hash = None
        mock_report.generated_at = "t"
        mock_report.lxmfy_version = "2.0.2"
        mock_report.privacy = True
        mock_report.send_blockers = []
        mock_report.receive_blockers = []
        mock_doctor.return_value = mock_report
        mock_save.return_value = "/tmp/out.json"
        assert run_debug_command(["doctor", "--json", "--no-save"]) == 0


class TestVerdictAndSeverity:
    def test_sort_fail_before_ok(self):
        from lxmfy.debugger import sort_checks_by_severity

        checks = [
            CheckResult("a", "ok", category="send"),
            CheckResult("b", "fail", category="network"),
            CheckResult("c", "warn", category="disk"),
        ]
        sorted_checks = sort_checks_by_severity(checks)
        assert sorted_checks[0].status == "fail"
        assert sorted_checks[-1].status == "ok"

    def test_verdict_cannot_send(self):
        from lxmfy.debugger import build_verdict

        checks = [
            CheckResult("interfaces_online", "fail", "0/1", category="network"),
            CheckResult("identity_known", "fail", "False", category="destination"),
        ]
        verdict, steps = build_verdict(
            checks,
            send_blockers=["interfaces_online: 0/1"],
            receive_blockers=[],
        )
        assert verdict == "cannot_send"
        assert steps

    def test_verdict_likely_ok(self):
        from lxmfy.debugger import build_verdict

        checks = [CheckResult("os", "ok", "Linux", category="environment")]
        verdict, steps = build_verdict(
            checks,
            send_blockers=[],
            receive_blockers=[],
        )
        assert verdict == "likely_ok"
        assert steps

    def test_verdict_shared_client_warn_step(self):
        from lxmfy.debugger import build_verdict

        checks = [
            CheckResult(
                "shared_instance_role",
                "warn",
                "RNS client via LocalClientInterface only",
                category="network",
            ),
        ]
        verdict, steps = build_verdict(
            checks,
            send_blockers=[],
            receive_blockers=[],
        )
        assert verdict == "likely_ok_with_warnings"
        assert any("LocalClientInterface" in s for s in steps)

    def test_report_includes_verdict(self, tmp_path):
        cfg = tmp_path / "botcfg"
        cfg.mkdir()
        (cfg / "config").write_text(
            "[reticulum]\nshare_instance = No\n[interfaces]\n",
            encoding="utf-8",
        )
        data = tmp_path / "data"
        data.mkdir()
        dbg = Debugger(config_path=str(cfg), reticulum_config_dir=str(cfg))
        dbg._storage_path = str(data)
        with patch.object(dbg, "ensure_reticulum", return_value=False):
            with patch.object(
                dbg,
                "check_interfaces",
                return_value=[
                    CheckResult(
                        "interfaces_online",
                        "fail",
                        "0/0",
                        category="network",
                    ),
                ],
            ):
                report = dbg.run_doctor()
        assert report.verdict in {
            "cannot_send",
            "cannot_send_or_receive",
            "cannot_receive",
            "issues_detected",
        }
        assert report.next_steps
        text = dbg.format_report_text(report)
        assert "verdict:" in text
        assert "Next Steps" in text


class TestStorageHistory:
    def test_reads_disk_attempts(self, tmp_path):
        import json

        data = tmp_path / "data"
        data.mkdir()
        dest = "ab" * 16
        (data / "delivery_attempts.json").write_text(
            json.dumps({dest: 3}),
            encoding="utf-8",
        )
        (data / "persisted_queue.json").write_text("[]", encoding="utf-8")
        dbg = Debugger(config_path=str(tmp_path), privacy=True)
        dbg._storage_path = str(data)
        checks = dbg.check_storage_history()
        by_name = {c.name: c for c in checks}
        assert by_name["delivery_attempts"].status == "warn"
        assert "…" in by_name["delivery_attempts"].detail
        assert dest not in by_name["delivery_attempts"].detail

    def test_corrupt_attempts_file(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "delivery_attempts.json").write_text("{not-json", encoding="utf-8")
        dbg = Debugger(config_path=str(tmp_path))
        dbg._storage_path = str(data)
        checks = dbg.check_storage_history()
        assert any(
            c.name == "delivery_attempts_file" and c.status == "warn" for c in checks
        )

    def test_wrong_type_attempts(self, tmp_path):
        import json

        data = tmp_path / "data"
        data.mkdir()
        (data / "delivery_attempts.json").write_text(
            json.dumps([1, 2]),
            encoding="utf-8",
        )
        dbg = Debugger(config_path=str(tmp_path))
        dbg._storage_path = str(data)
        checks = dbg.check_storage_history()
        assert any(
            c.name == "delivery_attempts_file" and "unexpected" in c.detail
            for c in checks
        )


class TestDeliveryConfig:
    def test_defaults_without_bot(self, tmp_path):
        dbg = Debugger(config_path=str(tmp_path))
        checks = dbg.check_delivery_config()
        by_name = {c.name: c for c in checks}
        assert by_name["delivery_config_source"].detail == "defaults"
        assert by_name["opportunistic_sending"].status == "ok"
        assert by_name["default_delivery_method"].detail == "OPPORTUNISTIC"


class TestCompareAndTimeline:
    def test_compare_invalid_hashes(self, tmp_path):
        dbg = Debugger(config_path=str(tmp_path))
        result = dbg.compare_destinations("aa", "bb")
        assert result["both_valid"] is False

    def test_compare_same_hash_note(self, tmp_path):
        dbg = Debugger(config_path=str(tmp_path))
        h = "cd" * 16
        with patch.object(dbg, "ensure_reticulum", return_value=False):
            result = dbg.compare_destinations(h, h.upper())
        assert result["both_valid"] is True
        assert any("same destination" in n for n in result["notes"])

    def test_probe_timeline_events(self, tmp_path):
        import RNS

        dbg = Debugger(config_path=str(tmp_path))
        h = "ef" * 16

        with patch.object(dbg, "ensure_reticulum", return_value=True):
            with patch.object(RNS.Identity, "recall", return_value=None):
                with patch.object(RNS.Identity, "recall_app_data", return_value=None):
                    with patch.object(RNS.Transport, "has_path", return_value=False):
                        with patch.object(
                            RNS.Transport,
                            "request_path",
                            return_value=None,
                        ):
                            probe = dbg.probe_destination(
                                h,
                                request_path=True,
                                wait=0.3,
                            )
        events = [e["event"] for e in probe.timeline]
        assert "probe_start" in events
        assert "identity_unknown" in events
        assert "path_missing" in events
        assert "path_requested" in events
        assert "path_timeout" in events
        assert probe.path_requested is True


class TestAdversarialDebugger:
    def test_destination_constructor_never_used_for_hash(self, tmp_path):
        import RNS

        identity = RNS.Identity()
        identity.to_file(str(tmp_path / "identity"))
        dbg = Debugger(config_path=str(tmp_path), privacy=False)
        with patch.object(RNS.Transport, "register_destination") as reg:
            with patch("RNS.Destination", wraps=RNS.Destination) as dest_cls:
                dest_cls.hash = staticmethod(RNS.Destination.hash)
                dbg.check_bot_identity()
        assert dest_cls.call_count == 0
        assert reg.call_count == 0

    def test_privacy_strips_username_from_report(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USER", "secretuser")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        (tmp_path / "home").mkdir()
        cfg = tmp_path / "home" / "secretuser" / "bot"
        cfg.mkdir(parents=True)
        (cfg / "config").write_text(
            "[reticulum]\nshare_instance = No\n",
            encoding="utf-8",
        )
        dbg = Debugger(
            config_path=str(cfg),
            reticulum_config_dir=str(cfg),
            privacy=True,
        )
        with patch.object(dbg, "ensure_reticulum", return_value=False):
            with patch.object(dbg, "check_interfaces", return_value=[]):
                report = dbg.run_doctor()
        text = dbg.format_report_text(report)
        assert "secretuser" not in text

    def test_no_privacy_keeps_full_hash_in_probe_dict(self):
        h = "aa" * 16
        probe = DestinationProbe(destination=h, valid_hash=True)
        assert probe.to_dict(privacy=False)["destination"] == h
        assert "…" in probe.to_dict(privacy=True)["destination"]

    def test_shared_instance_role_when_only_local_client(self, tmp_path):
        dbg = Debugger(config_path=str(tmp_path))

        class LocalClientInterface:
            name = "Local shared instance"
            online = True

        class FakeTransport:
            interfaces = [LocalClientInterface()]
            is_shared_instance = True

        with patch.object(dbg, "ensure_reticulum", return_value=True):
            with patch("RNS.Transport", FakeTransport):
                checks = dbg.check_interfaces()
        names = {c.name: c for c in checks}
        assert "shared_instance_role" in names
        assert names["shared_instance_role"].status == "warn"

    def test_compare_cli_requires_two(self):
        assert run_debug_command(["compare", "aa"]) == 1

    def test_compare_cli_json(self, tmp_path):
        h1 = "11" * 16
        h2 = "22" * 16
        out = tmp_path / "c.json"
        with patch("lxmfy.debugger.Debugger.compare_destinations") as mock_cmp:
            mock_cmp.return_value = {
                "both_valid": True,
                "both_identity_known": False,
                "both_have_path": False,
                "left": {"destination": h1, "valid_hash": True},
                "right": {"destination": h2, "valid_hash": True},
                "notes": [],
            }
            with patch("lxmfy.debugger.Debugger.run_doctor") as mock_doc:
                mock_doc.return_value = DoctorReport(privacy=True)
                with patch(
                    "lxmfy.debugger.Debugger.save_report",
                    return_value=str(out),
                ):
                    code = run_debug_command(
                        ["compare", h1, h2, "--json", "--output", str(out)],
                    )
        assert code == 2

    def test_build_verdict_dedupes_steps(self):
        from lxmfy.debugger import build_verdict

        checks = [
            CheckResult("interfaces_online", "fail", "0", category="network"),
            CheckResult("has_path", "fail", "False", category="destination"),
            CheckResult("identity_known", "fail", "False", category="destination"),
        ]
        _, steps = build_verdict(
            checks,
            send_blockers=["x"],
            receive_blockers=[],
            probe=DestinationProbe(
                destination="ab" * 16,
                valid_hash=True,
                identity_known=False,
                has_path=False,
            ),
        )
        assert len(steps) == len(set(steps))

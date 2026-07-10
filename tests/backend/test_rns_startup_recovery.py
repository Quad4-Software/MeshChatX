# SPDX-License-Identifier: 0BSD

"""Regression tests for RNS panic containment and progressive startup recovery."""

from __future__ import annotations

from RNS.vendor.configobj import ConfigObj

from meshchatx.src.backend import rns_startup_recovery as recovery


def test_install_rns_panic_containment_raises_instead_of_exit(monkeypatch):
    import RNS

    calls = {"exit": 0}

    def fake_exit(code=255):
        calls["exit"] += 1
        raise SystemExit(code)

    monkeypatch.setattr(RNS, "panic", lambda: fake_exit(255), raising=False)
    assert recovery.install_rns_panic_containment(force=True) is True
    try:
        RNS.panic()
        assert False, "expected RnsPanicError"
    except recovery.RnsPanicError:
        pass
    assert calls["exit"] == 0


def test_ensure_panic_on_interface_error_disabled(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
panic_on_interface_error = Yes
[interfaces]
""",
        encoding="utf-8",
    )
    assert recovery.ensure_panic_on_interface_error_disabled(str(config_path)) is True
    cfg = ConfigObj(str(config_path))
    assert str(cfg["reticulum"]["panic_on_interface_error"]).lower() in (
        "no",
        "false",
        "0",
    )


def test_create_reticulum_with_recovery_disables_named_then_retries(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
[interfaces]
[[BadIface]]
type = AutoInterface
interface_enabled = true
[[Good]]
type = TCPClientInterface
interface_enabled = true
""",
        encoding="utf-8",
    )
    calls = {"n": 0}

    def construct():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError('The interface "BadIface" failed to start')
        return "ok"

    result = recovery.create_reticulum_with_recovery(
        str(tmp_path),
        construct=construct,
        max_attempts=3,
    )
    assert result == "ok"
    assert calls["n"] == 2
    cfg = ConfigObj(str(config_path))
    assert str(cfg["interfaces"]["BadIface"]["interface_enabled"]).lower() in (
        "false",
        "no",
        "0",
    )
    assert str(cfg["interfaces"]["Good"]["interface_enabled"]).lower() in (
        "true",
        "yes",
        "1",
    )


def test_create_reticulum_with_recovery_escalates_to_i2p(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
[interfaces]
[[I2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
""",
        encoding="utf-8",
    )
    calls = {"n": 0}

    def construct():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("generic I2P brick")
        return "ok"

    assert (
        recovery.create_reticulum_with_recovery(
            str(tmp_path),
            construct=construct,
        )
        == "ok"
    )
    cfg = ConfigObj(str(config_path))
    assert str(cfg["interfaces"]["I2P"]["interface_enabled"]).lower() in (
        "false",
        "no",
        "0",
    )


def test_extract_interface_names_from_error():
    names = recovery.extract_interface_names_from_error(
        'AutoInterface[HomeLAN] failed; also interface "Radio1" offline',
    )
    assert "HomeLAN" in names
    assert "Radio1" in names


def test_apply_startup_recovery_step_autointerface(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
[interfaces]
[[Home]]
type = AutoInterface
interface_enabled = true
""",
        encoding="utf-8",
    )
    disabled = recovery.apply_startup_recovery_step(
        str(config_path),
        "bind failed",
        attempt=2,
    )
    assert "Home" in disabled
    cfg = ConfigObj(str(config_path))
    assert str(cfg["interfaces"]["Home"]["interface_enabled"]).lower() in (
        "false",
        "no",
        "0",
    )

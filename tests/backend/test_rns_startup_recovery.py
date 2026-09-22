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
        raise AssertionError("expected RnsPanicError")
    except recovery.RnsPanicError:
        pass
    assert calls["exit"] == 0


def test_contained_exit_is_reentrant_safe(monkeypatch):
    import RNS

    recovery._EXIT_IN_PROGRESS = False
    assert recovery.install_rns_panic_containment(force=True) is True
    handler_calls = {"n": 0}

    def counting_exit_handler():
        handler_calls["n"] += 1
        # Nested exit must not recurse or raise.
        RNS.exit(0)

    monkeypatch.setattr(
        RNS.Reticulum,
        "exit_handler",
        staticmethod(counting_exit_handler),
        raising=False,
    )
    RNS.exit(0)
    assert handler_calls["n"] == 1
    RNS.exit(0)
    assert handler_calls["n"] == 1


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


def test_apply_startup_recovery_step_does_not_blindly_disable_i2p(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
[interfaces]
[[MyI2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
""",
        encoding="utf-8",
    )
    disabled = recovery.apply_startup_recovery_step(
        str(config_path),
        "some unrelated bind failure with no interface name",
        attempt=0,
    )
    assert disabled == []
    cfg = ConfigObj(str(config_path))
    assert str(cfg["interfaces"]["MyI2P"]["interface_enabled"]).lower() in (
        "true",
        "yes",
        "1",
    )


def test_create_reticulum_with_recovery_uses_rns_log_for_unnamed_panic(tmp_path):
    import RNS

    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
[interfaces]
[[MyI2P]]
type = I2PInterface
interface_enabled = true
peers = aaa.b32.i2p
[[FlakyTcp]]
type = TCPClientInterface
interface_enabled = true
""",
        encoding="utf-8",
    )
    recovery.install_rns_panic_containment(force=True)
    calls = {"n": 0}

    def construct():
        calls["n"] += 1
        if calls["n"] == 1:
            RNS.log(
                'The interface "FlakyTcp" could not be created. Check your '
                "configuration file for errors!",
                RNS.LOG_ERROR,
            )
            RNS.panic()
        return "ok"

    result = recovery.create_reticulum_with_recovery(
        str(tmp_path),
        construct=construct,
        max_attempts=3,
    )
    assert result == "ok"
    cfg = ConfigObj(str(config_path))
    assert str(cfg["interfaces"]["FlakyTcp"]["interface_enabled"]).lower() in (
        "false",
        "no",
        "0",
    )
    assert str(cfg["interfaces"]["MyI2P"]["interface_enabled"]).lower() in (
        "true",
        "yes",
        "1",
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


def test_reset_rns_runtime_state_clears_singleton_and_interfaces():
    import RNS

    class _FakeIface:
        online = True
        detached = False

        def detach(self):
            self.online = False

    fake = _FakeIface()
    saved_instance = RNS.Reticulum._Reticulum__instance
    saved_interfaces = RNS.Transport.interfaces
    try:
        RNS.Reticulum._Reticulum__instance = object()
        RNS.Transport.interfaces = [fake]
        recovery.reset_rns_runtime_state()
        assert RNS.Reticulum._Reticulum__instance is None
        assert RNS.Transport.interfaces == []
        assert RNS.Transport._should_run is True
        assert fake.online is False
    finally:
        RNS.Reticulum._Reticulum__instance = saved_instance
        RNS.Transport.interfaces = saved_interfaces


def test_release_interface_resources_closes_bound_servers():
    import socket
    import socketserver

    class _FakeIface:
        pass

    server = socketserver.UDPServer(
        ("127.0.0.1", 0),
        socketserver.BaseRequestHandler,
    )
    port = server.server_address[1]
    outbound = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    iface = _FakeIface()
    iface.interface_servers = {"lo": server}
    iface.outbound_udp_socket = outbound
    iface.name = "Fake"

    recovery._release_interface_resources(iface)

    rebound = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rebound.bind(("127.0.0.1", port))
    rebound.close()
    assert outbound.fileno() == -1


def test_recovery_retry_after_singleton_failure(tmp_path, monkeypatch):
    import RNS

    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = True
[interfaces]
[[AutoInterface2]]
type = AutoInterface
interface_enabled = true
""",
        encoding="utf-8",
    )
    saved_instance = RNS.Reticulum._Reticulum__instance
    calls = {"n": 0}

    def construct():
        calls["n"] += 1
        if calls["n"] == 1:
            # Mirrors Reticulum.__init__: the singleton is assigned first
            # and stays set when a later interface fails to come up.
            RNS.Reticulum._Reticulum__instance = object()
            raise OSError(
                'The interface "AutoInterface2" could not be created: '
                "[Errno 98] Address already in use",
            )
        assert RNS.Reticulum._Reticulum__instance is None
        return "ok"

    monkeypatch.setattr(
        RNS.Reticulum,
        "_Reticulum__instance",
        None,
        raising=False,
    )
    try:
        result = recovery.create_reticulum_with_recovery(
            str(tmp_path),
            construct=construct,
            max_attempts=3,
        )
        assert result == "ok"
        assert calls["n"] == 2
        cfg = ConfigObj(str(config_path))
        assert str(
            cfg["interfaces"]["AutoInterface2"]["interface_enabled"],
        ).lower() in ("false", "no", "0")
    finally:
        RNS.Reticulum._Reticulum__instance = saved_instance


def test_sweep_orphaned_ratchet_files_removes_non_hex_names(tmp_path):
    ratchets = tmp_path / "storage" / "ratchets"
    ratchets.mkdir(parents=True)
    valid = "a" * 32
    (ratchets / valid).write_bytes(b"data")
    (ratchets / f"{valid[:-4]}.out").write_bytes(b"")
    (ratchets / ".ratchet.abc123.tmp").write_bytes(b"")
    (ratchets / "subdir").mkdir()

    removed = recovery.sweep_orphaned_ratchet_files(str(tmp_path))

    assert removed == 2
    assert (ratchets / valid).is_file()
    assert not (ratchets / f"{valid[:-4]}.out").exists()
    assert not (ratchets / ".ratchet.abc123.tmp").exists()
    assert (ratchets / "subdir").is_dir()


def test_sweep_orphaned_ratchet_files_missing_dir(tmp_path):
    assert recovery.sweep_orphaned_ratchet_files(str(tmp_path)) == 0


def test_create_reticulum_with_recovery_sweeps_ratchets(tmp_path, monkeypatch):
    ratchets = tmp_path / "storage" / "ratchets"
    ratchets.mkdir(parents=True)
    (ratchets / ("b" * 32 + ".out")).write_bytes(b"")
    (tmp_path / "config").write_text("[reticulum]\n[interfaces]\n", encoding="utf-8")

    called = []

    def construct():
        called.append(True)
        return object()

    result = recovery.create_reticulum_with_recovery(str(tmp_path), construct=construct)

    assert result is not None
    assert called
    assert not (ratchets / ("b" * 32 + ".out")).exists()

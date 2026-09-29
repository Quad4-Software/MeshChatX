"""Tests for Reticulum config discovery and shared-instance isolation."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from lxmfy.reticulum_config import (
    discover_user_reticulum_config_dir,
    ensure_isolated_share_instance_disabled,
    is_isolated_reticulum_dir,
    resolve_reticulum_config_dir,
)


def test_discover_user_reticulum_prefers_system_then_xdg(tmp_path):
    etc = tmp_path / "etc_reticulum"
    xdg = tmp_path / ".config" / "reticulum"
    home = tmp_path / ".reticulum"
    for path in (etc, xdg, home):
        path.mkdir(parents=True)
        (path / "config").write_text("[reticulum]\nshare_instance = Yes\n")

    found = discover_user_reticulum_config_dir(
        home=str(tmp_path),
        system_dir=str(etc),
    )
    assert found == str(etc.resolve())

    found_xdg = discover_user_reticulum_config_dir(
        home=str(tmp_path),
        system_dir=str(tmp_path / "missing_etc"),
    )
    assert found_xdg == str(xdg.resolve())


def test_discover_user_reticulum_falls_back_to_dot_reticulum(tmp_path):
    home = tmp_path / ".reticulum"
    home.mkdir()
    (home / "config").write_text("[reticulum]\nshare_instance = Yes\n")
    found = discover_user_reticulum_config_dir(
        home=str(tmp_path),
        system_dir=str(tmp_path / "missing_etc"),
    )
    assert found == str(home.resolve())


def test_resolve_prefers_explicit_then_env_then_discovery(tmp_path, monkeypatch):
    bot_cfg = tmp_path / "bot"
    bot_cfg.mkdir()
    user = tmp_path / ".reticulum"
    user.mkdir()
    (user / "config").write_text("[reticulum]\n")
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    missing_etc = str(tmp_path / "missing_etc")

    assert resolve_reticulum_config_dir(
        str(explicit),
        str(bot_cfg),
        environ={},
        home=str(tmp_path),
        system_dir=missing_etc,
    ) == str(explicit.resolve())

    assert resolve_reticulum_config_dir(
        None,
        str(bot_cfg),
        environ={"LXMFY_RETICULUM_CONFIG_DIR": str(user)},
        home=str(tmp_path),
        system_dir=missing_etc,
    ) == str(user.resolve())

    assert resolve_reticulum_config_dir(
        None,
        str(bot_cfg),
        environ={},
        home=str(tmp_path),
        system_dir=missing_etc,
    ) == str(user.resolve())

    empty_home = tmp_path / "empty_home"
    empty_home.mkdir()
    assert resolve_reticulum_config_dir(
        None,
        str(bot_cfg),
        environ={},
        home=str(empty_home),
        system_dir=missing_etc,
    ) == str(bot_cfg.resolve())


def test_ensure_isolated_creates_share_instance_no(tmp_path):
    rns_dir = tmp_path / "isolated"
    assert ensure_isolated_share_instance_disabled(str(rns_dir)) is True
    text = (rns_dir / "config").read_text()
    assert "share_instance = No" in text
    assert ensure_isolated_share_instance_disabled(str(rns_dir)) is False


def test_ensure_isolated_rewrites_share_instance_yes(tmp_path):
    rns_dir = tmp_path / "isolated"
    rns_dir.mkdir()
    (rns_dir / "config").write_text(
        "[reticulum]\nshare_instance = Yes\nenable_transport = Yes\n",
    )
    assert ensure_isolated_share_instance_disabled(str(rns_dir)) is True
    text = (rns_dir / "config").read_text()
    assert "share_instance = No" in text
    assert "share_instance = Yes" not in text


def test_is_isolated_reticulum_dir(tmp_path):
    bot = tmp_path / "bot"
    other = tmp_path / "other"
    bot.mkdir()
    other.mkdir()
    assert is_isolated_reticulum_dir(str(bot), str(bot)) is True
    assert is_isolated_reticulum_dir(str(other), str(bot)) is False


def _shared_instance_worker(
    role: str,
    cfg: str,
    q: multiprocessing.Queue,
    delay: float = 0.0,
):
    import RNS

    if delay:
        time.sleep(delay)
    try:
        r = RNS.Reticulum(configdir=cfg, loglevel=RNS.LOG_ERROR)
        q.put(
            (
                role,
                "started",
                r.is_shared_instance,
                r.is_connected_to_shared_instance,
                r.is_standalone_instance,
            ),
        )
        try:
            client = r.get_rpc_client()
            client.close()
            q.put((role, "rpc_ok"))
        except Exception as e:
            q.put((role, f"{type(e).__name__}: {e}"))
        if role == "master":
            time.sleep(6)
    finally:
        try:
            RNS.Reticulum.exit_handler()
        except Exception:
            pass


def _write_tcp_shared_config(
    path: Path, *, share: bool, iface: int, control: int
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    share_val = "Yes" if share else "No"
    (path / "config").write_text(
        "[reticulum]\n"
        "enable_transport = Yes\n"
        f"share_instance = {share_val}\n"
        "shared_instance_type = tcp\n"
        f"shared_instance_port = {iface}\n"
        f"instance_control_port = {control}\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n",
        encoding="utf-8",
    )


@pytest.mark.integration
def test_colliding_shared_instance_rejects_digest(tmp_path):
    """Different config dirs on the same shared ports fail RPC auth."""
    master = tmp_path / "master"
    client = tmp_path / "client"
    _write_tcp_shared_config(master, share=True, iface=47628, control=47629)
    _write_tcp_shared_config(client, share=True, iface=47628, control=47629)

    q: multiprocessing.Queue = multiprocessing.Queue()
    p1 = multiprocessing.Process(
        target=_shared_instance_worker,
        args=("master", str(master), q),
    )
    p2 = multiprocessing.Process(
        target=_shared_instance_worker,
        args=("client", str(client), q, 2.0),
    )
    p1.start()
    p2.start()
    p2.join(timeout=20)
    p1.terminate()
    p1.join(timeout=5)

    results = []
    while not q.empty():
        results.append(q.get())

    assert any(
        r[0] == "client" and "digest sent was rejected" in str(r[1]) for r in results
    )


@pytest.mark.integration
def test_isolated_share_instance_avoids_digest_rejection(tmp_path):
    """Guarantee: isolated configs with share_instance=No do not RPC-collide.

    RETICULUM_DIGEST_PROVED
    """
    master = tmp_path / "master"
    client = tmp_path / "client"
    ensure_isolated_share_instance_disabled(str(master))
    ensure_isolated_share_instance_disabled(str(client))
    _write_tcp_shared_config(master, share=False, iface=47728, control=47729)
    _write_tcp_shared_config(client, share=False, iface=47738, control=47739)

    q: multiprocessing.Queue = multiprocessing.Queue()
    p1 = multiprocessing.Process(
        target=_shared_instance_worker,
        args=("master", str(master), q),
    )
    p2 = multiprocessing.Process(
        target=_shared_instance_worker,
        args=("client", str(client), q, 1.5),
    )
    p1.start()
    p2.start()
    p2.join(timeout=20)
    p1.terminate()
    p1.join(timeout=5)

    results = []
    while not q.empty():
        results.append(q.get())

    started = [r for r in results if len(r) >= 5 and r[1] == "started"]
    assert len(started) == 2
    assert all(r[4] is True for r in started)
    assert not any("digest sent was rejected" in str(item) for item in results)
    print("RETICULUM_DIGEST_PROVED")

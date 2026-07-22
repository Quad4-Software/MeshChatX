"""Live RRC smoke test against a local rrcd hub over TCP loopback.

Requires rrcd installed and LXMFY_LIVE_RRC=1. Skips otherwise.
"""

from __future__ import annotations

import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import RNS

from lxmfy.rrc import RRCClient

REPO_ROOT = Path(__file__).resolve().parents[1]


def _can_import_rrcd() -> bool:
    try:
        import rrcd  # noqa: F401

        return True
    except Exception:
        return False


rrcd_available = _can_import_rrcd()
live_enabled = os.environ.get("LXMFY_LIVE_RRC", "").strip().lower() in {
    "1",
    "true",
    "yes",
}


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _write_rns_config(path: Path, *, server: bool, port: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if server:
        iface = f"""
[interfaces]
  [[TCP Server]]
    type = TCPServerInterface
    enabled = Yes
    listen_ip = 127.0.0.1
    listen_port = {port}
"""
    else:
        iface = f"""
[interfaces]
  [[TCP Client]]
    type = TCPClientInterface
    enabled = Yes
    target_host = 127.0.0.1
    target_port = {port}
"""
    (path / "config").write_text(
        f"""
[reticulum]
  enable_transport = Yes
  share_instance = No
  panic_on_interface_error = No

[logging]
  loglevel = 3
{iface}
""".lstrip(),
    )


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.skipif(not rrcd_available, reason="rrcd not installed")
@pytest.mark.skipif(
    not live_enabled,
    reason="Set LXMFY_LIVE_RRC=1 to run live RRC hub smoke test",
)
def test_live_rrc_hello_join_msg_roundtrip():
    """Run rrcd on a TCP server and connect an LXMFy RRC client over TCP."""
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        port = _free_port()
        hub_rns = home / "hub_rns"
        client_rns = home / "client_rns"
        rrcd_home = home / "rrcd"
        rrcd_home.mkdir()
        _write_rns_config(hub_rns, server=True, port=port)
        _write_rns_config(client_rns, server=False, port=port)

        env = os.environ.copy()
        env["RRCD_HOME"] = str(rrcd_home)

        init = subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "-m",
                "rrcd",
                "--configdir",
                str(hub_rns),
                "--hub-name",
                "LXMFyLiveHub",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        identity_path = rrcd_home / "hub_identity"
        assert identity_path.is_file(), init.stdout + init.stderr

        # rrcd.toml defaults configdir to empty and would override --configdir.
        rrcd_toml = rrcd_home / "rrcd.toml"
        text = rrcd_toml.read_text()
        text = text.replace('configdir = ""', f'configdir = "{hub_rns}"')
        if "announce_period_s = 0.0" in text:
            text = text.replace("announce_period_s = 0.0", "announce_period_s = 3.0")
        rrcd_toml.write_text(text)

        hub_proc = subprocess.Popen(
            [
                "poetry",
                "run",
                "python",
                "-m",
                "rrcd",
                "--configdir",
                str(hub_rns),
                "--hub-name",
                "LXMFyLiveHub",
                "--announce-period",
                "3",
                "--log-level",
                "INFO",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            port_deadline = time.time() + 15
            while time.time() < port_deadline:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.2)
            else:
                out = ""
                try:
                    hub_proc.terminate()
                    out = hub_proc.communicate(timeout=2)[0] or ""
                except Exception:
                    pass
                pytest.fail(f"hub TCP server did not start on {port}\n{out}")

            RNS.Reticulum(configdir=str(client_rns), loglevel=RNS.LOG_ERROR)
            time.sleep(6.0)

            hub_identity = RNS.Identity.from_file(str(identity_path))
            app_name, aspects = RNS.Destination.app_and_aspects_from_name("rrc.hub")
            hub_hash = RNS.Destination.hash(hub_identity, app_name, *aspects)
            RNS.Identity.remember(
                RNS.Identity.full_hash(hub_hash),
                hub_hash,
                hub_identity.get_public_key(),
            )

            path_deadline = time.time() + 20
            while time.time() < path_deadline and not RNS.Transport.has_path(hub_hash):
                RNS.Transport.request_path(hub_hash)
                time.sleep(0.5)

            events = []

            def on_event(event, client, payload):
                events.append((event, payload))

            client = RRCClient(
                identity=RNS.Identity(),
                hub_hash=hub_hash,
                nick="LiveBot",
                auto_reconnect=False,
                on_event=on_event,
            )
            client.set_auto_join(["lobby"])
            client.connect()

            deadline = time.time() + 30
            while time.time() < deadline and not client.connected:
                time.sleep(0.2)

            assert client.connected, (
                f"did not get WELCOME: {client.status_text} "
                f"has_path={RNS.Transport.has_path(hub_hash)} events={events}"
            )

            join_deadline = time.time() + 15
            while time.time() < join_deadline and "lobby" not in client.rooms:
                time.sleep(0.2)
            assert "lobby" in client.rooms

            mid = client.send_message("lobby", "live smoke from lxmfy")
            assert isinstance(mid, bytes) and len(mid) == 8
            client.disconnect()
            assert any(e[0] == "welcome" for e in events)
        finally:
            hub_proc.terminate()
            try:
                hub_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                hub_proc.kill()
            try:
                out = hub_proc.stdout.read() if hub_proc.stdout else ""
                if out:
                    print(out[-4000:])
            except Exception:
                pass
            try:
                RNS.Reticulum.exit_handler()
            except Exception:
                pass

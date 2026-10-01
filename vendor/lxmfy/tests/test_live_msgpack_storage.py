"""Live msgpack storage test on a real Reticulum instance.

A real (non-test-mode) LXMFBot with storage_type="msgpack" defers a send
to an unknown destination, which writes pending_sends to disk as
msgpack files. A second bot instance started on the same directories
must see the deferred send survive the restart.

Requires LXMFY_LIVE_LOCAL=1. Skips otherwise. No public network needed:
the Reticulum config uses no interfaces, so the instance is isolated.
"""

from __future__ import annotations

import multiprocessing
import os
import time
from pathlib import Path

import pytest

LIVE_ENABLED = os.environ.get("LXMFY_LIVE_LOCAL", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

UNKNOWN_DEST = "a1" * 16  # valid hex, no identity behind it


def _write_rns_config(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "config").write_text(
        "[reticulum]\n"
        "enable_transport = No\n"
        "share_instance = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n",
        encoding="utf-8",
    )


def _worker(config_dir: str, phase: str, result_q: multiprocessing.Queue) -> None:
    os.environ.pop("LXMFY_RETICULUM_CONFIG_DIR", None)
    try:
        from lxmfy import LXMFBot

        bot = LXMFBot(
            name="MsgpackLive",
            config_path=config_dir,
            reticulum_config_dir=config_dir,
            storage_type="msgpack",
            storage_path=str(Path(config_dir) / "store"),
            announce_enabled=False,
            announce_immediately=False,
            first_message_enabled=False,
            landlock_enabled=False,
            cogs_enabled=False,
            message_persistence_enabled=False,
            propagation_fallback_enabled=False,
            pending_sends_enabled=True,
            lxmf_commands_enabled=False,
            test_mode=False,
        )
        try:
            if phase == "write":
                bot.send(UNKNOWN_DEST, "held by msgpack", defer=True)
                time.sleep(0.5)
                pending = bot.storage.get("pending_sends", [])
                files = sorted(
                    p.name for p in (Path(config_dir) / "store").glob("*.msgpack")
                )
                result_q.put(
                    {
                        "phase": phase,
                        "pending": pending,
                        "files": files,
                        "ok": isinstance(pending, list) and len(pending) == 1,
                    },
                )
            else:
                pending = bot.storage.get("pending_sends", [])
                result_q.put(
                    {
                        "phase": phase,
                        "pending": pending,
                        "ok": isinstance(pending, list) and len(pending) == 1,
                    },
                )
        finally:
            bot.cleanup()
    except Exception as exc:  # pragma: no cover - diagnostic path
        import traceback

        result_q.put(
            {"phase": phase, "ok": False, "error": f"{exc}\n{traceback.format_exc()}"},
        )


def _run_phase(config_dir: str, phase: str, timeout: float = 60.0) -> dict:
    result_q: multiprocessing.Queue = multiprocessing.Queue()
    proc = multiprocessing.Process(
        target=_worker,
        args=(config_dir, phase, result_q),
    )
    proc.start()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)
        pytest.fail(f"msgpack live {phase} phase timed out")
    if result_q.empty():
        pytest.fail(f"msgpack live {phase} phase produced no result")
    result = result_q.get()
    if "error" in result:
        pytest.fail(f"msgpack live {phase} phase failed: {result['error']}")
    return result


@pytest.mark.skipif(
    not LIVE_ENABLED,
    reason="Set LXMFY_LIVE_LOCAL=1 to run the msgpack live storage test",
)
def test_msgpack_pending_sends_survive_restart(tmp_path):
    """A deferred send persists through msgpack storage across restarts."""
    config_dir = tmp_path / "bot"
    _write_rns_config(config_dir)

    write = _run_phase(str(config_dir), "write")
    assert write["ok"], f"deferred send was not stored: {write}"
    assert write["files"], "no .msgpack files were written"
    assert write["pending"][0]["destination"] == UNKNOWN_DEST

    read = _run_phase(str(config_dir), "read")
    assert read["ok"], f"pending_sends did not survive restart: {read}"
    assert read["pending"][0]["destination"] == UNKNOWN_DEST

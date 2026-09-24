# SPDX-License-Identifier: 0BSD
"""Live two-peer LXST call over local TCP interfaces.

Two isolated Reticulum subprocesses connect over a loopback TCP server/client
interface pair. The callee runs the headless MeshChatX audio stack
(HostlessAudioSource/HostlessAudioSink via install_hostless_lxst_audio), answers
an incoming call, plays a timed Opus greeting into the transmit mixer, and
records caller audio through a Tee fan-out into OpusFileSink on the real
LinkSource. The caller pushes generated PCM through the hostless push_pcm path.

This exercises the issue 114 surface for real: Telephony poking the LineSink
buffer attributes on the hostless sink, Pipeline accepting the Tee sink,
LinkSource.samplerate feeding OpusFileSink, and OpusFileSource timed pacing.

Enable with MESHCHAT_LIVE_RETICULUM=1 or MESHCHAT_LIVE_VALIDATION=1.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

pytest.importorskip("LXST")

from tests.backend.support.test_temp_dir import subprocess_test_env

_RUN = (
    os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"
    or os.environ.get("MESHCHAT_LIVE_VALIDATION") == "1"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CALL_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_LXST_TIMEOUT", "90"))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _write_config(config_dir: Path, interface_block: str) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config").write_text(
        "[reticulum]\n"
        "enable_transport = No\n"
        "share_instance = No\n"
        "panic_on_interface_error = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n"
        f"{interface_block}",
        encoding="utf-8",
    )


_CALLEE_SCRIPT = textwrap.dedent(
    """\
    import json, os, sys, threading, time

    repo_root, config_dir, share_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.path.insert(0, repo_root)

    import RNS
    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)

    from meshchatx.src.backend.web_audio_bridge import install_hostless_lxst_audio
    from meshchatx.src.backend.telephone_manager import TelephoneManager, Tee
    from meshchatx.src.backend import audio_codec

    result = {
        "hostless_installed": False,
        "ringing": 0,
        "established": 0,
        "ended": 0,
        "answered": False,
        "greeting_elapsed": None,
        "recorded_bytes": 0,
        "recorded_frames": 0,
        "recorded_max_amp": 0.0,
        "errors": [],
    }

    result["hostless_installed"] = install_hostless_lxst_audio()

    identity = RNS.Identity()
    tm = TelephoneManager(identity, storage_dir=share_dir)
    tm.web_audio_required = True
    tm.init_telephone()
    tm.set_call_policy(allowed_fn=lambda _hash: True)
    tel = tm.telephone

    def on_ringing(caller_identity):
        result["ringing"] += 1
        def _answer():
            time.sleep(0.5)
            try:
                if tel.call_status == 4:
                    result["answered"] = bool(tel.answer(caller_identity))
            except Exception as exc:
                result["errors"].append(f"answer: {exc}")
        threading.Thread(target=_answer, daemon=True).start()

    def on_established(caller_identity):
        result["established"] += 1

    def on_ended(caller_identity):
        result["ended"] += 1

    tm.set_callbacks(ringing=on_ringing, established=on_established, ended=on_ended)

    with open(os.path.join(share_dir, "callee.json"), "w", encoding="utf-8") as fh:
        json.dump({"identity_hash": identity.hash.hex()}, fh)

    def session():
        try:
            from LXST.Codecs import Null
            from LXST.Pipeline import Pipeline
            from LXST.Sinks import OpusFileSink, Sink
            from LXST.Sources import OpusFileSource

            # Play a 2s greeting. timed=True should take ~real-time, not burst.
            greeting = os.path.join(share_dir, "greeting.opus")
            audio_codec.write_silence_ogg_opus(greeting, seconds=2)
            src = OpusFileSource(greeting, target_frame_ms=60, timed=True)
            pipe = Pipeline(source=src, codec=Null(), sink=tel.transmit_mixer)
            t0 = time.time()
            pipe.start()
            while getattr(src, "running", False) and time.time() - t0 < 10:
                time.sleep(0.05)
            result["greeting_elapsed"] = round(time.time() - t0, 2)
            pipe.stop()

            if not tel.active_call:
                return

            # Mirror voicemail_manager.start_recording, plus the Tee fan-out
            # the websocket bridge needs on the receive path.
            rec_path = os.path.join(share_dir, "recording.opus")
            opus_sink = OpusFileSink(rec_path)
            opus_sink.samplerate = 48000

            class CountingSink(Sink):
                def __init__(self):
                    self.frames = 0
                    self.max_amp = 0.0
                def handle_frame(self, frame, source):
                    self.frames += 1
                    try:
                        import numpy as np
                        amp = float(np.abs(np.asarray(frame)).max())
                        if amp > self.max_amp:
                            self.max_amp = amp
                    except Exception:
                        pass
                def can_receive(self, from_source=None):
                    return True

            counter = CountingSink()
            tee = Tee(opus_sink)
            tee.add_sink(counter)
            rec_pipe = Pipeline(tel.active_call.audio_source, Null(), tee)
            rec_pipe.start()

            deadline = time.time() + 8
            while time.time() < deadline and tel.active_call:
                time.sleep(0.1)
            rec_pipe.stop()
            opus_sink.stop()
            result["recorded_frames"] = counter.frames
            result["recorded_max_amp"] = counter.max_amp
            if os.path.exists(rec_path):
                result["recorded_bytes"] = os.path.getsize(rec_path)
        except Exception as exc:
            import traceback
            result["errors"].append(f"session: {exc}: {traceback.format_exc()[-400:]}")

    def watch():
        deadline = time.time() + float(os.environ.get("MCX_LIVE_WAIT", "80"))
        session_started = False
        while time.time() < deadline:
            if tel.call_status == 6 and tel.active_call and not session_started:
                session_started = True
                session()
            if result["ended"] and result["recorded_frames"]:
                break
            time.sleep(0.1)
        if tel.active_call:
            try:
                tel.hangup()
            except Exception:
                pass
        with open(os.path.join(share_dir, "callee_result.json"), "w", encoding="utf-8") as fh:
            json.dump(result, fh)
        RNS.exit(0)
        os._exit(0)

    threading.Thread(target=watch, daemon=True).start()
    while True:
        try:
            tel.announce()
        except Exception:
            pass
        time.sleep(2.0)
    """,
)

_CALLER_SCRIPT = textwrap.dedent(
    """\
    import json, os, sys, threading, time

    repo_root, config_dir, share_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.path.insert(0, repo_root)

    import RNS
    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)

    from meshchatx.src.backend.web_audio_bridge import install_hostless_lxst_audio
    from meshchatx.src.backend.telephone_manager import TelephoneManager

    result = {
        "dialed": False,
        "established": False,
        "pushed_frames": 0,
        "errors": [],
    }

    install_hostless_lxst_audio()

    identity = RNS.Identity()
    tm = TelephoneManager(identity, storage_dir=share_dir)
    tm.web_audio_required = True
    tm.init_telephone()
    tm.set_call_policy(allowed_fn=lambda _hash: True)
    tel = tm.telephone

    # Wait for the callee announce, then recall its identity.
    callee_hash = bytes.fromhex(json.load(open(os.path.join(share_dir, "callee.json")))["identity_hash"])
    deadline = time.time() + 40
    remote_identity = None
    while time.time() < deadline and remote_identity is None:
        remote_identity = RNS.Identity.recall(callee_hash, from_identity_hash=True)
        time.sleep(0.25)

    if remote_identity is None:
        result["errors"].append("callee identity never announced")
    else:
        def dial():
            try:
                tel.call(remote_identity)
                result["dialed"] = True
            except Exception as exc:
                result["errors"].append(f"call: {exc}")
        threading.Thread(target=dial, daemon=True).start()

        est_deadline = time.time() + 40
        while time.time() < est_deadline:
            if tel.call_status == 6 and tel.active_call:
                result["established"] = True
                break
            time.sleep(0.1)

        if result["established"]:
            # Let the callee finish its timed greeting before sending audio.
            time.sleep(3.0)
            import numpy as np
            frame_samples = int(48000 * 0.060)
            t = np.arange(frame_samples)
            phase = 0
            pushes = int(4.0 / 0.060)
            for _ in range(pushes):
                if not tel.active_call:
                    break
                samples = 0.5 * np.sin(2 * np.pi * 440 * (phase + t) / 48000.0)
                phase += frame_samples
                pcm = (samples * 32767.0).astype(np.int16).tobytes()
                try:
                    source = getattr(tel, "audio_input", None)
                    if source is not None and hasattr(source, "push_pcm"):
                        source.push_pcm(pcm)
                        result["pushed_frames"] += 1
                except Exception as exc:
                    result["errors"].append(f"push_pcm: {exc}")
                time.sleep(0.060)
            time.sleep(0.5)
            try:
                tel.hangup()
            except Exception as exc:
                result["errors"].append(f"hangup: {exc}")

    with open(os.path.join(share_dir, "caller_result.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh)
    RNS.exit(0)
    os._exit(0)
    """,
)


@pytest.mark.integration
@pytest.mark.skipif(
    not _RUN,
    reason="Set MESHCHAT_LIVE_RETICULUM=1 to run the live two-peer LXST call test",
)
def test_lxst_live_headless_call_records_remote_audio(tmp_path):
    port = _free_port()
    callee_dir = tmp_path / "callee"
    caller_dir = tmp_path / "caller"
    share_dir = tmp_path / "share"
    share_dir.mkdir(parents=True, exist_ok=True)

    _write_config(
        callee_dir,
        "  [[LiveServer]]\n"
        "    type = TCPServerInterface\n"
        "    enabled = Yes\n"
        "    listen_ip = 127.0.0.1\n"
        f"    listen_port = {port}\n",
    )
    _write_config(
        caller_dir,
        "  [[LiveClient]]\n"
        "    type = TCPClientInterface\n"
        "    enabled = Yes\n"
        "    target_host = 127.0.0.1\n"
        f"    target_port = {port}\n",
    )

    env = subprocess_test_env({"MCX_LIVE_WAIT": str(CALL_TIMEOUT_S)})

    callee = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _CALLEE_SCRIPT,
            str(REPO_ROOT),
            str(callee_dir),
            str(share_dir),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        # Wait for the callee config/interface to come up before dialing in.
        ready_deadline = time.time() + 30
        callee_json = share_dir / "callee.json"
        while time.time() < ready_deadline and not callee_json.exists():
            if callee.poll() is not None:
                break
            time.sleep(0.2)
        assert callee_json.exists(), "callee never wrote identity info"
        time.sleep(2.0)

        caller = subprocess.run(
            [
                sys.executable,
                "-c",
                _CALLER_SCRIPT,
                str(REPO_ROOT),
                str(caller_dir),
                str(share_dir),
            ],
            capture_output=True,
            text=True,
            timeout=CALL_TIMEOUT_S + 30,
            check=False,
            env=env,
        )
        assert caller.returncode == 0, caller.stdout[-2000:]

        callee.wait(timeout=CALL_TIMEOUT_S + 30)
    finally:
        if callee.poll() is None:
            callee.kill()

    callee_out = ""
    if callee.stdout:
        callee_out = callee.stdout.read()[-2000:]

    callee_result_path = share_dir / "callee_result.json"
    caller_result_path = share_dir / "caller_result.json"
    assert callee_result_path.exists(), f"callee produced no result: {callee_out}"
    assert caller_result_path.exists(), "caller produced no result"

    callee_result = json.loads(callee_result_path.read_text(encoding="utf-8"))
    caller_result = json.loads(caller_result_path.read_text(encoding="utf-8"))

    assert callee_result["hostless_installed"] is True
    assert callee_result["ringing"] >= 1, f"callee never rang: {callee_result}"
    assert callee_result["answered"] is True, (
        f"callee failed to answer: {callee_result}"
    )
    assert callee_result["established"] >= 1
    assert caller_result["established"] is True, (
        f"caller never established: {caller_result}"
    )
    assert caller_result["pushed_frames"] > 0, (
        f"caller pushed no audio: {caller_result}"
    )

    # The greeting must play near real-time, not burst (timed=True regression).
    elapsed = callee_result["greeting_elapsed"]
    assert elapsed is not None, f"greeting never played: {callee_result}"
    assert 1.0 <= elapsed <= 8.0, f"greeting pacing off: {elapsed}s"

    # OpusFileSink on the real LinkSource must receive decoded frames through
    # the Tee. A silent/empty recording means the samplerate or Tee fix broke.
    assert callee_result["recorded_frames"] > 0, (
        f"no frames reached tee: {callee_result}"
    )
    assert callee_result["recorded_bytes"] > 0, f"empty recording: {callee_result}"
    assert callee_result["recorded_max_amp"] > 0.01, (
        f"recording is silent: {callee_result}"
    )
    assert callee_result["ended"] >= 1
    assert not callee_result["errors"], callee_result["errors"]
    assert not caller_result["errors"], caller_result["errors"]

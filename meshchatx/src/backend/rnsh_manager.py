# SPDX-License-Identifier: 0BSD

"""RNSh session manager for MeshChatX.

Tracks multiple rnsh subprocess sessions, keeps them running in the background
while the app is active, and persists session definitions plus output history.
"""

from __future__ import annotations

import contextlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid
from collections import deque


class RNSHSession:
    """Runtime state for a single rnsh session."""

    STATUS_STOPPED = "stopped"
    STATUS_RUNNING = "running"
    STATUS_FAILED = "failed"

    def __init__(self, manager, session_id, config):
        self.manager = manager
        self.session_id = session_id
        self.config = dict(config or {})
        self.created_at = float(self.config.get("created_at") or time.time())
        self.updated_at = float(self.config.get("updated_at") or self.created_at)

        self.status = str(self.config.get("status") or self.STATUS_STOPPED)
        self.pid = self.config.get("pid")
        self.last_exit_code = self.config.get("last_exit_code")
        self.last_error = self.config.get("last_error")
        self.last_command = self.config.get("last_command")

        self._process = None
        self._stop_requested = False
        self._output_seq = int(self.config.get("output_seq") or 0)
        self._output_chunks = deque(maxlen=4000)
        self._output_text = ""
        self._lock = threading.RLock()

        saved_output = self.config.get("output_chunks")
        if isinstance(saved_output, list):
            for item in saved_output:
                if not isinstance(item, dict):
                    continue
                seq = item.get("seq")
                text = item.get("text")
                ts = item.get("ts")
                if isinstance(seq, int) and isinstance(text, str):
                    self._output_chunks.append(
                        {
                            "seq": seq,
                            "text": text,
                            "ts": float(ts)
                            if isinstance(ts, (int, float))
                            else time.time(),
                        },
                    )
            if self._output_chunks:
                self._output_seq = max(self._output_seq, self._output_chunks[-1]["seq"])
                self._output_text = "".join(
                    chunk["text"] for chunk in self._output_chunks
                )

    @property
    def name(self):
        configured = self.config.get("name")
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
        mode = self.mode
        if mode == "listen":
            return "Listener"
        destination = self.destination
        if destination:
            return f"Session {destination[:10]}"
        return "Session"

    @property
    def mode(self):
        mode = self.config.get("mode")
        if mode == "listen":
            return "listen"
        return "connect"

    @property
    def destination(self):
        value = self.config.get("destination")
        if isinstance(value, str):
            return value.strip()
        return ""

    def to_dict(self, include_output_tail=False, output_tail_size=120):
        with self._lock:
            payload = {
                "id": self.session_id,
                "name": self.name,
                "mode": self.mode,
                "destination": self.destination,
                "config": dict(self.config),
                "status": self.status,
                "pid": self.pid,
                "last_exit_code": self.last_exit_code,
                "last_error": self.last_error,
                "last_command": self.last_command,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "output_seq": self._output_seq,
                "output_size": len(self._output_chunks),
            }
            if include_output_tail:
                payload["output_chunks"] = list(self._output_chunks)[
                    -max(1, int(output_tail_size)) :
                ]
                payload["output_text"] = self._output_text[-50000:]
            return payload

    def output_since(self, cursor):
        with self._lock:
            chunks = [chunk for chunk in self._output_chunks if chunk["seq"] > cursor]
            return {
                "chunks": chunks,
                "next_cursor": self._output_seq,
            }

    def clear_output(self):
        with self._lock:
            self._output_chunks.clear()
            self._output_text = ""
            self.updated_at = time.time()
        self.manager._on_session_change(self)
        self.manager.save()

    def append_output(self, text):
        if not isinstance(text, str) or not text:
            return None
        with self._lock:
            self._output_seq += 1
            chunk = {
                "seq": self._output_seq,
                "text": text,
                "ts": time.time(),
            }
            self._output_chunks.append(chunk)
            self._output_text += text
            if len(self._output_text) > 200000:
                self._output_text = self._output_text[-200000:]
            self.updated_at = chunk["ts"]
            return chunk

    def _build_command(self):
        executable = shutil.which("rnsh")
        if executable:
            command = [executable]
        else:
            command = [sys.executable, "-m", "RNS.Utilities.rnsh"]

        config_path = (self.config.get("config_path") or "").strip()
        if config_path:
            command.extend(["-c", config_path])

        identity_path = (self.config.get("identity_path") or "").strip()
        if identity_path:
            command.extend(["-i", identity_path])

        verbose = int(self.config.get("verbose") or 0)
        quiet = int(self.config.get("quiet") or 0)
        if verbose > 0:
            command.extend(["-v"] * min(verbose, 3))
        if quiet > 0:
            command.extend(["-q"] * min(quiet, 3))

        if bool(self.config.get("mirror")):
            command.append("-m")

        timeout = self.config.get("timeout")
        if timeout not in (None, ""):
            command.extend(["-w", str(timeout)])

        service = (self.config.get("service") or "").strip()
        if service:
            command.extend(["-s", service])

        extra_args = (self.config.get("extra_args") or "").strip()
        if extra_args:
            command.extend(shlex.split(extra_args))

        mode = self.mode
        if mode == "listen":
            command.append("-l")

            announce_period = self.config.get("announce_period")
            if announce_period not in (None, ""):
                command.extend(["-b", str(announce_period)])

            allowed_hashes = self.config.get("allowed_hashes")
            if isinstance(allowed_hashes, list):
                for item in allowed_hashes:
                    value = str(item).strip()
                    if value:
                        command.extend(["-a", value])

            if bool(self.config.get("no_auth")):
                command.append("-n")

            if bool(self.config.get("remote_command_as_args")):
                command.append("-A")

            if bool(self.config.get("no_remote_command")):
                command.append("-C")

            default_command = (self.config.get("default_command") or "").strip()
            if default_command:
                command.append("--")
                command.extend(shlex.split(default_command))
        else:
            if bool(self.config.get("no_id")):
                command.append("-N")

            destination = self.destination
            if not destination:
                raise ValueError("Destination hash is required for connect mode")
            command.append(destination)

            remote_command = (self.config.get("remote_command") or "").strip()
            if remote_command:
                command.append("--")
                command.extend(shlex.split(remote_command))

        return command

    def start(self):
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return self.to_dict(include_output_tail=True)

            command = self._build_command()
            self._stop_requested = False
            self.last_error = None
            self.last_exit_code = None
            self.last_command = " ".join(shlex.quote(part) for part in command)

            self._process = subprocess.Popen(  # noqa: S603
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )

            self.pid = self._process.pid
            self.status = self.STATUS_RUNNING
            self.updated_at = time.time()

        self.manager._on_session_change(self)
        self.manager.save()

        reader = threading.Thread(target=self._reader_loop, daemon=True)
        reader.start()

        waiter = threading.Thread(target=self._waiter_loop, daemon=True)
        waiter.start()

        return self.to_dict(include_output_tail=True)

    def stop(self):
        with self._lock:
            process = self._process
            self._stop_requested = True
        if process is None:
            return self.to_dict(include_output_tail=True)
        with contextlib.suppress(Exception):
            process.terminate()
        try:
            process.wait(timeout=2.5)
        except Exception:
            with contextlib.suppress(Exception):
                process.kill()
        return self.to_dict(include_output_tail=True)

    def send_input(self, text):
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        with self._lock:
            process = self._process
            if process is None or process.poll() is not None:
                raise RuntimeError("Session is not running")
            stdin = process.stdin
            if stdin is None:
                raise RuntimeError("Session stdin is unavailable")
            stdin.write(text.encode("utf-8", errors="replace"))
            stdin.flush()
            self.updated_at = time.time()
        self.manager.save()
        return self.to_dict(include_output_tail=False)

    def _reader_loop(self):
        while True:
            with self._lock:
                process = self._process
                stdout = process.stdout if process is not None else None
            if process is None or stdout is None:
                return
            try:
                chunk = os.read(stdout.fileno(), 4096)
            except Exception:
                return
            if not chunk:
                return
            text = chunk.decode("utf-8", errors="replace")
            output_chunk = self.append_output(text)
            if output_chunk is not None:
                self.manager._on_session_output(self, output_chunk)
                self.manager.save()

    def _waiter_loop(self):
        with self._lock:
            process = self._process
        if process is None:
            return

        exit_code = process.wait()
        with self._lock:
            self.last_exit_code = exit_code
            self.pid = None
            self._process = None
            if self._stop_requested:
                self.status = self.STATUS_STOPPED
            else:
                self.status = (
                    self.STATUS_FAILED if exit_code != 0 else self.STATUS_STOPPED
                )
                if exit_code != 0 and not self.last_error:
                    self.last_error = f"rnsh exited with code {exit_code}"
            self.updated_at = time.time()
        self.manager._on_session_change(self)
        self.manager.save()

    def shutdown(self):
        with contextlib.suppress(Exception):
            self.stop()

    def to_store(self):
        data = self.to_dict(include_output_tail=True, output_tail_size=400)
        data["created_at"] = self.created_at
        data["updated_at"] = self.updated_at
        data["status"] = self.status
        return data


class RNSHManager:
    """Manage multiple rnsh sessions and persisted state."""

    def __init__(self, storage_dir):
        self.storage_dir = storage_dir
        self._sessions = {}
        self._change_callback = None
        self._output_callback = None
        self._lock = threading.RLock()

    def set_change_callback(self, callback):
        self._change_callback = callback

    def set_output_callback(self, callback):
        self._output_callback = callback

    def _store_path(self):
        return os.path.join(self.storage_dir, "rnsh_sessions.json")

    def load(self):
        path = self._store_path()
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        sessions = data.get("sessions")
        if not isinstance(sessions, list):
            return
        with self._lock:
            self._sessions = {}
            for item in sessions:
                if not isinstance(item, dict):
                    continue
                session_id = item.get("id")
                if not isinstance(session_id, str) or not session_id.strip():
                    continue
                session = RNSHSession(self, session_id, item.get("config") or item)
                session.created_at = float(item.get("created_at") or session.created_at)
                session.updated_at = float(item.get("updated_at") or session.updated_at)
                session.status = RNSHSession.STATUS_STOPPED
                session.pid = None
                session.last_exit_code = item.get("last_exit_code")
                session.last_error = item.get("last_error")
                session.last_command = item.get("last_command")
                session._output_seq = int(item.get("output_seq") or session._output_seq)
                stored_chunks = item.get("output_chunks")
                if isinstance(stored_chunks, list):
                    session._output_chunks.clear()
                    session._output_text = ""
                    for chunk in stored_chunks:
                        if (
                            isinstance(chunk, dict)
                            and isinstance(chunk.get("seq"), int)
                            and isinstance(chunk.get("text"), str)
                        ):
                            session._output_chunks.append(
                                {
                                    "seq": chunk["seq"],
                                    "text": chunk["text"],
                                    "ts": float(chunk.get("ts") or time.time()),
                                },
                            )
                    session._output_text = "".join(
                        c["text"] for c in session._output_chunks
                    )
                    if session._output_chunks:
                        session._output_seq = max(
                            session._output_seq,
                            session._output_chunks[-1]["seq"],
                        )
                self._sessions[session_id] = session

    def save(self):
        with self._lock:
            payload = {
                "sessions": [session.to_store() for session in self._sessions.values()],
            }
        path = self._store_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def list_sessions(self):
        with self._lock:
            sessions = [
                session.to_dict(include_output_tail=True)
                for session in self._sessions.values()
            ]
        sessions.sort(key=lambda item: item.get("updated_at", 0), reverse=True)
        return {"sessions": sessions}

    def find_session(self, session_id):
        with self._lock:
            return self._sessions.get(session_id)

    def create_session(self, config):
        session_id = uuid.uuid4().hex
        session = RNSHSession(self, session_id, config or {})
        with self._lock:
            self._sessions[session_id] = session
        self._on_session_change(session)
        self.save()
        return session

    def remove_session(self, session_id):
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("Session not found")
        session.shutdown()
        with self._lock:
            self._sessions.pop(session_id, None)
        self.save()
        return True

    def start_session(self, session_id):
        session = self.find_session(session_id)
        if session is None:
            raise KeyError("Session not found")
        return session.start()

    def stop_session(self, session_id):
        session = self.find_session(session_id)
        if session is None:
            raise KeyError("Session not found")
        return session.stop()

    def send_input(self, session_id, text):
        session = self.find_session(session_id)
        if session is None:
            raise KeyError("Session not found")
        return session.send_input(text)

    def output_since(self, session_id, cursor=0):
        session = self.find_session(session_id)
        if session is None:
            raise KeyError("Session not found")
        try:
            cursor = int(cursor)
        except Exception:
            cursor = 0
        return session.output_since(max(0, cursor))

    def clear_output(self, session_id):
        session = self.find_session(session_id)
        if session is None:
            raise KeyError("Session not found")
        session.clear_output()
        return session.to_dict(include_output_tail=True)

    def shutdown(self):
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            with contextlib.suppress(Exception):
                session.shutdown()
        self.save()

    def _on_session_change(self, session):
        callback = self._change_callback
        if callback is not None:
            with contextlib.suppress(Exception):
                callback(session)

    def _on_session_output(self, session, chunk):
        callback = self._output_callback
        if callback is not None:
            with contextlib.suppress(Exception):
                callback(session, chunk)

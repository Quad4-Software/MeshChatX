# SPDX-License-Identifier: 0BSD

"""Bug report collector and sender over aspect mcx-bugs-v1."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

import RNS

from meshchatx.src.backend.announce_handler import AnnounceHandler
from meshchatx.src.backend.log_redaction import redact_diagnostic_text
from meshchatx.src.backend.path_utils import (
    link_establishment_window,
    path_response_window,
)

BUG_ASPECT = "mcx-bugs-v1"
REPORT_PATH = "/report"
MAX_LOG_LINES = 500
MAX_PAYLOAD_CHARS = 120_000
MAX_STORED_REPORTS = 50
MAX_COLLECTORS = 80


class BugReportManager:
    """Host-side collector destination and redacted log sender for plugins."""

    def __init__(self, app: Any):
        self.app = app
        self._lock = threading.RLock()
        self._destination: RNS.Destination | None = None
        self._announce_handler: AnnounceHandler | None = None
        self._collectors: dict[str, dict[str, Any]] = {}
        self._reports: list[dict[str, Any]] = []
        self._active_links: list[Any] = []
        self._storage_dir: str | None = None
        self._collector_name: str = ""

    def _identity(self):
        ctx = getattr(self.app, "current_context", None)
        if ctx is None:
            return None
        return getattr(ctx, "identity", None)

    def _ensure_storage_dir(self) -> str:
        if self._storage_dir and os.path.isdir(self._storage_dir):
            return self._storage_dir
        base = getattr(self.app, "storage_dir", None) or os.getcwd()
        path = os.path.join(base, "bug_reports")
        os.makedirs(path, exist_ok=True)
        self._storage_dir = path
        return path

    def status(self) -> dict[str, Any]:
        with self._lock:
            dest = self._destination
            return {
                "aspect": BUG_ASPECT,
                "collector_running": dest is not None,
                "destination_hash": dest.hash.hex() if dest is not None else None,
                "collector_name": self._collector_name,
                "collectors": len(self._collectors),
                "reports": len(self._reports),
            }

    def start_collector(self, *, announce: bool = True) -> dict[str, Any]:
        identity = self._identity()
        if identity is None:
            raise RuntimeError("identity is not available")
        with self._lock:
            if self._destination is not None:
                if announce:
                    self._announce_locked()
                return self.status()
            app_name, aspects = RNS.Destination.app_and_aspects_from_name(BUG_ASPECT)
            destination = RNS.Destination(
                identity,
                RNS.Destination.IN,
                RNS.Destination.SINGLE,
                app_name,
                *aspects,
            )
            destination.set_link_established_callback(self._on_link)
            destination.register_request_handler(
                REPORT_PATH,
                response_generator=self._report_response,
                allow=RNS.Destination.ALLOW_ALL,
            )
            self._destination = destination
            self._register_announce_handler()
            dest_hex = destination.hash.hex()
            self._collectors[dest_hex] = {
                "destination_hash": dest_hex,
                "aspect": BUG_ASPECT,
                "name": "local",
                "heard_at": time.time(),
                "identity_hash": identity.hash.hex()
                if hasattr(identity, "hash")
                else None,
            }
            if announce:
                self._announce_locked()
            return self.status()

    def stop_collector(self) -> dict[str, Any]:
        with self._lock:
            for link in list(self._active_links):
                try:
                    link.teardown()
                except Exception:
                    pass
            self._active_links.clear()
            if self._destination is not None:
                dest_hex = self._destination.hash.hex()
                self._collectors.pop(dest_hex, None)
                try:
                    self._destination.deregister_request_handler(REPORT_PATH)
                except Exception:
                    pass
                try:
                    RNS.Transport.deregister_destination(self._destination)
                except Exception:
                    pass
                self._destination = None
            self._unregister_announce_handler()
            return self.status()

    def announce(self) -> dict[str, Any]:
        with self._lock:
            if self._destination is None:
                raise RuntimeError("collector is not running")
            self._announce_locked()
            return self.status()

    def set_collector_name(self, name: str) -> dict[str, Any]:
        with self._lock:
            self._collector_name = str(name)[:64]
            return self.status()

    def _announce_locked(self) -> None:
        assert self._destination is not None
        display = ""
        try:
            ctx = getattr(self.app, "current_context", None)
            config = getattr(ctx, "config", None) if ctx else None
            if config is not None:
                display = str(config.display_name.get() or "")
        except Exception:
            display = ""
        name = self._collector_name
        if not name:
            name = display
        app_data = json.dumps(
            {"v": 1, "app": "meshchatx", "name": name[:64]},
            separators=(",", ":"),
        ).encode("utf-8")
        self._destination.announce(app_data=app_data)

    def _register_announce_handler(self) -> None:
        if self._announce_handler is not None:
            return
        handler = AnnounceHandler(BUG_ASPECT, self._on_collector_announce)
        RNS.Transport.register_announce_handler(handler)
        self._announce_handler = handler

    def _unregister_announce_handler(self) -> None:
        handler = self._announce_handler
        if handler is None:
            return
        try:
            RNS.Transport.deregister_announce_handler(handler)
        except Exception:
            try:
                if handler in RNS.Transport.announce_handlers:
                    RNS.Transport.announce_handlers.remove(handler)
            except Exception:
                pass
        self._announce_handler = None

    def ensure_discovery(self) -> None:
        with self._lock:
            self._register_announce_handler()

    def _on_collector_announce(
        self,
        aspect: str,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
    ) -> None:
        try:
            dest_hex = (
                destination_hash.hex()
                if isinstance(destination_hash, (bytes, bytearray))
                else str(destination_hash)
            )
            name = ""
            if isinstance(app_data, (bytes, bytearray)) and app_data:
                try:
                    parsed = json.loads(app_data.decode("utf-8", errors="replace"))
                    if isinstance(parsed, dict):
                        name = str(parsed.get("name") or "")[:64]
                except Exception:
                    name = app_data.decode("utf-8", errors="replace")[:64]
            with self._lock:
                self._collectors[dest_hex] = {
                    "destination_hash": dest_hex,
                    "aspect": aspect,
                    "name": name,
                    "heard_at": time.time(),
                    "identity_hash": (
                        announced_identity.hash.hex()
                        if announced_identity is not None
                        and hasattr(announced_identity, "hash")
                        else None
                    ),
                }
                if len(self._collectors) > MAX_COLLECTORS:
                    oldest = sorted(
                        self._collectors.values(),
                        key=lambda item: item.get("heard_at") or 0,
                    )
                    for entry in oldest[: len(self._collectors) - MAX_COLLECTORS]:
                        self._collectors.pop(entry["destination_hash"], None)
        except Exception as exc:
            print(f"bug report announce handling failed: {exc}")

    def list_collectors(self) -> dict[str, Any]:
        self.ensure_discovery()
        with self._lock:
            items = sorted(
                self._collectors.values(),
                key=lambda item: item.get("heard_at") or 0,
                reverse=True,
            )
            return {"collectors": items, "aspect": BUG_ASPECT}

    def list_reports(self, *, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit or 20), MAX_STORED_REPORTS))
        with self._lock:
            return {"reports": list(self._reports[:limit])}

    def delete_report(self, index: int) -> dict[str, Any]:
        index = int(index)
        with self._lock:
            if index < 0 or index >= len(self._reports):
                raise IndexError("report index out of range")
            removed = self._reports.pop(index)
            stamp = int(removed.get("received_at") or time.time())
            directory = self._ensure_storage_dir()
            path = os.path.join(directory, f"report-{stamp}-{os.getpid()}.json")
            try:
                os.remove(path)
            except Exception:
                pass
            return {"ok": True}

    def clear_reports(self) -> dict[str, Any]:
        with self._lock:
            self._reports.clear()
            directory = self._ensure_storage_dir()
            try:
                for name in os.listdir(directory):
                    if name.startswith("report-") and name.endswith(".json"):
                        os.remove(os.path.join(directory, name))
            except Exception:
                pass
            return {"ok": True}

    def _on_link(self, link) -> None:
        with self._lock:
            self._active_links.append(link)
        link.set_link_closed_callback(self._on_link_closed)

    def _on_link_closed(self, link) -> None:
        with self._lock:
            if link in self._active_links:
                self._active_links.remove(link)

    def _report_response(
        self,
        path,
        data,
        request_id,
        link_id,
        remote_identity,
        requested_at,
    ):
        try:
            if isinstance(data, (bytes, bytearray)):
                text = bytes(data).decode("utf-8", errors="replace")
            elif isinstance(data, str):
                text = data
            else:
                text = ""
            payload = json.loads(text) if text else {}
            if not isinstance(payload, dict):
                return {"ok": False, "error": "invalid payload"}
            source = None
            if remote_identity is not None and hasattr(remote_identity, "hash"):
                source = remote_identity.hash.hex()
            report = {
                "received_at": time.time(),
                "source": source,
                "title": str(payload.get("title") or "")[:200],
                "description": str(payload.get("description") or "")[:4000],
                "log_text": str(payload.get("log_text") or "")[:MAX_PAYLOAD_CHARS],
                "meta": payload.get("meta")
                if isinstance(payload.get("meta"), dict)
                else {},
            }
            with self._lock:
                self._reports.insert(0, report)
                self._reports = self._reports[:MAX_STORED_REPORTS]
            self._persist_report(report)
            return {"ok": True}
        except Exception as exc:
            print(f"bug report receive failed: {exc}")
            return {"ok": False, "error": str(exc)}

    def _persist_report(self, report: dict[str, Any]) -> None:
        try:
            directory = self._ensure_storage_dir()
            stamp = int(report.get("received_at") or time.time())
            path = os.path.join(directory, f"report-{stamp}-{os.getpid()}.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2)
        except Exception as exc:
            print(f"bug report persist failed: {exc}")

    def read_debug_logs(
        self,
        *,
        limit: int = 200,
        search: str | None = None,
        level: str | None = None,
        module: str | None = None,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit or 200), MAX_LOG_LINES))
        handler = None
        try:
            from meshchatx.src.backend import persistent_log_handler as plh

            handler = getattr(plh, "memory_log_handler", None)
        except Exception:
            handler = None
        if handler is None:
            handler = getattr(self.app, "memory_log_handler", None)
        if handler is None:
            database = getattr(self.app, "database", None)
            if database is not None and hasattr(database, "debug_logs"):
                logs = database.debug_logs.get_logs(
                    limit=limit,
                    search=search,
                    level=level,
                    module=module,
                )
                total = database.debug_logs.get_total_count(
                    search=search,
                    level=level,
                    module=module,
                )
                return {"logs": logs, "total": total, "limit": limit}
            return {"logs": [], "total": 0, "limit": limit}
        logs = handler.get_logs(
            limit=limit,
            search=search,
            level=level,
            module=module,
        )
        total = handler.get_total_count(
            search=search,
            level=level,
            module=module,
        )
        return {"logs": logs, "total": total, "limit": limit}

    def preview_report(self, args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit") or 200)
        log_data = self.read_debug_logs(limit=limit)
        lines = []
        for entry in log_data.get("logs") or []:
            ts = entry.get("timestamp")
            level = entry.get("level") or ""
            module = entry.get("module") or ""
            message = entry.get("message") or ""
            lines.append(f"{ts}\t{level}\t{module}\t{message}")
        log_text = redact_diagnostic_text("\n".join(lines))
        if len(log_text) > MAX_PAYLOAD_CHARS:
            log_text = log_text[:MAX_PAYLOAD_CHARS] + "\n[truncated]"
        return {
            "log_text": log_text,
            "chars": len(log_text),
            "line_count": len(lines),
            "total_available": log_data.get("total") or 0,
        }

    def _build_payload(self, args: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
        preview = self.preview_report(args)
        title = str(args.get("title") or "MeshChatX bug report")[:200]
        description = str(args.get("description") or "")[:4000]
        payload = {
            "v": 1,
            "aspect": BUG_ASPECT,
            "title": title,
            "description": description,
            "log_text": preview["log_text"],
            "meta": {
                "line_count": preview.get("line_count"),
                "sent_at": time.time(),
            },
        }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if len(body) > MAX_PAYLOAD_CHARS + 4096:
            raise ValueError("report payload is too large")
        return payload, body

    def _send_remote_report(
        self,
        dest_hex: str,
        dest_hash: bytes,
        body: bytes,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        identity = RNS.Identity.recall(dest_hash)
        if identity is None:
            raise LookupError(
                "Could not recall collector identity. "
                "Wait for an mcx-bugs-v1 announce or start a local collector.",
            )
        app_name, aspects = RNS.Destination.app_and_aspects_from_name(BUG_ASPECT)
        destination = RNS.Destination(
            identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            app_name,
            *aspects,
        )
        if not RNS.Transport.has_path(dest_hash):
            RNS.Transport.request_path(dest_hash)
            path_wait = float(args.get("path_timeout") or 0) or path_response_window(
                dest_hash,
            )
            deadline = time.time() + path_wait
            while time.time() < deadline:
                if RNS.Transport.has_path(dest_hash):
                    break
                time.sleep(0.2)
            if not RNS.Transport.has_path(dest_hash):
                raise TimeoutError(
                    "No path to bug collector. "
                    "Start a collector locally to test, or wait for mesh announces.",
                )

        link = RNS.Link(destination)
        established = threading.Event()
        response_event = threading.Event()
        response_holder: dict[str, Any] = {"value": None, "error": None}

        def on_established(lnk):
            established.set()

        def on_response(receipt):
            response_holder["value"] = getattr(receipt, "response", None)
            response_event.set()

        def on_failed(receipt=None):
            response_holder["error"] = "request failed"
            response_event.set()

        link.set_link_established_callback(on_established)
        link_wait = float(args.get("link_timeout") or 0) or link_establishment_window(
            link,
            dest_hash,
        )
        if not established.wait(timeout=link_wait):
            try:
                link.teardown()
            except Exception:
                pass
            raise TimeoutError("Could not establish link to bug collector")

        receipt = link.request(
            REPORT_PATH,
            data=body,
            response_callback=on_response,
            failed_callback=on_failed,
            timeout=float(args.get("request_timeout") or 30),
        )
        if receipt is None:
            try:
                link.teardown()
            except Exception:
                pass
            raise RuntimeError("Failed to send bug report request")
        if not response_event.wait(timeout=float(args.get("request_timeout") or 30)):
            try:
                link.teardown()
            except Exception:
                pass
            raise TimeoutError("Bug collector did not acknowledge the report")
        try:
            link.teardown()
        except Exception:
            pass
        if response_holder.get("error"):
            raise RuntimeError(response_holder["error"])
        return {
            "ok": True,
            "destination_hash": dest_hex,
            "bytes": len(body),
            "line_count": json.loads(body).get("meta", {}).get("line_count"),
            "response": response_holder.get("value"),
        }

    def _send_local_report(self, body: bytes) -> dict[str, Any]:
        response = self._report_response(
            path=REPORT_PATH,
            data=body,
            request_id=b"local",
            link_id=None,
            remote_identity=self._identity(),
            requested_at=time.time(),
        )
        if not isinstance(response, dict) or not response.get("ok"):
            error = (
                response.get("error")
                if isinstance(response, dict)
                else "local delivery failed"
            )
            raise RuntimeError(f"Local collector rejected the report: {error}")
        return {
            "ok": True,
            "destination_hash": "local",
            "bytes": len(body),
            "line_count": json.loads(body).get("meta", {}).get("line_count"),
            "response": response,
        }

    def send_report(self, args: dict[str, Any]) -> dict[str, Any]:
        dest_hex = args.get("destination_hash")
        if not isinstance(dest_hex, str) or not dest_hex.strip():
            raise ValueError("destination_hash is required")

        if (
            len(dest_hex) < 32
            or len(dest_hex) > 64
            or len(dest_hex) % 2 != 0
            or any(ch not in "0123456789abcdefABCDEF" for ch in dest_hex)
        ):
            raise ValueError(
                f"Invalid collector hash: '{dest_hex[:20]}{'...' if len(dest_hex) > 20 else ''}' "
                f"must be 32-64 hex characters (even length).",
            )
        try:
            dest_hash = bytes.fromhex(dest_hex)
        except ValueError as exc:
            raise ValueError(
                f"Invalid collector hash: '{dest_hex[:20]}...' "
                f"must be 32-64 hex characters (even length).",
            ) from exc

        _payload, body = self._build_payload(args)

        with self._lock:
            is_local = (
                self._destination is not None
                and self._destination.hash.hex().lower() == dest_hex.lower()
            )

        if is_local:
            return self._send_local_report(body)

        return self._send_remote_report(dest_hex, dest_hash, body, args)

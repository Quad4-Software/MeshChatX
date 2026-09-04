# SPDX-License-Identifier: 0BSD

"""Bug report collector and sender over aspect mcx-bugs-v1."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import threading
import time
import uuid
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
MAX_STORED_ISSUES = 200
MAX_COLLECTORS = 80
MAX_PENDING_SENDS = 20
COLLECTOR_RATE_LIMIT = 12
COLLECTOR_RATE_WINDOW_SEC = 60.0
ISSUE_STATUSES = frozenset({"new", "seen", "resolved"})


def _normalize_fingerprint_text(text: str) -> str:
    cleaned = redact_diagnostic_text(text or "")
    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lines.append(stripped)
    return "\n".join(lines[:40])


def compute_fingerprint(
    *,
    exception_type: str = "",
    stack: str = "",
    title: str = "",
) -> str:
    base = f"{exception_type.strip().lower()}\n{_normalize_fingerprint_text(stack)}"
    if not base.strip():
        base = title.strip().lower() or "untitled"
    return hashlib.sha256(base.encode("utf-8", errors="replace")).hexdigest()


class BugReportManager:
    """Host-side collector destination and redacted log sender for plugins."""

    def __init__(self, app: Any):
        self.app = app
        self._lock = threading.RLock()
        self._destination: RNS.Destination | None = None
        self._announce_handler: AnnounceHandler | None = None
        self._collectors: dict[str, dict[str, Any]] = {}
        self._reports: list[dict[str, Any]] = []
        self._issues: dict[str, dict[str, Any]] = {}
        self._pending_sends: list[dict[str, Any]] = []
        self._active_links: list[Any] = []
        self._storage_dir: str | None = None
        self._collector_name: str = ""
        self._source_hits: dict[str, list[float]] = {}
        self._load_persisted()

    def _identity(self):
        ctx = getattr(self.app, "current_context", None)
        if ctx is None:
            return None
        return getattr(ctx, "identity", None)

    def _identity_storage_base(self) -> str:
        ctx = getattr(self.app, "current_context", None)
        if ctx is not None:
            for attr in ("storage_dir", "storage_path", "path"):
                value = getattr(ctx, attr, None)
                if isinstance(value, str) and value:
                    return value
            identity = getattr(ctx, "identity", None)
            if identity is not None and hasattr(identity, "hash"):
                base = getattr(self.app, "storage_dir", None) or os.getcwd()
                return os.path.join(base, "identities", identity.hash.hex())
        return getattr(self.app, "storage_dir", None) or os.getcwd()

    def _ensure_storage_dir(self) -> str:
        base = self._identity_storage_base()
        path = os.path.join(base, "bug_reports")
        os.makedirs(path, exist_ok=True)
        self._storage_dir = path
        return path

    def _issues_dir(self) -> str:
        path = os.path.join(self._ensure_storage_dir(), "issues")
        os.makedirs(path, exist_ok=True)
        return path

    def _pending_dir(self) -> str:
        path = os.path.join(self._ensure_storage_dir(), "pending")
        os.makedirs(path, exist_ok=True)
        return path

    def _load_persisted(self) -> None:
        try:
            directory = self._ensure_storage_dir()
        except Exception:
            return
        reports: list[dict[str, Any]] = []
        try:
            for name in os.listdir(directory):
                if not name.startswith("report-") or not name.endswith(".json"):
                    continue
                path = os.path.join(directory, name)
                try:
                    with open(path, encoding="utf-8") as handle:
                        data = json.load(handle)
                    if isinstance(data, dict):
                        if "id" not in data:
                            data["id"] = name[len("report-") : -len(".json")]
                        reports.append(data)
                except Exception:
                    continue
        except Exception:
            reports = []
        reports.sort(key=lambda item: float(item.get("received_at") or 0), reverse=True)
        self._reports = reports[:MAX_STORED_REPORTS]

        issues: dict[str, dict[str, Any]] = {}
        try:
            for name in os.listdir(self._issues_dir()):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(self._issues_dir(), name)
                try:
                    with open(path, encoding="utf-8") as handle:
                        data = json.load(handle)
                    if isinstance(data, dict) and data.get("fingerprint"):
                        issues[str(data["fingerprint"])] = data
                except Exception:
                    continue
        except Exception:
            issues = {}
        self._issues = issues

        pending: list[dict[str, Any]] = []
        try:
            for name in os.listdir(self._pending_dir()):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(self._pending_dir(), name)
                try:
                    with open(path, encoding="utf-8") as handle:
                        data = json.load(handle)
                    if isinstance(data, dict):
                        pending.append(data)
                except Exception:
                    continue
        except Exception:
            pending = []
        pending.sort(key=lambda item: float(item.get("created_at") or 0))
        self._pending_sends = pending[:MAX_PENDING_SENDS]

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
                "issues": len(self._issues),
                "pending_sends": len(self._pending_sends),
                "capture_enabled": self._capture_enabled(),
            }

    def _capture_enabled(self) -> bool:
        try:
            ctx = getattr(self.app, "current_context", None)
            config = getattr(ctx, "config", None) if ctx else None
            if config is None:
                config = getattr(self.app, "config", None)
            if config is None:
                return True
            getter = getattr(config, "bug_capture_enabled", None)
            if getter is None:
                return True
            if callable(getter):
                return bool(getter.get() if hasattr(getter, "get") else getter())
            if hasattr(getter, "get"):
                return bool(getter.get())
            return bool(getter)
        except Exception:
            return True

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
            self._retry_pending_for_collector(dest_hex)
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
            report_id = str(removed.get("id") or "")
            directory = self._ensure_storage_dir()
            if report_id:
                path = os.path.join(directory, f"report-{report_id}.json")
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

    def _rate_limit_ok(self, source: str | None) -> bool:
        key = source or "anonymous"
        now = time.time()
        hits = [
            t
            for t in self._source_hits.get(key, [])
            if now - t < COLLECTOR_RATE_WINDOW_SEC
        ]
        if len(hits) >= COLLECTOR_RATE_LIMIT:
            self._source_hits[key] = hits
            return False
        hits.append(now)
        self._source_hits[key] = hits
        return True

    def _ingest_payload(
        self, payload: dict[str, Any], source: str | None
    ) -> dict[str, Any]:
        if not self._rate_limit_ok(source):
            return {"ok": False, "error": "rate limited"}
        title = str(payload.get("title") or "")[:200]
        description = str(payload.get("description") or "")[:4000]
        log_text = redact_diagnostic_text(str(payload.get("log_text") or ""))[
            :MAX_PAYLOAD_CHARS
        ]
        exception = (
            payload.get("exception")
            if isinstance(payload.get("exception"), dict)
            else {}
        )
        stack = redact_diagnostic_text(
            str(exception.get("stack") or payload.get("stack") or "")
        )
        exception_type = redact_diagnostic_text(str(exception.get("type") or ""))[:200]
        exception_value = redact_diagnostic_text(str(exception.get("value") or ""))[
            :2000
        ]
        fingerprint = str(payload.get("fingerprint") or "").strip()
        if not fingerprint:
            fingerprint = compute_fingerprint(
                exception_type=exception_type,
                stack=stack,
                title=title,
            )
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        breadcrumbs = payload.get("breadcrumbs")
        if not isinstance(breadcrumbs, list):
            breadcrumbs = []
        report_id = str(uuid.uuid4())
        received_at = time.time()
        report = {
            "id": report_id,
            "received_at": received_at,
            "source": source,
            "title": title,
            "description": description,
            "log_text": log_text,
            "fingerprint": fingerprint,
            "exception": {
                "type": exception_type,
                "value": exception_value,
                "stack": stack[:MAX_PAYLOAD_CHARS],
            },
            "breadcrumbs": breadcrumbs[-50:],
            "meta": meta,
            "v": int(payload.get("v") or 1),
        }
        with self._lock:
            self._reports.insert(0, report)
            self._reports = self._reports[:MAX_STORED_REPORTS]
            self._merge_issue_from_report(report)
        self._persist_report(report)
        return {"ok": True, "id": report_id, "fingerprint": fingerprint}

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
            return self._ingest_payload(payload, source)
        except Exception as exc:
            print(f"bug report receive failed: {exc}")
            return {"ok": False, "error": str(exc)}

    def _persist_report(self, report: dict[str, Any]) -> None:
        try:
            directory = self._ensure_storage_dir()
            report_id = str(report.get("id") or uuid.uuid4())
            report["id"] = report_id
            path = os.path.join(directory, f"report-{report_id}.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2)
        except Exception as exc:
            print(f"bug report persist failed: {exc}")

    def _persist_issue(self, issue: dict[str, Any]) -> None:
        try:
            fingerprint = str(issue.get("fingerprint") or "")
            if not fingerprint:
                return
            path = os.path.join(self._issues_dir(), f"{fingerprint}.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(issue, handle, indent=2)
        except Exception as exc:
            print(f"bug issue persist failed: {exc}")

    def _merge_issue_from_report(self, report: dict[str, Any]) -> dict[str, Any]:
        fingerprint = str(report.get("fingerprint") or "")
        now = float(report.get("received_at") or time.time())
        existing = self._issues.get(fingerprint)
        if existing is None:
            issue = {
                "fingerprint": fingerprint,
                "title": report.get("title") or "Untitled",
                "description": report.get("description") or "",
                "status": "new",
                "count": 1,
                "first_seen": now,
                "last_seen": now,
                "source": report.get("source"),
                "exception": report.get("exception") or {},
                "log_text": report.get("log_text") or "",
                "breadcrumbs": report.get("breadcrumbs") or [],
                "meta": report.get("meta") or {},
                "last_report_id": report.get("id"),
            }
        else:
            issue = dict(existing)
            issue["count"] = int(issue.get("count") or 0) + 1
            issue["last_seen"] = now
            issue["title"] = report.get("title") or issue.get("title")
            issue["description"] = report.get("description") or issue.get("description")
            issue["exception"] = report.get("exception") or issue.get("exception")
            issue["log_text"] = report.get("log_text") or issue.get("log_text")
            issue["breadcrumbs"] = report.get("breadcrumbs") or issue.get("breadcrumbs")
            issue["meta"] = report.get("meta") or issue.get("meta")
            issue["last_report_id"] = report.get("id")
            if issue.get("status") == "resolved":
                issue["status"] = "new"
            if report.get("source"):
                issue["source"] = report.get("source")
        self._issues[fingerprint] = issue
        if len(self._issues) > MAX_STORED_ISSUES:
            ordered = sorted(
                self._issues.values(),
                key=lambda item: float(item.get("last_seen") or 0),
            )
            for stale in ordered[: len(self._issues) - MAX_STORED_ISSUES]:
                fp = str(stale.get("fingerprint") or "")
                self._issues.pop(fp, None)
                try:
                    os.remove(os.path.join(self._issues_dir(), f"{fp}.json"))
                except Exception:
                    pass
        self._persist_issue(issue)
        return issue

    def list_issues(
        self, *, limit: int = 50, status: str | None = None
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit or 50), MAX_STORED_ISSUES))
        with self._lock:
            items = list(self._issues.values())
        if status:
            items = [i for i in items if i.get("status") == status]
        items.sort(key=lambda item: float(item.get("last_seen") or 0), reverse=True)
        return {"issues": items[:limit], "total": len(items)}

    def get_issue(self, fingerprint: str) -> dict[str, Any]:
        fingerprint = str(fingerprint or "").strip()
        with self._lock:
            issue = self._issues.get(fingerprint)
            if issue is None:
                raise LookupError("issue not found")
            return {"issue": dict(issue)}

    def set_issue_status(self, fingerprint: str, status: str) -> dict[str, Any]:
        fingerprint = str(fingerprint or "").strip()
        status = str(status or "").strip()
        if status not in ISSUE_STATUSES:
            raise ValueError(f"status must be one of {sorted(ISSUE_STATUSES)}")
        with self._lock:
            issue = self._issues.get(fingerprint)
            if issue is None:
                raise LookupError("issue not found")
            issue = dict(issue)
            issue["status"] = status
            self._issues[fingerprint] = issue
            self._persist_issue(issue)
            return {"ok": True, "issue": issue}

    def record_local(self, args: dict[str, Any]) -> dict[str, Any]:
        if not self._capture_enabled() and not args.get("force"):
            return {"ok": False, "skipped": True, "reason": "capture disabled"}
        title = str(args.get("title") or "Local error")[:200]
        description = str(args.get("description") or "")[:4000]
        exception = (
            args.get("exception") if isinstance(args.get("exception"), dict) else {}
        )
        stack = str(exception.get("stack") or args.get("stack") or "")
        exception_type = str(exception.get("type") or args.get("type") or "Error")
        exception_value = str(exception.get("value") or args.get("message") or "")
        log_text = str(args.get("log_text") or "")
        if not log_text:
            preview = self.preview_report({"limit": int(args.get("limit") or 100)})
            log_text = preview.get("log_text") or ""
        fingerprint = str(args.get("fingerprint") or "").strip() or compute_fingerprint(
            exception_type=exception_type,
            stack=stack,
            title=title,
        )
        raw_meta = args.get("meta")
        overlay: dict[str, Any] = {}
        if isinstance(raw_meta, dict):
            overlay = raw_meta
        meta = {
            **self._default_meta(source=str(args.get("source") or "local")),
            **overlay,
        }
        payload = {
            "v": 2,
            "aspect": BUG_ASPECT,
            "kind": str(args.get("kind") or "exception"),
            "title": title,
            "description": description,
            "fingerprint": fingerprint,
            "exception": {
                "type": exception_type,
                "value": exception_value,
                "stack": stack,
            },
            "breadcrumbs": args.get("breadcrumbs")
            if isinstance(args.get("breadcrumbs"), list)
            else [],
            "meta": meta,
            "log_text": log_text,
        }
        result = self._ingest_payload(payload, source="local")
        if result.get("ok"):
            with self._lock:
                issue = self._issues.get(fingerprint)
            result["issue"] = issue
        return result

    def _app_version(self) -> str:
        try:
            from meshchatx import __version__

            return str(__version__)
        except Exception:
            return ""

    def _default_meta(self, *, source: str) -> dict[str, Any]:
        return {
            "app_version": self._app_version(),
            "platform": platform.system(),
            "channel": "release",
            "source": source,
            "sent_at": time.time(),
        }

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
        issue_fp = str(args.get("fingerprint") or "").strip()
        issue = None
        if issue_fp:
            with self._lock:
                issue = self._issues.get(issue_fp)
        if issue is not None:
            log_text = redact_diagnostic_text(str(issue.get("log_text") or ""))
            if len(log_text) > MAX_PAYLOAD_CHARS:
                log_text = log_text[:MAX_PAYLOAD_CHARS] + "\n[truncated]"
            exception = (
                issue.get("exception")
                if isinstance(issue.get("exception"), dict)
                else {}
            )
            title = str(
                args.get("title") or issue.get("title") or "MeshChatX bug report"
            )[:200]
            description = str(
                args.get("description") or issue.get("description") or ""
            )[:4000]
            payload = {
                "v": 2,
                "aspect": BUG_ASPECT,
                "kind": "exception",
                "title": title,
                "description": description,
                "fingerprint": issue_fp,
                "exception": {
                    "type": redact_diagnostic_text(str(exception.get("type") or ""))[
                        :200
                    ],
                    "value": redact_diagnostic_text(str(exception.get("value") or ""))[
                        :2000
                    ],
                    "stack": redact_diagnostic_text(str(exception.get("stack") or ""))[
                        :MAX_PAYLOAD_CHARS
                    ],
                },
                "breadcrumbs": issue.get("breadcrumbs")
                if isinstance(issue.get("breadcrumbs"), list)
                else [],
                "log_text": log_text,
                "meta": {
                    **self._default_meta(
                        source=str((issue.get("meta") or {}).get("source") or "local")
                    ),
                    "line_count": log_text.count("\n") + (1 if log_text else 0),
                },
            }
        else:
            preview = self.preview_report(args)
            title = str(args.get("title") or "MeshChatX bug report")[:200]
            description = str(args.get("description") or "")[:4000]
            payload = {
                "v": 2,
                "aspect": BUG_ASPECT,
                "kind": "log",
                "title": title,
                "description": description,
                "fingerprint": compute_fingerprint(
                    title=title, stack=preview["log_text"]
                ),
                "log_text": preview["log_text"],
                "meta": {
                    **self._default_meta(source="manual"),
                    "line_count": preview.get("line_count"),
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

    def _validate_dest_hex(self, dest_hex: str) -> bytes:
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
            return bytes.fromhex(dest_hex)
        except ValueError as exc:
            raise ValueError(
                f"Invalid collector hash: '{dest_hex[:20]}...' "
                f"must be 32-64 hex characters (even length).",
            ) from exc

    def send_report(self, args: dict[str, Any]) -> dict[str, Any]:
        dest_hex = str(args.get("destination_hash") or "")
        dest_hash = self._validate_dest_hex(dest_hex)
        _payload, body = self._build_payload(args)

        with self._lock:
            is_local = (
                self._destination is not None
                and self._destination.hash.hex().lower() == dest_hex.lower()
            )

        try:
            if is_local:
                return self._send_local_report(body)
            return self._send_remote_report(dest_hex, dest_hash, body, args)
        except TimeoutError:
            if args.get("enqueue_on_timeout"):
                return self.enqueue_send({**args, "body_b64": None, "_body": body})
            raise

    def enqueue_send(self, args: dict[str, Any]) -> dict[str, Any]:
        dest_hex = str(args.get("destination_hash") or "")
        self._validate_dest_hex(dest_hex)
        if "_body" in args and isinstance(args["_body"], (bytes, bytearray)):
            body = bytes(args["_body"])
            payload = json.loads(body.decode("utf-8"))
        else:
            payload, body = self._build_payload(args)
        entry = {
            "id": str(uuid.uuid4()),
            "created_at": time.time(),
            "destination_hash": dest_hex,
            "title": str(payload.get("title") or "")[:200],
            "fingerprint": payload.get("fingerprint"),
            "body": body.decode("utf-8"),
        }
        with self._lock:
            self._pending_sends.append(entry)
            self._pending_sends = self._pending_sends[-MAX_PENDING_SENDS:]
        self._persist_pending(entry)
        return {
            "ok": True,
            "queued": True,
            "id": entry["id"],
            "pending": len(self._pending_sends),
        }

    def _persist_pending(self, entry: dict[str, Any]) -> None:
        try:
            path = os.path.join(self._pending_dir(), f"{entry['id']}.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(entry, handle, indent=2)
        except Exception as exc:
            print(f"bug pending persist failed: {exc}")

    def list_pending_sends(self) -> dict[str, Any]:
        with self._lock:
            items = [
                {
                    "id": e.get("id"),
                    "created_at": e.get("created_at"),
                    "destination_hash": e.get("destination_hash"),
                    "title": e.get("title"),
                    "fingerprint": e.get("fingerprint"),
                }
                for e in self._pending_sends
            ]
        return {"pending": items}

    def cancel_pending_send(self, pending_id: str) -> dict[str, Any]:
        pending_id = str(pending_id or "")
        with self._lock:
            before = len(self._pending_sends)
            self._pending_sends = [
                e for e in self._pending_sends if e.get("id") != pending_id
            ]
        try:
            os.remove(os.path.join(self._pending_dir(), f"{pending_id}.json"))
        except Exception:
            pass
        return {"ok": True, "removed": before - len(self._pending_sends)}

    def _retry_pending_for_collector(self, dest_hex: str) -> None:
        with self._lock:
            pending = [
                e for e in self._pending_sends if e.get("destination_hash") == dest_hex
            ]
        for entry in pending:
            try:
                body = str(entry.get("body") or "").encode("utf-8")
                dest_hash = bytes.fromhex(str(entry.get("destination_hash")))
                self._send_remote_report(
                    str(entry.get("destination_hash")),
                    dest_hash,
                    body,
                    {"path_timeout": 5, "link_timeout": 10, "request_timeout": 20},
                )
                self.cancel_pending_send(str(entry.get("id")))
            except Exception:
                continue

    def on_identity_switch(self) -> None:
        """Clear in-memory state and reload from the new identity storage."""
        with self._lock:
            try:
                if self._destination is not None:
                    self.stop_collector()
            except Exception:
                pass
            self._reports = []
            self._issues = {}
            self._pending_sends = []
            self._storage_dir = None
            self._source_hits = {}
            self._load_persisted()

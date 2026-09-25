# SPDX-License-Identifier: 0BSD

"""Crash recovery and adaptive diagnostics for MeshChatX.

Uses entropy, KL-divergence, and Bayesian weight learning. Crash history is
persisted. Priors refine over time (conjugate Beta-Binomial model).
"""

import asyncio
import contextlib
import errno
import faulthandler
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import sys
import threading
import time
import traceback

import psutil
import RNS

from meshchatx.src.env_utils import env_bool

_DEFAULT_PRIORS = {
    "DB_SYNC_FAILURE": 0.05,
    "DB_CORRUPTION": 0.05,
    "ASYNC_RACE": 0.10,
    "CROSS_LOOP_BOUND": 0.10,
    "OOM": 0.02,
    "CONFIG_MISSING": 0.01,
    "FILESYSTEM_PERMISSION_DENIED": 0.05,
    "RNS_IDENTITY_FAILURE": 0.05,
    "LXMF_STORAGE_FAILURE": 0.05,
    "INTERFACE_OFFLINE": 0.05,
    "UNSUPPORTED_PYTHON": 0.05,
    "LEGACY_SYSTEM_LIMITATION": 0.05,
}

# Repeat reports for the same crash signature are summarized instead of
# re-printing the full diagnosis, so a crash loop cannot flood stderr.
_REPEAT_REPORT_WINDOW_SEC = 60.0

# Crash reports are mirrored to <storage_dir>/crash_reports/, capped.
_CRASH_REPORT_KEEP = 20


class CrashRecovery:
    """Intercept crashes and report diagnostics plus environment state.

    Learns from crash history to refine root-cause probabilities over time.
    """

    def __init__(
        self,
        storage_dir=None,
        database_path=None,
        public_dir=None,
        reticulum_config_dir=None,
        database=None,
        log_handler=None,
    ):
        self.storage_dir = storage_dir
        self.database_path = database_path
        self.public_dir = public_dir
        self.reticulum_config_dir = reticulum_config_dir
        self.database = database
        self.log_handler = log_handler
        self.app = None
        self.enabled = True
        self._learned_priors = None
        # Re-entrancy is per-thread; a shared bool would either miss the
        # guard under a non-atomic check-set or suppress a second thread's
        # report entirely. The report lock serializes output instead.
        self._local = threading.local()
        self._report_lock = threading.Lock()
        self._signature_last_report: dict[str, float] = {}
        self._prev_sys_hook = None
        self._prev_threading_hook = None
        self._prev_unraisable_hook = None

        # Check environment variable to allow disabling the recovery system
        if env_bool("MESHCHAT_NO_CRASH_RECOVERY"):
            self.enabled = False

    def install(self):
        """Installs the crash recovery exception hook into the system.

        Covers both the main thread (sys.excepthook) and background
        threads (threading.excepthook).  A daemon worker dying silently is
        a common source of hard-to-diagnose failures, so its exception is
        diagnosed and logged without tearing down the whole process.
        """
        if not self.enabled:
            return

        if self._prev_sys_hook is None:
            self._prev_sys_hook = sys.excepthook
        sys.excepthook = self.handle_exception

        if self._prev_threading_hook is None:
            self._prev_threading_hook = threading.excepthook
        threading.excepthook = self._handle_thread_exception

        if self._prev_unraisable_hook is None:
            self._prev_unraisable_hook = sys.unraisablehook
        sys.unraisablehook = self._handle_unraisable

        # Native crashes (segfaults inside RNS crypto, codec libs, sqlite)
        # never reach Python hooks; faulthandler at least dumps the frames.
        with contextlib.suppress(Exception):
            faulthandler.enable()

        # asyncio task exceptions ("never retrieved") and loop errors are
        # not covered by sys.excepthook; route them through this handler.
        self.install_asyncio_handlers()

    def disable(self):
        """Disables the crash recovery system manually."""
        self.enabled = False
        if self._prev_sys_hook is not None:
            sys.excepthook = self._prev_sys_hook
            self._prev_sys_hook = None
        if self._prev_threading_hook is not None:
            threading.excepthook = self._prev_threading_hook
            self._prev_threading_hook = None
        if self._prev_unraisable_hook is not None:
            sys.unraisablehook = self._prev_unraisable_hook
            self._prev_unraisable_hook = None
        try:
            from meshchatx.src.backend.async_utils import AsyncUtils

            AsyncUtils.set_exception_handler(None)
        except Exception:
            pass

    def install_asyncio_handlers(self):
        """Attach the loop exception handler to every known event loop."""
        try:
            from meshchatx.src.backend.async_utils import AsyncUtils

            AsyncUtils.set_exception_handler(self.handle_asyncio_exception)
        except Exception:
            pass

    def handle_asyncio_exception(self, loop, context):
        """Loop exception handler routing real exceptions to the diagnosis.

        Message-only contexts (e.g. destroyed pending tasks) stay with the
        default handler.
        """
        if not self.enabled:
            with contextlib.suppress(Exception):
                loop.default_exception_handler(context)
            return
        exc = context.get("exception") if isinstance(context, dict) else None
        if not isinstance(exc, BaseException) or isinstance(
            exc,
            (KeyboardInterrupt, SystemExit),
        ):
            with contextlib.suppress(Exception):
                loop.default_exception_handler(context)
            return
        # asyncio.CancelledError reaching the loop handler is normal
        # teardown noise, not a crash.
        if isinstance(exc, asyncio.CancelledError):
            return
        # This runs on the loop thread: waiting on the report lock would
        # stall every task on the loop while another crash is diagnosed.
        self.handle_exception(
            type(exc),
            exc,
            exc.__traceback__,
            exit_process=False,
            wait_for_report=False,
        )

    def _handle_unraisable(self, args):
        """sys.unraisablehook adapter for __del__ and GC-side exceptions."""
        if not self.enabled or getattr(args, "exc_type", None) is None:
            fallback = self._prev_unraisable_hook or getattr(
                sys,
                "__unraisablehook__",
                None,
            )
            if fallback is not None:
                with contextlib.suppress(Exception):
                    fallback(args)
            return
        # Unraisable hooks can run inside GC pauses or interpreter shutdown;
        # never block them on the report lock.
        self.handle_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            exit_process=False,
            wait_for_report=False,
        )

    def _handle_thread_exception(self, args):
        """threading.excepthook adapter. Diagnoses without killing the process."""
        if args.exc_type is None or issubclass(args.exc_type, SystemExit):
            return
        thread_name = getattr(args.thread, "name", "unknown")
        try:
            sys.stderr.write(
                f"\n[crash_recovery] Unhandled exception in thread '{thread_name}':\n",
            )
        except Exception:
            pass
        self.handle_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            exit_process=False,
        )

    def update_paths(
        self,
        storage_dir=None,
        database_path=None,
        public_dir=None,
        reticulum_config_dir=None,
    ):
        """Updates the internal paths used for system diagnosis."""
        if storage_dir:
            self.storage_dir = storage_dir
        if database_path:
            self.database_path = database_path
        if public_dir:
            self.public_dir = public_dir
        if reticulum_config_dir:
            self.reticulum_config_dir = reticulum_config_dir

    def set_database(self, database):
        """Provide database access for crash persistence and weight learning."""
        self.database = database
        self._load_learned_priors()

    def _load_learned_priors(self):
        """Load learned Bayesian priors from the config table."""
        if not self.database:
            return
        try:
            raw = self.database.config.get("diagnostic_weights")
            if raw:
                self._learned_priors = json.loads(raw)
        except Exception:
            self._learned_priors = None

    def _get_prior(self, cause_key):
        """Return the learned prior for a cause, falling back to the hardcoded default."""
        if self._learned_priors and cause_key in self._learned_priors:
            return self._learned_priors[cause_key]
        return _DEFAULT_PRIORS.get(cause_key, 0.05)

    def _persist_crash(
        self,
        error_type,
        error_msg,
        causes,
        symptoms,
        entropy,
        divergence,
        exc_value=None,
        exc_traceback=None,
        signature=None,
    ):
        """Store crash event in crash_history for future learning."""
        if not self.database:
            return
        try:
            top_cause = causes[0]["description"] if causes else "Unknown"
            # Store the raw heuristic score, not the normalized share: the
            # learner's confidence gate (min_probability=60) is calibrated
            # against the heuristic scale, where shares run much lower.
            top_prob = causes[0].get("score", causes[0]["probability"]) if causes else 0
            stored_symptoms = dict(symptoms) if isinstance(symptoms, dict) else {}
            if signature:
                stored_symptoms["_signature"] = signature
            self.database.crash_history.insert_crash(
                timestamp=time.time(),
                error_type=error_type,
                error_message=error_msg,
                diagnosed_cause=top_cause,
                symptoms=stored_symptoms,
                probability=top_prob,
                entropy=entropy,
                divergence=divergence,
            )
            self.database.crash_history.cleanup_old(max_entries=200)
        except Exception:
            pass

    def _update_learned_weights(self):
        """Bayesian weight update using Beta-Binomial conjugate model.

        Only confident diagnoses train the model: learning from its own
        low-confidence guesses would amplify early mistakes (pseudo-label
        confirmation bias). The posterior is also clamped to a band around
        the default prior so self-labels can shift but never dominate.
        """
        if not self.database:
            return
        try:
            freq_rows = self.database.crash_history.get_cause_frequencies(
                limit=50,
                min_probability=60,
            )
            if not freq_rows:
                return
            total = sum(r["count"] for r in freq_rows)
            if total < 3:
                return

            cause_counts = {r["diagnosed_cause"]: r["count"] for r in freq_rows}
            weights = {}
            for key, default in _DEFAULT_PRIORS.items():
                desc = self._cause_key_to_description(key)
                count = cause_counts.get(desc, 0)
                alpha = 1.0 + count
                beta = 1.0 + (total - count)
                posterior = alpha / (alpha + beta)
                floor = default * 0.25
                ceiling = min(0.9, default * 4.0)
                weights[key] = round(
                    max(floor, min(ceiling, posterior)),
                    4,
                )

            self.database.config.set("diagnostic_weights", json.dumps(weights))
            self._learned_priors = weights
        except Exception:
            pass

    @staticmethod
    def _cause_key_to_description(key):
        """Map internal cause keys to their human-readable descriptions."""
        mapping = {
            "DB_SYNC_FAILURE": "In-Memory Database Sync Failure",
            "DB_CORRUPTION": "SQLite Database Corruption",
            "ASYNC_RACE": "Asynchronous Initialization Race Condition",
            "CROSS_LOOP_BOUND": "Cross-Loop asyncio Primitive Reuse",
            "OOM": "System Resource Exhaustion (OOM)",
            "CONFIG_MISSING": "Missing Reticulum Configuration",
            "FILESYSTEM_PERMISSION_DENIED": "Filesystem Permission Denied",
            "RNS_IDENTITY_FAILURE": "Reticulum Identity Load Failure",
            "LXMF_STORAGE_FAILURE": "LXMF Router Storage Failure",
            "INTERFACE_OFFLINE": "Reticulum Interface Initialization Failure",
            "UNSUPPORTED_PYTHON": "Unsupported Python Environment",
            "LEGACY_SYSTEM_LIMITATION": "Legacy System Resource Limitation",
        }
        return mapping.get(key, key)

    def handle_exception(
        self,
        exc_type,
        exc_value,
        exc_traceback,
        *,
        exit_process=True,
        wait_for_report=True,
    ):
        """Intercepts unhandled exceptions to provide a detailed diagnosis report."""
        if not self.enabled:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Let keyboard interrupts pass through normally
        if not isinstance(exc_type, type) or issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Guard against re-entrancy per thread: if the diagnostic path itself
        # raises, fall back to the default hook instead of recursing.
        if getattr(self._local, "handling", False):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        self._local.handling = True

        try:
            signature = self._crash_signature(exc_type, exc_value, exc_traceback)
            suppressed = self._is_repeat_signature(signature)
            # Serialize concurrent crash reports so two threads do not
            # interleave output. Bounded so a wedged first report cannot
            # block process exit. Non-blocking callers (asyncio loop handler,
            # unraisable hook) drop to a one-liner plus persistence instead.
            acquired = (
                self._report_lock.acquire(timeout=10)
                if wait_for_report
                else self._report_lock.acquire(blocking=False)
            )
            if acquired:
                try:
                    self._diagnose_and_report(
                        exc_type,
                        exc_value,
                        exc_traceback,
                        signature=signature,
                        suppressed=suppressed,
                    )
                finally:
                    self._report_lock.release()
            elif not wait_for_report:
                with contextlib.suppress(Exception):
                    sys.stderr.write(
                        f"[crash_recovery] {signature} "
                        f"{getattr(exc_type, '__name__', exc_type)} report "
                        "deferred: another diagnosis is in progress\n",
                    )
                self._persist_lightweight(
                    exc_type,
                    exc_value,
                    exc_traceback,
                    signature,
                )
            else:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
        except Exception:
            try:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
            except Exception:
                pass
        finally:
            self._local.handling = False

        if exit_process:
            sys.exit(1)

    @staticmethod
    def _crash_signature(exc_type, exc_value, exc_traceback):
        """Stable fingerprint: exception type plus top in-app frames.

        Sentry-style grouping: stack frames are normalized to file basename
        and function name, so line shifts do not churn the signature and the
        same root cause lands in the same bucket.
        """
        parts = [getattr(exc_type, "__name__", str(exc_type))]
        try:
            frames = traceback.extract_tb(exc_traceback) if exc_traceback else []
            app_frames = [
                f for f in frames if "meshchat" in f.filename.replace("\\", "/")
            ]
            chosen = app_frames[:4] if app_frames else frames[-4:]
            parts.extend(f"{os.path.basename(f.filename)}:{f.name}" for f in chosen)
        except Exception:
            pass
        raw = "\n".join(parts).encode("utf-8", "replace")
        return hashlib.sha256(raw).hexdigest()[:16]

    def _is_repeat_signature(self, signature):
        """True when this signature produced a full report recently."""
        now = time.monotonic()
        last = self._signature_last_report.get(signature)
        self._signature_last_report[signature] = now
        if len(self._signature_last_report) > 256:
            cutoff = now - _REPEAT_REPORT_WINDOW_SEC
            self._signature_last_report = {
                s: t for s, t in self._signature_last_report.items() if t >= cutoff
            }
            # Rapid churn of distinct signatures can out-run expiry, so drop
            # the oldest entries outright to keep the map bounded.
            if len(self._signature_last_report) > 256:
                oldest = sorted(
                    self._signature_last_report.items(),
                    key=lambda kv: kv[1],
                )
                for s, _ in oldest[: len(self._signature_last_report) - 256]:
                    self._signature_last_report.pop(s, None)
        return last is not None and (now - last) < _REPEAT_REPORT_WINDOW_SEC

    def _persist_lightweight(
        self,
        exc_type,
        exc_value,
        exc_traceback,
        signature,
    ):
        """Persist a deferred crash without the full environment scan.

        Used when the report lock is busy and the caller must not block
        (asyncio loop handler, unraisable hook).
        """
        analysis = self._analyze_cause_full(
            exc_type,
            exc_value,
            {},
            exc_traceback=exc_traceback,
        )
        with contextlib.suppress(Exception):
            self._persist_crash(
                getattr(exc_type, "__name__", str(exc_type)),
                str(exc_value),
                analysis["causes"],
                analysis["symptoms"],
                0.0,
                0.0,
                exc_value=exc_value,
                exc_traceback=exc_traceback,
                signature=signature,
            )

    def _count_signature_occurrences(self, signature):
        """Count prior persisted crashes with this signature."""
        if not self.database or not signature:
            return 0
        try:
            count = 0
            for row in self.database.crash_history.get_recent_crashes(
                limit=200,
            ):
                symptoms = row.get("symptoms")
                if isinstance(symptoms, str):
                    try:
                        symptoms = json.loads(symptoms)
                    except (TypeError, ValueError):
                        continue
                if (
                    isinstance(symptoms, dict)
                    and symptoms.get("_signature") == signature
                ):
                    count += 1
            return count
        except Exception:
            return 0

    def _open_report_file(self, signature):
        """Mirror the report to <storage_dir>/crash_reports/ for attachability."""
        if not self.storage_dir:
            return None
        try:
            report_dir = os.path.join(self.storage_dir, "crash_reports")
            os.makedirs(report_dir, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            path = os.path.join(
                report_dir,
                f"crash-{stamp}-{signature or 'na'}.log",
            )
            handle = open(path, "w", encoding="utf-8", errors="replace")
            self._rotate_report_dir(report_dir)
            return handle
        except Exception:
            return None

    @staticmethod
    def _rotate_report_dir(report_dir):
        """Keep only the newest _CRASH_REPORT_KEEP report files."""
        try:
            entries = [
                os.path.join(report_dir, name)
                for name in os.listdir(report_dir)
                if name.startswith("crash-") and name.endswith(".log")
            ]
            if len(entries) <= _CRASH_REPORT_KEEP:
                return
            entries.sort(key=lambda p: os.path.getmtime(p))
            for stale in entries[:-_CRASH_REPORT_KEEP]:
                with contextlib.suppress(OSError):
                    os.remove(stale)
        except Exception:
            pass

    class _TeeWriter:
        """Minimal write/flush fan-out to stderr and a report file."""

        __slots__ = ("_targets",)

        def __init__(self, targets):
            self._targets = targets

        def write(self, text):
            for target in self._targets:
                try:
                    target.write(text)
                except Exception:
                    pass

        def flush(self):
            for target in self._targets:
                try:
                    target.flush()
                except Exception:
                    pass

    def _diagnose_and_report(
        self,
        exc_type,
        exc_value,
        exc_traceback,
        signature=None,
        suppressed=False,
    ):
        """Render the crash diagnosis report to stderr and a report file."""
        error_msg = str(exc_value)
        error_type = exc_type.__name__

        if suppressed:
            # Same signature reported within the window: persist for learning
            # but keep stderr quiet so a crash loop cannot flood the console.
            try:
                sys.stderr.write(
                    f"[crash_recovery] repeat crash {signature} "
                    f"({error_type}: {error_msg[:120]}) suppressed\n",
                )
            except Exception:
                pass
            analysis = self._analyze_cause_full(
                exc_type,
                exc_value,
                {},
                exc_traceback=exc_traceback,
            )
            entropy, divergence = self._calculate_system_entropy({})
            with contextlib.suppress(Exception):
                self._persist_crash(
                    error_type,
                    error_msg,
                    analysis["causes"],
                    analysis["symptoms"],
                    entropy,
                    divergence,
                    exc_value=exc_value,
                    exc_traceback=exc_traceback,
                    signature=signature,
                )
                self._update_learned_weights()
            return

        report_file = self._open_report_file(signature)
        targets = [sys.stderr]
        if report_file is not None:
            targets.append(report_file)
        out = self._TeeWriter(targets)

        try:
            self._write_report_body(
                out,
                exc_type,
                exc_value,
                exc_traceback,
                error_type,
                error_msg,
                signature,
            )
        finally:
            if report_file is not None:
                with contextlib.suppress(Exception):
                    report_file.close()

    def _write_report_body(
        self,
        out,
        exc_type,
        exc_value,
        exc_traceback,
        error_type,
        error_msg,
        signature,
    ):
        # Print visual separator
        out.write("\n" + "=" * 70 + "\n")
        out.write("!!! APPLICATION CRASH DETECTED !!!\n")
        out.write("=" * 70 + "\n")

        if signature:
            out.write(f"\nCrash Signature: {signature}\n")
            occurrences = self._count_signature_occurrences(signature)
            if occurrences:
                out.write(
                    f"  This signature has been seen {occurrences} "
                    "time(s) before in crash history.\n",
                )

        top_frame = self._top_app_frame(exc_traceback)
        if top_frame is not None:
            out.write(
                f"  Top app frame: {os.path.basename(top_frame.filename)}:"
                f"{top_frame.lineno} in {top_frame.name}\n",
            )

        out.write("\nError Summary:\n")
        out.write(f"  Type:    {error_type}\n")
        out.write(f"  Message: {error_msg}\n")

        # Perform logical diagnosis
        out.write("\nSystem Environment Diagnosis:\n")
        diagnosis_results = {}
        try:
            diagnosis_results = self.run_diagnosis(file=out, crash_exception=exc_value)
        except Exception as e:
            out.write(f"  [ERROR] Failed to complete diagnosis: {e}\n")

        out.write("\nRoot Cause Analysis:\n")
        analysis = self._analyze_cause_full(
            exc_type,
            exc_value,
            diagnosis_results,
            exc_traceback=exc_traceback,
        )
        causes = analysis["causes"]
        symptoms = analysis["symptoms"]

        entropy, divergence = self._calculate_system_entropy(diagnosis_results)

        out.write(f"  [System Entropy: {entropy:.4f} bits]\n")
        out.write(f"  [KL-Divergence: {divergence:.4f} bits]\n")

        if self.log_handler:
            log_ent = self.log_handler.current_log_entropy
            err_rate = self.log_handler.current_error_rate
            out.write(f"  [Log Entropy (60s): {log_ent:.4f} bits]\n")
            out.write(f"  [Error Rate (60s): {err_rate:.2%}]\n")

        if self._learned_priors:
            out.write("  [Bayesian Priors: Learned from crash history]\n")

        out.write("  (shares are normalized across candidate causes)\n")

        for cause in causes:
            out.write(
                f"  - [{cause['probability']}% Probability] {cause['description']}\n",
            )
            out.write(f"    Reasoning: {cause['reasoning']}\n")

        out.write("\nTechnical Traceback:\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=out)

        self._write_recent_log_tail(out)

        out.write("\n" + "=" * 70 + "\n")
        out.write("Recovery Suggestions:\n")

        # Dynamic suggestions based on causes
        if causes:
            for i, cause in enumerate(causes, 1):
                for suggestion in cause.get("suggestions", []):
                    out.write(f"  {i}. {suggestion}\n")
        else:
            # Fallback standard suggestions
            out.write("  1. Review the 'System Environment Diagnosis' section above.\n")
            out.write(
                "  2. Verify that all dependencies are installed (poetry install or pip install -r requirements.txt).\n",
            )
            out.write(
                "  3. If database corruption is suspected, try starting with --auto-recover.\n",
            )

        out.write(
            "  *. If the issue persists, report it to Ivan over another LXMF client: f489752fbef161c64d65e385a4e9fc74\n",
        )
        out.write("=" * 70 + "\n\n")
        out.flush()

        # Persist crash and update weights (best-effort, never raise)
        with contextlib.suppress(Exception):
            self._persist_crash(
                error_type,
                error_msg,
                causes,
                symptoms,
                entropy,
                divergence,
                exc_value=exc_value,
                exc_traceback=exc_traceback,
                signature=signature,
            )
            self._update_learned_weights()

    @staticmethod
    def _top_app_frame(exc_traceback):
        """Deepest traceback frame inside application code, if any."""
        if exc_traceback is None:
            return None
        try:
            frames = traceback.extract_tb(exc_traceback)
            app_frames = [
                f for f in frames if "meshchat" in f.filename.replace("\\", "/")
            ]
            if app_frames:
                return app_frames[-1]
            return frames[-1] if frames else None
        except Exception:
            return None

    def _write_recent_log_tail(self, out):
        """Last warnings/errors from the in-memory log ring as breadcrumbs."""
        handler = self.log_handler
        if handler is None:
            return
        try:
            with handler.lock:
                entries = [
                    e
                    for e in list(handler.logs_buffer)
                    if e.get("level") in ("WARNING", "ERROR", "CRITICAL")
                ][-12:]
        except Exception:
            return
        if not entries:
            return
        out.write("\nRecent warnings/errors (breadcrumbs):\n")
        for entry in entries:
            msg = str(entry.get("message", "")).replace("\n", " ")[:200]
            module = entry.get("module", "?")
            level = entry.get("level", "?")
            out.write(f"  [{level}] {module}: {msg}\n")

    def _analyze_cause(self, exc_type, exc_value, diagnosis, exc_traceback=None):
        """Rank likely root causes using heuristics and Bayesian priors."""
        return self._analyze_cause_full(
            exc_type,
            exc_value,
            diagnosis,
            exc_traceback=exc_traceback,
        )["causes"]

    def _analyze_cause_full(
        self,
        exc_type,
        exc_value,
        diagnosis,
        exc_traceback=None,
    ):
        causes = []
        error_msg = str(exc_value).lower()
        error_type = exc_type.__name__.lower()

        # Traceback evidence: which subsystems appear in the failing stack.
        # Frames in application code carry far more signal than the exception
        # message alone, which is why the analysis reads the traceback.
        frame_paths = []
        if exc_traceback is not None:
            try:
                frame_paths = [
                    f.filename.replace("\\", "/").lower()
                    for f in traceback.extract_tb(exc_traceback)
                ]
            except Exception:
                frame_paths = []

        def frames_have(*needles):
            return any(needle in path for needle in needles for path in frame_paths)

        # Define potential root causes with prior probabilities (learned or default)
        potential_causes = {
            "DB_SYNC_FAILURE": {
                "probability": self._get_prior("DB_SYNC_FAILURE"),
                "description": "In-Memory Database Sync Failure",
                "reasoning": "A background thread attempted to access an in-memory database that was not initialized in its local context.",
                "suggestions": [
                    "Ensure the application is using a shared connection for :memory: databases.",
                    "Update to the latest version of MeshChatX which includes a fix for this.",
                ],
            },
            "DB_CORRUPTION": {
                "probability": self._get_prior("DB_CORRUPTION"),
                "description": "SQLite Database Corruption",
                "reasoning": "The database file on disk has become physically or logically corrupted.",
                "suggestions": [
                    "Use --auto-recover to attempt a repair.",
                    "Restore from a recent backup using --restore-db <backup_path>.",
                ],
            },
            "ASYNC_RACE": {
                "probability": self._get_prior("ASYNC_RACE"),
                "description": "Asynchronous Initialization Race Condition",
                "reasoning": "A component tried to access the asyncio event loop before it was started.",
                "suggestions": [
                    "Check if you are running a supported Python version (3.10+ recommended).",
                    "Verify that background tasks are correctly deferred until the loop is running.",
                ],
            },
            "CROSS_LOOP_BOUND": {
                "probability": self._get_prior("CROSS_LOOP_BOUND"),
                "description": "Cross-Loop asyncio Primitive Reuse",
                "reasoning": (
                    "An asyncio primitive (Lock, Queue, Event, Task) created on one "
                    "event loop was awaited on a different loop, usually a worker "
                    "thread running asyncio.run or a stale loop reference."
                ),
                "suggestions": [
                    "Re-dispatch the work onto the owning loop via asyncio.run_coroutine_threadsafe.",
                    "Report this crash: it indicates a shared asyncio object reached a foreign event loop.",
                ],
            },
            "OOM": {
                "probability": self._get_prior("OOM"),
                "description": "System Resource Exhaustion (OOM)",
                "reasoning": "Available system memory is extremely low, leading to allocation failures.",
                "suggestions": [
                    "Close other memory-intensive applications.",
                    "Relaunch in Emergency Mode (--emergency) to reduce startup memory use.",
                    "Add more RAM or swap space to the system.",
                ],
            },
            "CONFIG_MISSING": {
                "probability": self._get_prior("CONFIG_MISSING"),
                "description": "Missing Reticulum Configuration",
                "reasoning": "The Reticulum Network Stack (RNS) could not find its configuration file.",
                "suggestions": [
                    "Ensure ~/.reticulum/config exists or provide a custom path via --reticulum-config-dir.",
                ],
            },
            "FILESYSTEM_PERMISSION_DENIED": {
                "probability": self._get_prior("FILESYSTEM_PERMISSION_DENIED"),
                "description": "Filesystem Permission Denied",
                "reasoning": "The process could not create or write a required directory or file (EACCES/EPERM).",
                "suggestions": [
                    "Fix ownership or permissions on the storage path (or its parent). The process user must be able to create that directory.",
                    "If using Docker or Podman, mount the volume with UID/GID matching the container user, use docker run --user, or chown the host directory.",
                    "Set MESHCHAT_STORAGE_DIR to a writable location, or point --storage-dir at a directory the runtime user owns.",
                ],
            },
            "RNS_IDENTITY_FAILURE": {
                "probability": self._get_prior("RNS_IDENTITY_FAILURE"),
                "description": "Reticulum Identity Load Failure",
                "reasoning": "The Reticulum identity file is missing, corrupt, or unreadable.",
                "suggestions": [
                    "Check permissions on the identity file.",
                    "If the file is corrupt, you may need to recreate it (this will change your address).",
                ],
            },
            "LXMF_STORAGE_FAILURE": {
                "probability": self._get_prior("LXMF_STORAGE_FAILURE"),
                "description": "LXMF Router Storage Failure",
                "reasoning": "The LXMF router could not access its message storage directory.",
                "suggestions": [
                    "Verify that the storage directory is writable.",
                    "Check for filesystem-level locks or full disks.",
                ],
            },
            "INTERFACE_OFFLINE": {
                "probability": self._get_prior("INTERFACE_OFFLINE"),
                "description": "Reticulum Interface Initialization Failure",
                "reasoning": "No active communication interfaces could be established.",
                "suggestions": [
                    "Check your Reticulum config for interface errors.",
                    "Verify hardware connections (USB, Serial, Ethernet) for LoRa/TNC devices.",
                ],
            },
            "UNSUPPORTED_PYTHON": {
                "probability": self._get_prior("UNSUPPORTED_PYTHON"),
                "description": "Unsupported Python Environment",
                "reasoning": "The application is running on an outdated or incompatible Python version.",
                "suggestions": [
                    "Upgrade to Python 3.10 or higher (3.11/3.12+ recommended).",
                    "Check if you are running inside a legacy virtualenv.",
                ],
            },
            "LEGACY_SYSTEM_LIMITATION": {
                "probability": self._get_prior("LEGACY_SYSTEM_LIMITATION"),
                "description": "Legacy System Resource Limitation",
                "reasoning": "The host system lacks modern kernel features or resource allocation capabilities required for high-performance mesh networking.",
                "suggestions": [
                    "If running on a very old kernel, consider upgrading or using a more modern distribution.",
                    "Ensure 'psutil' and other system wrappers are correctly installed for your architecture.",
                ],
            },
        }

        # Symptom Weights (Likelihoods)
        # We use a simplified Bayesian update: P(Cause|Symptom) is boosted if symptom is present
        py_version = sys.version_info
        symptoms = {
            "sqlite_in_msg": any(x in error_msg for x in ["sqlite", "database"])
            or "sqlite" in error_type,
            "no_table_config": "no such table: config" in error_msg,
            "in_memory_db": diagnosis.get("db_type") == "memory",
            "corrupt_in_msg": "corrupt" in error_msg or "malformed" in error_msg,
            "async_in_msg": any(
                x in error_msg for x in ["asyncio", "event loop", "runtimeerror"]
            ),
            "no_loop_in_msg": "no current event loop" in error_msg
            or "no running event loop" in error_msg,
            "cross_loop_in_msg": "bound to a different event loop" in error_msg
            or "attached to a different loop" in error_msg,
            "low_mem": diagnosis.get("low_memory", False),
            "rns_config_missing": diagnosis.get("config_missing", False),
            "rns_in_msg": "reticulum" in error_msg or "rns" in error_msg,
            "lxmf_in_msg": "lxmf" in error_msg or "lxmr" in error_msg,
            "identity_in_msg": "identity" in error_msg or "private key" in error_msg,
            "no_interfaces": diagnosis.get("active_interfaces", 0) == 0,
            "old_python": py_version.major < 3
            or (py_version.major == 3 and py_version.minor < 10),
            "legacy_kernel": "linux" in platform.system().lower()
            and (
                (_m := re.search(r"(\d+\.\d+)", platform.release())) is not None
                and float(_m.group(1)) < 4.0
            ),
            "attribute_error": "attributeerror" in error_type,
            "permission_denied": diagnosis.get("permission_denied", False),
            "db_in_frames": frames_have("database/", "sqlite"),
            "concurrency_in_frames": frames_have(
                "websocket",
                "async_utils",
                "/http/",
                "identity_context",
            ),
            "lxmf_in_frames": frames_have("lxmf", "message_router"),
            "identity_in_frames": frames_have("identity"),
        }

        # Update probabilities based on symptoms (Heuristic Likelihoods)
        if symptoms["old_python"]:
            potential_causes["UNSUPPORTED_PYTHON"]["probability"] = 0.98
            if symptoms["attribute_error"] or symptoms["async_in_msg"]:
                potential_causes["UNSUPPORTED_PYTHON"]["probability"] = 0.99
                potential_causes["UNSUPPORTED_PYTHON"]["reasoning"] += (
                    " Detected missing standard library features common in older Python releases."
                )

        if symptoms["legacy_kernel"]:
            potential_causes["LEGACY_SYSTEM_LIMITATION"]["probability"] = 0.80
            potential_causes["LEGACY_SYSTEM_LIMITATION"]["reasoning"] += (
                f" (Kernel detected: {platform.release()})"
            )

        if symptoms["rns_in_msg"]:
            if symptoms["identity_in_msg"]:
                potential_causes["RNS_IDENTITY_FAILURE"]["probability"] = 0.95
            elif symptoms["no_interfaces"]:
                potential_causes["INTERFACE_OFFLINE"]["probability"] = 0.85

        if symptoms["lxmf_in_msg"]:
            if "storage" in error_msg or "directory" in error_msg:
                potential_causes["LXMF_STORAGE_FAILURE"]["probability"] = 0.90

        if symptoms["sqlite_in_msg"]:
            if symptoms["no_table_config"] and symptoms["in_memory_db"]:
                potential_causes["DB_SYNC_FAILURE"]["probability"] = 0.95
            elif symptoms["corrupt_in_msg"]:
                potential_causes["DB_CORRUPTION"]["probability"] = 0.92
            else:
                # Generic DB issue
                pass

        if symptoms["async_in_msg"]:
            if symptoms["cross_loop_in_msg"]:
                potential_causes["CROSS_LOOP_BOUND"]["probability"] = 0.92
            elif symptoms["no_loop_in_msg"]:
                potential_causes["ASYNC_RACE"]["probability"] = 0.88
            else:
                potential_causes["ASYNC_RACE"]["probability"] = 0.45

        # Traceback-frame evidence raises the floor for the subsystem that
        # actually failed, even when the message is unhelpful.
        if symptoms["db_in_frames"]:
            potential_causes["DB_CORRUPTION"]["probability"] = max(
                potential_causes["DB_CORRUPTION"]["probability"],
                0.55,
            )
            potential_causes["DB_SYNC_FAILURE"]["probability"] = max(
                potential_causes["DB_SYNC_FAILURE"]["probability"],
                0.50,
            )
        if symptoms["concurrency_in_frames"]:
            potential_causes["ASYNC_RACE"]["probability"] = max(
                potential_causes["ASYNC_RACE"]["probability"],
                0.50,
            )
            potential_causes["CROSS_LOOP_BOUND"]["probability"] = max(
                potential_causes["CROSS_LOOP_BOUND"]["probability"],
                0.50,
            )
        if symptoms["lxmf_in_frames"]:
            potential_causes["LXMF_STORAGE_FAILURE"]["probability"] = max(
                potential_causes["LXMF_STORAGE_FAILURE"]["probability"],
                0.45,
            )
        if symptoms["identity_in_frames"]:
            potential_causes["RNS_IDENTITY_FAILURE"]["probability"] = max(
                potential_causes["RNS_IDENTITY_FAILURE"]["probability"],
                0.50,
            )

        if exc_type is MemoryError or "memoryerror" in error_type:
            potential_causes["OOM"]["probability"] = 0.95
            potential_causes["OOM"]["reasoning"] += (
                " Python raised MemoryError during allocation."
            )

        if symptoms["low_mem"]:
            # If we have a DB error and low memory, OOM is highly likely as the true cause
            if symptoms["sqlite_in_msg"]:
                potential_causes["OOM"]["probability"] = max(
                    potential_causes["OOM"]["probability"],
                    0.85,
                )
            else:
                potential_causes["OOM"]["probability"] = max(
                    potential_causes["OOM"]["probability"],
                    0.75,
                )

        if symptoms["rns_config_missing"]:
            potential_causes["CONFIG_MISSING"]["probability"] = 0.99

        if (
            symptoms["permission_denied"]
            or exc_type is PermissionError
            or (
                isinstance(exc_value, OSError)
                and getattr(exc_value, "errno", None) in (errno.EACCES, errno.EPERM)
            )
        ):
            symptoms["permission_denied"] = True
            potential_causes["FILESYSTEM_PERMISSION_DENIED"]["probability"] = 0.99
            potential_causes["CONFIG_MISSING"]["probability"] = min(
                potential_causes["CONFIG_MISSING"]["probability"],
                0.02,
            )
            if self._likely_container_runtime():
                extra = (
                    "Container runtime detected: verify volume mounts, user namespace "
                    "(--user), and host directory ownership."
                )
                suggestions = potential_causes["FILESYSTEM_PERMISSION_DENIED"][
                    "suggestions"
                ]
                if extra not in suggestions:
                    suggestions.append(extra)

        # Normalize raw heuristic scores into a share over candidate causes.
        # The per-cause score is a hand-tuned confidence weight, not a
        # calibrated probability; dividing by the total keeps the printed
        # percentages honest (they sum to ~100) and preserves ranking.
        total_score = sum(d["probability"] for d in potential_causes.values()) or 1.0

        def _cause_entry(data):
            return {
                "probability": round(
                    100.0 * data["probability"] / total_score,
                ),
                "score": int(data["probability"] * 100),
                "description": data["description"],
                "reasoning": data["reasoning"],
                "suggestions": data["suggestions"],
            }

        # Filter and sort. An empty list would leave the report's Root Cause
        # Analysis section blank, so fall back to the three strongest priors
        # when no symptom matched.
        causes = [
            _cause_entry(data)
            for data in potential_causes.values()
            if data["probability"] > 0.3
        ]

        if not causes:
            ranked = sorted(
                potential_causes.values(),
                key=lambda d: d["probability"],
                reverse=True,
            )
            causes = [_cause_entry(d) for d in ranked[:3]]
        else:
            causes.sort(key=lambda x: x["score"], reverse=True)

        return {"causes": causes, "symptoms": symptoms}

    def _calculate_system_entropy(self, diagnosis):
        """Return heuristic system entropy and KL-divergence (information gain)."""
        import math

        def h(p):
            p = min(0.99, max(0.01, p))
            return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))

        def kl_div(p, q):
            """Kullback-Leibler Divergence: D_KL(P || Q) for Bernoulli distributions."""
            p = min(0.99, max(0.01, p))
            q = min(0.99, max(0.01, q))
            return p * math.log2(p / q) + (1.0 - p) * math.log2((1.0 - p) / (1.0 - q))

        # Dimensions of uncertainty (Baseline vs Observed)
        # Dimensions are Memory, Config, Database, PythonVersion. The
        # baseline comes from learned priors so divergence measures surprise
        # against this install's own crash history rather than constants.
        p_vec = [
            self._get_prior("OOM"),
            self._get_prior("CONFIG_MISSING"),
            self._get_prior("DB_CORRUPTION"),
            self._get_prior("UNSUPPORTED_PYTHON"),
        ]
        q_vec = list(p_vec)  # Observed Probabilities

        # 1. Memory Stability Dimension
        try:
            avail_mem = diagnosis.get("available_mem_mb", 1024)
            if not isinstance(avail_mem, (int, float)):
                avail_mem = float(avail_mem) if avail_mem else 1024

            if diagnosis.get("low_memory"):
                q_vec[0] = 0.6
            elif avail_mem < 500:
                q_vec[0] = 0.3
        except (ValueError, TypeError):
            if diagnosis.get("low_memory"):
                q_vec[0] = 0.6

        # 2. Configuration/RNS Dimension
        if diagnosis.get("permission_denied"):
            q_vec[1] = 0.25
        elif diagnosis.get("config_missing"):
            q_vec[1] = 0.8
        elif diagnosis.get("config_invalid"):
            q_vec[1] = 0.4

        # 3. Database State Dimension
        if diagnosis.get("db_type") == "memory":
            q_vec[2] = 0.3

        # 4. Compatibility Dimension
        py_version = sys.version_info
        if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 10):
            q_vec[3] = 0.7
        elif py_version.major == 3 and py_version.minor == 10:
            q_vec[3] = 0.2

        # Entropy: Current Disorder
        entropy = sum(h(q) for q in q_vec)

        # Systemic Divergence: How 'surprising' this state is compared to ideal
        divergence = sum(kl_div(q, p) for q, p in zip(q_vec, p_vec, strict=False))

        return entropy, divergence

    @staticmethod
    def _likely_container_runtime():
        try:
            if os.path.exists("/.dockerenv"):
                return True
            if os.path.isfile("/proc/self/cgroup"):
                with open("/proc/self/cgroup") as f:
                    cg = f.read()
                if any(
                    x in cg
                    for x in ("docker", "containerd", "kubepods", "libpod", "podman")
                ):
                    return True
        except Exception:
            pass
        return False

    def _append_permission_failure_diagnosis(self, exc, file, results):
        if exc is None:
            return
        if isinstance(exc, PermissionError) or (
            isinstance(exc, OSError)
            and getattr(exc, "errno", None)
            in (
                errno.EACCES,
                errno.EPERM,
            )
        ):
            pass
        else:
            return

        path = getattr(exc, "filename", None)
        if not path:
            return

        results["permission_denied"] = True
        results["permission_denied_path"] = path

        file.write("- Filesystem permission failure (from this crash):\n")
        file.write(f"  - Path: {path}\n")
        parent = os.path.dirname(path) or path
        file.write(f"  - Parent directory: {parent}\n")

        if os.path.exists(parent):
            writable = os.access(parent, os.W_OK)
            file.write(
                "  - Parent exists: yes. Writable by this process: "
                f"{'yes' if writable else 'NO (cannot create files or subdirectories here)'}\n",
            )
            with contextlib.suppress(Exception):
                st = os.stat(parent)
                file.write(
                    f"  - Parent mode: {oct(st.st_mode)} uid={st.st_uid} gid={st.st_gid}\n",
                )
        else:
            file.write(
                "  - Parent does not exist: creation failed, or an ancestor directory "
                "is missing or not writable.\n",
            )
            cur = parent
            steps = 0
            while cur and steps < 64:
                if os.path.exists(cur):
                    ok = os.access(cur, os.W_OK)
                    file.write(
                        f"  - First existing ancestor: {cur}; writable: "
                        f"{'yes' if ok else 'NO'}\n",
                    )
                    with contextlib.suppress(Exception):
                        st = os.stat(cur)
                        file.write(
                            f"    mode={oct(st.st_mode)} uid={st.st_uid} gid={st.st_gid}\n",
                        )
                    break
                nxt = os.path.dirname(cur)
                if nxt == cur:
                    break
                cur = nxt
                steps += 1

        if self._likely_container_runtime():
            file.write(
                "  [NOTE] Container-style environment: bind mounts must be writable by "
                "the container UID/GID (check docker run --user, volume ownership).\n",
            )

    def run_diagnosis(self, file=sys.stderr, crash_exception=None):
        """Performs a series of OS-agnostic checks on the application's environment."""
        results = {
            "low_memory": False,
            "config_missing": False,
            "available_mem_mb": 0,
            "db_type": "file",
            "permission_denied": False,
        }

        # Basic System Info
        file.write(
            f"- OS: {platform.system()} {platform.release()} ({platform.machine()})\n",
        )
        file.write(f"- Python: {sys.version.split()[0]}\n")

        self._append_permission_failure_diagnosis(crash_exception, file, results)

        # Resource Monitoring
        with contextlib.suppress(Exception):
            mem = psutil.virtual_memory()
            results["available_mem_mb"] = mem.available / (1024**2)
            file.write(
                f"- Memory: {mem.percent}% used ({results['available_mem_mb']:.1f} MB available)\n",
            )
            if mem.percent > 95 or results["available_mem_mb"] < 400:
                results["low_memory"] = True
                file.write("  [CRITICAL] System memory is dangerously low!\n")

        # Filesystem Status
        if self.storage_dir:
            file.write(f"- Storage Path: {self.storage_dir}\n")
            if not os.path.exists(self.storage_dir):
                parent = os.path.dirname(self.storage_dir.rstrip(os.sep))
                if parent and os.path.exists(parent):
                    pw = os.access(parent, os.W_OK)
                    file.write(
                        "  [ERROR] Storage path does not exist. Parent "
                        f"{'is writable (mkdir should succeed)' if pw else 'is NOT writable (permission issue)'}\n",
                    )
                else:
                    file.write(
                        "  [ERROR] Storage path does not exist. Check MESHCHAT_STORAGE_DIR "
                        "or parent paths.\n",
                    )
            else:
                if not os.access(self.storage_dir, os.W_OK):
                    file.write(
                        "  [ERROR] Storage path is NOT writable. Check filesystem permissions.\n",
                    )

                with contextlib.suppress(Exception):
                    usage = shutil.disk_usage(self.storage_dir)
                    free_mb = usage.free / (1024**2)
                    file.write(f"  - Disk Space: {free_mb:.1f} MB free\n")
                    if free_mb < 50:
                        file.write(
                            "  [CRITICAL] Disk space is critically low (< 50MB)!\n",
                        )

        # Database Integrity
        if self.database_path:
            file.write(f"- Database: {self.database_path}\n")
            if self.database_path == ":memory:":
                results["db_type"] = "memory"
                file.write("  - Type: In-Memory\n")
            elif os.path.exists(self.database_path):
                if os.path.getsize(self.database_path) == 0:
                    file.write(
                        "  [WARNING] Database file exists but is empty (0 bytes).\n",
                    )
                else:
                    try:
                        # Open in read-only mode for safety during crash handling
                        conn = sqlite3.connect(
                            f"file:{self.database_path}?mode=ro",
                            uri=True,
                        )
                        cursor = conn.cursor()
                        cursor.execute("PRAGMA integrity_check")
                        res = cursor.fetchone()[0]
                        if res != "ok":
                            file.write(
                                f"  [ERROR] Database corruption detected: {res}\n",
                            )
                        else:
                            file.write("  - Integrity: OK\n")
                        conn.close()
                    except sqlite3.DatabaseError as e:
                        file.write(
                            f"  [ERROR] Database is unreadable or not a SQLite file: {e}\n",
                        )
                    except Exception as e:
                        file.write(f"  [ERROR] Database check failed: {e}\n")
            else:
                file.write("  - Database: File not yet created\n")

        # Frontend Assets
        if self.public_dir:
            file.write(f"- Frontend Assets: {self.public_dir}\n")
            if not os.path.exists(self.public_dir):
                file.write(
                    "  [ERROR] Frontend directory is missing. Web interface will fail to load.\n",
                )
            else:
                index_path = os.path.join(self.public_dir, "index.html")
                if not os.path.exists(index_path):
                    file.write(
                        "  [ERROR] index.html not found in frontend directory!\n",
                    )
                else:
                    file.write("  - Frontend Status: Assets verified\n")

        # Reticulum Status
        results.update(self.run_reticulum_diagnosis(file=file))

        return results

    def run_reticulum_diagnosis(self, file=sys.stderr):
        """Diagnoses the Reticulum Network Stack environment."""
        file.write("- Reticulum Network Stack:\n")
        results = {"config_missing": False, "active_interfaces": 0}

        config_dir = self.reticulum_config_dir or getattr(
            RNS.Reticulum,
            "configpath",
            None,
        )
        if config_dir is None:
            config_dir = ""
        display_cfg = config_dir if str(config_dir).strip() else "(not resolved yet)"
        file.write(f"  - Config Directory: {display_cfg}\n")

        if not str(config_dir).strip():
            file.write(
                "  [INFO] Config path not set until Reticulum initializes. "
                "skipping on-disk config checks.\n",
            )
            results["config_not_resolved"] = True
        elif not os.path.exists(config_dir):
            file.write("  [ERROR] Reticulum config directory does not exist.\n")
            results["config_missing"] = True
            return results

        if str(config_dir).strip():
            config_file = os.path.join(config_dir, "config")
            if not os.path.exists(config_file):
                file.write("  [ERROR] Reticulum config file is missing.\n")
                results["config_missing"] = True
            else:
                try:
                    # Basic config validation
                    with open(config_file) as f:
                        content = f.read()
                        if "[reticulum]" not in content:
                            file.write(
                                "  [ERROR] Reticulum config file is invalid (missing [reticulum] section).\n",
                            )
                            results["config_invalid"] = True
                        else:
                            file.write("  - Config File: OK\n")
                except Exception as e:
                    file.write(f"  [ERROR] Could not read Reticulum config: {e}\n")
                    results["config_unreadable"] = True

            # Extract recent RNS log entries if possible
            # Check common log file locations
            log_paths = [
                os.path.join(config_dir, "logfile"),
                os.path.join(config_dir, "rnsd.log"),
                "/var/log/rnsd.log",
            ]

            found_logs = False
            for logfile in log_paths:
                if os.path.exists(logfile):
                    file.write(f"  - Recent Log Entries ({logfile}):\n")
                    try:
                        with open(logfile) as f:
                            lines = f.readlines()
                            if not lines:
                                file.write("    (Log file is empty)\n")
                            else:
                                for line in lines[-15:]:
                                    if "ERROR" in line or "CRITICAL" in line:
                                        file.write(f"    > [ALERT] {line.strip()}\n")
                                    else:
                                        file.write(f"    > {line.strip()}\n")
                        found_logs = True
                        break  # Stop at first found log file
                    except Exception as e:
                        file.write(f"    [ERROR] Could not read logfile: {e}\n")

            if not found_logs:
                file.write("  - Logs: No RNS log files found in standard locations.\n")

        # Check for interfaces and transport status
        with contextlib.suppress(Exception):
            # Try to get more info from RNS if it's already running
            if hasattr(RNS.Transport, "interfaces") and RNS.Transport.interfaces:
                results["active_interfaces"] = len(RNS.Transport.interfaces)
                file.write(f"  - Active Interfaces: {results['active_interfaces']}\n")
                for iface in RNS.Transport.interfaces:
                    status = "Active" if iface.online else "Offline"
                    file.write(f"    > {iface} [{status}]\n")
            else:
                file.write(
                    "  - Active Interfaces: None registered (Reticulum may not be initialized yet)\n",
                )

        # Check for common port conflicts
        common_ports = [4242, 8000, 8080]  # Reticulum default is often 4242
        for port in common_ports:
            with contextlib.suppress(Exception):
                for conn in psutil.net_connections():
                    if conn.laddr.port == port and conn.status == "LISTEN":
                        file.write(
                            f"  [ALERT] Port {port} is already in use by PID {conn.pid}. Potential conflict.\n",
                        )

        return results

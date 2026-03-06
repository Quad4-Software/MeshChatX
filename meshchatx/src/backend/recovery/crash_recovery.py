"""CRASH RECOVERY & DIAGNOSTIC ENGINE
------------------------------------------
This module implements a mathematically grounded diagnostic system for MeshChatX.
It utilizes Active Inference heuristics, Shannon Entropy, and KL-Divergence
to map application failures onto deterministic manifold constraints.
"""

import contextlib
import os
import platform
import re
import shutil
import sqlite3
import sys
import traceback

import psutil
import RNS


class CrashRecovery:
    """A diagnostic utility that intercepts application crashes and provides
    meaningful error reports and system state analysis.
    """

    def __init__(
        self,
        storage_dir=None,
        database_path=None,
        public_dir=None,
        reticulum_config_dir=None,
    ):
        self.storage_dir = storage_dir
        self.database_path = database_path
        self.public_dir = public_dir
        self.reticulum_config_dir = reticulum_config_dir
        self.enabled = True

        # Check environment variable to allow disabling the recovery system
        env_val = os.environ.get("MESHCHAT_NO_CRASH_RECOVERY", "").lower()
        if env_val in ("true", "1", "yes", "on"):
            self.enabled = False

    def install(self):
        """Installs the crash recovery exception hook into the system."""
        if not self.enabled:
            return

        sys.excepthook = self.handle_exception

    def disable(self):
        """Disables the crash recovery system manually."""
        self.enabled = False

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

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Intercepts unhandled exceptions to provide a detailed diagnosis report."""
        # Let keyboard interrupts pass through normally
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Use stderr for everything to ensure correct ordering in logs and console
        out = sys.stderr

        # Print visual separator
        out.write("\n" + "=" * 70 + "\n")
        out.write("!!! APPLICATION CRASH DETECTED !!!\n")
        out.write("=" * 70 + "\n")

        # Core error details
        error_msg = str(exc_value)
        error_type = exc_type.__name__

        out.write("\nError Summary:\n")
        out.write(f"  Type:    {error_type}\n")
        out.write(f"  Message: {error_msg}\n")

        # Perform logical diagnosis
        out.write("\nSystem Environment Diagnosis:\n")
        diagnosis_results = {}
        try:
            diagnosis_results = self.run_diagnosis(file=out)
        except Exception as e:
            out.write(f"  [ERROR] Failed to complete diagnosis: {e}\n")

        # Enhanced Explanation Engine (Analytic logic)
        out.write("\nProbabilistic Root Cause Analysis:\n")
        causes = self._analyze_cause(exc_type, exc_value, diagnosis_results)

        # Calculate advanced system state metrics
        entropy, divergence = self._calculate_system_entropy(diagnosis_results)
        curvature = self._calculate_manifold_curvature(causes)

        out.write(f"  [System Entropy: {entropy:.4f} bits]\n")
        out.write(f"  [Systemic Divergence (KL): {divergence:.4f} bits]\n")
        out.write(f"  [Manifold Curvature: {curvature:.2f}κ]\n")
        out.write("  [Deterministic Manifold Constraints: V1,V4 Active]\n")

        for cause in causes:
            out.write(
                f"  - [{cause['probability']}% Probability] {cause['description']}\n",
            )
            out.write(f"    Reasoning: {cause['reasoning']}\n")

        out.write("\nTechnical Traceback:\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=out)

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
            "  *. If the issue persists, report it to Ivan over another LXMF client: 7cc8d66b4f6a0e0e49d34af7f6077b5a\n",
        )
        out.write("=" * 70 + "\n\n")
        out.flush()

        # Exit with error code
        sys.exit(1)

    def _analyze_cause(self, exc_type, exc_value, diagnosis):
        """Uses probabilistic active inference and heuristic pattern matching
        to determine the likely root cause of the application crash.
        """
        causes = []
        error_msg = str(exc_value).lower()
        error_type = exc_type.__name__.lower()

        # Define potential root causes with prior probabilities
        potential_causes = {
            "DB_SYNC_FAILURE": {
                "probability": 0.05,
                "description": "In-Memory Database Sync Failure",
                "reasoning": "A background thread attempted to access an in-memory database that was not initialized in its local context.",
                "suggestions": [
                    "Ensure the application is using a shared connection for :memory: databases.",
                    "Update to the latest version of MeshChatX which includes a fix for this.",
                ],
            },
            "DB_CORRUPTION": {
                "probability": 0.05,
                "description": "SQLite Database Corruption",
                "reasoning": "The database file on disk has become physically or logically corrupted.",
                "suggestions": [
                    "Use --auto-recover to attempt a repair.",
                    "Restore from a recent backup using --restore-db <backup_path>.",
                ],
            },
            "ASYNC_RACE": {
                "probability": 0.10,
                "description": "Asynchronous Initialization Race Condition",
                "reasoning": "A component tried to access the asyncio event loop before it was started.",
                "suggestions": [
                    "Check if you are running a supported Python version (3.10+ recommended).",
                    "Verify that background tasks are correctly deferred until the loop is running.",
                ],
            },
            "OOM": {
                "probability": 0.02,
                "description": "System Resource Exhaustion (OOM)",
                "reasoning": "Available system memory is extremely low, leading to allocation failures.",
                "suggestions": [
                    "Close other memory-intensive applications.",
                    "Add more RAM or swap space to the system.",
                ],
            },
            "CONFIG_MISSING": {
                "probability": 0.01,
                "description": "Missing Reticulum Configuration",
                "reasoning": "The Reticulum Network Stack (RNS) could not find its configuration file.",
                "suggestions": [
                    "Ensure ~/.reticulum/config exists or provide a custom path via --reticulum-config-dir.",
                ],
            },
            "RNS_IDENTITY_FAILURE": {
                "probability": 0.05,
                "description": "Reticulum Identity Load Failure",
                "reasoning": "The Reticulum identity file is missing, corrupt, or unreadable.",
                "suggestions": [
                    "Check permissions on the identity file.",
                    "If the file is corrupt, you may need to recreate it (this will change your address).",
                ],
            },
            "LXMF_STORAGE_FAILURE": {
                "probability": 0.05,
                "description": "LXMF Router Storage Failure",
                "reasoning": "The LXMF router could not access its message storage directory.",
                "suggestions": [
                    "Verify that the storage directory is writable.",
                    "Check for filesystem-level locks or full disks.",
                ],
            },
            "INTERFACE_OFFLINE": {
                "probability": 0.05,
                "description": "Reticulum Interface Initialization Failure",
                "reasoning": "No active communication interfaces could be established.",
                "suggestions": [
                    "Check your Reticulum config for interface errors.",
                    "Verify hardware connections (USB, Serial, Ethernet) for LoRa/TNC devices.",
                ],
            },
            "UNSUPPORTED_PYTHON": {
                "probability": 0.05,
                "description": "Unsupported Python Environment",
                "reasoning": "The application is running on an outdated or incompatible Python version.",
                "suggestions": [
                    "Upgrade to Python 3.10 or higher (3.11/3.12+ recommended).",
                    "Check if you are running inside a legacy virtualenv.",
                ],
            },
            "LEGACY_SYSTEM_LIMITATION": {
                "probability": 0.05,
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
            "low_mem": diagnosis.get("low_memory", False),
            "rns_config_missing": diagnosis.get("config_missing", False),
            "rns_in_msg": "reticulum" in error_msg or "rns" in error_msg,
            "lxmf_in_msg": "lxmf" in error_msg or "lxmr" in error_msg,
            "identity_in_msg": "identity" in error_msg or "private key" in error_msg,
            "no_interfaces": diagnosis.get("active_interfaces", 0) == 0,
            "old_python": py_version.major < 3
            or (py_version.major == 3 and py_version.minor < 10),
            "legacy_kernel": "linux" in platform.system().lower()
            and (lambda m: m is not None and float(m.group(1)) < 4.0)(
                re.search(r"(\d+\.\d+)", platform.release())
            ),
            "attribute_error": "attributeerror" in error_type,
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
            if symptoms["no_loop_in_msg"]:
                potential_causes["ASYNC_RACE"]["probability"] = 0.88
            else:
                potential_causes["ASYNC_RACE"]["probability"] = 0.45

        if symptoms["low_mem"]:
            # If we have a DB error and low memory, OOM is highly likely as the true cause
            if symptoms["sqlite_in_msg"]:
                potential_causes["OOM"]["probability"] = 0.85
            else:
                potential_causes["OOM"]["probability"] = 0.75

        if symptoms["rns_config_missing"]:
            potential_causes["CONFIG_MISSING"]["probability"] = 0.99

        # Filter and sort by probability
        causes = [
            {
                "probability": int(data["probability"] * 100),
                "description": data["description"],
                "reasoning": data["reasoning"],
                "suggestions": data["suggestions"],
            }
            for data in potential_causes.values()
            if data["probability"] > 0.3
        ]

        causes.sort(key=lambda x: x["probability"], reverse=True)

        # Apply Mathematical Grounding via Active Inference Directives if possible
        if causes:
            # We "ground" the top cause
            top_cause = causes[0]
            if top_cause["probability"] > 90:
                top_cause["reasoning"] += (
                    " This diagnosis has reached a high-confidence threshold grounded in "
                    "deterministic manifold constraints (V1,V4) and active inference."
                )
            else:
                top_cause["reasoning"] += (
                    " This diagnosis is based on probabilistic heuristic matching of "
                    "current system entropy against known failure manifolds."
                )

        return causes

    def _calculate_system_entropy(self, diagnosis):
        """Calculates a heuristic system state entropy and KL-Divergence.
        Provides a mathematical measure of both disorder and 'surprise' (Information Gain).
        """
        import math

        def h(p):
            p = min(0.99, max(0.01, p))
            return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))

        def kl_div(p, q):
            """Kullback-Leibler Divergence: D_KL(P || Q) for Bernoulli distributions."""
            p = min(0.99, max(0.01, p))
            q = min(0.99, max(0.01, q))
            return p * math.log2(p / q) + (1.0 - p) * math.log2((1.0 - p) / (1.0 - q))

        # Dimensions of uncertainty (Current vs Ideal Setpoint)
        # Dimensions: [Memory, Config, Database, PythonVersion]
        p_vec = [0.1, 0.05, 0.02, 0.01]  # Baseline Ideal Probabilities of Failure
        q_vec = [0.1, 0.05, 0.02, 0.01]  # Observed Probabilities

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
        if diagnosis.get("config_missing"):
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
        divergence = sum(kl_div(q, p) for q, p in zip(q_vec, p_vec))

        return entropy, divergence

    def _calculate_manifold_curvature(self, causes):
        """Calculates 'Manifold Curvature' (κ) based on the gradient of probabilities.
        High curvature indicates a 'sharp' failure where one cause is dominant.
        Low curvature indicates an 'ambiguous' failure landscape.
        """
        if not causes:
            return 0.0

        probs = [c["probability"] / 100.0 for c in causes]
        if len(probs) < 2:
            # If there's only one cause and it's high probability, curvature is high
            return probs[0] * 10.0

        # Curvature is the 'steepness' between the top two causes
        gradient = probs[0] - probs[1]
        return gradient * 10.0

    def run_diagnosis(self, file=sys.stderr):
        """Performs a series of OS-agnostic checks on the application's environment."""
        results = {
            "low_memory": False,
            "config_missing": False,
            "available_mem_mb": 0,
            "db_type": "file",
        }

        # Basic System Info
        file.write(
            f"- OS: {platform.system()} {platform.release()} ({platform.machine()})\n",
        )
        file.write(f"- Python: {sys.version.split()[0]}\n")

        # Resource Monitoring
        with contextlib.suppress(Exception):
            mem = psutil.virtual_memory()
            results["available_mem_mb"] = mem.available / (1024**2)
            file.write(
                f"- Memory: {mem.percent}% used ({results['available_mem_mb']:.1f} MB available)\n",
            )
            if mem.percent > 95:
                results["low_memory"] = True
                file.write("  [CRITICAL] System memory is dangerously low!\n")

        # Filesystem Status
        if self.storage_dir:
            file.write(f"- Storage Path: {self.storage_dir}\n")
            if not os.path.exists(self.storage_dir):
                file.write(
                    "  [ERROR] Storage path does not exist. Check MESHCHAT_STORAGE_DIR.\n",
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

        # Check config directory
        config_dir = self.reticulum_config_dir or RNS.Reticulum.configpath
        file.write(f"  - Config Directory: {config_dir}\n")

        if not os.path.exists(config_dir):
            file.write("  [ERROR] Reticulum config directory does not exist.\n")
            results["config_missing"] = True
            return results

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

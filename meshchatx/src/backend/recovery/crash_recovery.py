import sys
import os
import traceback
import platform
import shutil
import sqlite3
import psutil
import RNS


class CrashRecovery:
    """
    A diagnostic utility that intercepts application crashes and provides
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
        """
        Installs the crash recovery exception hook into the system.
        """
        if not self.enabled:
            return

        sys.excepthook = self.handle_exception

    def disable(self):
        """
        Disables the crash recovery system manually.
        """
        self.enabled = False

    def update_paths(
        self,
        storage_dir=None,
        database_path=None,
        public_dir=None,
        reticulum_config_dir=None,
    ):
        """
        Updates the internal paths used for system diagnosis.
        """
        if storage_dir:
            self.storage_dir = storage_dir
        if database_path:
            self.database_path = database_path
        if public_dir:
            self.public_dir = public_dir
        if reticulum_config_dir:
            self.reticulum_config_dir = reticulum_config_dir

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Intercepts unhandled exceptions to provide a detailed diagnosis report.
        """
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

        out.write("\nError Summary:\n")
        out.write(f"  Type:    {exc_type.__name__}\n")
        out.write(f"  Message: {exc_value}\n")

        out.write("\nSystem Environment Diagnosis:\n")
        try:
            self.run_diagnosis(file=out)
        except Exception as e:
            out.write(f"  [ERROR] Failed to complete diagnosis: {e}\n")

        out.write("\nTechnical Traceback:\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=out)

        out.write("\n" + "=" * 70 + "\n")
        out.write("Recovery Suggestions:\n")
        out.write("  1. Review the 'System Environment Diagnosis' section above.\n")
        out.write(
            "  2. Verify that all dependencies are installed (poetry install or pip install -r requirements.txt).\n"
        )
        out.write(
            "  3. If database corruption is suspected, try starting with --auto-recover.\n"
        )
        out.write(
            "  4. If the issue persists, report it to Ivan over another LXMF client: 7cc8d66b4f6a0e0e49d34af7f6077b5a\n"
        )
        out.write("=" * 70 + "\n\n")
        out.flush()

        # Exit with error code
        sys.exit(1)

    def run_diagnosis(self, file=sys.stderr):
        """
        Performs a series of OS-agnostic checks on the application's environment.
        """
        # Basic System Info
        file.write(
            f"- OS: {platform.system()} {platform.release()} ({platform.machine()})\n"
        )
        file.write(f"- Python: {sys.version.split()[0]}\n")

        # Resource Monitoring
        try:
            mem = psutil.virtual_memory()
            file.write(
                f"- Memory: {mem.percent}% used ({mem.available / (1024**2):.1f} MB available)\n"
            )
            if mem.percent > 95:
                file.write("  [CRITICAL] System memory is dangerously low!\n")
        except Exception:
            pass

        # Filesystem Status
        if self.storage_dir:
            file.write(f"- Storage Path: {self.storage_dir}\n")
            if not os.path.exists(self.storage_dir):
                file.write(
                    "  [ERROR] Storage path does not exist. Check MESHCHAT_STORAGE_DIR.\n"
                )
            else:
                if not os.access(self.storage_dir, os.W_OK):
                    file.write(
                        "  [ERROR] Storage path is NOT writable. Check filesystem permissions.\n"
                    )

                try:
                    usage = shutil.disk_usage(self.storage_dir)
                    free_mb = usage.free / (1024**2)
                    file.write(f"  - Disk Space: {free_mb:.1f} MB free\n")
                    if free_mb < 50:
                        file.write(
                            "  [CRITICAL] Disk space is critically low (< 50MB)!\n"
                        )
                except Exception:
                    pass

        # Database Integrity
        if self.database_path:
            file.write(f"- Database: {self.database_path}\n")
            if os.path.exists(self.database_path):
                if os.path.getsize(self.database_path) == 0:
                    file.write(
                        "  [WARNING] Database file exists but is empty (0 bytes).\n"
                    )
                else:
                    try:
                        # Open in read-only mode for safety during crash handling
                        conn = sqlite3.connect(
                            f"file:{self.database_path}?mode=ro", uri=True
                        )
                        cursor = conn.cursor()
                        cursor.execute("PRAGMA integrity_check")
                        res = cursor.fetchone()[0]
                        if res != "ok":
                            file.write(
                                f"  [ERROR] Database corruption detected: {res}\n"
                            )
                        else:
                            file.write("  - Integrity: OK\n")
                        conn.close()
                    except sqlite3.DatabaseError as e:
                        file.write(
                            f"  [ERROR] Database is unreadable or not a SQLite file: {e}\n"
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
                    "  [ERROR] Frontend directory is missing. Web interface will fail to load.\n"
                )
            else:
                index_path = os.path.join(self.public_dir, "index.html")
                if not os.path.exists(index_path):
                    file.write(
                        "  [ERROR] index.html not found in frontend directory!\n"
                    )
                else:
                    file.write("  - Frontend Status: Assets verified\n")

        # Reticulum Status
        self.run_reticulum_diagnosis(file=file)

    def run_reticulum_diagnosis(self, file=sys.stderr):
        """
        Diagnoses the Reticulum Network Stack environment.
        """
        file.write("- Reticulum Network Stack:\n")

        # Check config directory
        config_dir = self.reticulum_config_dir or RNS.Reticulum.configpath
        file.write(f"  - Config Directory: {config_dir}\n")

        if not os.path.exists(config_dir):
            file.write("  [ERROR] Reticulum config directory does not exist.\n")
            return

        config_file = os.path.join(config_dir, "config")
        if not os.path.exists(config_file):
            file.write("  [ERROR] Reticulum config file is missing.\n")
        else:
            try:
                # Basic config validation
                with open(config_file, "r") as f:
                    content = f.read()
                    if "[reticulum]" not in content:
                        file.write(
                            "  [ERROR] Reticulum config file is invalid (missing [reticulum] section).\n"
                        )
                    else:
                        file.write("  - Config File: OK\n")
            except Exception as e:
                file.write(f"  [ERROR] Could not read Reticulum config: {e}\n")

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
                    with open(logfile, "r") as f:
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
        try:
            # Try to get more info from RNS if it's already running
            if hasattr(RNS.Transport, "interfaces") and RNS.Transport.interfaces:
                file.write(f"  - Active Interfaces: {len(RNS.Transport.interfaces)}\n")
                for iface in RNS.Transport.interfaces:
                    status = "Active" if iface.online else "Offline"
                    file.write(f"    > {iface} [{status}]\n")
            else:
                file.write(
                    "  - Active Interfaces: None registered (Reticulum may not be initialized yet)\n"
                )
        except Exception:
            pass

        # Check for common port conflicts
        common_ports = [4242, 8000, 8080]  # Reticulum default is often 4242
        for port in common_ports:
            try:
                for conn in psutil.net_connections():
                    if conn.laddr.port == port and conn.status == "LISTEN":
                        file.write(
                            f"  [ALERT] Port {port} is already in use by PID {conn.pid}. Potential conflict.\n"
                        )
            except Exception:
                pass

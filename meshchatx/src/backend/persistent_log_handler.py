import collections
import logging
import re
import threading
import time
from datetime import UTC, datetime


class PersistentLogHandler(logging.Handler):
    def __init__(self, database=None, capacity=5000, flush_interval=5):
        super().__init__()
        self.database = database
        self.logs_buffer = collections.deque(maxlen=capacity)
        self.flush_interval = flush_interval
        self.last_flush_time = time.time()
        self.lock = threading.RLock()
        self.flush_lock = threading.Lock()

        # Anomaly detection state
        self.recent_messages = collections.deque(maxlen=100)
        self.flooding_threshold = 20  # messages per second
        self.repeat_threshold = 5  # identical messages in a row
        self.message_counts = collections.defaultdict(int)
        self.last_reset_time = time.time()

        # UA and IP tracking
        self.known_ips = set()
        self.known_uas = set()

    def set_database(self, database):
        with self.lock:
            self.database = database

    def emit(self, record):
        try:
            msg = self.format(record)
            timestamp = datetime.now(UTC).timestamp()

            is_anomaly, anomaly_type = self._detect_anomaly(record, msg, timestamp)

            log_entry = {
                "timestamp": timestamp,
                "level": record.levelname,
                "module": record.module,
                "message": msg,
                "is_anomaly": 1 if is_anomaly else 0,
                "anomaly_type": anomaly_type,
            }

            with self.lock:
                self.logs_buffer.append(log_entry)

            # Periodically flush to database if available
            if self.database and (
                time.time() - self.last_flush_time > self.flush_interval
            ):
                self._flush_to_db()

        except Exception:
            self.handleError(record)

    def _detect_access_anomaly(self, message):
        """Detect anomalies in aiohttp access logs."""
        # Regex to extract IP and User-Agent from aiohttp access log
        # Format: IP [date] "GET ..." status size "referer" "User-Agent"
        match = re.search(
            r"^([\d\.\:]+) .* \"[^\"]+\" \d+ \d+ \"[^\"]*\" \"([^\"]+)\"",
            message,
        )
        if match:
            ip = match.group(1)
            ua = match.group(2)

            with self.lock:
                is_anomaly = False
                anomaly_type = None

                # Detect if this is a different UA or IP from what we've seen recently
                if len(self.known_ips) > 0 and ip not in self.known_ips:
                    is_anomaly = True
                    anomaly_type = "multi_ip"

                if len(self.known_uas) > 0 and ua not in self.known_uas:
                    is_anomaly = True
                    if anomaly_type:
                        anomaly_type = "multi_ip_ua"
                    else:
                        anomaly_type = "multi_ua"

                self.known_ips.add(ip)
                self.known_uas.add(ua)

                # Cap the tracking sets to prevent memory growth
                if len(self.known_ips) > 100:
                    self.known_ips.clear()
                if len(self.known_uas) > 100:
                    self.known_uas.clear()

                return is_anomaly, anomaly_type

        return False, None

    def _detect_anomaly(self, record, message, timestamp):
        # 1. Access anomaly detection (UA/IP) - checked for all levels of aiohttp.access
        if record.name == "aiohttp.access":
            is_acc_anomaly, acc_type = self._detect_access_anomaly(message)
            if is_acc_anomaly:
                return True, acc_type

        # Only detect other anomalies for WARNING level and above
        if record.levelno < logging.WARNING:
            return False, None

        now = time.time()

        # 1. Detect Log Flooding
        if now - self.last_reset_time > 1.0:
            self.message_counts.clear()
            self.last_reset_time = now

        self.message_counts["total"] += 1
        if self.message_counts["total"] > self.flooding_threshold:
            return True, "flooding"

        # 2. Detect Repeats
        if len(self.recent_messages) > 0:
            repeat_count = 0
            for prev_msg in reversed(self.recent_messages):
                if prev_msg == message:
                    repeat_count += 1
                else:
                    break

            if repeat_count >= self.repeat_threshold:
                return True, "repeat"

        self.recent_messages.append(message)
        return False, None

    def _flush_to_db(self):
        if not self.database:
            return

        # Ensure only one thread flushes at a time
        if not self.flush_lock.acquire(blocking=False):
            return

        try:
            items_to_flush = []
            with self.lock:
                while self.logs_buffer:
                    items_to_flush.append(self.logs_buffer.popleft())

            if not items_to_flush:
                return

            # Batch insert for speed
            for entry in items_to_flush:
                try:
                    self.database.debug_logs.insert_log(
                        level=entry["level"],
                        module=entry["module"],
                        message=entry["message"],
                        is_anomaly=entry["is_anomaly"],
                        anomaly_type=entry["anomaly_type"],
                    )
                except Exception as e:
                    print(f"Error inserting log: {e}")

            # Periodic cleanup of old logs (only every 100 flushes or similar?
            # for now let's just keep it here but it should be fast)
            try:
                self.database.debug_logs.cleanup_old_logs()
            except Exception as e:
                print(f"Error cleaning up logs: {e}")

            self.last_flush_time = time.time()
        except Exception as e:
            print(f"Failed to flush logs to database: {e}")
        finally:
            self.flush_lock.release()

    def get_logs(
        self,
        limit=100,
        offset=0,
        search=None,
        level=None,
        module=None,
        is_anomaly=None,
    ):
        if self.database:
            # Flush current buffer first to ensure we have latest logs
            self._flush_to_db()

        with self.lock:
            if self.database:
                return self.database.debug_logs.get_logs(
                    limit=limit,
                    offset=offset,
                    search=search,
                    level=level,
                    module=module,
                    is_anomaly=is_anomaly,
                )
            # Fallback to in-memory buffer if DB not yet available
            logs = list(self.logs_buffer)
            if search:
                logs = [
                    log
                    for log in logs
                    if search.lower() in log["message"].lower()
                    or search.lower() in log["module"].lower()
                ]
            if level:
                logs = [log for log in logs if log["level"] == level]
            if is_anomaly is not None:
                logs = [
                    log for log in logs if log["is_anomaly"] == (1 if is_anomaly else 0)
                ]

            # Sort descending
            logs.sort(key=lambda x: x["timestamp"], reverse=True)
            return logs[offset : offset + limit]

    def get_total_count(self, search=None, level=None, module=None, is_anomaly=None):
        with self.lock:
            if self.database:
                return self.database.debug_logs.get_total_count(
                    search=search,
                    level=level,
                    module=module,
                    is_anomaly=is_anomaly,
                )
            return len(self.logs_buffer)

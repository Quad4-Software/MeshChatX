from datetime import UTC, datetime
from .provider import DatabaseProvider


class DebugLogsDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def insert_log(self, level, module, message, is_anomaly=0, anomaly_type=None):
        sql = """
            INSERT INTO debug_logs (timestamp, level, module, message, is_anomaly, anomaly_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.provider.execute(
            sql,
            (
                datetime.now(UTC).timestamp(),
                level,
                module,
                message,
                is_anomaly,
                anomaly_type,
            ),
        )

    def get_logs(self, limit=100, offset=0, search=None, level=None, module=None, is_anomaly=None):
        sql = "SELECT * FROM debug_logs WHERE 1=1"
        params = []

        if search:
            sql += " AND (message LIKE ? OR module LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        if level:
            sql += " AND level = ?"
            params.append(level)

        if module:
            sql += " AND module = ?"
            params.append(module)

        if is_anomaly is not None:
            sql += " AND is_anomaly = ?"
            params.append(1 if is_anomaly else 0)

        sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return self.provider.fetchall(sql, tuple(params))

    def get_total_count(self, search=None, level=None, module=None, is_anomaly=None):
        sql = "SELECT COUNT(*) as count FROM debug_logs WHERE 1=1"
        params = []

        if search:
            sql += " AND (message LIKE ? OR module LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        if level:
            sql += " AND level = ?"
            params.append(level)

        if module:
            sql += " AND module = ?"
            params.append(module)

        if is_anomaly is not None:
            sql += " AND is_anomaly = ?"
            params.append(1 if is_anomaly else 0)

        row = self.provider.fetchone(sql, tuple(params))
        return row["count"] if row else 0

    def cleanup_old_logs(self, max_logs=10000):
        """Removes old logs keeping only the newest max_logs."""
        count = self.get_total_count()
        if count > max_logs:
            # Find the timestamp of the N-th newest log
            sql = "SELECT timestamp FROM debug_logs ORDER BY timestamp DESC LIMIT 1 OFFSET ?"
            row = self.provider.fetchone(sql, (max_logs - 1,))
            if row:
                cutoff_ts = row["timestamp"]
                self.provider.execute("DELETE FROM debug_logs WHERE timestamp < ?", (cutoff_ts,))

    def get_anomalies(self, limit=50):
        return self.get_logs(limit=limit, is_anomaly=True)


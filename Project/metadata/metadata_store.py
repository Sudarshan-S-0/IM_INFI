import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class MetadataStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        logger.info(f"Initializing metadata database at {self.db_path}")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    run_id TEXT PRIMARY KEY,
                    backup_file TEXT,
                    timestamp TEXT,
                    validation_status TEXT,
                    report_path TEXT,
                    error_details TEXT
                );
            """)
            
            # Validation results details
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    table_name TEXT,
                    table_check TEXT,
                    row_count_check TEXT,
                    checksum_check TEXT,
                    integrity_check TEXT,
                    FOREIGN KEY (run_id) REFERENCES executions(run_id)
                );
            """)
            
            # Notifications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    type TEXT,
                    status TEXT,
                    target TEXT,
                    error_message TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (run_id) REFERENCES executions(run_id)
                );
            """)
            
            conn.commit()

    def log_execution(self, run_id: str, backup_file: str, status: str, report_path: str, error_details: str = None):
        """Logs the high-level workflow execution details."""
        timestamp = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO executions (run_id, backup_file, timestamp, validation_status, report_path, error_details)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (run_id, backup_file, timestamp, status, report_path, error_details))
            conn.commit()

    def log_validation_result(self, run_id: str, table_name: str, table_check: str, row_count_check: str, checksum_check: str, integrity_check: str):
        """Logs table-specific details of a validation execution."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO validation_results (run_id, table_name, table_check, row_count_check, checksum_check, integrity_check)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (run_id, table_name, table_check, row_count_check, checksum_check, integrity_check))
            conn.commit()

    def log_notification(self, run_id: str, notif_type: str, status: str, target: str, error_message: str = None):
        """Logs alerts / reports dispatched via notifiers."""
        timestamp = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (run_id, type, status, target, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (run_id, notif_type, status, target, error_message, timestamp))
            conn.commit()

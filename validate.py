import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def _serialize_row(row: Any) -> bytes:
    if isinstance(row, sqlite3.Row):
        row = tuple(row)
    elif hasattr(row, '__iter__') and not isinstance(row, (str, bytes, bytearray)):
        row = tuple(row)
    return str(row).encode("utf-8")

def check_table_existence(conn: sqlite3.Connection, expected_tables: List[str]) -> dict:
    logger.info("Checking table existence")
    result = {"status": True, "tables": {}}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        for table in expected_tables:
            exists = table in existing_tables
            result["tables"][table] = exists
            if not exists:
                result["status"] = False
                logger.error(f"Missing required table: {table}")
    except Exception as e:
        logger.exception("Error checking table existence")
        result["status"] = False
        result["error"] = str(e)
    return result

def validate_row_counts(conn: sqlite3.Connection, expected_counts: Dict[str, int]) -> dict:
    logger.info("Validating row counts")
    result = {"status": True, "counts": {}}
    try:
        cursor = conn.cursor()
        for table, expected_count in expected_counts.items():
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                actual_count = cursor.fetchone()[0]
                status = actual_count == expected_count
                result["counts"][table] = {
                    "actual": actual_count,
                    "expected": expected_count,
                    "status": status
                }
                if not status:
                    result["status"] = False
                    logger.error(f"Row count mismatch for '{table}': expected {expected_count}, got {actual_count}")
            except Exception as e:
                result["status"] = False
                result["counts"][table] = {
                    "status": False,
                    "error": str(e)
                }
    except Exception as e:
        logger.exception("Error validating row counts")
        result["status"] = False
        result["error"] = str(e)
    return result

def generate_checksums(conn: sqlite3.Connection, tables: List[str], expected_checksums: Dict[str, str]) -> dict:
    logger.info("Validating checksums")
    result = {"status": True, "tables": {}}
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        for table in tables:
            expected = expected_checksums.get(table)
            try:
                cursor.execute(f"PRAGMA table_info({table});")
                table_info = cursor.fetchall()
                columns = [row[1] for row in table_info]
                if not columns:
                    raise ValueError(f"Table '{table}' has no columns or does not exist.")
                
                pk_cols = [row[1] for row in table_info if row[5] > 0]
                order_clause = ", ".join(pk_cols) if pk_cols else ", ".join(columns)
                
                cursor.execute(f"SELECT * FROM {table} ORDER BY {order_clause};")
                hasher = hashlib.sha256()
                
                while True:
                    rows = cursor.fetchmany(1000)
                    if not rows:
                        break
                    for row in rows:
                        hasher.update(_serialize_row(row))
                        
                checksum = hasher.hexdigest()
                matches = checksum == expected
                result["tables"][table] = {
                    "actual": checksum,
                    "expected": expected,
                    "status": matches
                }
                if not matches:
                    result["status"] = False
                    logger.error(f"Checksum mismatch for '{table}': expected {expected}, got {checksum}")
            except Exception as e:
                result["status"] = False
                result["tables"][table] = {
                    "status": False,
                    "error": str(e)
                }
    except Exception as e:
        logger.exception("Error validating checksums")
        result["status"] = False
        result["error"] = str(e)
    return result

def run_integrity_check(conn: sqlite3.Connection) -> dict:
    logger.info("Running integrity check")
    result = {"status": False, "result": ""}
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        check_res = cursor.fetchone()[0]
        result["result"] = check_res
        if isinstance(check_res, str) and check_res.lower() == "ok":
            result["status"] = True
    except Exception as e:
        logger.exception("Error running integrity check")
        result["error"] = str(e)
    return result

def validate_database(db_path: Path, metrics: Dict[str, Any]) -> dict:
    """Runs all database checks using configuration-driven expectations."""
    db_path = Path(db_path)
    results = {
        "table_check": "FAIL",
        "row_count_check": "FAIL",
        "checksum_check": "FAIL",
        "integrity_check": "FAIL",
        "overall_status": "FAIL",
        "details": {}
    }
    
    if not db_path.exists():
        logger.error(f"Database not found for validation: {db_path}")
        return results
        
    expected_tables = metrics.get("expected_tables", [])
    expected_counts = metrics.get("expected_counts", {})
    expected_checksums = metrics.get("expected_checksums", {})
    
    conn = None
    try:
        db_uri = f"file:{db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        
        # Table check
        t_res = check_table_existence(conn, expected_tables)
        results["details"]["table_check"] = t_res
        results["table_check"] = "PASS" if t_res["status"] else "FAIL"
        
        # Row count check
        r_res = validate_row_counts(conn, expected_counts)
        results["details"]["row_count_check"] = r_res
        results["row_count_check"] = "PASS" if r_res["status"] else "FAIL"
        
        # Checksums
        c_res = generate_checksums(conn, expected_tables, expected_checksums)
        results["details"]["checksum_check"] = c_res
        results["checksum_check"] = "PASS" if c_res["status"] else "FAIL"
        
        # SQLite Integrity check
        i_res = run_integrity_check(conn)
        results["details"]["integrity_check"] = i_res
        results["integrity_check"] = "PASS" if i_res["status"] else "FAIL"
        
        all_passed = (
            results["table_check"] == "PASS" and
            results["row_count_check"] == "PASS" and
            results["checksum_check"] == "PASS" and
            results["integrity_check"] == "PASS"
        )
        results["overall_status"] = "PASS" if all_passed else "FAIL"
        
        if not all_passed:
            reasons = []
            if not t_res["status"]:
                missing = [tbl for tbl, exists in t_res["tables"].items() if not exists]
                reasons.append(f"Missing tables: {', '.join(missing)}")
                
            if not r_res["status"]:
                mismatches = []
                for tbl, cnt_info in r_res["counts"].items():
                    if not cnt_info.get("status"):
                        if "error" in cnt_info:
                            mismatches.append(f"{tbl} (Error: {cnt_info['error']})")
                        else:
                            mismatches.append(f"{tbl} (Got {cnt_info['actual']}, Expected {cnt_info['expected']})")
                reasons.append(f"Row count mismatches: {', '.join(mismatches)}")
                
            if not c_res["status"]:
                mismatches = []
                for tbl, hash_info in c_res["tables"].items():
                    if not hash_info.get("status"):
                        if "error" in hash_info:
                            mismatches.append(f"{tbl} (Error: {hash_info['error']})")
                        else:
                            mismatches.append(f"{tbl} (Got {hash_info['actual'][:8]}..., Expected {hash_info['expected'][:8]}...)")
                reasons.append(f"Checksum mismatches: {', '.join(mismatches)}")
                
            if not i_res["status"]:
                reasons.append(f"Integrity check failed: {i_res.get('result', i_res.get('error', 'unknown error'))}")
                
            results["error"] = " | ".join(reasons)
        
    except Exception as e:
        logger.exception("Error during database validation")
        results["error"] = str(e)
    finally:
        if conn:
            conn.close()
            
    return results

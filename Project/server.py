import os
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Self-healing working directory alignment
if Path("Project").is_dir() and not Path("server.py").exists():
    os.chdir("Project")

from workflow_agent.orchestrator import run_backup_verification_workflow

PORT = 8000
logger = logging.getLogger("dashboard_server")

class DashboardHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging in terminal if desired, or redirect to logger
        logger.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format%args))

    def do_HEAD(self):
        # Respond to Render health checks
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

    def do_GET(self):
        # API: Get execution history
        if self.path == "/api/executions":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            db_path = Path("metadata/metadata.db")
            executions = []
            if db_path.exists():
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM executions ORDER BY timestamp DESC LIMIT 50;")
                    rows = cursor.fetchall()
                    for r in rows:
                        executions.append(dict(r))
                    conn.close()
                except Exception as e:
                    executions = [{"error": str(e)}]
            self.wfile.write(json.dumps(executions).encode("utf-8"))
            return
            
        # API: Get logs
        elif self.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            
            log_path = Path("logs/backup_verification.log")
            log_content = "No logs generated yet."
            if log_path.exists():
                try:
                    with log_path.open("r", encoding="utf-8") as f:
                        # Return last 200 lines to avoid massive load times
                        lines = f.readlines()
                        log_content = "".join(lines[-200:])
                except Exception as e:
                    log_content = f"Error reading logs: {e}"
            self.wfile.write(log_content.encode("utf-8"))
            return
            
        # API: Get config
        elif self.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            config_path = Path("config.json")
            config_data = {}
            if config_path.exists():
                try:
                    with config_path.open("r", encoding="utf-8") as f:
                        config_data = json.load(f)
                    # Expose environment override status to frontend UI
                    config_data["env_sender_active"] = "SENDER_EMAIL" in os.environ
                    config_data["env_password_active"] = "SENDER_PASSWORD" in os.environ
                    config_data["env_receiver_active"] = "RECEIVER_EMAIL" in os.environ
                    config_data["env_github_token_active"] = "GITHUB_TOKEN" in os.environ
                    config_data["env_github_owner_active"] = "GITHUB_OWNER" in os.environ
                    config_data["env_github_repo_active"] = "GITHUB_REPO" in os.environ
                    config_data["env_groq_active"] = "GROQ_API_KEY" in os.environ
                except Exception as e:
                    config_data = {"error": str(e)}
            self.wfile.write(json.dumps(config_data).encode("utf-8"))
            return

        # API: Get available databases list
        elif self.path == "/api/databases":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            db_files = []
            try:
                for p in Path(".").rglob("*.db"):
                    # Exclude database files in sandbox, backups, metadata or git directories
                    parts_lower = [part.lower() for part in p.parts]
                    if any(x in parts_lower for x in ["sandbox", "backups", "metadata", ".git"]):
                        continue
                    db_files.append({
                        "name": p.name,
                        "path": p.as_posix(),
                        "size_kb": round(p.stat().st_size / 1024, 2),
                        "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat()
                    })
            except Exception as e:
                db_files = [{"error": str(e)}]
            self.wfile.write(json.dumps(db_files).encode("utf-8"))
            return

        # API: Get notifications for a run
        elif self.path.startswith("/api/notifications"):
            from urllib.parse import urlparse, parse_qs
            query = urlparse(self.path).query
            params = parse_qs(query)
            run_id = params.get("run_id", [""])[0]
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            db_path = Path("metadata/metadata.db")
            notifications = []
            if db_path.exists() and run_id:
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM notifications WHERE run_id = ? ORDER BY timestamp ASC;", (run_id,))
                    rows = cursor.fetchall()
                    for r in rows:
                        notifications.append(dict(r))
                    conn.close()
                except Exception as e:
                    notifications = [{"error": str(e)}]
            self.wfile.write(json.dumps(notifications).encode("utf-8"))
            return

        # API: Poll for background run status
        elif self.path == "/api/run-status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            in_progress = getattr(DashboardHTTPRequestHandler, '_run_in_progress', False)
            result = getattr(DashboardHTTPRequestHandler, '_run_result', None)
            
            if in_progress:
                self.wfile.write(json.dumps({"status": "running"}).encode("utf-8"))
            elif result:
                self.wfile.write(json.dumps({"status": "done", "result": result}).encode("utf-8"))
                DashboardHTTPRequestHandler._run_result = None
            else:
                self.wfile.write(json.dumps({"status": "idle"}).encode("utf-8"))
            return

        if self.path.startswith("/reports/"):
            requested_file = os.path.basename(self.path)
            full_path = Path("reports") / requested_file
            
            # 1. If file exists physically on disk, serve it directly
            if full_path.exists() and full_path.is_file():
                self.send_response(200)
                content_types = {
                    ".json": "application/json",
                    ".txt": "text/plain"
                }
                self.send_header("Content-Type", content_types.get(full_path.suffix, "text/plain"))
                self.send_header("Content-Disposition", f"attachment; filename=\"{requested_file}\"")
                self.end_headers()
                with full_path.open("rb") as f:
                    self.wfile.write(f.read())
                return

            # 2. Re-generate report dynamically from metadata database if missing (Render ephemeral fallback)
            db_path = Path("metadata/metadata.db")
            if db_path.exists():
                try:
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Normalize search: always search by the JSON variant of the filename
                    base_name = requested_file
                    if base_name.endswith(".txt"):
                        base_name = base_name[:-4] + ".json"
                    
                    # Strategy 1: Match by report_path LIKE
                    cursor.execute("SELECT * FROM executions WHERE report_path LIKE ? LIMIT 1;", (f"%{base_name}%",))
                    exec_row = cursor.fetchone()
                    
                    # Strategy 2: Match by timestamp extracted from filename (e.g. report_20260610_091956)
                    if not exec_row:
                        import re
                        ts_match = re.search(r"(\d{8}_\d{6})", requested_file)
                        if ts_match:
                            ts_str = ts_match.group(1)
                            cursor.execute("SELECT * FROM executions WHERE report_path LIKE ? LIMIT 1;", (f"%{ts_str}%",))
                            exec_row = cursor.fetchone()
                    
                    # Strategy 3: Match by run_id if the filename is a UUID
                    if not exec_row:
                        name_no_ext = requested_file.rsplit(".", 1)[0]
                        cursor.execute("SELECT * FROM executions WHERE run_id = ? LIMIT 1;", (name_no_ext,))
                        exec_row = cursor.fetchone()
                    
                    if exec_row:
                        run_id = exec_row["run_id"]
                        backup_file = exec_row["backup_file"]
                        timestamp = exec_row["timestamp"]
                        status = exec_row["validation_status"]
                        error_details = exec_row["error_details"]
                        
                        # Get validation results details
                        cursor.execute("SELECT * FROM validation_results WHERE run_id = ?;", (run_id,))
                        results_rows = cursor.fetchall()
                        
                        # Reconstruct validation results
                        validation_results = {
                            "overall_status": status,
                        }
                        if results_rows:
                            r = results_rows[0]
                            validation_results.update({
                                "table_check": r["table_check"],
                                "row_count_check": r["row_count_check"],
                                "checksum_check": r["checksum_check"],
                                "integrity_check": r["integrity_check"]
                            })
                        if error_details:
                            validation_results["error"] = error_details
                        
                        conn.close()
                        
                        self.send_response(200)
                        if requested_file.endswith(".json"):
                            self.send_header("Content-Type", "application/json")
                            self.send_header("Content-Disposition", f"attachment; filename=\"{requested_file}\"")
                            self.end_headers()
                            report_data = {
                                "run_id": run_id,
                                "backup_name": backup_file,
                                "timestamp": timestamp,
                                "validation_results": validation_results
                            }
                            self.wfile.write(json.dumps(report_data, indent=4).encode("utf-8"))
                        else:
                            self.send_header("Content-Type", "text/plain")
                            self.send_header("Content-Disposition", f"attachment; filename=\"{requested_file}\"")
                            self.end_headers()
                            txt_content = []
                            txt_content.append("=========================================")
                            txt_content.append("   BACKUP VERIFICATION RUN REPORT        ")
                            txt_content.append("=========================================")
                            txt_content.append(f"Run ID:      {run_id}")
                            txt_content.append(f"Backup File: {backup_file}")
                            txt_content.append(f"Timestamp:   {timestamp}")
                            txt_content.append(f"Status:      {status}")
                            txt_content.append("-----------------------------------------")
                            txt_content.append("Validation Stages:")
                            txt_content.append(f"  - Table existence: {validation_results.get('table_check', 'FAIL')}")
                            txt_content.append(f"  - Row count check: {validation_results.get('row_count_check', 'FAIL')}")
                            txt_content.append(f"  - Checksums check: {validation_results.get('checksum_check', 'FAIL')}")
                            txt_content.append(f"  - Integrity check: {validation_results.get('integrity_check', 'FAIL')}")
                            txt_content.append("=========================================")
                            if error_details:
                                txt_content.append(f"\nErrors:\n{error_details}")
                            
                            self.wfile.write("\n".join(txt_content).encode("utf-8"))
                        return
                    else:
                        conn.close()
                except Exception as e:
                    logger.error(f"Failed to dynamically generate report: {e}")

        # Static file routing
        file_map = {
            "/": "index.html",
            "/index.html": "index.html",
            "/dashboard.html": "dashboard.html",
            "/dashboard.css": "dashboard.css",
            "/dashboard.js": "dashboard.js"
        }
        
        rel_path = file_map.get(self.path)
        if rel_path:
            full_path = Path(rel_path)
            if full_path.exists():
                self.send_response(200)
                content_types = {
                    ".html": "text/html",
                    ".css": "text/css",
                    ".js": "application/javascript"
                }
                self.send_header("Content-Type", content_types.get(full_path.suffix, "text/plain"))
                self.end_headers()
                with full_path.open("rb") as f:
                    self.wfile.write(f.read())
                return
                
        # 404 Not Found
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"File not found.")

    def do_POST(self):
        # API: Authentication Login Verification
        if self.path == "/api/login":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response_data = {"authenticated": False}
            try:
                credentials = json.loads(post_data.decode("utf-8"))
                username = credentials.get("username", "")
                password = credentials.get("password", "")
                
                # Check environment variables or defaults
                expected_user = os.environ.get("ADMIN_USER", "admin")
                expected_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
                
                if username == expected_user and password == expected_pass:
                    response_data = {"authenticated": True}
            except Exception as e:
                response_data = {"authenticated": False, "error": str(e)}
                
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
            return

        # API: Trigger backup verification workflow run (background thread)
        if self.path == "/api/run":
            import threading
            
            # Check if a run is already in progress
            if getattr(DashboardHTTPRequestHandler, '_run_in_progress', False):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "A verification run is already in progress. Please wait."}).encode("utf-8"))
                return
            
            DashboardHTTPRequestHandler._run_in_progress = True
            DashboardHTTPRequestHandler._run_result = None
            
            def background_run():
                try:
                    config_path = Path("config.json")
                    with config_path.open("r", encoding="utf-8") as f:
                        config = json.load(f)
                    success = run_backup_verification_workflow(config, "config.json")
                    DashboardHTTPRequestHandler._run_result = {"success": True, "result": "PASS" if success else "FAIL"}
                except Exception as e:
                    DashboardHTTPRequestHandler._run_result = {"success": False, "error": str(e)}
                finally:
                    DashboardHTTPRequestHandler._run_in_progress = False
            
            thread = threading.Thread(target=background_run, daemon=True)
            thread.start()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "started": True}).encode("utf-8"))
            return

            
            
        # API: Save configuration
        if self.path == "/api/config":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response_data = {"success": False}
            try:
                new_config = json.loads(post_data.decode("utf-8"))
                config_path = Path("config.json")
                with config_path.open("w", encoding="utf-8") as f:
                    json.dump(new_config, f, indent=4)
                response_data = {"success": True}
            except Exception as e:
                response_data = {"success": False, "error": str(e)}
                
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
            return

        # API: AI Assistant
        if self.path == "/api/ai":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response_data = {"reply": ""}
            try:
                payload = json.loads(post_data.decode("utf-8"))
                error_context = payload.get("error", "No active error.")
                query = payload.get("query", "Explain the error.")
                response_data["reply"] = query_ollama(error_context, query)
            except Exception as e:
                response_data = {"reply": f"AI Assistant Error: {e}"}
                
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
            return

        # 404 Not Found
        self.send_response(404)
        self.end_headers()

def query_ollama(error_context: str, query: str) -> str:
    db_keywords = [
        "db", "database", "checksum", "row", "count", "table", "lock", 
        "fail", "error", "verify", "integrity", "sqlite", "column", 
        "sql", "query", "record", "data", "restore", "schema",
        "build", "compile", "run", "script", "migration", "log", "status"
    ]
    
    query_lower = query.lower()
    error_lower = error_context.lower()
    
    # Check if the query itself is database-related, error-related, or build-related.
    # If the query is completely unrelated, return the exact rejection message.
    is_related = any(kw in query_lower for kw in db_keywords)
    if not is_related:
        return "sorry ! i can't help with this "

    # Build prompt for Groq AI
    prompt = f"""You are a Database Verification AI Assistant.
The system experienced this error:
{error_context}

User Query:
{query}

Explain this error clearly and provide direct steps to fix/rectify it. Keep your answer professional and concise.
If the query is not related to database errors, verification, database locking, database files, SQL, or database administration, you must reply with exactly: "sorry ! i can't help with this "."""

    try:
        import requests
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            logger.warning("GROQ_API_KEY not set. Falling back to expert rules.")
            raise ValueError("No Groq API key configured")
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a Database Verification AI Assistant. You help users diagnose and fix database backup verification errors. Keep answers professional and concise."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        logger.info("Sending request to Groq API...")
        res = requests.post(groq_url, json=payload, headers=headers, timeout=10)
        logger.info(f"Groq API Status Code: {res.status_code}")
        if res.status_code == 200:
            res_json = res.json()
            choices = res_json.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                text = message.get("content", "").strip()
                if text:
                    return text
            logger.warning("Failed to extract text from Groq response.")
        else:
            logger.warning(f"Groq API returned non-200 code: {res.text}")
    except Exception as e:
        logger.warning(f"Groq API error occurred: {e}. Using expert fallback system...")
        
    # Expert fallback rules
    if "checksum" in error_lower or "checksum" in query_lower:
        return """### 🤖 AI Rectification Guide: Checksum Mismatch

**Cause**: The database data has changed compared to the expected SHA-256 signatures registered in `config.json`. This occurs if records are modified, inserted, or deleted.

**Steps to Rectify**:
1. **Confirm Changes**: If you recently inserted/updated records (like in `backup_huge_error.db`), this error is expected.
2. **Retrieve New Hashes**: Run the database hash calculator to get the new sha256 checksums.
3. **Update Configuration**: Open `config.json` and replace the hash values in `expected_checksums` for the corresponding database and table.
4. **Rerun Verification**: Trigger a new run. It will now successfully PASS."""
        
    elif "row count" in error_lower or "count" in query_lower:
        return """### 🤖 AI Rectification Guide: Row Count Mismatch

**Cause**: The number of records in one or more tables (`users`, `orders`, `products`) does not match the expectations set inside your configuration.

**Steps to Rectify**:
1. Check your source database tables to find the actual count of rows.
2. Open `config.json` and adjust the counts under `expected_counts` for the matching database name (e.g. set `"users": 50000`).
3. Save the config and execute verification again. It will now evaluate successfully."""
        
    elif "table" in error_lower or "missing table" in error_lower or "table" in query_lower:
        return """### 🤖 AI Rectification Guide: Missing Tables

**Cause**: One or more required tables (`users`, `orders`, `products`) are not defined in the restored database structure.

**Steps to Rectify**:
1. Open your source database and check if the schemas exist.
2. Verify that your SQL migration script (e.g., `backup/create_backup.sql`) correctly creates the tables before compiling the database.
3. Recompile the database and copy/move it back to your source directory."""

    elif "lock" in error_lower or "lock" in query_lower or "permission" in error_lower:
        return """### 🤖 AI Rectification Guide: Database Locks / Permission Denied

**Cause**: SQLite database files are file-based and can become locked if another active connection (like a DB Browser, Python console, or local worker process) does not release the file locks.

**Steps to Rectify**:
1. **Close External Connections**: Terminate any open SQL explorers, DB browser tabs, or other script processes executing queries on the source or sandbox directories.
2. **Check Access permissions**: Ensure the user running `server.py` or `main.py` has full write/read access to the project root and subfolders.
3. **Force Release**: If locks persist on Windows, restart your command prompt terminal or IDE to kill hanging file handles."""

    return f"""### 🤖 AI Assistant (Offline Fallback System)

I see you asked about: *"{query}"*.

**Error Context**:
`{error_context}`

**Suggestions**:
1. Check your database state and verify your settings inside `config.json`.
2. Ensure you have terminated open handles to database files to avoid SQLite locks.
3. Check the real-time system logs under the **Log Console** tab for trace logs.
4. Verify your internet connection and ensure your Groq API key is configured and authorized."""

def run_server():
    # Setup simple console logging for web requests
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    port = int(os.environ.get("PORT", PORT))
    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, DashboardHTTPRequestHandler)
    print(f"Dashboard server running at: http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()

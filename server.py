import os
import json
import sqlite3
import logging
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from workflow_agent.orchestrator import run_backup_verification_workflow

PORT = 8000
logger = logging.getLogger("dashboard_server")

class DashboardHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging in terminal if desired, or redirect to logger
        logger.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format%args))

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
                except Exception as e:
                    config_data = {"error": str(e)}
            self.wfile.write(json.dumps(config_data).encode("utf-8"))
            return

        if self.path.startswith("/reports/"):
            requested_file = os.path.basename(self.path)
            full_path = Path("reports") / requested_file
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

        # Static file routing
        file_map = {
            "/": "index.html",
            "/index.html": "index.html",
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
        # API: Trigger backup verification workflow run
        if self.path == "/api/run":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response_data = {"success": False}
            try:
                config_path = Path("config.json")
                with config_path.open("r", encoding="utf-8") as f:
                    config = json.load(f)
                # Run the orchestrator workflow
                success = run_backup_verification_workflow(config, "config.json")
                response_data = {"success": True, "result": "PASS" if success else "FAIL"}
            except Exception as e:
                response_data = {"success": False, "error": str(e)}
                
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
            return
            
        # API: Save configuration
        elif self.path == "/api/config":
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
        elif self.path == "/api/ai":
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

    # Build prompt for Gemini
    prompt = f"""You are a Database Verification AI Assistant.
The system experienced this error:
{error_context}

User Query:
{query}

Explain this error clearly and provide direct steps to fix/rectify it. Keep your answer professional and concise.
If the query is not related to database errors, verification, database locking, database files, SQL, or database administration, you must reply with exactly: "sorry ! i can't help with this "."""

    try:
        import requests
        api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyB8ltvrf1u9_d5_TjKauocnkSUm2SqMK5Q")
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        logger.info("Sending request to Gemini API...")
        res = requests.post(gemini_url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        logger.info(f"Gemini API Status Code: {res.status_code}")
        if res.status_code == 200:
            res_json = res.json()
            logger.info(f"Gemini API Response JSON: {json.dumps(res_json)}")
            candidates = res_json.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    if text:
                        return text
            logger.warning("Failed to extract text parts from Gemini response.")
        else:
            logger.warning(f"Gemini API returned non-200 code: {res.text}")
    except Exception as e:
        logger.warning(f"Gemini API error occurred: {e}. Using expert fallback system...")
        
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
4. Verify your internet connection and ensure your Gemini API key in `server.py` is configured and authorized."""

def run_server():
    # Setup simple console logging for web requests
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    port = int(os.environ.get("PORT", PORT))
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, DashboardHTTPRequestHandler)
    print(f"Dashboard server running at: http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()

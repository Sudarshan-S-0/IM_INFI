document.addEventListener("DOMContentLoaded", () => {
    // Navigation controls
    const tabLinks = document.querySelectorAll(".tab-link");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const navBar = document.getElementById("main-navigation");
    
    let logIntervalId = null;

    tabLinks.forEach(link => {
        link.addEventListener("click", () => {
            const targetTab = link.getAttribute("data-tab");
            
            tabLinks.forEach(l => l.classList.remove("active"));
            tabPanels.forEach(p => p.classList.remove("active"));
            
            link.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
            
            // Clear log polling when switching away
            if (logIntervalId) {
                clearInterval(logIntervalId);
                logIntervalId = null;
            }
            
            // Reload logs when logs tab is active and start interval polling
            if (targetTab === "logs-tab") {
                fetchLogs();
                logIntervalId = setInterval(fetchLogs, 3000);
            }
        });
    });

    // Elements
    const triggerRunBtn = document.getElementById("trigger-run-btn");
    const btnSpinner = document.getElementById("btn-spinner");
    const btnText = triggerRunBtn.querySelector(".btn-text");
    const runsTableBody = document.getElementById("runs-table-body");
    const logConsole = document.getElementById("log-console-output");
    const clearLogsBtn = document.getElementById("clear-logs-view-btn");
    const configForm = document.getElementById("config-form");
    
    // Stats elements
    const statTotalRuns = document.getElementById("stat-total-runs");
    const statSuccessRate = document.getElementById("stat-success-rate");
    const statTargetDb = document.getElementById("stat-target-db");
    const statLastStatus = document.getElementById("stat-last-status");
    
    // Modal elements
    const reportModal = document.getElementById("report-modal");
    const closeModalBtn = document.getElementById("close-modal-btn");
    const modalContent = document.getElementById("modal-report-content");
    
    // Toast notification
    const toast = document.getElementById("toast-notification");

    // Modal Close
    closeModalBtn.addEventListener("click", () => {
        reportModal.classList.remove("active");
    });
    
    window.addEventListener("click", (e) => {
        if (e.target === reportModal) {
            reportModal.classList.remove("active");
        }
    });

    // Clear logs
    clearLogsBtn.addEventListener("click", () => {
        logConsole.textContent = "";
    });

    // Show toast message
    function showToast(message, type = "info") {
        toast.textContent = message;
        toast.className = "toast"; // Reset
        
        if (type === "success") toast.classList.add("success");
        if (type === "error") toast.classList.add("error");
        
        toast.classList.add("active");
        setTimeout(() => {
            toast.classList.remove("active");
        }, 4000);
    }

    // Cache executions to render details on row click
    let executionsCache = [];

    // Fetch and render executions list
    async function fetchExecutions() {
        try {
            const res = await fetch("/api/executions");
            if (!res.ok) throw new Error("Could not fetch executions history.");
            const data = await res.json();
            
            executionsCache = data;
            renderExecutionsTable(data);
            updateStatsSummary(data);
        } catch (err) {
            console.error(err);
            runsTableBody.innerHTML = `<tr><td colspan="5" class="loading-state text-ruby">Error loading history: ${err.message}</td></tr>`;
        }
    }

    function renderExecutionsTable(data) {
        if (data.length === 0) {
            runsTableBody.innerHTML = `<tr><td colspan="6" class="loading-state">No execution runs logged yet.</td></tr>`;
            return;
        }
        
        runsTableBody.innerHTML = "";
        data.forEach(exec => {
            if (exec.error) return; // Skip errors
            
            // Extract filename from path
            const reportPath = exec.report_path || "";
            const jsonFilename = reportPath.split(/[\\/]/).pop();
            const txtFilename = jsonFilename ? jsonFilename.replace(".json", ".txt") : "";
            
            const tr = document.createElement("tr");
            tr.id = `run-row-${exec.run_id}`;
            tr.innerHTML = `
                <td><code>${exec.run_id.substring(0, 8)}...</code></td>
                <td>${exec.timestamp ? exec.timestamp.replace("T", " ").substring(0, 19) : "N/A"}</td>
                <td><code>${exec.backup_file || "N/A"}</code></td>
                <td>
                    ${jsonFilename ? `
                        <a href="/reports/${jsonFilename}" class="btn btn-clear" style="padding: 2px 6px; font-size: 11px; color: var(--accent-blue);" download onclick="event.stopPropagation();">📂 JSON</a>
                        <a href="/reports/${txtFilename}" class="btn btn-clear" style="padding: 2px 6px; font-size: 11px; color: var(--accent-amber);" download onclick="event.stopPropagation();">📄 TXT</a>
                    ` : "N/A"}
                </td>
                <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-secondary);" title="${exec.error_details || ""}">
                    ${exec.error_details || "—"}
                </td>
                <td><span class="badge ${exec.validation_status === "PASS" ? "badge-pass" : "badge-fail"}">${exec.validation_status}</span></td>
            `;
            
            tr.addEventListener("click", () => showExecutionDetails(exec.run_id));
            runsTableBody.appendChild(tr);
        });
    }



    // Detail modal display
    function showExecutionDetails(runId) {
        const exec = executionsCache.find(e => e.run_id === runId);
        if (!exec) return;
        
        modalContent.innerHTML = `
            <div class="results-modal-grid">
                <div class="results-modal-row">
                    <span class="results-modal-label">Run ID</span>
                    <code>${exec.run_id}</code>
                </div>
                <div class="results-modal-row">
                    <span class="results-modal-label">Execution Time</span>
                    <span>${exec.timestamp.replace("T", " ").substring(0, 19)}</span>
                </div>
                <div class="results-modal-row">
                    <span class="results-modal-label">Backup Filename</span>
                    <code>${exec.backup_file}</code>
                </div>
                <div class="results-modal-row">
                    <span class="results-modal-label">Overall Status</span>
                    <span class="badge ${exec.validation_status === "PASS" ? "badge-pass" : "badge-fail"}">${exec.validation_status}</span>
                </div>
                <div class="results-modal-row">
                    <span class="results-modal-label">Report Saved Path</span>
                    <code>${exec.report_path}</code>
                </div>
                ${exec.error_details ? `
                <div class="results-modal-row" style="flex-direction: column; align-items: flex-start; gap: 8px;">
                    <span class="results-modal-label" style="color: var(--accent-ruby)">Error Context</span>
                    <pre style="width: 100%; white-space: pre-wrap; font-family: monospace; font-size: 12px; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px;">${exec.error_details}</pre>
                </div>
                ` : ""}
            </div>
        `;
        
        reportModal.classList.add("active");
    }

    // Fetch and render logs
    async function fetchLogs() {
        try {
            const res = await fetch("/api/logs");
            if (!res.ok) throw new Error("Could not fetch log stream.");
            const logText = await res.text();
            
            logConsole.textContent = logText;
            // Auto-scroll to the bottom of the logs console
            logConsole.scrollTop = logConsole.scrollHeight;
        } catch (err) {
            logConsole.textContent = `Error reading logs: ${err.message}`;
        }
    }
    
    // Fetch and populate configuration form
    async function fetchConfig() {
        try {
            const res = await fetch("/api/config");
            if (!res.ok) throw new Error("Could not retrieve config variables.");
            const config = await res.json();
            
            // Populate fields
            document.getElementById("input-db-path").value = config.database_path || "";
            document.getElementById("input-backup-dir").value = config.backup_directory || "";
            document.getElementById("input-sandbox-dir").value = config.sandbox_directory || "";
            document.getElementById("input-report-dir").value = config.report_directory || "";
            document.getElementById("input-retention").value = config.retention_days || 7;
            document.getElementById("select-scheduler-mode").value = config.scheduler_mode || "manual";
            document.getElementById("input-retry-count").value = config.retry_count || 3;
            document.getElementById("input-retry-delay").value = config.retry_delay_seconds || 2;
            
            // Display Stats target db name
            statTargetDb.textContent = (config.database_path || "backup.db").split("/").pop();
            
            // GitHub Notifiers
            const gh = config.github_settings || {};
            document.getElementById("check-github-enable").checked = gh.enabled || false;
            document.getElementById("input-github-token").value = gh.github_token || "";
            document.getElementById("input-github-owner").value = gh.repository_owner || "";
            document.getElementById("input-github-repo").value = gh.repository_name || "";
            
            // Gmail Notifiers
            const gm = config.gmail_settings || {};
            document.getElementById("check-gmail-enable").checked = gm.enabled || false;
            document.getElementById("input-gmail-sender").value = gm.sender_email || "";
            document.getElementById("input-gmail-password").value = gm.sender_password || "";
            document.getElementById("input-gmail-receiver").value = gm.receiver_email || "";
            
        } catch (err) {
            console.error(err);
            showToast(`Error loading configuration: ${err.message}`, "error");
        }
    }

    // Save configuration form POST handler
    configForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const payload = {
            database_path: document.getElementById("input-db-path").value,
            backup_directory: document.getElementById("input-backup-dir").value,
            sandbox_directory: document.getElementById("input-sandbox-dir").value,
            report_directory: document.getElementById("input-report-dir").value,
            retention_days: parseInt(document.getElementById("input-retention").value),
            scheduler_mode: document.getElementById("select-scheduler-mode").value,
            scheduler_settings: {
                daily_time: "02:00",
                hourly_minute: 0,
                every_n_minutes_interval: 15
            },
            retry_count: parseInt(document.getElementById("input-retry-count").value),
            retry_delay_seconds: parseInt(document.getElementById("input-retry-delay").value),
            github_settings: {
                enabled: document.getElementById("check-github-enable").checked,
                github_token: document.getElementById("input-github-token").value,
                repository_owner: document.getElementById("input-github-owner").value,
                repository_name: document.getElementById("input-github-repo").value
            },
            gmail_settings: {
                enabled: document.getElementById("check-gmail-enable").checked,
                smtp_server: "smtp.gmail.com",
                smtp_port: 587,
                sender_email: document.getElementById("input-gmail-sender").value,
                sender_password: document.getElementById("input-gmail-password").value,
                receiver_email: document.getElementById("input-gmail-receiver").value
            },
            logging_settings: {
                level: "INFO",
                file_path: "logs/backup_verification.log"
            },
            validation_metrics: {
                "backup.db": {
                    "expected_tables": ["users", "orders", "products"],
                    "expected_counts": { "users": 3, "orders": 3, "products": 3 },
                    "expected_checksums": {
                        "users": "dfd7ed9f21512bee326e4f877fdcc585574137bc0fd326739bc461ee71641205",
                        "orders": "f1895a2d95312281a5e6e77672e826d827975f338c44e5e0f98984610a6af61d",
                        "products": "5080070d5b9a9e08f93174feff6dd1b1cfeccae9dfeb76952a8959892286c1d6"
                    }
                },
                "backup_new.db": {
                    "expected_tables": ["users", "orders", "products"],
                    "expected_counts": { "users": 4, "orders": 4, "products": 4 },
                    "expected_checksums": {
                        "users": "b06940bde3c740413e9c5144d54260871a5e4da1838a0b2f1269905c95bf0bd0",
                        "orders": "d504419cc9e8309b1f3db1d58e38466e382292173db44866a1fa0897a7271e9e",
                        "products": "30c502b54c8fa4a33b9a4ad154d34b16f396a9d107f3601d2ee78e88f307f3de"
                    }
                },
                "backup_dummy.db": {
                    "expected_tables": ["users", "orders", "products"],
                    "expected_counts": { "users": 5, "orders": 5, "products": 5 },
                    "expected_checksums": {
                        "users": "89e24979043f200cdafb98cb68eb62ef3d28feca3b3fb05559ad3b5bae2d694e",
                        "orders": "bcc2f93148098305c0a645d5aa38c685791b4bcea98fc3b925f7aa33c49ef9b8",
                        "products": "c6d3fd1ebde8ee7f3b422baeae70c9167d9d2834f42381a4eb3f6aaa0bfae05f"
                    }
                }
            }
        };
        
        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                showToast("Configuration saved successfully!", "success");
                statTargetDb.textContent = payload.database_path.split("/").pop();
            } else {
                throw new Error(data.error || "Save error occurred.");
            }
        } catch (err) {
            showToast(`Failed to save config: ${err.message}`, "error");
        }
    });

    // Trigger Run workflow button click handler
    triggerRunBtn.addEventListener("click", async () => {
        triggerRunBtn.disabled = true;
        btnSpinner.style.display = "inline-block";
        btnText.textContent = "Verifying...";
        
        showToast("Backup Verification run triggered in background...", "info");
        
        try {
            const res = await fetch("/api/run", { method: "POST" });
            const data = await res.json();
            
            if (data.success) {
                if (data.result === "PASS") {
                    showToast("Verification PASS! Backup is complete and fully validated.", "success");
                } else {
                    showToast("Verification FAIL! Database validation checks encountered errors.", "error");
                }
                
                // Refresh execution logs and list views
                await fetchExecutions();
                await fetchLogs();
                
                // Open modal detail for the newest run immediately
                if (executionsCache.length > 0) {
                    showExecutionDetails(executionsCache[0].run_id);
                }
            } else {
                throw new Error(data.error || "Failed to complete run.");
            }
        } catch (err) {
            console.error(err);
            showToast(`Workflow execution failed: ${err.message}`, "error");
        } finally {
            triggerRunBtn.disabled = false;
            btnSpinner.style.display = "none";
            btnText.textContent = "⚡ Trigger Run";
        }
    });

    // AI Assistant Tab Logic
    const aiActiveError = document.getElementById("ai-active-error");
    const aiChatFeed = document.getElementById("ai-chat-feed");
    const aiQueryForm = document.getElementById("ai-query-form");
    const aiQueryInput = document.getElementById("ai-query-input");
    const aiSuggestExplain = document.getElementById("ai-suggest-explain");
    const aiSuggestChecksum = document.getElementById("ai-suggest-checksum");
    const aiSuggestCounts = document.getElementById("ai-suggest-counts");

    let lastErrorContext = "No active validation error detected.";

    function appendMessage(sender, text, isBot = false) {
        const div = document.createElement("div");
        div.className = `ai-msg ${isBot ? 'bot' : 'user'}`;
        
        // Simple inline markdown formatting
        const formattedText = text
            .replace(/\n/g, "<br>")
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/### (.*?)(<br>|$)/g, "<h3>$1</h3>")
            .replace(/`([^`]+)`/g, "<code>$1</code>");
            
        div.style.padding = "12px 16px";
        div.style.borderRadius = isBot ? "12px 12px 12px 0" : "12px 12px 0 12px";
        div.style.border = "1px solid var(--border-color)";
        div.style.maxWidth = "85%";
        div.style.lineHeight = "1.5";
        div.style.alignSelf = isBot ? "flex-start" : "flex-end";
        div.style.background = isBot ? "rgba(255, 255, 255, 0.03)" : "rgba(0, 210, 255, 0.08)";
        
        div.innerHTML = `<strong>${isBot ? '🤖 AI Assistant' : '👤 You'}:</strong><div style="margin-top: 6px;">${formattedText}</div>`;
        
        aiChatFeed.appendChild(div);
        aiChatFeed.scrollTop = aiChatFeed.scrollHeight;
    }

    async function sendQuery(queryText) {
        appendMessage("You", queryText, false);
        
        // Add loading bubble
        const loadDiv = document.createElement("div");
        loadDiv.className = "ai-msg bot loading";
        loadDiv.style.alignSelf = "flex-start";
        loadDiv.style.color = "var(--text-secondary)";
        loadDiv.innerHTML = "<em>🤖 Thinking...</em>";
        aiChatFeed.appendChild(loadDiv);
        aiChatFeed.scrollTop = aiChatFeed.scrollHeight;
        
        try {
            const res = await fetch("/api/ai", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    error: lastErrorContext,
                    query: queryText
                })
            });
            if (!res.ok) throw new Error("API call failed.");
            const data = await res.json();
            
            loadDiv.remove();
            appendMessage("AI Assistant", data.reply, true);
        } catch (err) {
            loadDiv.remove();
            appendMessage("AI Assistant", `Failed to get a response: ${err.message}`, true);
        }
    }

    aiQueryForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const queryText = aiQueryInput.value.trim();
        if (!queryText) return;
        aiQueryInput.value = "";
        sendQuery(queryText);
    });

    aiSuggestExplain.addEventListener("click", () => {
        sendQuery("Can you explain the last validation error in detail and tell me how to fix it?");
    });
    aiSuggestChecksum.addEventListener("click", () => {
        sendQuery("How do I fix a checksum check failure in the backup verification system?");
    });
    aiSuggestCounts.addEventListener("click", () => {
        sendQuery("How do I fix a row count verification mismatch error?");
    });

    function updateStatsSummary(data) {
        const validRuns = data.filter(e => !e.error);
        const total = validRuns.length;
        statTotalRuns.textContent = total;
        
        if (total > 0) {
            const passes = validRuns.filter(e => e.validation_status === "PASS").length;
            const successRate = Math.round((passes / total) * 100);
            statSuccessRate.textContent = `${successRate}%`;
            
            const lastRun = validRuns[0];
            statLastStatus.textContent = lastRun.validation_status;
            statLastStatus.className = lastRun.validation_status === "PASS" ? "text-emerald" : "text-ruby";
            
            // Set AI context
            if (lastRun.validation_status === "FAIL") {
                lastErrorContext = lastRun.error_details || "Validation check failed.";
                aiActiveError.textContent = lastErrorContext;
                aiActiveError.style.color = "var(--accent-ruby)";
            } else {
                lastErrorContext = "No active validation error detected.";
                aiActiveError.textContent = lastErrorContext;
                aiActiveError.style.color = "var(--accent-emerald)";
            }
        } else {
            statSuccessRate.textContent = "0%";
            statLastStatus.textContent = "N/A";
            statLastStatus.className = "";
            lastErrorContext = "No active validation error detected.";
            aiActiveError.textContent = lastErrorContext;
            aiActiveError.style.color = "var(--text-secondary)";
        }
    }

    // Initial Load
    fetchExecutions();
    fetchConfig();
    fetchLogs();
});

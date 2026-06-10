import logging
from datetime import datetime
from reporting.github_issue_creator import create_github_issue
from reporting.gmail_notifier import send_gmail_notification

logger = logging.getLogger(__name__)

def dispatch_notifications(config: dict, run_id: str, backup_name: str, validation_results: dict, metadata_store) -> dict:
    """Orchestrates notification dispatch logic across Github and Gmail based on execution outcome."""
    overall_status = validation_results.get("overall_status", "FAIL")
    timestamp_str = datetime.now().isoformat()
    
    # 1. Compose messages
    subject = f"Backup Verification System Alert - Run ID {run_id}: {overall_status}"
    
    body_text = f"""Backup Verification Event Notification
-------------------------------------------
Execution ID:     {run_id}
Backup File:      {backup_name}
Timestamp:        {timestamp_str}
Status:           {overall_status}

Validation Details:
  - Table Existence: {validation_results.get('table_check', 'FAIL')}
  - Row Count Check: {validation_results.get('row_count_check', 'FAIL')}
  - Checksums Check: {validation_results.get('checksum_check', 'FAIL')}
  - Integrity Check: {validation_results.get('integrity_check', 'FAIL')}
"""
    if "error" in validation_results:
        body_text += f"\nError Details:\n{validation_results['error']}"
        
    outcomes = {}
    
    # 2. Gmail notifier
    gmail_ok = send_gmail_notification(config, subject, body_text)
    outcomes["gmail"] = "SUCCESS" if gmail_ok else "FAILED"
    if metadata_store:
        target_email = config.get("gmail_settings", {}).get("receiver_email", "unknown")
        metadata_store.log_notification(
            run_id=run_id,
            notif_type="Gmail",
            status="SUCCESS" if gmail_ok else "FAIL",
            target=target_email,
            error_message=None if gmail_ok else "Check logs for SMTP error"
        )
        
    # 3. GitHub Notifier (only triggers if validation fails)
    if overall_status == "FAIL":
        issue_title = f"Backup Verification Failed - Run ID {run_id}"
        issue_body = f"""### Backup Verification Failure Report

- **Run ID:** `{run_id}`
- **Backup File:** `{backup_name}`
- **Failure Time:** `{timestamp_str}`

#### Verification Checks Summary:
- **Table Existence Check:** `{validation_results.get('table_check', 'FAIL')}`
- **Row Count Check:** `{validation_results.get('row_count_check', 'FAIL')}`
- **SHA-256 Checksums Check:** `{validation_results.get('checksum_check', 'FAIL')}`
- **SQLite Database Integrity:** `{validation_results.get('integrity_check', 'FAIL')}`

#### Details / Stacktrace:
```text
{validation_results.get('error', 'No trace output.')}
```
"""
        github_url = create_github_issue(config, issue_title, issue_body)
        github_ok = bool(github_url)
        outcomes["github"] = "SUCCESS" if github_ok else "FAILED"
        if metadata_store:
            gh_settings = config.get("github_settings", {})
            owner = gh_settings.get("repository_owner", "Vannilavan05")
            repo = gh_settings.get("repository_name", "IM_INFI")
            if not owner or owner == "YOUR_GITHUB_OWNER":
                owner = "Vannilavan05"
            if not repo or repo == "YOUR_GITHUB_REPO":
                repo = "IM_INFI"
            target_val = github_url if github_ok else f"{owner}/{repo}"
            metadata_store.log_notification(
                run_id=run_id,
                notif_type="GitHub",
                status="SUCCESS" if github_ok else "FAIL",
                target=target_val,
                error_message=None if github_ok else "Check logs for GitHub API error"
            )
    else:
        outcomes["github"] = "SKIPPED"
        
    return outcomes

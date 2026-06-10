# Backup Verification Simulator

## 📌 Project Overview
Backup Verification Simulator is an automated system designed to verify whether database backups are actually usable when needed.

Many organizations create backups regularly but fail to test whether those backups can be restored successfully. This project automates the process of restoring, validating, reporting, and monitoring backups to ensure recovery readiness.

The system performs backup verification by restoring backups into a sandbox environment, validating the restored data, generating reports, and automatically creating GitHub issues when failures occur.

## 🎯 Problem Statement
Organizations often:
- Create backups regularly
- Store backups without verification
- Discover corrupted backups only during emergencies
- Spend significant time manually validating backups

This can result in:
- Data loss
- Business downtime
- Recovery failures
- Increased operational risk

## 💡 Solution
The Backup Verification Simulator automatically:
- Selects a backup
- Restores it in a sandbox environment
- Validates restored data
- Generates verification reports
- Creates GitHub issues for failures
- Stores logs and metadata
- Provides a web dashboard for monitoring and management

## 🔄 System Workflow
```
Backup Creation
       │
       ▼
Workflow Agent
       │
       ▼
Restore Backup
       │
       ▼
Validate Data
       │
       ▼
  PASS / FAIL
   │         │
   ▼         ▼
Generate    Generate
PASS Report FAIL Report
              │
              ▼
      Create GitHub Issue
              │
              ▼
     Store Logs & Metadata
              │
              ▼
       Dashboard Display
```

## 🏗 System Architecture
```
     User
      │
      ▼
Web Dashboard
      │
      ▼
FastAPI / Flask Backend
      │
      ▼
Workflow Agent
      ├── Restore Module
      ├── Validation Module
      ├── Report Generator
      ├── GitHub Integration
      └── Scheduler
              │
              ▼
         SQLite Database
```

## 👥 Team Contributions

### Sujeth M (Backup & Scheduler Module)
**Responsibilities:**
- Database Backup Creation
- Backup Rotation
- Scheduler Configuration
- Automated Backup Execution

### Vannilavan C (Restore & Validation Module)
**Responsibilities:**
- Backup Restoration
- Sandbox Environment Setup
- Database Validation
- PASS/FAIL Verification

### Sudarshan S (Workflow Agent & Logging)
**Responsibilities:**
- Workflow Orchestration
- Configuration Management
- Execution Control
- Logging System
- Module Integration

### Vishwa Adhesh (Reporting & GitHub Automation)
**Responsibilities:**
- Report Generation
- Verification Summary
- GitHub Issue Creation
- Notification Handling

## 🛠 Technology Stack
- **Backend:** Python
- **Web Framework:** FastAPI / Flask
- **Database:** SQLite
- **Automation:** Scheduler
- **Version Control:** Git & GitHub
- **Deployment:** Render
- **APIs:** GitHub API, Gmail Notification API

## 📂 Project Structure
```
IM_INFI/
│
├── backup.py
├── restore.py
├── validate.py
├── scheduler.py
├── main.py
├── config.json
│
├── workflow_agent/
│   ├── workflow_agent.py
│   ├── logger.py
│   └── config.py
│
├── reporting/
│   ├── report_generator.py
│   ├── github_issue.py
│   ├── gmail_notifier.py
│   └── db_store.py
│
├── templates/
├── static/
├── reports/
├── backups/
├── sandbox/
│
└── metadata.db
```

## ⚙️ Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Vannilavan05/IM_INFI.git
   cd IM_INFI
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
4. Run the web dashboard:
   ```bash
   python webapp.py
   ```

## 📈 Expected Outcome
The system ensures that backups are not only stored but also tested and validated regularly, improving confidence in disaster recovery and minimizing the risk of backup failures.

## 🏁 Conclusion
Backup Verification Simulator transforms backups from passive storage copies into actively verified recovery assets.

> "A backup is only useful if it can be restored successfully, and this project ensures exactly that."

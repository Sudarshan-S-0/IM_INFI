import logging
from pathlib import Path
from workflow_agent.execution_context import ExecutionContext
from workflow_agent.retry_manager import execute_with_retry
import backup
import restore
import validate
from reporting.report_generator import generate_reports
from reporting.notification_manager import dispatch_notifications
from metadata.metadata_store import MetadataStore

logger = logging.getLogger(__name__)

def run_backup_verification_workflow(config: dict, config_path: str = "config.json") -> bool:
    """Executes the orchestrator workflow loop."""
    context = ExecutionContext()
    run_id = context.run_id
    logger.info(f"Starting Backup Verification workflow. Run ID: {run_id}")
    
    # Initialize metadata store
    meta_db_path = Path("metadata/metadata.db")
    meta_store = MetadataStore(meta_db_path)
    
    source_db_path = Path(config.get("database_path"))
    backup_dir = Path(config.get("backup_directory", "backups"))
    sandbox_dir = Path(config.get("sandbox_directory", "sandbox"))
    report_dir = Path(config.get("report_directory", "reports"))
    retention_days = int(config.get("retention_days", 7))
    
    retries = int(config.get("retry_count", 3))
    delay_seconds = float(config.get("retry_delay_seconds", 2))
    
    backup_path = None
    restored_db_path = None
    validation_results = None
    overall_status = "FAIL"
    error_msg = None
    
    try:
        # 1. CREATE BACKUP
        context.start_stage("backup_creation")
        try:
            backup_path = execute_with_retry(
                backup.create_backup,
                retries,
                delay_seconds,
                source_db_path,
                backup_dir
            )
            context.end_stage("backup_creation", "SUCCESS", {"backup_file": str(backup_path)})
        except Exception as e:
            error_msg = f"Backup stage failed: {e}"
            context.end_stage("backup_creation", "FAIL", {"error": error_msg})
            raise RuntimeError(error_msg)
            
        # 2. BACKUP CLEANUP (ROTATION)
        context.start_stage("backup_cleanup")
        try:
            removed = backup.cleanup_old_backups(backup_dir, retention_days)
            context.end_stage("backup_cleanup", "SUCCESS", {"removed_count": len(removed)})
        except Exception as e:
            logger.warning(f"Cleanup stage warning: {e}")
            context.end_stage("backup_cleanup", "WARNING", {"error": str(e)})
            
        # 3. RESTORE BACKUP
        context.start_stage("sandbox_restore")
        try:
            # Restore to sandbox/restored.db
            restored_db_path = execute_with_retry(
                restore.restore_backup,
                retries,
                delay_seconds,
                backup_path,
                sandbox_dir
            )
            
            # Verify restoration connectivity
            verified = execute_with_retry(
                restore.verify_restoration,
                retries,
                delay_seconds,
                restored_db_path
            )
            if not verified:
                raise RuntimeError("Restoration connectivity verification check failed.")
                
            context.end_stage("sandbox_restore", "SUCCESS", {"restored_db_path": str(restored_db_path)})
        except Exception as e:
            error_msg = f"Restore stage failed: {e}"
            context.end_stage("sandbox_restore", "FAIL", {"error": error_msg})
            raise RuntimeError(error_msg)
            
        # 4. DATABASE VALIDATION
        context.start_stage("database_validation")
        try:
            # Determine source target key (e.g. backup.db, backup_new.db, backup_dummy.db)
            target_name = source_db_path.name
            metrics_dict = config.get("validation_metrics", {})
            target_metrics = metrics_dict.get(target_name)
            
            if not target_metrics:
                # Fallback to default metrics if not found
                target_metrics = metrics_dict.get("backup.db", {})
                logger.warning(f"No validation metrics found for {target_name} in config.json. Using fallback default metrics.")
                
            validation_results = validate.validate_database(restored_db_path, target_metrics)
            overall_status = validation_results.get("overall_status", "FAIL")
            context.end_stage("database_validation", "SUCCESS" if overall_status == "PASS" else "FAIL", validation_results)
            
            if overall_status != "PASS":
                error_msg = "Database validation checks failed. See report for details."
        except Exception as e:
            error_msg = f"Validation stage failed: {e}"
            validation_results = {"overall_status": "FAIL", "error": error_msg}
            context.end_stage("database_validation", "FAIL", {"error": error_msg})
            raise RuntimeError(error_msg)
            
    except Exception as top_err:
        logger.error(f"Orchestrator workflow interrupted: {top_err}")
        if not validation_results:
            validation_results = {"overall_status": "FAIL", "error": str(top_err)}
        overall_status = "FAIL"
        error_msg = str(top_err)
        
    # 5. GENERATE REPORT (runs even on validation failures)
    json_path, txt_path = None, None
    try:
        backup_name = backup_path.name if backup_path else source_db_path.name
        json_path, txt_path = generate_reports(run_id, backup_name, validation_results, report_dir)
    except Exception as e:
        logger.error(f"Failed to generate reports: {e}")
        
    # 6. LOG TO METADATA DATABASE
    try:
        backup_file_name = backup_path.name if backup_path else "unknown"
        report_str = str(json_path) if json_path else "unknown"
        meta_store.log_execution(
            run_id=run_id,
            backup_file=backup_file_name,
            status=overall_status,
            report_path=report_str,
            error_details=error_msg
        )
        
        # Log table-specific validation details
        table_check = validation_results.get("table_check", "FAIL")
        row_count_check = validation_results.get("row_count_check", "FAIL")
        checksum_check = validation_results.get("checksum_check", "FAIL")
        integrity_check = validation_results.get("integrity_check", "FAIL")
        
        expected_tables = target_metrics.get("expected_tables", ["users", "orders", "products"]) if 'target_metrics' in locals() else ["users", "orders", "products"]
        for table in expected_tables:
            meta_store.log_validation_result(
                run_id=run_id,
                table_name=table,
                table_check=table_check,
                row_count_check=row_count_check,
                checksum_check=checksum_check,
                integrity_check=integrity_check
            )
    except Exception as e:
        logger.error(f"Failed to save metadata to metadata.db: {e}")
        
    # 7. SEND NOTIFICATIONS
    try:
        backup_file_name = backup_path.name if backup_path else "unknown"
        dispatch_notifications(config, run_id, backup_file_name, validation_results, meta_store)
    except Exception as e:
        logger.error(f"Failed to dispatch notifications: {e}")
        
    return overall_status == "PASS"

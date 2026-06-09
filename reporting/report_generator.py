import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_reports(run_id: str, backup_name: str, validation_results: dict, report_dir: Path) -> tuple:
    """Generates both JSON and text reports inside reports/ directory."""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"report_{timestamp}.json"
    txt_path = report_dir / f"report_{timestamp}.txt"
    
    # JSON content
    report_data = {
        "run_id": run_id,
        "backup_name": backup_name,
        "timestamp": datetime.now().isoformat(),
        "validation_results": validation_results
    }
    
    # Save JSON report
    logger.info(f"Saving JSON report to {json_path}")
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4)
        
    # Build text report
    txt_content = []
    txt_content.append("=========================================")
    txt_content.append("   BACKUP VERIFICATION RUN REPORT        ")
    txt_content.append("=========================================")
    txt_content.append(f"Run ID:      {run_id}")
    txt_content.append(f"Backup File: {backup_name}")
    txt_content.append(f"Timestamp:   {report_data['timestamp']}")
    txt_content.append(f"Status:      {validation_results.get('overall_status', 'FAIL')}")
    txt_content.append("-----------------------------------------")
    txt_content.append("Validation Stages:")
    txt_content.append(f"  - Table existence: {validation_results.get('table_check', 'FAIL')}")
    txt_content.append(f"  - Row count check: {validation_results.get('row_count_check', 'FAIL')}")
    txt_content.append(f"  - Checksums check: {validation_results.get('checksum_check', 'FAIL')}")
    txt_content.append(f"  - Integrity check: {validation_results.get('integrity_check', 'FAIL')}")
    txt_content.append("=========================================")
    
    if "error" in validation_results:
        txt_content.append(f"\nErrors:\n{validation_results['error']}")
        
    # Save Text report
    logger.info(f"Saving Text report to {txt_path}")
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(txt_content))
        
    return json_path, txt_path

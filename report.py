import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def generate_report(results: dict, report_path: Path = Path("report.json")) -> str:
    """Generates a validation report file and returns the final status."""
    report_path = Path(report_path)
    logger.info("Generating report to %s", report_path)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "final_status": results.get("overall_status", "FAIL"),
        "results": results
    }

    try:
        with report_path.open("w", encoding="utf-8") as report_file:
            json.dump(report_data, report_file, indent=4)
        logger.info("Report saved to %s", report_path)
    except Exception:
        logger.exception("Failed to generate report JSON file.")

    return report_data["final_status"]

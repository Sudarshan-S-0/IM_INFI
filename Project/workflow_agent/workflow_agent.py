from __future__ import annotations

import json
import os
import random
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from workflow_agent.config import BACKUP_FOLDER, REPORTS_FOLDER, BACKUP_EXTENSION
from workflow_agent.logger import log_error, log_info


@dataclass(frozen=True)
class StageOutcome:
    status: str  # "SKIPPED" | "SUCCESS" | "FAILURE" | "ERROR"
    duration_ms: int
    reason: Optional[str] = None
    error: Optional[str] = None


@dataclass
class WorkflowReport:
    run_id: str
    started_at: str
    finished_at: str
    duration_ms: int

    final_status: str  # "PASS" | "FAIL"
    backup: dict
    stages: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_ms(start: float) -> int:
    return int(round((time.time() - start) * 1000))


def _project_root() -> Path:
    # workflow_agent/workflow_agent.py -> project root is parent of workflow_agent/
    return Path(__file__).resolve().parent.parent


def _resolve_path(relative_or_absolute: str) -> Path:
    p = Path(relative_or_absolute)
    return p if p.is_absolute() else (_project_root() / p)


def discover_backups(backup_folder: str = BACKUP_FOLDER, backup_extension: str = BACKUP_EXTENSION) -> list[Path]:
    """Discover candidate backup files.

    Rules:
    - Only regular files with matching extension.
    - Ignores directories/symlinks.
    - Ignores unreadable entries.
    """

    folder = _resolve_path(backup_folder)
    if not folder.exists():
        return []

    if not folder.is_dir():
        return []

    backups: list[Path] = []
    try:
        for entry in folder.iterdir():
            try:
                if not entry.is_file() or entry.is_symlink():
                    continue
                if entry.suffix.lower() != backup_extension.lower():
                    continue
                backups.append(entry)
            except OSError:
                # Permission/read issues: skip entry
                continue
    except OSError:
        return []

    return sorted(backups)


def get_random_backup(backups: list[Path], rng: Optional[random.Random] = None) -> Path:
    if not backups:
        raise FileNotFoundError("No backup files found")
    rng = rng or random.Random()
    return rng.choice(backups)


def default_restore_stub(backup_path: Path) -> bool:
    # Stub: replace/inject in future.
    return True


def default_validation_stub() -> bool:
    # Stub: replace/inject in future.
    return True


def run_workflow(
    restore_fn: Callable[[Path], bool] = default_restore_stub,
    validation_fn: Callable[[], bool] = default_validation_stub,
    rng: Optional[random.Random] = None,
    write_report: bool = True,
) -> WorkflowReport:
    run_id = str(uuid.uuid4())
    started_at = _utc_now_iso()
    overall_start = time.time()

    # Initialize report with placeholders
    report = WorkflowReport(
        run_id=run_id,
        started_at=started_at,
        finished_at="",
        duration_ms=0,
        final_status="FAIL",
        backup={"selected": None},
        stages={},
    )

    # Stages
    discovery_outcome: StageOutcome
    restore_outcome: StageOutcome
    validation_outcome: StageOutcome

    try:
        log_info(f"[{run_id}] Workflow Started")

        d_start = time.time()
        backups = discover_backups()
        if not backups:
            discovery_outcome = StageOutcome(
                status="FAILURE",
                duration_ms=_duration_ms(d_start),
                reason="No backups discovered",
                error=None,
            )
            raise FileNotFoundError("No backup files found")

        selected_backup = get_random_backup(backups, rng=rng)
        report.backup["selected"] = {
            "filename": selected_backup.name,
            "path": str(selected_backup),
            "size_bytes": selected_backup.stat().st_size,
            "extension": selected_backup.suffix,
        }
        log_info(f"[{run_id}] Selected Backup: {selected_backup.name}")
        discovery_outcome = StageOutcome(
            status="SUCCESS",
            duration_ms=_duration_ms(d_start),
            reason=None,
            error=None,
        )

        # Restore
        r_start = time.time()
        try:
            restore_ok = bool(restore_fn(selected_backup))
            restore_outcome = StageOutcome(
                status="SUCCESS" if restore_ok else "FAILURE",
                duration_ms=_duration_ms(r_start),
                reason=None if restore_ok else "Restore returned failure",
                error=None,
            )
        except Exception as e:
            restore_outcome = StageOutcome(
                status="ERROR",
                duration_ms=_duration_ms(r_start),
                reason="Restore raised exception",
                error=type(e).__name__ + ": " + str(e),
            )
            log_error(f"[{run_id}] Restore exception: {type(e).__name__}: {e}")
            log_error("TRACE:\n" + traceback.format_exc())
            raise

        if restore_outcome.status != "SUCCESS":
            raise RuntimeError("Restore failed")

        # Validation
        v_start = time.time()
        try:
            validation_ok = bool(validation_fn())
            validation_outcome = StageOutcome(
                status="SUCCESS" if validation_ok else "FAILURE",
                duration_ms=_duration_ms(v_start),
                reason=None if validation_ok else "Validation returned failure",
                error=None,
            )
        except Exception as e:
            validation_outcome = StageOutcome(
                status="ERROR",
                duration_ms=_duration_ms(v_start),
                reason="Validation raised exception",
                error=type(e).__name__ + ": " + str(e),
            )
            log_error(f"[{run_id}] Validation exception: {type(e).__name__}: {e}")
            log_error("TRACE:\n" + traceback.format_exc())
            raise

        report.final_status = "PASS" if validation_outcome.status == "SUCCESS" else "FAIL"

    except Exception as e:
        # Discovery/restore/validation error already logged at stage level where appropriate.
        log_error(f"[{run_id}] Workflow failed: {type(e).__name__}: {e}")
        log_error("TRACE:\n" + traceback.format_exc())

        # Best-effort stage outcomes if unset
        report.final_status = "FAIL"

        # If discovery didn't set outcomes, set generic placeholders
        if "discovery" not in report.stages:
            discovery_outcome = StageOutcome(
                status="ERROR",
                duration_ms=_duration_ms(overall_start),
                reason="Discovery/early failure",
                error=type(e).__name__ + ": " + str(e),
            )
        if "restore" not in report.stages:
            restore_outcome = StageOutcome(
                status="SKIPPED",
                duration_ms=0,
                reason="Not executed due to earlier failure",
                error=None,
            )
        if "validation" not in report.stages:
            validation_outcome = StageOutcome(
                status="SKIPPED",
                duration_ms=0,
                reason="Not executed due to earlier failure",
                error=None,
            )

    finally:
        report.finished_at = _utc_now_iso()
        report.duration_ms = int(_duration_ms(overall_start))

        # Populate stages (only if missing)
        if "discovery" not in report.stages:
            report.stages["discovery"] = asdict(locals().get("discovery_outcome")) if "discovery_outcome" in locals() else None
        if "restore" not in report.stages:
            report.stages["restore"] = asdict(locals().get("restore_outcome")) if "restore_outcome" in locals() else None
        if "validation" not in report.stages:
            report.stages["validation"] = asdict(locals().get("validation_outcome")) if "validation_outcome" in locals() else None

        # If stage outcomes existed earlier, they may not be set into stages yet.
        # Ensure canonical stage keys.
        if "discovery" in locals() and report.stages.get("discovery") is None:
            pass

        report.stages["discovery"] = asdict(locals().get("discovery_outcome"))
        report.stages["restore"] = asdict(locals().get("restore_outcome"))
        report.stages["validation"] = asdict(locals().get("validation_outcome"))

        log_info(f"[{run_id}] Final Result: {report.final_status} (duration_ms={report.duration_ms})")

        if write_report:
            reports_dir = _resolve_path(REPORTS_FOLDER)
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = reports_dir / f"{run_id}.json"
            report_json = report.to_dict()
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(report_json, f, indent=2)
            log_info(f"[{run_id}] Report written: {report_path}")

    # If stubs were used, they always return PASS; still correct per decision logic.
    return report


if __name__ == "__main__":
    run_workflow()

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def create_backup(source_db_path: Path, backup_dir: Path) -> Path:
    """Creates a timestamped backup of the source database."""
    source_db_path = Path(source_db_path)
    backup_dir = Path(backup_dir)
    
    if not source_db_path.exists():
        raise FileNotFoundError(f"Source database not found at {source_db_path}")
        
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.db"
    dest_path = backup_dir / backup_filename
    
    logger.info(f"Creating backup from {source_db_path} to {dest_path}")
    shutil.copy2(source_db_path, dest_path)
    return dest_path

def cleanup_old_backups(backup_dir: Path, retention_days: int) -> list:
    """Deletes backups older than the specified retention days."""
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []
        
    removed_files = []
    now = datetime.now()
    
    for file in backup_dir.iterdir():
        if file.is_file() and file.name.startswith("backup_") and file.suffix == ".db":
            try:
                # Find age of file
                file_time = datetime.fromtimestamp(file.stat().st_mtime)
                age_days = (now - file_time).days
                if age_days >= retention_days:
                    logger.info(f"Deleting expired backup: {file.name} (age: {age_days} days)")
                    file.unlink()
                    removed_files.append(file)
            except Exception as e:
                logger.error(f"Error checking/deleting {file.name}: {e}")
                
    return removed_files

def list_available_backups(backup_dir: Path) -> list:
    """Returns a list of all available backup files sorted chronologically."""
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []
        
    backups = [
        file for file in backup_dir.iterdir()
        if file.is_file() and file.name.startswith("backup_") and file.suffix == ".db"
    ]
    # Sort chronologically by name
    return sorted(backups)

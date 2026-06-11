import os
import shutil
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

def create_sandbox(sandbox_dir: Path) -> Path:
    """Prepares and cleans the sandbox folder for restoration."""
    sandbox_dir = Path(sandbox_dir)
    if sandbox_dir.exists():
        logger.info(f"Cleaning sandbox directory: {sandbox_dir}")
        for item in sandbox_dir.iterdir():
            if item.name != ".gitkeep":
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
    else:
        sandbox_dir.mkdir(parents=True, exist_ok=True)
    return sandbox_dir

def restore_backup(backup_path: Path, sandbox_dir: Path, restored_name: str = "restored.db") -> Path:
    """Copies the backup database to sandbox folder."""
    backup_path = Path(backup_path)
    sandbox_dir = Path(sandbox_dir)
    
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
    create_sandbox(sandbox_dir)
    dest_path = sandbox_dir / restored_name
    
    logger.info(f"Restoring backup {backup_path} to {dest_path}")
    shutil.copy2(backup_path, dest_path)
    return dest_path

def verify_restoration(restored_db_path: Path) -> bool:
    """Tests basic connectivity and accessibility of the restored database."""
    restored_db_path = Path(restored_db_path)
    if not restored_db_path.exists():
        logger.error(f"Restored database file does not exist: {restored_db_path}")
        return False
        
    conn = None
    try:
        conn = sqlite3.connect(restored_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        res = cursor.fetchone()
        if res and res[0] == 1:
            logger.info("Restoration verification connection check successful.")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to verify restored database: {e}")
        return False
    finally:
        if conn:
            conn.close()

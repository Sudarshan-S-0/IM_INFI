import time
import json
import logging
from pathlib import Path
import schedule
from workflow_agent.orchestrator import run_backup_verification_workflow

logger = logging.getLogger(__name__)

def load_config(config_path: Path) -> dict:
    """Loads JSON configuration."""
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def run_job(config_path: Path):
    """Fires a verification run, reloading config first."""
    logger.info("Scheduled task triggered. Hot-reloading config...")
    try:
        config = load_config(config_path)
        success = run_backup_verification_workflow(config, str(config_path))
        if success:
            logger.info("Scheduled job execution completed successfully.")
        else:
            logger.warning("Scheduled job execution returned validation failures.")
    except Exception as e:
        logger.error(f"Scheduled job execution failed: {e}")

def setup_schedules(config_path: Path):
    """Registers schedule triggers based on configuration settings."""
    schedule.clear()
    
    config = load_config(config_path)
    mode = config.get("scheduler_mode", "manual").lower()
    settings = config.get("scheduler_settings", {})
    
    if mode == "manual":
        logger.info("Scheduler mode is set to 'manual'. No jobs scheduled.")
        return False
        
    logger.info(f"Setting up schedule jobs for mode: {mode}")
    
    if mode == "daily":
        daily_time = settings.get("daily_time", "02:00")
        schedule.every().day.at(daily_time).do(run_job, config_path=config_path)
        logger.info(f"Scheduled daily run at {daily_time}")
        
    elif mode == "hourly":
        minute = int(settings.get("hourly_minute", 0))
        # schedule at a specific minute of every hour
        schedule.every().hour.at(f":{minute:02d}").do(run_job, config_path=config_path)
        logger.info(f"Scheduled hourly run at minute :{minute:02d}")
        
    elif mode == "every_n_minutes":
        interval = int(settings.get("every_n_minutes_interval", 15))
        schedule.every(interval).minutes.do(run_job, config_path=config_path)
        logger.info(f"Scheduled run every {interval} minutes")
        
    else:
        logger.warning(f"Unknown scheduler mode: {mode}")
        return False
        
    return True

def start_scheduler_loop(config_path_str: str):
    """Runs the scheduling loop, listening for configuration hot-reloads."""
    config_path = Path(config_path_str)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")
        
    logger.info("Starting Scheduler Daemon. Press Ctrl+C to exit.")
    
    # Initial setup
    setup_schedules(config_path)
    last_mtime = config_path.stat().st_mtime
    
    try:
        while True:
            # Check if config file was modified to hot-reload scheduling definitions
            current_mtime = config_path.stat().st_mtime
            if current_mtime != last_mtime:
                logger.info("Detected change in config.json. Rebuilding schedules...")
                setup_schedules(config_path)
                last_mtime = current_mtime
                
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler Daemon stopped by user.")

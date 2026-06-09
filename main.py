import os
import sys
import json
import argparse
import logging
from pathlib import Path
from workflow_agent.orchestrator import run_backup_verification_workflow
from scheduler import start_scheduler_loop

def setup_logging(config: dict):
    """Configures structured file and console logging."""
    logging_settings = config.get("logging_settings", {})
    log_level_str = logging_settings.get("level", "INFO").upper()
    log_file_str = logging_settings.get("file_path", "logs/backup_verification.log")
    
    log_level = getattr(logging, log_level_str, logging.INFO)
    log_file = Path(log_file_str)
    
    # Ensure logs folder exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Clean up existing log handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    root_logger.setLevel(log_level)
    
    # Quiet noisy external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully.")

def load_config(config_path_str: str) -> dict:
    config_path = Path(config_path_str)
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
        
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main() -> int:
    parser = argparse.ArgumentParser(description="IM_INFI - Backup Verification Simulator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true", help="Run verification workflow once and exit.")
    group.add_argument("--run", action="store_true", help="Start scheduling daemon loop.")
    
    parser.add_argument("--config", type=str, default="config.json", help="Path to config.json settings file.")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Initialize logging
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Backup Verification Simulator.")
    
    if args.once:
        logger.info("Starting one-off execution...")
        success = run_backup_verification_workflow(config, args.config)
        logger.info(f"One-off run complete. Status: {'PASS' if success else 'FAIL'}")
        return 0 if success else 1
        
    elif args.run:
        logger.info("Starting scheduling daemon...")
        try:
            start_scheduler_loop(args.config)
        except Exception as e:
            logger.critical(f"Scheduler daemon crashed: {e}")
            return 1
            
    return 0

if __name__ == "__main__":
    sys.exit(main())

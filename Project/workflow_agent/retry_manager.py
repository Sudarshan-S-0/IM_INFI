import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def execute_with_retry(func: Callable, retries: int, delay_seconds: float, *args, **kwargs) -> Any:
    """Executes a function with retry logic."""
    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt}/{retries} of {func.__name__} failed with error: {e}")
            if attempt < retries:
                logger.info(f"Sleeping for {delay_seconds} seconds before retrying...")
                time.sleep(delay_seconds)
                
    logger.error(f"All {retries} attempts failed for function {func.__name__}")
    raise last_exception

"""
Structured logging with strategy context
"""
import logging
import sys
from config import config

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with consistent formatting"""
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)
    
    # Formatter
    formatter = logging.Formatter(
        config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger

def log_strategy_event(logger: logging.Logger, strategy_id: str, event: str, **kwargs):
    """Log strategy-specific event with context"""
    extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    message = f"[{strategy_id}] {event}"
    if extra_info:
        message += f" | {extra_info}"
    logger.info(message)
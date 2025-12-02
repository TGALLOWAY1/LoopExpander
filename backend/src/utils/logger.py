"""Logging utilities."""
import logging
import sys

from config import LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """
    Create and configure a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logging.Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


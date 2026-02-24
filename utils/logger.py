"""
Logger Utility
==============

Centralized logging configuration for the Quantum Intelligence Hub.
Uses module-prefixed structured logging: [FETCHER], [CLASSIFIER], [STORAGE], etc.
"""

import logging
import sys
from typing import Optional


_configured_loggers = set()


def get_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)

    Returns:
        Configured logger instance

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("[FETCHER] Fetched 10 articles from The Quantum Insider")
    """
    logger = logging.getLogger(name)

    if name in _configured_loggers:
        return logger

    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        if format_string is None:
            format_string = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

        formatter = logging.Formatter(
            format_string,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    _configured_loggers.add(name)

    return logger


def configure_root_logger(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> None:
    """Configure the root logger for the application."""
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

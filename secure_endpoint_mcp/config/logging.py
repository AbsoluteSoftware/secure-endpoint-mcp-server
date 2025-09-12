#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

"""
Logging configuration for the application.

This module configures structlog for JSON logging and provides
a function to get a logger with the appropriate configuration.
"""

import logging
import sys

import structlog
from structlog.types import Processor

from secure_endpoint_mcp.config.settings import settings

# Map string log levels to logging module levels
LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def configure_logging() -> None:
    """
    Configure structlog for JSON logging.

    This sets up structlog to output JSON-formatted logs to stderr
    with the log level configured from settings.

    Note: Some messages from external libraries might still appear if they
    use a different logging mechanism or bypass the standard Python logging
    configuration.
    """
    # Get the log level from settings
    log_level_str = settings.LOG_LEVEL.lower()
    log_level = LOG_LEVEL_MAP.get(log_level_str, logging.INFO)

    # Configure the standard library logging
    logging.basicConfig(
        level=log_level,  # Set the default level to the configured level
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
        force=True,
    )

    logging.getLogger().setLevel(log_level)

    # Configure structlog processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger with the given name.

    Args:
        name: The name of the logger, typically __name__

    Returns:
        A structlog logger configured for JSON logging
    """
    return structlog.get_logger(name)


# Configure logging when the module is imported
configure_logging()

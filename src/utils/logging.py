# src/utils/logging.py

import logging
import os
import sys
from logging import Logger
from logging.handlers import RotatingFileHandler
from typing import Optional

class StructuredLogger:
    """
    A structured logger for the e-commerce platform, providing a consistent logging format
    and handling various logging levels.
    """

    def __init__(self, name: str, log_file: Optional[str] = None, level: int = logging.INFO):
        """
        Initializes the StructuredLogger with a specified name, log file, and logging level.

        :param name: The name of the logger.
        :param log_file: Optional log file path. If None, logs will be output to stderr.
        :param level: The logging level (default: logging.INFO).
        """
        self.logger: Logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Create a console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._get_formatter())
        self.logger.addHandler(console_handler)

        # If a log file is specified, create a file handler
        if log_file:
            file_handler = RotatingFileHandler(log_file, maxBytes=10**6, backupCount=5)
            file_handler.setFormatter(self._get_formatter())
            self.logger.addHandler(file_handler)

    def _get_formatter(self) -> logging.Formatter:
        """
        Returns a structured logging formatter.

        :return: A logging formatter instance.
        """
        return logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", '
            '"message": "%(message)s", "module": "%(module)s", "line": "%(lineno)d"}'
        )

    def debug(self, message: str, **kwargs) -> None:
        """Logs a message with level DEBUG."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Logs a message with level INFO."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Logs a message with level WARNING."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Logs a message with level ERROR."""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Logs a message with level CRITICAL."""
        self.logger.critical(message, extra=kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Logs an exception with level ERROR."""
        self.logger.error(message, exc_info=True, extra=kwargs)

# Example usage:
if __name__ == "__main__":
    log_file_path = os.getenv("LOG_FILE_PATH", "app.log")
    logger = StructuredLogger(name="ECommercePlatformLogger", log_file=log_file_path)

    # Example logging
    logger.info("Application started")
    try:
        # Simulate some operations
        logger.debug("Debugging information")
        raise ValueError("An example error")
    except Exception as e:
        logger.exception("An error occurred", error=str(e))
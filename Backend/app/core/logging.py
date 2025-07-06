"""
Logging configuration
"""
import logging
import logging.config
import sys
from pathlib import Path

from app.config import settings


def setup_logging() -> None:
    """
    Setup application logging configuration
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s [%(pathname)s:%(lineno)d]: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "default",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "": {  # Root logger
                "level": settings.log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app": {
                "level": settings.log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Set logging level for the app
    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    app_logger.info(f"Logging configured with level: {settings.log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Configured logger
    """
    return logging.getLogger(f"app.{name}")
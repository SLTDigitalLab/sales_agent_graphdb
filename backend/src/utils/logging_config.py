import logging
import os
import coloredlogs

def setup_logging():
    """
    Configures the global logging settings for the application.
    Uses coloredlogs for pretty terminal output.
    """
    # Get log level from .env, default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # valid levels safety check
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Standard format: Time - Logger Name - Level - Message
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Install colored logs 
    coloredlogs.install(
        level=log_level,
        fmt=log_format,
        datefmt=date_format,
        level_styles={
            'debug': {'color': 'white', 'faint': True},
            'info': {'color': 'green'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red', 'bold': True},
            'critical': {'color': 'red', 'bold': True, 'background': 'white'},
        },
        field_styles={
            'asctime': {'color': 'cyan'},
            'name': {'color': 'blue'},
            'levelname': {'color': 'magenta', 'bold': True},
        }
    )

    logging.info(f"Logging initialized at level: {log_level}")

def get_logger(name):
    """
    Returns a configured logger instance for a specific file.
    Usage: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
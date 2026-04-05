import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

def setup_logging(config):
    """Setup logging configuration.

    Args:
        config: Configuration object
    """
    # Create logs directory if needed
    config.setup_directories()

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # File handler with rotation
    log_file = config.LOGS_DIR / config.LOG_FILE_PATH.split('/')[-1]
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=config.BACKUP_LOG_COUNT
    )
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logging initialized")
    return logger

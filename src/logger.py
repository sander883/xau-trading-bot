import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def setup_logging(config):
    """Setup logging configuration with color support.

    Args:
        config: Configuration object

    Returns:
        Logger instance
    """
    try:
        # Create logs directory if needed
        if hasattr(config, 'setup_directories'):
            config.setup_directories()
        elif hasattr(config, 'LOGS_DIR'):
            config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Create logger
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, config.LOG_LEVEL))

        # Remove existing handlers
        logger.handlers = []

        # File handler with rotation
        if hasattr(config, 'LOGS_DIR'):
            log_dir = config.LOGS_DIR
        else:
            log_dir = Path('logs')
            log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / config.LOG_FILE_PATH.split('/')[-1]
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=config.BACKUP_LOG_COUNT
        )
        file_handler.setLevel(getattr(logging, config.LOG_LEVEL))

        # Console handler with optional color
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.LOG_LEVEL))

        # Formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        if HAS_COLORLOG:
            console_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            console_formatter = file_formatter

        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        logger.info("=" * 70)
        logger.info("Logging initialized successfully")
        logger.info(f"Log level: {config.LOG_LEVEL}")
        logger.info(f"Log file: {log_file}")
        logger.info("=" * 70)

        return logger

    except Exception as e:
        print(f"ERROR: Failed to setup logging: {e}")
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger()

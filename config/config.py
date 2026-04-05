import os
from dotenv import load_dotenv
from pathlib import Path
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class TradingConfig:
    """Configuration for trading bot with validation."""

    # MetaTrader5 Configuration
    MT5_LOGIN = int(os.getenv('MT5_LOGIN', '0'))
    MT5_PASSWORD = os.getenv('MT5_PASSWORD', '')
    MT5_SERVER = os.getenv('MT5_SERVER', 'MetaQuotes-Demo')

    # Trading Configuration
    SYMBOL = os.getenv('SYMBOL', 'XAUUSD')
    TIMEFRAME = os.getenv('TIMEFRAME', '1H')
    LOT_SIZE = float(os.getenv('LOT_SIZE', '0.1'))
    INITIAL_BALANCE = float(os.getenv('INITIAL_BALANCE', '10000'))

    # Risk Management
    MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', '500'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '2'))
    STOP_LOSS_PIPS = float(os.getenv('STOP_LOSS_PIPS', '50'))
    TAKE_PROFIT_PIPS = float(os.getenv('TAKE_PROFIT_PIPS', '150'))
    MAX_OPEN_TRADES = int(os.getenv('MAX_OPEN_TRADES', '3'))

    # AI Model Configuration
    MODEL_TYPE = os.getenv('MODEL_TYPE', 'xgboost').lower()
    PREDICTION_CONFIDENCE_THRESHOLD = float(os.getenv('PREDICTION_CONFIDENCE_THRESHOLD', '0.65'))
    RETRAIN_FREQUENCY = int(os.getenv('RETRAIN_FREQUENCY', '7'))

    # Telegram Notifications
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    TELEGRAM_NOTIFICATIONS_ENABLED = os.getenv('TELEGRAM_NOTIFICATIONS_ENABLED', 'false').lower() == 'true'

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/trading_bot.log')
    MAX_LOG_SIZE = os.getenv('MAX_LOG_SIZE', '10MB')
    BACKUP_LOG_COUNT = int(os.getenv('BACKUP_LOG_COUNT', '5'))

    # Backtesting
    BACKTEST_START_DATE = os.getenv('BACKTEST_START_DATE', '2023-01-01')
    BACKTEST_END_DATE = os.getenv('BACKTEST_END_DATE', '2024-01-01')
    BACKTEST_INITIAL_CAPITAL = float(os.getenv('BACKTEST_INITIAL_CAPITAL', '10000'))

    @classmethod
    def validate(cls):
        """Validate critical configuration parameters."""
        errors = []

        if cls.MODEL_TYPE not in ['xgboost', 'sklearn']:
            errors.append(f"MODEL_TYPE must be 'xgboost' or 'sklearn', got {cls.MODEL_TYPE}")

        if cls.LOT_SIZE <= 0:
            errors.append("LOT_SIZE must be positive")

        if cls.MAX_DAILY_LOSS <= 0:
            errors.append("MAX_DAILY_LOSS must be positive")

        if cls.PREDICTION_CONFIDENCE_THRESHOLD < 0 or cls.PREDICTION_CONFIDENCE_THRESHOLD > 1:
            errors.append("PREDICTION_CONFIDENCE_THRESHOLD must be between 0 and 1")

        if cls.TELEGRAM_NOTIFICATIONS_ENABLED:
            if not cls.TELEGRAM_BOT_TOKEN or not cls.TELEGRAM_CHAT_ID:
                errors.append("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required when notifications enabled")

        if errors:
            error_msg = "\n".join(errors)
            logger.error(f"Configuration validation failed:\n{error_msg}")
            raise ValueError(f"Configuration validation failed:\n{error_msg}")

        return True

    @classmethod
    def get_timeframe_minutes(cls):
        """Convert timeframe string to minutes."""
        tf_map = {
            '1M': 1, '5M': 5, '15M': 15, '30M': 30,
            '1H': 60, '4H': 240, '1D': 1440
        }
        return tf_map.get(cls.TIMEFRAME, 60)


class Config(TradingConfig):
    """Main configuration class."""

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent
    CONFIG_DIR = PROJECT_ROOT / 'config'
    DATA_DIR = PROJECT_ROOT / 'data'
    LOGS_DIR = PROJECT_ROOT / 'logs'
    MODELS_DIR = PROJECT_ROOT / 'models'
    SRC_DIR = PROJECT_ROOT / 'src'

    # Ensure directories exist
    @classmethod
    def setup_directories(cls):
        """Create necessary directories if they don't exist."""
        for directory in [cls.DATA_DIR, cls.LOGS_DIR, cls.MODELS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

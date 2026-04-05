#!/usr/bin/env python3
"""
AI Trading Bot for XAUUSD (Gold)

Main entry point for the application.
Features:
- MetaTrader5 integration
- AI-powered predictions (XGBoost/sklearn)
- Risk management
- Backtesting
- Telegram notifications
"""

import logging
import time
import signal
import sys
from datetime import datetime, timedelta

from config import Config
from src.logger import setup_logging
from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalysis
from src.ml_model import MLModel
from src.risk_manager import RiskManager
from src.trading_engine import TradingEngine
from src.telegram_notifier import TelegramNotifier
from src.backtester import Backtester

logger = logging.getLogger(__name__)

# Global variables for cleanup
data_fetcher = None
trading_engine = None
telegram_notifier = None


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("Shutdown signal received")
    cleanup()
    sys.exit(0)


def cleanup():
    """Cleanup resources."""
    if trading_engine:
        trading_engine.cleanup()
    if data_fetcher:
        data_fetcher.cleanup()
    if telegram_notifier:
        telegram_notifier.send_system_status('STOPPED', 'Bot shutdown')


def initialize_components(config):
    """Initialize all bot components.

    Args:
        config: Configuration object

    Returns:
        Dictionary with all initialized components
    """
    try:
        logger.info("Initializing trading bot components...")

        # Data fetcher
        data_fetcher = DataFetcher(config)
        if not data_fetcher.connected:
            logger.error("Failed to connect to MetaTrader5")
            return None

        # ML Model
        ml_model = MLModel(config, config.MODEL_TYPE)

        # Risk Manager
        risk_manager = RiskManager(config)

        # Telegram Notifier
        telegram_notifier = TelegramNotifier(config)
        if config.TELEGRAM_NOTIFICATIONS_ENABLED:
            telegram_notifier.send_system_status('STARTING', 'Bot initializing...')

        # Trading Engine
        trading_engine = TradingEngine(
            config,
            data_fetcher,
            risk_manager,
            ml_model,
            telegram_notifier
        )

        logger.info("All components initialized successfully")

        return {
            'data_fetcher': data_fetcher,
            'ml_model': ml_model,
            'risk_manager': risk_manager,
            'trading_engine': trading_engine,
            'telegram_notifier': telegram_notifier,
        }

    except Exception as e:
        logger.error(f"Error initializing components: {e}")
        return None


def train_or_load_model(config, ml_model, data_fetcher):
    """Train or load ML model.

    Args:
        config: Configuration object
        ml_model: MLModel instance
        data_fetcher: DataFetcher instance

    Returns:
        True if successful
    """
    try:
        # Try to load existing model
        latest_model = None
        models_dir = config.MODELS_DIR
        if models_dir.exists():
            models = sorted(models_dir.glob('model_*.pkl'), reverse=True)
            if models:
                latest_model = models[0]

        if latest_model:
            logger.info(f"Loading model from {latest_model}")
            if ml_model.load_model(latest_model):
                return True

        # Train new model
        logger.info("Training new model...")
        historical_data = data_fetcher.get_historical_data(
            config.SYMBOL,
            config.TIMEFRAME,
            config.BACKTEST_START_DATE,
            config.BACKTEST_END_DATE
        )

        if historical_data is None:
            logger.error("Failed to fetch historical data for training")
            return False

        # Calculate technical indicators
        ta = TechnicalAnalysis(historical_data)
        ta.calculate_moving_averages()
        ta.calculate_rsi()
        ta.calculate_bollinger_bands()
        ta.calculate_atr()
        ta.calculate_stochastic()
        ta.calculate_volume_indicators()

        # Prepare and train
        X, y = ml_model.prepare_data(ta.df)
        if X is None:
            logger.error("Failed to prepare data for training")
            return False

        metrics = ml_model.train(X, y)
        if metrics is None:
            logger.error("Model training failed")
            return False

        ml_model.save_model()
        return True

    except Exception as e:
        logger.error(f"Error training/loading model: {e}")
        return False


def backtest_strategy(config, ml_model, data_fetcher):
    """Run backtest on strategy.

    Args:
        config: Configuration object
        ml_model: MLModel instance
        data_fetcher: DataFetcher instance
    """
    try:
        logger.info("Starting backtest...")

        # Fetch historical data
        historical_data = data_fetcher.get_historical_data(
            config.SYMBOL,
            config.TIMEFRAME,
            config.BACKTEST_START_DATE,
            config.BACKTEST_END_DATE
        )

        if historical_data is None:
            logger.error("Failed to fetch data for backtest")
            return

        # Create backtester
        backtester = Backtester(config)

        # Run backtest
        results = backtester.run_backtest(
            historical_data,
            ml_model,
            lambda df: TechnicalAnalysis(df).calculate_moving_averages()
        )

        if results:
            logger.info(f"""
Backtest Results:
- Total Trades: {results['total_trades']}
- Win Rate: {results['win_rate']:.1f}%
- ROI: {results['roi']:.2f}%
- Profit Factor: {results['profit_factor']:.2f}
- Max Drawdown: {results['max_drawdown']:.2f}%
- Sharpe Ratio: {results['sharpe_ratio']:.2f}
            """)

            # Export report
            backtester.export_backtest_report()

    except Exception as e:
        logger.error(f"Error during backtest: {e}")


def main_trading_loop(components, config):
    """Main trading loop.

    Args:
        components: Dictionary with initialized components
        config: Configuration object
    """
    try:
        data_fetcher = components['data_fetcher']
        ml_model = components['ml_model']
        risk_manager = components['risk_manager']
        trading_engine = components['trading_engine']
        telegram_notifier = components['telegram_notifier']

        logger.info("Starting main trading loop...")
        telegram_notifier.send_system_status('RUNNING', f'Symbol: {config.SYMBOL}, Timeframe: {config.TIMEFRAME}')

        last_report_time = datetime.now()
        cycle_count = 0

        while True:
            try:
                # Fetch current data
                df = data_fetcher.get_ohlc_data(config.SYMBOL, config.TIMEFRAME, 500)
                if df is None:
                    logger.warning("Failed to fetch OHLC data, retrying...")
                    time.sleep(60)
                    continue

                # Calculate technical indicators
                ta = TechnicalAnalysis(df)
                ta.calculate_moving_averages()
                ta.calculate_rsi()
                ta.calculate_bollinger_bands()
                ta.calculate_atr()
                ta.calculate_stochastic()
                ta.calculate_volume_indicators()

                # Get current price
                current_price = df['Close'].iloc[-1]

                # Extract features for ML
                features = ta.get_features_for_ml()
                if features is not None and len(features) > 0:
                    # Use last row as input
                    ml_features = features.iloc[-1].values.reshape(1, -1)

                    # Execute trading cycle
                    cycle_result = trading_engine.execute_trading_cycle(
                        ml_features,
                        ta,
                        current_price
                    )

                    cycle_count += 1
                    logger.debug(f"Trading cycle {cycle_count} completed: "
                               f"Trend={cycle_result['trend']}, "
                               f"Prediction={cycle_result['prediction']}, "
                               f"Confidence={cycle_result['confidence']:.2f}")

                # Send daily report
                if datetime.now() - last_report_time >= timedelta(hours=24):
                    account_info = trading_engine.get_account_info()
                    risk_metrics = risk_manager.get_risk_metrics()

                    if account_info and risk_metrics:
                        telegram_notifier.send_daily_report(risk_metrics, account_info)
                    last_report_time = datetime.now()

                # Wait for next cycle (check every minute or based on config)
                wait_time = max(60, config.get_timeframe_minutes() * 60)
                logger.debug(f"Waiting {wait_time} seconds for next cycle...")
                time.sleep(wait_time)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                telegram_notifier.send_error_alert(str(e))
                time.sleep(60)

    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise


def main():
    """Main entry point."""
    try:
        # Setup configuration
        Config.setup_directories()
        Config.validate()

        # Setup logging
        setup_logging(Config)
        logger.info("="*50)
        logger.info("AI Trading Bot for XAUUSD")
        logger.info(f"Start time: {datetime.now()}")
        logger.info("="*50)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Initialize components
        components = initialize_components(Config)
        if components is None:
            logger.error("Failed to initialize components")
            return

        # Check command line arguments
        import sys
        if len(sys.argv) > 1:
            if sys.argv[1] == 'backtest':
                logger.info("Running in backtest mode...")
                backtest_strategy(Config, components['ml_model'], components['data_fetcher'])
                return

        # Train or load model
        if not train_or_load_model(Config, components['ml_model'], components['data_fetcher']):
            logger.error("Failed to prepare model")
            return

        # Start main trading loop
        main_trading_loop(components, Config)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        cleanup()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
AI Trading Bot for XAUUSD (Gold)

Production-ready main entry point with comprehensive logging and error handling.
Features:
- MetaTrader5 integration
- AI-powered predictions with advanced feature engineering
- Risk management with dynamic position sizing
- XAUUSD-specific optimizations
- Backtesting system
- Telegram notifications
- Comprehensive logging
"""

import logging
import time
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Import configuration first
try:
    from config import Config
    logger_setup_done = False
except Exception as e:
    print(f"FATAL: Failed to import Config: {e}")
    sys.exit(1)

# Setup logging
try:
    from src.logger import setup_logging
    setup_logging(Config)
    logger = logging.getLogger(__name__)
    logger_setup_done = True
    logger.info("Main script started")
except Exception as e:
    print(f"FATAL: Failed to setup logging: {e}")
    sys.exit(1)

# Import all modules with error handling
MODULES = {}
MODULE_LIST = [
    ('DataFetcher', 'src.data_fetcher'),
    ('TechnicalAnalysis', 'src.technical_analysis'),
    ('AdvancedMLModel', 'src.advanced_ml_model'),
    ('RiskManager', 'src.risk_manager'),
    ('TradingEngine', 'src.trading_engine'),
    ('TelegramNotifier', 'src.telegram_notifier'),
    ('Backtester', 'src.backtester'),
    ('MarketSessionFilter', 'src.market_session_filter'),
    ('PatternDetector', 'src.pattern_detector'),
    ('LiquidityDetector', 'src.liquidity_detector'),
    ('MarketConditionDetector', 'src.market_condition_detector'),
    ('NewsEventDetector', 'src.news_event_detector'),
    ('SpreadChecker', 'src.spread_checker'),
    ('XAUUSDVolatilityFilter', 'src.xauusd_volatility_filter'),
    ('XAUUSDOptimizer', 'src.xauusd_optimizer'),
]

logger.info(f"Importing {len(MODULE_LIST)} modules...")

for class_name, module_path in MODULE_LIST:
    try:
        module = __import__(module_path, fromlist=[class_name])
        MODULES[class_name] = getattr(module, class_name)
        logger.debug(f"✓ Imported {class_name}")
    except Exception as e:
        logger.error(f"✗ Failed to import {class_name} from {module_path}: {e}")
        MODULES[class_name] = None

# Global state
state = {
    'data_fetcher': None,
    'trading_engine': None,
    'telegram_notifier': None,
    'running': False,
    'start_time': None,
}


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.warning(f"\nShutdown signal received ({sig})")
    state['running'] = False
    cleanup()
    sys.exit(0)


def cleanup():
    """Cleanup resources and close connections."""
    logger.info("=" * 70)
    logger.info("Cleanup: Closing resources...")

    try:
        if state['trading_engine']:
            logger.info("Cleanup: Closing trading engine...")
            state['trading_engine'].cleanup()
            logger.info("✓ Trading engine closed")
    except Exception as e:
        logger.error(f"Error closing trading engine: {e}")

    try:
        if state['data_fetcher']:
            logger.info("Cleanup: Closing data fetcher...")
            state['data_fetcher'].cleanup()
            logger.info("✓ Data fetcher closed")
    except Exception as e:
        logger.error(f"Error closing data fetcher: {e}")

    try:
        if state['telegram_notifier']:
            logger.info("Cleanup: Sending shutdown notification...")
            state['telegram_notifier'].send_system_status('STOPPED', 'Bot shutdown')
            logger.info("✓ Shutdown notification sent")
    except Exception as e:
        logger.error(f"Error sending shutdown notification: {e}")

    logger.info("Cleanup: Complete")
    logger.info("=" * 70)


def validate_configuration():
    """Validate configuration settings.

    Returns:
        True if valid, False otherwise
    """
    logger.info("=" * 70)
    logger.info("Configuration Validation")
    logger.info("=" * 70)

    try:
        Config.setup_directories()
        logger.info(f"✓ Directories created")

        Config.validate()
        logger.info(f"✓ Configuration validated")

        # Log key settings
        logger.info(f"  Symbol: {Config.SYMBOL}")
        logger.info(f"  Timeframe: {Config.TIMEFRAME}")
        logger.info(f"  Lot Size: {Config.LOT_SIZE}")
        logger.info(f"  Initial Balance: ${Config.INITIAL_BALANCE:,.2f}")
        logger.info(f"  Max Daily Loss: ${Config.MAX_DAILY_LOSS:,.2f}")
        logger.info(f"  Risk Per Trade: {Config.RISK_PERCENT_PER_TRADE}%")
        logger.info(f"  Model Type: {Config.MODEL_TYPE}")
        logger.info(f"  Notifications: {'Enabled' if Config.TELEGRAM_NOTIFICATIONS_ENABLED else 'Disabled'}")

        return True

    except Exception as e:
        logger.error(f"✗ Configuration validation failed: {e}")
        return False


def initialize_components():
    """Initialize all trading components.

    Returns:
        Dictionary with initialized components or None if failed
    """
    logger.info("=" * 70)
    logger.info("Component Initialization")
    logger.info("=" * 70)

    components = {}

    try:
        # 1. Data Fetcher
        logger.info("1. Initializing DataFetcher...")
        DataFetcher = MODULES.get('DataFetcher')
        if not DataFetcher:
            raise ImportError("DataFetcher module not available")

        state['data_fetcher'] = DataFetcher(Config)
        if not state['data_fetcher'].connected:
            logger.error("✗ Failed to connect to MetaTrader5")
            logger.info("  Make sure MetaTrader5 is running and logged in")
            return None

        logger.info("✓ DataFetcher initialized")
        components['data_fetcher'] = state['data_fetcher']

        # 2. ML Model
        logger.info("2. Initializing Advanced ML Model...")
        AdvancedMLModel = MODULES.get('AdvancedMLModel')
        if not AdvancedMLModel:
            logger.warning("⚠ AdvancedMLModel not available, using standard MLModel")
            from src.ml_model import MLModel
            ml_model = MLModel(Config, Config.MODEL_TYPE)
        else:
            ml_model = AdvancedMLModel(Config, Config.MODEL_TYPE)

        logger.info(f"✓ ML Model initialized ({Config.MODEL_TYPE})")
        components['ml_model'] = ml_model

        # 3. Risk Manager
        logger.info("3. Initializing RiskManager...")
        RiskManager = MODULES.get('RiskManager')
        if not RiskManager:
            raise ImportError("RiskManager module not available")

        components['risk_manager'] = RiskManager(Config)
        logger.info("✓ RiskManager initialized")

        # 4. Telegram Notifier
        logger.info("4. Initializing TelegramNotifier...")
        TelegramNotifier = MODULES.get('TelegramNotifier')
        if not TelegramNotifier:
            raise ImportError("TelegramNotifier module not available")

        state['telegram_notifier'] = TelegramNotifier(Config)
        if Config.TELEGRAM_NOTIFICATIONS_ENABLED:
            state['telegram_notifier'].send_system_status('STARTING', 'Bot initializing...')
            logger.info("✓ TelegramNotifier initialized and notification sent")
        else:
            logger.info("✓ TelegramNotifier initialized (notifications disabled)")

        components['telegram_notifier'] = state['telegram_notifier']

        # 5. Trading Engine
        logger.info("5. Initializing TradingEngine...")
        TradingEngine = MODULES.get('TradingEngine')
        if not TradingEngine:
            raise ImportError("TradingEngine module not available")

        state['trading_engine'] = TradingEngine(
            Config,
            state['data_fetcher'],
            components['risk_manager'],
            ml_model,
            state['telegram_notifier']
        )
        logger.info("✓ TradingEngine initialized")
        components['trading_engine'] = state['trading_engine']

        # 6. XAUUSD Optimizer
        logger.info("6. Initializing XAUUSD Optimizer...")
        XAUUSDOptimizer = MODULES.get('XAUUSDOptimizer')
        if XAUUSDOptimizer:
            # Will be initialized with live data
            logger.info("✓ XAUUSD Optimizer module available")
        else:
            logger.warning("⚠ XAUUSD Optimizer not available")

        components['xauusd_optimizer'] = XAUUSDOptimizer

        logger.info("=" * 70)
        logger.info("✓ ALL COMPONENTS INITIALIZED SUCCESSFULLY")
        logger.info("=" * 70)

        return components

    except Exception as e:
        logger.error(f"✗ Component initialization failed: {e}", exc_info=True)
        return None


def train_or_load_model(ml_model, data_fetcher):
    """Train or load ML model.

    Args:
        ml_model: ML model instance
        data_fetcher: Data fetcher instance

    Returns:
        True if successful
    """
    logger.info("=" * 70)
    logger.info("Model Training/Loading")
    logger.info("=" * 70)

    try:
        # Try to load existing model
        models_dir = Config.MODELS_DIR
        if models_dir.exists():
            models = sorted(models_dir.glob('model_*.pkl'), reverse=True)
            if models:
                latest_model = models[0]
                logger.info(f"Found existing model: {latest_model.name}")
                logger.info("Loading model...")

                if ml_model.load_model(latest_model):
                    logger.info("✓ Model loaded successfully")
                    return True

        # Train new model
        logger.info("Training new model...")
        logger.info("Fetching historical data...")

        historical_data = data_fetcher.get_historical_data(
            Config.SYMBOL,
            Config.TIMEFRAME,
            Config.BACKTEST_START_DATE,
            Config.BACKTEST_END_DATE
        )

        if historical_data is None:
            logger.error("✗ Failed to fetch historical data")
            return False

        logger.info(f"✓ Fetched {len(historical_data)} candles")

        # Calculate indicators
        logger.info("Calculating technical indicators...")
        ta = __import__('src.technical_analysis', fromlist=['TechnicalAnalysis']).TechnicalAnalysis(historical_data)
        ta.calculate_moving_averages()
        ta.calculate_rsi()
        ta.calculate_bollinger_bands()
        ta.calculate_atr()
        ta.calculate_stochastic()
        ta.calculate_volume_indicators()
        logger.info("✓ Indicators calculated")

        # Prepare and train
        logger.info("Preparing data for training...")
        X, y = ml_model.prepare_data(ta.df)

        if X is None:
            logger.error("✗ Failed to prepare data")
            return False

        logger.info(f"✓ Data prepared: {X.shape[0]} samples")

        logger.info("Training model...")
        metrics = ml_model.train(X, y)

        if metrics is None:
            logger.error("✗ Model training failed")
            return False

        logger.info(f"✓ Model trained successfully")
        logger.info(f"  Train Accuracy: {metrics.get('train_accuracy', 0):.2%}")
        logger.info(f"  Test Accuracy: {metrics.get('test_accuracy', 0):.2%}")

        # Save model
        logger.info("Saving model...")
        ml_model.save_model()
        logger.info("✓ Model saved")

        return True

    except Exception as e:
        logger.error(f"✗ Model training/loading failed: {e}", exc_info=True)
        return False


def run_backtest(components):
    """Run backtest on strategy.

    Args:
        components: Initialized components

    Returns:
        True if successful
    """
    logger.info("=" * 70)
    logger.info("BACKTEST MODE")
    logger.info("=" * 70)

    try:
        data_fetcher = components['data_fetcher']
        ml_model = components['ml_model']
        Backtester = MODULES.get('Backtester')

        if not Backtester:
            logger.error("✗ Backtester module not available")
            return False

        logger.info("Fetching historical data for backtest...")
        historical_data = data_fetcher.get_historical_data(
            Config.SYMBOL,
            Config.TIMEFRAME,
            Config.BACKTEST_START_DATE,
            Config.BACKTEST_END_DATE
        )

        if historical_data is None:
            logger.error("✗ Failed to fetch historical data")
            return False

        logger.info(f"✓ Fetched {len(historical_data)} candles")

        # Create backtester
        backtester = Backtester(Config)

        logger.info("Running backtest...")
        TechnicalAnalysis = MODULES.get('TechnicalAnalysis')

        results = backtester.run_backtest(
            historical_data,
            ml_model,
            lambda df: TechnicalAnalysis(df).calculate_moving_averages()
        )

        if results:
            logger.info("=" * 70)
            logger.info("BACKTEST RESULTS")
            logger.info("=" * 70)
            logger.info(f"Total Trades: {results.get('total_trades', 0)}")
            logger.info(f"Winning Trades: {results.get('winning_trades', 0)}")
            logger.info(f"Losing Trades: {results.get('losing_trades', 0)}")
            logger.info(f"Win Rate: {results.get('win_rate', 0):.1f}%")
            logger.info(f"ROI: {results.get('roi', 0):.2f}%")
            logger.info(f"Profit Factor: {results.get('profit_factor', 0):.2f}")
            logger.info(f"Max Drawdown: {results.get('max_drawdown', 0):.2f}%")
            logger.info(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
            logger.info("=" * 70)

            # Export reports
            logger.info("Exporting backtest reports...")
            backtester.export_backtest_report()
            if hasattr(backtester, 'export_html_report'):
                backtester.export_html_report()
            if hasattr(backtester, 'export_summary_text'):
                backtester.export_summary_text()
            logger.info("✓ Reports exported to data/ directory")

            return True

        logger.error("✗ Backtest failed")
        return False

    except Exception as e:
        logger.error(f"✗ Backtest error: {e}", exc_info=True)
        return False


def main_trading_loop(components):
    """Main trading loop.

    Args:
        components: Initialized components
    """
    data_fetcher = components['data_fetcher']
    ml_model = components['ml_model']
    risk_manager = components['risk_manager']
    trading_engine = components['trading_engine']
    telegram_notifier = components['telegram_notifier']
    XAUUSDOptimizer = components.get('xauusd_optimizer')

    logger.info("=" * 70)
    logger.info("LIVE TRADING MODE")
    logger.info("=" * 70)
    logger.info(f"Symbol: {Config.SYMBOL}")
    logger.info(f"Timeframe: {Config.TIMEFRAME}")
    logger.info(f"Start Time: {datetime.now()}")
    logger.info("=" * 70)

    state['running'] = True
    state['start_time'] = datetime.now()
    cycle_count = 0
    last_report_time = datetime.now()

    while state['running']:
        try:
            cycle_count += 1
            cycle_start = datetime.now()

            # Log cycle start
            logger.debug(f"\n{'='*50}")
            logger.debug(f"TRADING CYCLE #{cycle_count}")
            logger.debug(f"{'='*50}")

            # Fetch data
            logger.debug("Fetching market data...")
            df = data_fetcher.get_ohlc_data(Config.SYMBOL, Config.TIMEFRAME, 500)

            if df is None:
                logger.warning("Failed to fetch data, retrying in 60 seconds...")
                time.sleep(60)
                continue

            current_price = df['Close'].iloc[-1]
            logger.info(f"Cycle {cycle_count}: Current Price: {current_price:.2f}")

            # Technical Analysis
            logger.debug("Calculating technical indicators...")
            TechnicalAnalysis = MODULES.get('TechnicalAnalysis')
            ta = TechnicalAnalysis(df)
            ta.calculate_moving_averages()
            ta.calculate_rsi()
            ta.calculate_bollinger_bands()
            ta.calculate_atr()
            ta.calculate_stochastic()
            ta.calculate_volume_indicators()

            logger.debug(f"  Trend: {ta.identify_trend()}")
            logger.debug(f"  Signal Strength: {ta.get_signal_strength()}")

            # Get features for ML
            logger.debug("Extracting ML features...")
            features = ta.get_features_for_ml()

            if features is not None and len(features) > 0:
                ml_features = features.iloc[-1].values.reshape(1, -1)

                # Make prediction
                logger.debug("Getting ML prediction...")
                prediction, confidence, is_confident = ml_model.predict_with_confidence(ml_features)

                if is_confident:
                    signal_type = 'BUY' if prediction == 1 else 'SELL'
                    logger.info(f"Signal: {signal_type} (Confidence: {confidence:.2%})")
                else:
                    logger.debug(f"Low confidence prediction: {confidence:.2%}")

            # Check daily loss
            logger.debug(f"Daily Loss: ${risk_manager.daily_loss:.2f} / ${Config.MAX_DAILY_LOSS:.2f}")

            # Cycle timing
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            logger.debug(f"Cycle Duration: {cycle_duration:.2f}s")

            # Daily report
            if datetime.now() - last_report_time >= timedelta(hours=24):
                logger.info("=" * 70)
                logger.info("DAILY REPORT")
                logger.info("=" * 70)

                account_info = trading_engine.get_account_info()
                if account_info:
                    logger.info(f"Balance: ${account_info['balance']:,.2f}")
                    logger.info(f"Equity: ${account_info['equity']:,.2f}")
                    logger.info(f"Profit: ${account_info['profit']:,.2f}")

                metrics = risk_manager.get_risk_metrics()
                logger.info(f"Open Trades: {metrics['open_trades']}")
                logger.info(f"Total Closed: {metrics['total_closed_trades']}")
                logger.info(f"Win Rate: {metrics['win_rate']:.1f}%")
                logger.info(f"Total P&L: ${metrics['total_profit_loss']:,.2f}")

                logger.info("=" * 70)

                if telegram_notifier:
                    telegram_notifier.send_daily_report(metrics, account_info)

                last_report_time = datetime.now()

            # Wait for next cycle
            wait_time = max(60, Config.get_timeframe_minutes() * 60)
            logger.debug(f"Waiting {wait_time} seconds for next cycle...")
            time.sleep(min(wait_time, 60))  # Check every minute max

        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt received")
            break

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            if telegram_notifier:
                telegram_notifier.send_error_alert(f"Trading cycle error: {str(e)}")
            time.sleep(60)  # Wait before retry


def main():
    """Main entry point."""
    try:
        logger.info("="*70)
        logger.info("AI TRADING BOT FOR XAUUSD")
        logger.info("="*70)
        logger.info(f"Start Time: {datetime.now()}")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Config File: {Path('.env').absolute()}")
        logger.info("="*70)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Validate configuration
        if not validate_configuration():
            logger.error("Configuration validation failed. Exiting.")
            sys.exit(1)

        # Initialize components
        components = initialize_components()
        if components is None:
            logger.error("Component initialization failed. Exiting.")
            sys.exit(1)

        # Check for command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == 'backtest':
                logger.info("Running in BACKTEST mode...")
                if run_backtest(components):
                    logger.info("Backtest completed successfully")
                    sys.exit(0)
                else:
                    logger.error("Backtest failed")
                    sys.exit(1)

        # Train or load model
        logger.info("Preparing ML model...")
        if not train_or_load_model(components['ml_model'], components['data_fetcher']):
            logger.error("Model preparation failed. Exiting.")
            sys.exit(1)

        # Start main trading loop
        logger.info("Starting main trading loop...")
        main_trading_loop(components)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        cleanup()
        logger.info("Bot stopped")


if __name__ == '__main__':
    main()

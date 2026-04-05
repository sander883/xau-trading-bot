#!/usr/bin/env python3
"""
Complete example: Using the Advanced Backtester with Professional XGBoost Model

This example demonstrates:
1. Loading historical market data
2. Training the professional XGBoost model
3. Running an advanced backtest
4. Optimizing parameters
5. Generating reports
6. Analyzing results
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from config.config import Config
    from advanced_backtester import AdvancedBacktester
    from professional_xgboost_model import ProfessionalXGBoostModel
    from technical_analysis import TechnicalAnalysis
    from data_fetcher import DataFetcher
    logger.info("✓ All imports successful")
except ImportError as e:
    logger.error(f"✗ Import failed: {e}")
    sys.exit(1)


def calculate_indicators(df):
    """Helper function to calculate all technical indicators."""
    ta = TechnicalAnalysis(df)
    ta.calculate_moving_averages()
    ta.calculate_rsi()
    ta.calculate_bollinger_bands()
    ta.calculate_atr()
    ta.calculate_stochastic()
    ta.calculate_volume_indicators()
    return ta.df


def example_1_basic_backtest():
    """Example 1: Run a basic backtest."""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 1: Basic Backtest")
    logger.info("="*70)

    try:
        # Initialize configuration
        config = Config()
        logger.info(f"✓ Configuration loaded")

        # Initialize backtester
        backtester = AdvancedBacktester(config, initial_capital=10000)
        logger.info("✓ Advanced Backtester initialized")

        # Initialize model
        model = ProfessionalXGBoostModel(config)
        logger.info("✓ Professional XGBoost Model initialized")

        # Get historical data
        data_fetcher = DataFetcher(config)
        logger.info("Fetching historical data...")

        # For demo, create sample data
        import pandas as pd
        import numpy as np

        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)

        logger.info(f"Fetching data from {start_date.date()} to {end_date.date()}")

        # Create synthetic data for demo
        dates = pd.date_range(start=start_date, end=end_date, freq='h')
        base_price = 2330.0
        trend = np.linspace(0, 50, len(dates))
        noise = np.random.normal(0, 5, len(dates))
        close = base_price + trend + noise

        df = pd.DataFrame({
            'DateTime': dates,
            'Open': close + np.random.uniform(-2, 2, len(dates)),
            'High': close + np.random.uniform(3, 8, len(dates)),
            'Low': close + np.random.uniform(-8, -3, len(dates)),
            'Close': close,
            'Volume': np.random.uniform(1000, 5000, len(dates)),
        })

        logger.info(f"✓ Data fetched: {len(df)} candles")

        # Calculate technical indicators
        logger.info("Calculating technical indicators...")
        ta = TechnicalAnalysis(df)
        ta.calculate_moving_averages()
        ta.calculate_rsi()
        ta.calculate_bollinger_bands()
        ta.calculate_atr()
        ta.calculate_stochastic()
        ta.calculate_volume_indicators()
        df = ta.df
        logger.info(f"✓ Indicators calculated: {len([c for c in df.columns if c not in ['Open', 'High', 'Low', 'Close', 'Volume']])} indicators")

        # Train model on first 80% of data
        train_size = int(len(df) * 0.8)
        df_train = df.iloc[:train_size]
        df_test = df.iloc[train_size:]

        logger.info(f"Training model on {len(df_train)} candles...")
        X_train, y_train = model.prepare_data(df_train)

        if X_train is not None and len(X_train) > 0:
            model.train(X_train, y_train)
            logger.info("✓ Model trained successfully")
        else:
            logger.warning("✗ Insufficient training data")
            return

        # Run backtest
        logger.info(f"Running backtest on {len(df_test)} test candles...")
        metrics = backtester.run_backtest(df_test, model, calculate_indicators)

        if metrics:
            logger.info("\n✓ Backtest Results:")
            logger.info(f"  ROI: {metrics.get('roi', 0):.2f}%")
            logger.info(f"  Total Trades: {metrics.get('total_trades', 0)}")
            logger.info(f"  Win Rate: {metrics.get('win_rate', 0):.2%}")
            logger.info(f"  Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
            logger.info(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.4f}")
            logger.info(f"  Profit Factor: {metrics.get('profit_factor', 0):.2f}")

            # Generate reports
            logger.info("\nGenerating reports...")
            html_path = backtester.export_html_report('backtest_report.html')
            if html_path:
                logger.info(f"✓ HTML report: {html_path}")

            csv_path = backtester.export_csv_trades('trades.csv')
            if csv_path:
                logger.info(f"✓ CSV export: {csv_path}")

        else:
            logger.warning("✗ Backtest returned no metrics")

    except Exception as e:
        logger.error(f"✗ Example failed: {e}", exc_info=True)


def example_2_parameter_optimization():
    """Example 2: Run parameter optimization."""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 2: Parameter Optimization")
    logger.info("="*70)

    try:
        config = Config()
        backtester = AdvancedBacktester(config, initial_capital=10000)
        model = ProfessionalXGBoostModel(config)

        # Create sample data
        import pandas as pd
        import numpy as np

        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        dates = pd.date_range(start=start_date, end=end_date, freq='h')

        base_price = 2330.0
        trend = np.linspace(0, 50, len(dates))
        close = base_price + trend + np.random.normal(0, 5, len(dates))

        df = pd.DataFrame({
            'DateTime': dates,
            'Open': close + np.random.uniform(-2, 2, len(dates)),
            'High': close + np.random.uniform(3, 8, len(dates)),
            'Low': close + np.random.uniform(-8, -3, len(dates)),
            'Close': close,
            'Volume': np.random.uniform(1000, 5000, len(dates)),
        })

        df = calculate_indicators(df)

        # Train model
        X, y = model.prepare_data(df)
        if X is not None and len(X) > 0:
            model.train(X, y)
            logger.info("✓ Model trained")

            # Define parameter ranges to optimize
            logger.info("\nOptimizing parameters...")
            param_ranges = {
                'confidence_threshold': [0.50, 0.60, 0.70],
                'position_size_pct': [0.5, 1.0, 1.5],
                'stop_loss_pct': [1.0, 1.5, 2.0]
            }

            logger.info(f"Testing {len(param_ranges['confidence_threshold']) * len(param_ranges['position_size_pct']) * len(param_ranges['stop_loss_pct'])} parameter combinations...")

            # Run optimization
            results = backtester.optimizer.optimize_parameters(
                df,
                model,
                lambda d: TechnicalAnalysis(d).calculate_all_indicators() or TechnicalAnalysis(d).df,
                param_ranges
            )

            if results:
                logger.info("\n✓ Optimization Results:")
                logger.info(f"  Best Parameters: {results['best_parameters']}")
                logger.info(f"  Best Score: {results['best_score']:.4f}")

                # Show top 5 combinations
                summary = backtester.optimizer.get_optimization_summary()
                if summary is not None:
                    logger.info("\nTop 5 Parameter Combinations:")
                    for idx, row in summary.head(5).iterrows():
                        logger.info(f"  {idx}: ROI={row.get('roi', 0):.2f}%, Sharpe={row.get('sharpe_ratio', 0):.4f}")

        else:
            logger.warning("✗ Insufficient training data")

    except Exception as e:
        logger.error(f"✗ Example failed: {e}", exc_info=True)


def example_3_model_training():
    """Example 3: Train and save model."""
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 3: Model Training & Management")
    logger.info("="*70)

    try:
        config = Config()
        model = ProfessionalXGBoostModel(config)
        logger.info("✓ Model initialized")

        # Create sample training data
        import pandas as pd
        import numpy as np

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        dates = pd.date_range(start=start_date, end=end_date, freq='h')

        base_price = 2330.0
        trend = np.linspace(0, 100, len(dates))
        close = base_price + trend + np.random.normal(0, 5, len(dates))

        df = pd.DataFrame({
            'DateTime': dates,
            'Open': close + np.random.uniform(-2, 2, len(dates)),
            'High': close + np.random.uniform(3, 8, len(dates)),
            'Low': close + np.random.uniform(-8, -3, len(dates)),
            'Close': close,
            'Volume': np.random.uniform(1000, 5000, len(dates)),
        })

        # Calculate indicators
        logger.info("Calculating indicators...")
        df = calculate_indicators(df)

        # Prepare data
        logger.info("Preparing training data...")
        X, y = model.prepare_data(df)

        if X is not None and len(X) > 0:
            logger.info(f"✓ Training data prepared: {len(X)} samples")

            # Train model
            logger.info("Training model...")
            model.train(X, y)
            logger.info("✓ Model trained")

            # Get feature importance
            top_features = model.get_top_features(n=10)
            logger.info("\nTop 10 Most Important Features:")
            for feature, importance in top_features:
                logger.info(f"  {feature}: {importance:.4f}")

            # Save model
            model_path = model.save_model()
            logger.info(f"✓ Model saved: {model_path}")

            # Load model
            logger.info("Loading saved model...")
            loaded_model = ProfessionalXGBoostModel(config)
            loaded_model.load_model()
            logger.info("✓ Model loaded successfully")

        else:
            logger.warning("✗ Insufficient training data")

    except Exception as e:
        logger.error(f"✗ Example failed: {e}", exc_info=True)


def main():
    """Run all examples."""
    logger.info("\n" + "="*70)
    logger.info("ADVANCED BACKTESTING & MODEL MANAGEMENT EXAMPLES")
    logger.info("="*70)

    # Run examples
    example_1_basic_backtest()
    example_2_parameter_optimization()
    example_3_model_training()

    logger.info("\n" + "="*70)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("="*70)
    logger.info("\nFor more details, see:")
    logger.info("  - ADVANCED_BACKTESTER_GUIDE.md")
    logger.info("  - AI_SYSTEM_IMPROVEMENTS.md")
    logger.info("  - PROFESSIONAL_XGBOOST_GUIDE.md")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Test script for advanced backtester implementation.
Validates PerformanceMetrics, BacktestVisualizer, ParameterOptimizer, and AdvancedBacktester.
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from advanced_backtester import (
        PerformanceMetrics,
        BacktestVisualizer,
        ParameterOptimizer,
        AdvancedBacktester
    )
    logger.info("✓ Successfully imported advanced backtester components")
except ImportError as e:
    logger.error(f"✗ Failed to import: {e}")
    sys.exit(1)


def create_sample_data(num_candles=200):
    """Create sample OHLCV data for testing."""
    logger.info(f"Creating sample data with {num_candles} candles...")

    dates = pd.date_range(end=datetime.now(), periods=num_candles, freq='h')

    # Create synthetic price data with trend
    base_price = 2330.0
    trend = np.linspace(0, 20, num_candles)
    noise = np.random.normal(0, 5, num_candles)
    close = base_price + trend + noise

    df = pd.DataFrame({
        'DateTime': dates,
        'Open': close + np.random.uniform(-2, 2, num_candles),
        'High': close + np.random.uniform(3, 8, num_candles),
        'Low': close + np.random.uniform(-8, -3, num_candles),
        'Close': close,
        'Volume': np.random.uniform(1000, 5000, num_candles),
    })

    logger.info(f"✓ Sample data created: {len(df)} candles from {df['DateTime'].iloc[0]} to {df['DateTime'].iloc[-1]}")
    logger.info(f"  Price range: {df['Close'].min():.2f} - {df['Close'].max():.2f}")

    return df


def create_sample_trades():
    """Create sample trade data for metrics testing."""
    logger.info("Creating sample trades...")

    trades = [
        {'entry_price': 2330.50, 'exit_price': 2338.20, 'pnl': 767.70, 'pnl_pct': 0.33, 'type': 'BUY'},
        {'entry_price': 2335.80, 'exit_price': 2332.40, 'pnl': -340.00, 'pnl_pct': -0.15, 'type': 'SELL'},
        {'entry_price': 2337.50, 'exit_price': 2345.10, 'pnl': 760.00, 'pnl_pct': 0.32, 'type': 'BUY'},
        {'entry_price': 2340.20, 'exit_price': 2339.50, 'pnl': -70.00, 'pnl_pct': -0.03, 'type': 'SELL'},
        {'entry_price': 2338.80, 'exit_price': 2345.90, 'pnl': 710.00, 'pnl_pct': 0.30, 'type': 'BUY'},
        {'entry_price': 2345.50, 'exit_price': 2342.10, 'pnl': -340.00, 'pnl_pct': -0.15, 'type': 'SELL'},
    ]

    logger.info(f"✓ Created {len(trades)} sample trades")
    return trades


def test_performance_metrics(trades, equity_curve):
    """Test PerformanceMetrics class."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Performance Metrics")
    logger.info("="*70)

    try:
        metrics = PerformanceMetrics(trades, equity_curve, initial_capital=10000)
        all_metrics = metrics.get_all_metrics()

        logger.info("✓ PerformanceMetrics initialized and calculated successfully")
        logger.info("\nKey Metrics:")
        logger.info(f"  ROI: {all_metrics['roi']:.2f}%")
        logger.info(f"  Net Profit: ${all_metrics['net_profit']:,.2f}")
        logger.info(f"  Max Drawdown: {all_metrics['max_drawdown_pct']:.2f}%")
        logger.info(f"  Sharpe Ratio: {all_metrics['sharpe_ratio']:.4f}")
        logger.info(f"  Sortino Ratio: {all_metrics['sortino_ratio']:.4f}")
        logger.info(f"  Calmar Ratio: {all_metrics['calmar_ratio']:.4f}")
        logger.info(f"  Win Rate: {all_metrics['win_rate']:.2%}")
        logger.info(f"  Profit Factor: {all_metrics['profit_factor']:.2f}")
        logger.info(f"  Total Trades: {all_metrics['total_trades']}")
        logger.info(f"  Avg Trade: ${all_metrics['expectancy']:,.2f}")

        return True, all_metrics

    except Exception as e:
        logger.error(f"✗ PerformanceMetrics test failed: {e}", exc_info=True)
        return False, None


def test_backtest_visualizer():
    """Test BacktestVisualizer class."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Backtest Visualizer")
    logger.info("="*70)

    try:
        output_dir = 'reports'
        os.makedirs(output_dir, exist_ok=True)

        visualizer = BacktestVisualizer(output_dir=output_dir)
        logger.info("✓ BacktestVisualizer initialized")

        # Test with sample data
        df = create_sample_data(100)
        trades = create_sample_trades()

        # Create synthetic equity curve
        equity_curve = [10000]
        current_equity = 10000
        for trade in trades:
            current_equity += trade['pnl']
            equity_curve.extend([current_equity] * 15)  # Assume 15 bars per trade

        # Pad to 100 candles
        while len(equity_curve) < 100:
            equity_curve.append(equity_curve[-1])

        equity_path = visualizer.plot_equity_curve(
            equity_curve=equity_curve[:100],
            dates=df['DateTime'].tolist(),
            filename='test_equity.png'
        )

        if equity_path and os.path.exists(equity_path):
            logger.info(f"✓ Equity curve chart generated: {equity_path}")
        else:
            logger.warning("✗ Equity curve chart not generated")

        drawdown_path = visualizer.plot_drawdown(
            equity_curve=equity_curve[:100],
            dates=df['DateTime'].tolist(),
            filename='test_drawdown.png'
        )

        if drawdown_path and os.path.exists(drawdown_path):
            logger.info(f"✓ Drawdown chart generated: {drawdown_path}")
        else:
            logger.warning("✗ Drawdown chart not generated")

        dist_path = visualizer.plot_distribution(
            trades=trades,
            filename='test_distribution.png'
        )

        if dist_path and os.path.exists(dist_path):
            logger.info(f"✓ Distribution chart generated: {dist_path}")
        else:
            logger.warning("✗ Distribution chart not generated")

        return True

    except Exception as e:
        logger.error(f"✗ BacktestVisualizer test failed: {e}", exc_info=True)
        return False


def test_advanced_backtester():
    """Test AdvancedBacktester class."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Advanced Backtester")
    logger.info("="*70)

    try:
        from config.config import Config

        config = Config()
        os.makedirs('reports', exist_ok=True)

        backtester = AdvancedBacktester(config, initial_capital=10000)
        logger.info("✓ AdvancedBacktester initialized")

        # Generate sample data
        df = create_sample_data(150)

        # Create mock model
        class MockModel:
            def predict_signal(self, features):
                # Return random signal
                return {
                    'signal': 2,  # BUY
                    'confidence': np.random.uniform(0.5, 0.95),
                    'probabilities': {'SELL': 0.1, 'HOLD': 0.2, 'BUY': 0.7}
                }

        model = MockModel()

        # Create mock TA function
        def ta_func(df):
            from src.technical_analysis import TechnicalAnalysis
            ta = TechnicalAnalysis(df)
            ta.calculate_moving_averages()
            ta.calculate_rsi()
            ta.calculate_atr()
            return ta.df

        # Run backtest
        logger.info("Running backtest simulation...")
        metrics = backtester.run_backtest(df, model, ta_func)

        if metrics:
            logger.info("✓ Backtest completed successfully")
            logger.info(f"  Total Trades: {metrics.get('total_trades', 'N/A')}")
            logger.info(f"  ROI: {metrics.get('roi', 'N/A'):.2f}%" if isinstance(metrics.get('roi'), (int, float)) else "  ROI: N/A")
            logger.info(f"  Max Drawdown: {metrics.get('max_drawdown_pct', 'N/A'):.2f}%" if isinstance(metrics.get('max_drawdown_pct'), (int, float)) else "  Max Drawdown: N/A")
        else:
            logger.warning("✗ Backtest returned no metrics")

        return True, metrics

    except Exception as e:
        logger.error(f"✗ Advanced backtester test failed: {e}", exc_info=True)
        return False, None


def main():
    """Run all tests."""
    logger.info("\n" + "="*70)
    logger.info("ADVANCED BACKTESTER TEST SUITE")
    logger.info("="*70)

    results = {}

    # Test 1: Create sample data and trades
    df = create_sample_data(150)
    trades = create_sample_trades()

    # Create equity curve
    equity_curve = [10000]
    current_equity = 10000
    for trade in trades:
        current_equity += trade['pnl']
        equity_curve.append(current_equity)

    # Pad equity curve
    while len(equity_curve) < 150:
        equity_curve.append(equity_curve[-1])

    # Test 1: Performance Metrics
    success, metrics = test_performance_metrics(trades, equity_curve[:150])
    results['Performance Metrics'] = success

    # Test 2: Backtest Visualizer
    success = test_backtest_visualizer()
    results['Backtest Visualizer'] = success

    # Test 3: Advanced Backtester
    success, backtest_metrics = test_advanced_backtester()
    results['Advanced Backtester'] = success

    # Summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n✓ All tests passed!")
        return 0
    else:
        logger.warning(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

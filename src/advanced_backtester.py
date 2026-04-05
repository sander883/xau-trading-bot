"""
Advanced backtesting system with detailed metrics, visualizations, and optimization.

Features:
- Comprehensive performance metrics (winrate, drawdown, profit factor, etc.)
- Equity curve visualization
- Automatic parameter optimization
- Professional HTML reports with charts
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Calculate comprehensive performance metrics."""

    def __init__(self, trades: List[Dict], equity_curve: List[float], initial_capital: float):
        """Initialize metrics calculator.

        Args:
            trades: List of trade dictionaries
            equity_curve: List of equity values over time
            initial_capital: Starting capital
        """
        self.trades = trades
        self.equity_curve = np.array(equity_curve)
        self.initial_capital = initial_capital
        self.metrics = {}
        self._calculate_all_metrics()

    def _calculate_all_metrics(self):
        """Calculate all performance metrics."""
        self._calculate_basic_metrics()
        self._calculate_drawdown_metrics()
        self._calculate_ratio_metrics()
        self._calculate_trade_metrics()

    def _calculate_basic_metrics(self):
        """Calculate basic profitability metrics."""
        if len(self.equity_curve) == 0:
            self.metrics['total_return'] = 0
            self.metrics['roi'] = 0
            self.metrics['net_profit'] = 0
            return

        final_capital = self.equity_curve[-1]
        self.metrics['net_profit'] = final_capital - self.initial_capital
        self.metrics['total_return'] = self.metrics['net_profit'] / self.initial_capital
        self.metrics['roi'] = self.metrics['total_return'] * 100

    def _calculate_drawdown_metrics(self):
        """Calculate drawdown-related metrics."""
        if len(self.equity_curve) == 0:
            self.metrics['max_drawdown'] = 0
            self.metrics['max_drawdown_pct'] = 0
            self.metrics['current_drawdown'] = 0
            return

        # Running maximum
        running_max = np.maximum.accumulate(self.equity_curve)

        # Drawdown from running maximum
        drawdowns = (self.equity_curve - running_max) / running_max

        self.metrics['max_drawdown'] = np.min(drawdowns)
        self.metrics['max_drawdown_pct'] = self.metrics['max_drawdown'] * 100

        # Current drawdown
        current_drawdown = (self.equity_curve[-1] - running_max[-1]) / running_max[-1]
        self.metrics['current_drawdown'] = current_drawdown * 100

        # Drawdown duration
        self.metrics['max_drawdown_duration'] = self._calculate_drawdown_duration(drawdowns)

    def _calculate_drawdown_duration(self, drawdowns):
        """Calculate longest drawdown duration in days."""
        in_drawdown = drawdowns < 0
        changes = np.diff(np.concatenate(([False], in_drawdown, [False])).astype(int))
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]

        if len(starts) == 0:
            return 0

        durations = ends - starts
        return int(np.max(durations)) if len(durations) > 0 else 0

    def _calculate_ratio_metrics(self):
        """Calculate ratio-based metrics."""
        if len(self.equity_curve) < 2:
            self.metrics['sharpe_ratio'] = 0
            self.metrics['sortino_ratio'] = 0
            self.metrics['calmar_ratio'] = 0
            return

        # Daily returns
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1]

        # Sharpe ratio (assuming 252 trading days, 0% risk-free rate)
        if len(returns) > 0 and np.std(returns) > 0:
            annual_return = np.mean(returns) * 252
            annual_std = np.std(returns) * np.sqrt(252)
            self.metrics['sharpe_ratio'] = annual_return / (annual_std + 1e-6)
        else:
            self.metrics['sharpe_ratio'] = 0

        # Sortino ratio (only downside volatility)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = np.std(downside_returns) * np.sqrt(252)
            self.metrics['sortino_ratio'] = annual_return / (downside_std + 1e-6)
        else:
            self.metrics['sortino_ratio'] = 0

        # Calmar ratio (annual return / max drawdown)
        max_dd = abs(self.metrics['max_drawdown'])
        if max_dd > 0:
            self.metrics['calmar_ratio'] = annual_return / max_dd
        else:
            self.metrics['calmar_ratio'] = 0

    def _calculate_trade_metrics(self):
        """Calculate trade-specific metrics."""
        if len(self.trades) == 0:
            self.metrics['total_trades'] = 0
            self.metrics['winning_trades'] = 0
            self.metrics['losing_trades'] = 0
            self.metrics['win_rate'] = 0
            self.metrics['avg_win'] = 0
            self.metrics['avg_loss'] = 0
            self.metrics['profit_factor'] = 0
            self.metrics['expectancy'] = 0
            return

        # Trade counts
        self.metrics['total_trades'] = len(self.trades)
        winning = [t for t in self.trades if t.get('pnl', 0) > 0]
        losing = [t for t in self.trades if t.get('pnl', 0) < 0]

        self.metrics['winning_trades'] = len(winning)
        self.metrics['losing_trades'] = len(losing)
        self.metrics['win_rate'] = len(winning) / len(self.trades) if self.trades else 0

        # Average win/loss
        winning_pnls = [t.get('pnl', 0) for t in winning]
        losing_pnls = [t.get('pnl', 0) for t in losing]

        self.metrics['avg_win'] = np.mean(winning_pnls) if winning_pnls else 0
        self.metrics['avg_loss'] = np.mean(losing_pnls) if losing_pnls else 0

        # Profit factor
        gross_profit = sum(winning_pnls) if winning_pnls else 0
        gross_loss = abs(sum(losing_pnls)) if losing_pnls else 0
        self.metrics['profit_factor'] = gross_profit / (gross_loss + 1e-6) if gross_loss > 0 else 0

        # Expectancy
        total_pnl = sum([t.get('pnl', 0) for t in self.trades])
        self.metrics['expectancy'] = total_pnl / len(self.trades) if self.trades else 0

    def get_all_metrics(self) -> Dict:
        """Get all calculated metrics.

        Returns:
            Dictionary with all metrics
        """
        return self.metrics.copy()


class BacktestVisualizer:
    """Create visualizations of backtest results."""

    def __init__(self, output_dir='reports'):
        """Initialize visualizer.

        Args:
            output_dir: Directory to save visualizations
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not HAS_MATPLOTLIB:
            logger.warning("Matplotlib not available, visualizations disabled")

    def plot_equity_curve(self, equity_curve: List[float], dates: List = None, filename: str = None) -> Optional[str]:
        """Plot equity curve over time.

        Args:
            equity_curve: List of equity values
            dates: List of dates (optional)
            filename: Output filename

        Returns:
            Path to saved figure or None
        """
        if not HAS_MATPLOTLIB:
            return None

        try:
            fig, ax = plt.subplots(figsize=(14, 6))

            if dates:
                ax.plot(dates, equity_curve, linewidth=2, color='steelblue', label='Equity')
            else:
                ax.plot(equity_curve, linewidth=2, color='steelblue', label='Equity')

            ax.set_xlabel('Time')
            ax.set_ylabel('Equity ($)')
            ax.set_title('Equity Curve Over Time')
            ax.grid(True, alpha=0.3)
            ax.legend()

            plt.tight_layout()

            if filename is None:
                filename = f"equity_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=100)
            plt.close()

            logger.info(f"✓ Equity curve saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error plotting equity curve: {e}")
            return None

    def plot_drawdown(self, equity_curve: List[float], dates: List = None, filename: str = None) -> Optional[str]:
        """Plot drawdown over time.

        Args:
            equity_curve: List of equity values
            dates: List of dates (optional)
            filename: Output filename

        Returns:
            Path to saved figure or None
        """
        if not HAS_MATPLOTLIB:
            return None

        try:
            equity_array = np.array(equity_curve)
            running_max = np.maximum.accumulate(equity_array)
            drawdown = (equity_array - running_max) / running_max * 100

            fig, ax = plt.subplots(figsize=(14, 6))

            if dates:
                ax.fill_between(dates, drawdown, 0, color='red', alpha=0.3, label='Drawdown')
                ax.plot(dates, drawdown, color='darkred', linewidth=1)
            else:
                ax.fill_between(range(len(drawdown)), drawdown, 0, color='red', alpha=0.3, label='Drawdown')
                ax.plot(drawdown, color='darkred', linewidth=1)

            ax.set_xlabel('Time')
            ax.set_ylabel('Drawdown (%)')
            ax.set_title('Drawdown Over Time')
            ax.grid(True, alpha=0.3)
            ax.legend()

            plt.tight_layout()

            if filename is None:
                filename = f"drawdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=100)
            plt.close()

            logger.info(f"✓ Drawdown chart saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error plotting drawdown: {e}")
            return None

    def plot_distribution(self, trades: List[Dict], filename: str = None) -> Optional[str]:
        """Plot trade P&L distribution.

        Args:
            trades: List of trade dictionaries
            filename: Output filename

        Returns:
            Path to saved figure or None
        """
        if not HAS_MATPLOTLIB or len(trades) == 0:
            return None

        try:
            pnls = [t.get('pnl', 0) for t in trades]

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

            # Histogram
            ax1.hist(pnls, bins=20, color='steelblue', edgecolor='black', alpha=0.7)
            ax1.axvline(x=0, color='red', linestyle='--', linewidth=2)
            ax1.set_xlabel('P&L ($)')
            ax1.set_ylabel('Frequency')
            ax1.set_title('Trade P&L Distribution')
            ax1.grid(True, alpha=0.3)

            # Win/Loss pie chart
            wins = len([p for p in pnls if p > 0])
            losses = len([p for p in pnls if p < 0])
            breaks = len([p for p in pnls if p == 0])

            ax2.pie([wins, losses, breaks], labels=['Wins', 'Losses', 'Breaks'],
                   colors=['green', 'red', 'gray'], autopct='%1.1f%%')
            ax2.set_title('Win/Loss Distribution')

            plt.tight_layout()

            if filename is None:
                filename = f"distribution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=100)
            plt.close()

            logger.info(f"✓ Distribution chart saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error plotting distribution: {e}")
            return None


class ParameterOptimizer:
    """Automatically optimize strategy parameters."""

    def __init__(self, backtester, config):
        """Initialize optimizer.

        Args:
            backtester: Backtester instance
            config: Configuration object
        """
        self.backtester = backtester
        self.config = config
        self.optimization_results = []

    def optimize_parameters(self, df, ml_model, ta_func, param_ranges: Dict) -> Dict:
        """Optimize parameters using grid search.

        Args:
            df: Historical data
            ml_model: ML model
            ta_func: Technical analysis function
            param_ranges: Dictionary of parameters to optimize with ranges
                         Example: {
                             'confidence_threshold': [0.60, 0.65, 0.70],
                             'take_profit_pct': [1.0, 1.5, 2.0]
                         }

        Returns:
            Dictionary with best parameters and results
        """
        try:
            logger.info("=" * 70)
            logger.info("PARAMETER OPTIMIZATION")
            logger.info("=" * 70)

            best_result = None
            best_score = float('-inf')
            total_combinations = 1

            # Calculate total combinations
            for param_range in param_ranges.values():
                total_combinations *= len(param_range)

            logger.info(f"Testing {total_combinations} parameter combinations...")

            combination = 0

            # Generate all parameter combinations
            from itertools import product

            param_keys = list(param_ranges.keys())
            param_values = list(param_ranges.values())

            for values in product(*param_values):
                combination += 1

                # Create parameter dict
                params = dict(zip(param_keys, values))

                # Run backtest with these parameters
                logger.info(f"\n[{combination}/{total_combinations}] Testing: {params}")

                result = self._run_backtest_with_params(df, ml_model, ta_func, params)

                if result:
                    # Calculate score (Sharpe ratio weighted)
                    score = (
                        result.get('sharpe_ratio', 0) * 0.4 +
                        result.get('roi', 0) / 100 * 0.3 +
                        result.get('win_rate', 0) * 0.2 +
                        result.get('profit_factor', 0) * 0.1
                    )

                    result['score'] = score
                    self.optimization_results.append(result)

                    logger.info(f"  Score: {score:.4f}")
                    logger.info(f"  ROI: {result.get('roi', 0):.2f}%")
                    logger.info(f"  Win Rate: {result.get('win_rate', 0):.2%}")
                    logger.info(f"  Sharpe: {result.get('sharpe_ratio', 0):.4f}")

                    if score > best_score:
                        best_score = score
                        best_result = result

            logger.info("\n" + "=" * 70)
            logger.info("OPTIMIZATION COMPLETE")
            logger.info("=" * 70)
            logger.info(f"Best Score: {best_score:.4f}")
            logger.info(f"Best Parameters: {best_result['parameters'] if best_result else 'None'}")

            return {
                'best_parameters': best_result['parameters'] if best_result else None,
                'best_score': best_score,
                'best_result': best_result,
                'all_results': self.optimization_results
            }

        except Exception as e:
            logger.error(f"Error during optimization: {e}", exc_info=True)
            return None

    def _run_backtest_with_params(self, df, ml_model, ta_func, params: Dict) -> Optional[Dict]:
        """Run backtest with specific parameters.

        Args:
            df: Historical data
            ml_model: ML model
            ta_func: Technical analysis function
            params: Parameters to use

        Returns:
            Backtest results or None
        """
        try:
            # Apply parameters to config temporarily
            original_params = {}
            for key, value in params.items():
                if hasattr(self.backtester.config, key.upper()):
                    original_params[key] = getattr(self.backtester.config, key.upper())
                    setattr(self.backtester.config, key.upper(), value)

            # Run backtest
            result = self.backtester.run_backtest(df, ml_model, ta_func)

            # Restore original parameters
            for key, value in original_params.items():
                setattr(self.backtester.config, key.upper(), value)

            if result:
                result['parameters'] = params

            return result

        except Exception as e:
            logger.error(f"Error in backtest with params: {e}")
            return None

    def get_optimization_summary(self) -> pd.DataFrame:
        """Get optimization results as DataFrame.

        Returns:
            DataFrame with optimization results
        """
        if not self.optimization_results:
            return None

        df = pd.DataFrame(self.optimization_results)
        df = df.sort_values('score', ascending=False)
        return df


class AdvancedBacktester:
    """Advanced backtesting system with metrics, visualization, and optimization."""

    def __init__(self, config, initial_capital=None):
        """Initialize advanced backtester.

        Args:
            config: Configuration object
            initial_capital: Starting capital
        """
        self.config = config
        self.initial_capital = initial_capital or config.BACKTEST_INITIAL_CAPITAL
        self.trades = []
        self.equity_curve = []
        self.dates = []

        self.metrics = None
        self.visualizer = BacktestVisualizer(config.LOGS_DIR / 'backtest_reports')
        self.optimizer = ParameterOptimizer(self, config)

        logger.info("✓ Advanced Backtester initialized")

    def run_backtest(self, df, ml_model, ta_func) -> Dict:
        """Run comprehensive backtest.

        Args:
            df: Historical OHLC data
            ml_model: Trained ML model
            ta_func: Technical analysis function

        Returns:
            Dictionary with comprehensive results
        """
        try:
            logger.info("=" * 70)
            logger.info("RUNNING BACKTEST")
            logger.info("=" * 70)

            self.trades = []
            self.equity_curve = [self.initial_capital]
            self.dates = []

            capital = self.initial_capital
            position = None

            for i in range(len(df) - 1):
                current_price = df['Close'].iloc[i]
                next_price = df['Close'].iloc[i + 1]

                # Store date
                if hasattr(df.index[i], 'to_pydatetime'):
                    self.dates.append(df.index[i].to_pydatetime())
                else:
                    self.dates.append(i)

                # Generate prediction
                if i >= 20:
                    # Use ML model
                    window_df = df.iloc[max(0, i-50):i+1]
                    signal = self._get_ml_signal(window_df, ml_model)

                    # Entry logic
                    if position is None and signal['meets_threshold']:
                        if signal['prediction'] == 2:  # BUY
                            position = self._open_position('BUY', current_price, i)
                        elif signal['prediction'] == 0:  # SELL
                            position = self._open_position('SELL', current_price, i)

                    # Exit logic
                    if position:
                        pnl, exit_reason = self._check_exit(position, current_price, i)

                        if pnl is not None:
                            position['exit_price'] = current_price
                            position['exit_index'] = i
                            position['pnl'] = pnl
                            position['pnl_pct'] = (pnl / position['entry_price']) * 100
                            position['bars_held'] = i - position['entry_index']
                            position['exit_reason'] = exit_reason

                            self.trades.append(position)
                            capital += pnl
                            position = None

                # Update equity
                self.equity_curve.append(capital)

            logger.info(f"✓ Backtest complete")
            logger.info(f"  Total trades: {len(self.trades)}")

            # Calculate metrics
            self.metrics = PerformanceMetrics(self.trades, self.equity_curve, self.initial_capital)
            metrics_dict = self.metrics.get_all_metrics()

            logger.info(f"  ROI: {metrics_dict.get('roi', 0):.2f}%")
            logger.info(f"  Win Rate: {metrics_dict.get('win_rate', 0):.2%}")
            logger.info(f"  Sharpe Ratio: {metrics_dict.get('sharpe_ratio', 0):.4f}")
            logger.info(f"  Max Drawdown: {metrics_dict.get('max_drawdown_pct', 0):.2f}%")
            logger.info(f"  Profit Factor: {metrics_dict.get('profit_factor', 0):.2f}")

            return metrics_dict

        except Exception as e:
            logger.error(f"Error during backtest: {e}", exc_info=True)
            return None

    def _get_ml_signal(self, df, ml_model):
        """Get signal from ML model."""
        try:
            from src.professional_xgboost_model import ProfessionalXGBoostModel

            if isinstance(ml_model, ProfessionalXGBoostModel):
                # Use professional model
                features = ml_model.engineer_features(df)
                if hasattr(ml_model, 'preprocessor'):
                    features_scaled = ml_model.preprocessor.transform(features.iloc[-1:].values)
                else:
                    features_scaled = features.iloc[-1:].values

                return ml_model.predict_signal(features_scaled, self.config.PREDICTION_CONFIDENCE_THRESHOLD)
            else:
                # Fallback
                return {'meets_threshold': False, 'confidence': 0}

        except Exception as e:
            logger.error(f"Error getting ML signal: {e}")
            return {'meets_threshold': False, 'confidence': 0}

    def _open_position(self, trade_type, price, index):
        """Open a new position."""
        return {
            'type': trade_type,
            'entry_price': price,
            'entry_index': index,
            'entry_time': datetime.now()
        }

    def _check_exit(self, position, current_price, index):
        """Check exit conditions."""
        # Simple exit: 2% TP or 1% SL
        pnl = None
        reason = None

        if position['type'] == 'BUY':
            pnl_pct = (current_price - position['entry_price']) / position['entry_price']

            if pnl_pct >= 0.02:  # 2% TP
                pnl = (current_price - position['entry_price']) * 100  # Assume 100 units
                reason = 'TP'
            elif pnl_pct <= -0.01:  # 1% SL
                pnl = (current_price - position['entry_price']) * 100
                reason = 'SL'
            elif index - position['entry_index'] > 100:  # Max 100 bars
                pnl = (current_price - position['entry_price']) * 100
                reason = 'MaxBars'

        elif position['type'] == 'SELL':
            pnl_pct = (position['entry_price'] - current_price) / position['entry_price']

            if pnl_pct >= 0.02:  # 2% TP
                pnl = (position['entry_price'] - current_price) * 100
                reason = 'TP'
            elif pnl_pct <= -0.01:  # 1% SL
                pnl = (position['entry_price'] - current_price) * 100
                reason = 'SL'
            elif index - position['entry_index'] > 100:  # Max 100 bars
                pnl = (position['entry_price'] - current_price) * 100
                reason = 'MaxBars'

        return pnl, reason

    def export_html_report(self, filename: str = None) -> Optional[str]:
        """Export comprehensive HTML report.

        Args:
            filename: Output filename

        Returns:
            Path to saved report
        """
        try:
            if not self.metrics or not self.trades:
                logger.error("No backtest results to export")
                return None

            metrics = self.metrics.get_all_metrics()

            # Create report HTML
            html = self._generate_html_report(metrics)

            if filename is None:
                filename = f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

            filepath = self.config.LOGS_DIR / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w') as f:
                f.write(html)

            logger.info(f"✓ HTML report saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting HTML report: {e}")
            return None

    def _generate_html_report(self, metrics: Dict) -> str:
        """Generate HTML report content.

        Args:
            metrics: Performance metrics dictionary

        Returns:
            HTML content as string
        """
        # Generate charts
        equity_chart = self.visualizer.plot_equity_curve(self.equity_curve, self.dates)
        drawdown_chart = self.visualizer.plot_drawdown(self.equity_curve, self.dates)
        dist_chart = self.visualizer.plot_distribution(self.trades)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Backtest Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background-color: #1f77b4; color: white; padding: 20px; border-radius: 5px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background-color: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1f77b4; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .chart {{ margin: 30px 0; text-align: center; }}
        .chart img {{ max-width: 100%; height: auto; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background-color: white; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f9f9f9; font-weight: bold; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Backtest Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <h2>Performance Summary</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-label">Total Return (ROI)</div>
            <div class="metric-value {'positive' if metrics['roi'] > 0 else 'negative'}">{metrics['roi']:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Net Profit</div>
            <div class="metric-value {'positive' if metrics['net_profit'] > 0 else 'negative'}">${metrics['net_profit']:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value negative">{metrics['max_drawdown_pct']:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value">{metrics['sharpe_ratio']:.4f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Sortino Ratio</div>
            <div class="metric-value">{metrics['sortino_ratio']:.4f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Calmar Ratio</div>
            <div class="metric-value">{metrics['calmar_ratio']:.4f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value {'positive' if metrics['win_rate'] > 0.5 else ''}">{metrics['win_rate']:.2%}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Profit Factor</div>
            <div class="metric-value">{metrics['profit_factor']:.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Average Trade</div>
            <div class="metric-value">${metrics['expectancy']:,.2f}</div>
        </div>
    </div>

    <h2>Trade Statistics</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-label">Total Trades</div>
            <div class="metric-value">{metrics['total_trades']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Winning Trades</div>
            <div class="metric-value positive">{metrics['winning_trades']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Losing Trades</div>
            <div class="metric-value negative">{metrics['losing_trades']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Average Win</div>
            <div class="metric-value positive">${metrics['avg_win']:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Average Loss</div>
            <div class="metric-value negative">${metrics['avg_loss']:,.2f}</div>
        </div>
    </div>

    <h2>Charts</h2>
    {f'<div class="chart"><h3>Equity Curve</h3><img src="{Path(equity_chart).name}" alt="Equity Curve"></div>' if equity_chart else ''}
    {f'<div class="chart"><h3>Drawdown</h3><img src="{Path(drawdown_chart).name}" alt="Drawdown"></div>' if drawdown_chart else ''}
    {f'<div class="chart"><h3>Trade Distribution</h3><img src="{Path(dist_chart).name}" alt="Distribution"></div>' if dist_chart else ''}

    <h2>Recent Trades</h2>
    <table>
        <tr>
            <th>Entry Price</th>
            <th>Exit Price</th>
            <th>P&L</th>
            <th>P&L %</th>
            <th>Type</th>
            <th>Bars Held</th>
            <th>Exit Reason</th>
        </tr>
        {self._generate_trade_rows()}
    </table>

    <div class="footer">
        <p>This report was automatically generated by Advanced Backtester</p>
    </div>
</body>
</html>
        """

        return html

    def _generate_trade_rows(self) -> str:
        """Generate HTML table rows for recent trades."""
        if not self.trades:
            return '<tr><td colspan="7">No trades</td></tr>'

        rows = []
        for trade in self.trades[-20:]:
            pnl_class = 'positive' if trade['pnl'] > 0 else 'negative'
            pnl_pct_class = 'positive' if trade.get('pnl_pct', 0) > 0 else 'negative'

            row = (
                f'<tr>'
                f'<td>${trade["entry_price"]:.2f}</td>'
                f'<td>${trade["exit_price"]:.2f}</td>'
                f'<td class="{pnl_class}">${trade["pnl"]:,.2f}</td>'
                f'<td class="{pnl_pct_class}">{trade.get("pnl_pct", 0):.2f}%</td>'
                f'<td>{trade["type"]}</td>'
                f'<td>{trade.get("bars_held", 0)}</td>'
                f'<td>{trade.get("exit_reason", "N/A")}</td>'
                f'</tr>'
            )
            rows.append(row)

        return '\n        '.join(rows)

    def export_csv_trades(self, filename: str = None) -> Optional[str]:
        """Export trades to CSV.

        Args:
            filename: Output filename

        Returns:
            Path to saved file
        """
        try:
            if not self.trades:
                logger.warning("No trades to export")
                return None

            df = pd.DataFrame(self.trades)

            if filename is None:
                filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            filepath = self.config.LOGS_DIR / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            df.to_csv(filepath, index=False)

            logger.info(f"✓ Trades exported: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting trades: {e}")
            return None

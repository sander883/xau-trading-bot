import logging
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class Backtester:
    """Backtesting system for strategy validation."""

    def __init__(self, config, initial_capital=None):
        """Initialize backtester.

        Args:
            config: Configuration object
            initial_capital: Starting capital (default: from config)
        """
        self.config = config
        self.initial_capital = initial_capital or config.BACKTEST_INITIAL_CAPITAL
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = []
        self.drawdown = 0

    def run_backtest(self, df, ml_model, ta_analysis_func):
        """Run backtest on historical data.

        Args:
            df: DataFrame with OHLC data
            ml_model: Trained ML model
            ta_analysis_func: Function to calculate technical analysis

        Returns:
            Backtest results dictionary
        """
        try:
            results = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit_loss': 0,
                'roi': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0,
            }

            position = None
            trade_id = 0

            for i in range(len(df) - 1):
                # Get current and next price
                current_price = df['Close'].iloc[i]
                next_price = df['Close'].iloc[i + 1]

                # Calculate indicators for decision
                window_df = df.iloc[max(0, i-100):i+1]
                ta = ta_analysis_func(window_df)

                # Get features for ML
                if i > 20:  # Need enough data
                    features = self._extract_features(window_df)
                    if features is not None:
                        prediction, confidence = ml_model.predict_single(features)
                        trend = ta.identify_trend()

                        # Enter trade
                        if position is None and confidence > self.config.PREDICTION_CONFIDENCE_THRESHOLD:
                            if prediction == 1 and trend == 'UPTREND':
                                position = {
                                    'id': trade_id,
                                    'type': 'BUY',
                                    'entry_price': current_price,
                                    'entry_index': i,
                                    'entry_time': df.index[i]
                                }
                                trade_id += 1

                            elif prediction == 0 and trend == 'DOWNTREND':
                                position = {
                                    'id': trade_id,
                                    'type': 'SELL',
                                    'entry_price': current_price,
                                    'entry_index': i,
                                    'entry_time': df.index[i]
                                }
                                trade_id += 1

                        # Exit trade
                        if position is not None:
                            exit_reason = self._check_exit_conditions(
                                position, current_price, next_price, df.iloc[i]
                            )

                            if exit_reason:
                                pnl = self._calculate_pnl(position, next_price)
                                self.capital += pnl

                                self.trades.append({
                                    'id': position['id'],
                                    'type': position['type'],
                                    'entry_price': position['entry_price'],
                                    'exit_price': next_price,
                                    'entry_time': position['entry_time'],
                                    'exit_time': df.index[i + 1],
                                    'pnl': pnl,
                                    'exit_reason': exit_reason
                                })

                                results['total_trades'] += 1
                                if pnl > 0:
                                    results['winning_trades'] += 1
                                else:
                                    results['losing_trades'] += 1

                                position = None

                # Track equity curve
                self.equity_curve.append(self.capital)

            # Calculate final metrics
            if results['total_trades'] > 0:
                results['win_rate'] = (results['winning_trades'] / results['total_trades']) * 100
                results['total_profit_loss'] = self.capital - self.initial_capital
                results['roi'] = (results['total_profit_loss'] / self.initial_capital) * 100
                results['profit_factor'] = self._calculate_profit_factor()
                results['max_drawdown'] = self._calculate_max_drawdown()
                results['sharpe_ratio'] = self._calculate_sharpe_ratio()

            logger.info(f"Backtest completed: {results['total_trades']} trades, "
                       f"ROI: {results['roi']:.2f}%, Win Rate: {results['win_rate']:.1f}%")

            return results

        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return None

    def _extract_features(self, df):
        """Extract ML features from data."""
        try:
            feature_cols = [col for col in df.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']]
            if feature_cols and len(df) > 0:
                return df[feature_cols].iloc[-1].values.flatten()
            return None
        except Exception:
            return None

    def _check_exit_conditions(self, position, current_price, next_price, current_row):
        """Check if position should be closed."""
        # Simple exit: opposite signal or 5% profit/loss
        exit_threshold = 0.05

        if position['type'] == 'BUY':
            if (current_price - position['entry_price']) / position['entry_price'] >= exit_threshold:
                return 'TP_HIT'
            if (position['entry_price'] - current_price) / position['entry_price'] >= exit_threshold * 0.5:
                return 'SL_HIT'
        else:
            if (position['entry_price'] - current_price) / position['entry_price'] >= exit_threshold:
                return 'TP_HIT'
            if (current_price - position['entry_price']) / position['entry_price'] >= exit_threshold * 0.5:
                return 'SL_HIT'

        return None

    def _calculate_pnl(self, position, exit_price):
        """Calculate profit/loss for a trade."""
        if position['type'] == 'BUY':
            return (exit_price - position['entry_price']) * 100  # Simplified
        else:
            return (position['entry_price'] - exit_price) * 100

    def _calculate_profit_factor(self):
        """Calculate profit factor (gross profit / gross loss)."""
        gross_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] < 0))

        if gross_loss == 0:
            return 0
        return gross_profit / gross_loss

    def _calculate_max_drawdown(self):
        """Calculate maximum drawdown."""
        if not self.equity_curve:
            return 0

        peak = self.equity_curve[0]
        max_dd = 0

        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd

        return max_dd * 100

    def _calculate_sharpe_ratio(self, risk_free_rate=0.02):
        """Calculate Sharpe ratio."""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0

        returns = np.diff(self.equity_curve) / np.array(self.equity_curve[:-1])
        excess_returns = returns - (risk_free_rate / 252)

        if np.std(excess_returns) == 0:
            return 0

        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)

    def get_trade_summary(self):
        """Get summary of all trades."""
        df_trades = pd.DataFrame(self.trades)
        return df_trades if not df_trades.empty else None

    def export_backtest_report(self, filename='backtest_report.csv'):
        """Export backtest report to CSV."""
        try:
            df_trades = self.get_trade_summary()
            if df_trades is not None:
                filepath = self.config.DATA_DIR / filename
                df_trades.to_csv(filepath, index=False)
                logger.info(f"Backtest report exported to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting backtest report: {e}")

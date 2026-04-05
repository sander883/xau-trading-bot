import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict

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

    def generate_detailed_report(self) -> Dict:
        """Generate comprehensive backtest report.

        Returns:
            Dictionary with detailed backtest metrics
        """
        if not self.trades:
            return {}

        df_trades = pd.DataFrame(self.trades)

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl'] > 0])
        losing_trades = len([t for t in self.trades if t['pnl'] < 0])
        breakeven_trades = total_trades - winning_trades - losing_trades

        # P&L metrics
        total_profit = sum([t['pnl'] for t in self.trades if t['pnl'] > 0])
        total_loss = sum([t['pnl'] for t in self.trades if t['pnl'] < 0])
        net_profit = total_profit + total_loss

        # Win metrics
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_win = (total_profit / winning_trades) if winning_trades > 0 else 0
        avg_loss = (total_loss / losing_trades) if losing_trades > 0 else 0
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else 0

        # Streak analysis
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0

        for trade in self.trades:
            if trade['pnl'] > 0:
                current_streak += 1
                max_win_streak = max(max_win_streak, current_streak)
            elif trade['pnl'] < 0:
                current_streak -= 1
                max_loss_streak = max(max_loss_streak, abs(current_streak))
            else:
                current_streak = 0

        # Duration analysis
        durations = []
        for trade in self.trades:
            if 'exit_time' in trade and 'entry_time' in trade:
                duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600
                durations.append(duration)

        avg_trade_duration = np.mean(durations) if durations else 0
        max_trade_duration = max(durations) if durations else 0

        # Return metrics
        roi = ((self.capital - self.initial_capital) / self.initial_capital * 100) if self.initial_capital > 0 else 0
        max_dd = self._calculate_max_drawdown()
        sharpe = self._calculate_sharpe_ratio()

        # Recovery metrics
        trades_by_type = {}
        for trade in self.trades:
            trade_type = trade.get('type', 'UNKNOWN')
            if trade_type not in trades_by_type:
                trades_by_type[trade_type] = {'count': 0, 'wins': 0, 'total_pnl': 0}
            trades_by_type[trade_type]['count'] += 1
            if trade['pnl'] > 0:
                trades_by_type[trade_type]['wins'] += 1
            trades_by_type[trade_type]['total_pnl'] += trade['pnl']

        return {
            'summary': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'breakeven_trades': breakeven_trades,
                'win_rate': win_rate,
            },
            'profitability': {
                'total_profit': total_profit,
                'total_loss': total_loss,
                'net_profit': net_profit,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
            },
            'streaks': {
                'max_win_streak': max_win_streak,
                'max_loss_streak': max_loss_streak,
            },
            'performance': {
                'roi': roi,
                'max_drawdown': max_dd,
                'sharpe_ratio': sharpe,
                'avg_trade_duration_hours': avg_trade_duration,
                'max_trade_duration_hours': max_trade_duration,
            },
            'by_type': trades_by_type,
            'timestamp': datetime.now()
        }

    def export_html_report(self, filename='backtest_report.html'):
        """Export comprehensive HTML report.

        Args:
            filename: Output filename
        """
        try:
            report = self.generate_detailed_report()
            if not report:
                logger.warning("No trades to report")
                return

            html_content = self._generate_html_report(report)
            filepath = self.config.DATA_DIR / filename

            with open(filepath, 'w') as f:
                f.write(html_content)

            logger.info(f"HTML report exported to {filepath}")

        except Exception as e:
            logger.error(f"Error exporting HTML report: {e}")

    def _generate_html_report(self, report) -> str:
        """Generate HTML report content.

        Args:
            report: Report dictionary from generate_detailed_report()

        Returns:
            HTML string
        """
        summary = report.get('summary', {})
        profit = report.get('profitability', {})
        perf = report.get('performance', {})
        streaks = report.get('streaks', {})

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f0f0f0; }}
                .positive {{ color: green; font-weight: bold; }}
                .negative {{ color: red; font-weight: bold; }}
                .metric-box {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #4CAF50; }}
            </style>
        </head>
        <body>
            <h1>Trading Backtest Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <h2>Summary Statistics</h2>
            <table>
                <tr>
                    <td>Total Trades</td>
                    <td>{summary.get('total_trades', 0)}</td>
                </tr>
                <tr>
                    <td>Winning Trades</td>
                    <td class="positive">{summary.get('winning_trades', 0)}</td>
                </tr>
                <tr>
                    <td>Losing Trades</td>
                    <td class="negative">{summary.get('losing_trades', 0)}</td>
                </tr>
                <tr>
                    <td>Win Rate</td>
                    <td>{summary.get('win_rate', 0):.1f}%</td>
                </tr>
            </table>

            <h2>Profitability</h2>
            <table>
                <tr>
                    <td>Total Profit</td>
                    <td class="positive">${profit.get('total_profit', 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Total Loss</td>
                    <td class="negative">${profit.get('total_loss', 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Net Profit</td>
                    <td class="{'positive' if profit.get('net_profit', 0) >= 0 else 'negative'}">${profit.get('net_profit', 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Average Win</td>
                    <td class="positive">${profit.get('avg_win', 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Average Loss</td>
                    <td class="negative">${profit.get('avg_loss', 0):,.2f}</td>
                </tr>
                <tr>
                    <td>Profit Factor</td>
                    <td>{profit.get('profit_factor', 0):.2f}</td>
                </tr>
            </table>

            <h2>Performance Metrics</h2>
            <table>
                <tr>
                    <td>ROI</td>
                    <td class="{'positive' if perf.get('roi', 0) >= 0 else 'negative'}">{perf.get('roi', 0):.2f}%</td>
                </tr>
                <tr>
                    <td>Max Drawdown</td>
                    <td class="negative">{perf.get('max_drawdown', 0):.2f}%</td>
                </tr>
                <tr>
                    <td>Sharpe Ratio</td>
                    <td>{perf.get('sharpe_ratio', 0):.2f}</td>
                </tr>
                <tr>
                    <td>Avg Trade Duration</td>
                    <td>{perf.get('avg_trade_duration_hours', 0):.1f} hours</td>
                </tr>
                <tr>
                    <td>Max Trade Duration</td>
                    <td>{perf.get('max_trade_duration_hours', 0):.1f} hours</td>
                </tr>
            </table>

            <h2>Trade Streaks</h2>
            <table>
                <tr>
                    <td>Max Win Streak</td>
                    <td class="positive">{streaks.get('max_win_streak', 0)}</td>
                </tr>
                <tr>
                    <td>Max Loss Streak</td>
                    <td class="negative">{streaks.get('max_loss_streak', 0)}</td>
                </tr>
            </table>

            <h2>All Trades</h2>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>P&L</th>
                    <th>Reason</th>
                </tr>
        """

        for trade in self.trades[:100]:  # Limit to first 100 trades for HTML readability
            pnl_class = 'positive' if trade['pnl'] > 0 else 'negative'
            html += f"""
                <tr>
                    <td>{trade['id']}</td>
                    <td>{trade['type']}</td>
                    <td>{trade['entry_price']:.2f}</td>
                    <td>{trade['exit_price']:.2f}</td>
                    <td class="{pnl_class}">${trade['pnl']:,.2f}</td>
                    <td>{trade.get('exit_reason', 'N/A')}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        return html

    def export_summary_text(self, filename='backtest_summary.txt'):
        """Export summary report as text file.

        Args:
            filename: Output filename
        """
        try:
            report = self.generate_detailed_report()
            if not report:
                logger.warning("No trades to report")
                return

            filepath = self.config.DATA_DIR / filename

            with open(filepath, 'w') as f:
                f.write("="*60 + "\n")
                f.write("BACKTEST REPORT\n")
                f.write("="*60 + "\n\n")

                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Initial Capital: ${self.initial_capital:,.2f}\n")
                f.write(f"Final Capital: ${self.capital:,.2f}\n\n")

                summary = report.get('summary', {})
                f.write("SUMMARY\n")
                f.write("-"*60 + "\n")
                f.write(f"Total Trades:     {summary.get('total_trades', 0)}\n")
                f.write(f"Winning Trades:   {summary.get('winning_trades', 0)}\n")
                f.write(f"Losing Trades:    {summary.get('losing_trades', 0)}\n")
                f.write(f"Win Rate:         {summary.get('win_rate', 0):.1f}%\n\n")

                profit = report.get('profitability', {})
                f.write("PROFITABILITY\n")
                f.write("-"*60 + "\n")
                f.write(f"Total Profit:     ${profit.get('total_profit', 0):,.2f}\n")
                f.write(f"Total Loss:       ${profit.get('total_loss', 0):,.2f}\n")
                f.write(f"Net Profit:       ${profit.get('net_profit', 0):,.2f}\n")
                f.write(f"Profit Factor:    {profit.get('profit_factor', 0):.2f}\n\n")

                perf = report.get('performance', {})
                f.write("PERFORMANCE\n")
                f.write("-"*60 + "\n")
                f.write(f"ROI:              {perf.get('roi', 0):.2f}%\n")
                f.write(f"Max Drawdown:     {perf.get('max_drawdown', 0):.2f}%\n")
                f.write(f"Sharpe Ratio:     {perf.get('sharpe_ratio', 0):.2f}\n\n")

            logger.info(f"Summary report exported to {filepath}")

        except Exception as e:
            logger.error(f"Error exporting summary report: {e}")

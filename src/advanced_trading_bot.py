import logging
import MetaTrader5 as mt5
from datetime import datetime, timedelta

from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalysis
from src.ml_model import MLModel
from src.risk_manager import RiskManager
from src.trading_engine import TradingEngine
from src.telegram_notifier import TelegramNotifier
from src.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from src.combined_strategy import CombinedStrategy

logger = logging.getLogger(__name__)


class AdvancedTradingBot:
    """Advanced trading bot with multi-timeframe analysis and combined strategy."""

    def __init__(self, config, data_fetcher, ml_model, risk_manager,
                 trading_engine, telegram_notifier):
        """Initialize advanced trading bot.

        Args:
            config: Configuration object
            data_fetcher: DataFetcher instance
            ml_model: MLModel instance
            risk_manager: RiskManager instance
            trading_engine: TradingEngine instance
            telegram_notifier: TelegramNotifier instance
        """
        self.config = config
        self.data_fetcher = data_fetcher
        self.ml_model = ml_model
        self.risk_manager = risk_manager
        self.trading_engine = trading_engine
        self.telegram_notifier = telegram_notifier

        # Initialize advanced components
        if config.MULTI_TIMEFRAME_ENABLED:
            self.mtf_analyzer = MultiTimeframeAnalyzer(
                data_fetcher,
                config.MULTI_TIMEFRAMES
            )
        else:
            self.mtf_analyzer = None

        self.strategy = CombinedStrategy(config, ml_model)
        self.last_signal_time = None

    def analyze_market(self):
        """Perform comprehensive market analysis.

        Returns:
            Dictionary with analysis results
        """
        try:
            analysis = {
                'timestamp': datetime.now(),
                'symbol': self.config.SYMBOL,
                'current_price': None,
                'mtf_analysis': None,
                'strategy_signal': None,
                'should_trade': False,
            }

            # Fetch current OHLC data
            df = self.data_fetcher.get_ohlc_data(
                self.config.SYMBOL,
                self.config.TIMEFRAME,
                500
            )

            if df is None:
                logger.error("Failed to fetch market data")
                return analysis

            current_price = df['Close'].iloc[-1]
            analysis['current_price'] = current_price

            # Multi-timeframe analysis
            if self.mtf_analyzer:
                if self.mtf_analyzer.analyze(self.config.SYMBOL):
                    mtf_summary = self.mtf_analyzer.get_mtf_summary()
                    analysis['mtf_analysis'] = mtf_summary

                    logger.info(f"MTF Analysis: {mtf_summary['overall_trend']}")
                    self.telegram_notifier.send_mtf_analysis(
                        self.config.SYMBOL,
                        mtf_summary
                    )

            # Technical analysis on primary timeframe
            ta = TechnicalAnalysis(df)
            ta.calculate_moving_averages()
            ta.calculate_rsi()
            ta.calculate_bollinger_bands()
            ta.calculate_atr()
            ta.calculate_stochastic()
            ta.calculate_volume_indicators()

            # Get ML features
            features = ta.get_features_for_ml()
            ml_features = features.iloc[-1].values.reshape(1, -1) if features is not None else None

            # Get combined strategy signal
            signal_dict = self.strategy.get_signal(ta, ml_features)
            analysis['strategy_signal'] = signal_dict

            # Determine if trade should be opened
            if self.strategy.should_trade(signal_dict, self.config.PREDICTION_CONFIDENCE_THRESHOLD):
                analysis['should_trade'] = True

                # Log strategy explanation
                explanation = self.strategy.get_signal_explanation(signal_dict)
                logger.info(f"Trading Signal: {explanation}")

                # Send Telegram analysis
                self.telegram_notifier.send_signal_analysis(
                    self.config.SYMBOL,
                    signal_dict
                )

            return analysis

        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            self.telegram_notifier.send_error_alert(f"Market analysis error: {str(e)}")
            return {'error': str(e)}

    def execute_trade_logic(self, analysis):
        """Execute trading logic based on analysis.

        Args:
            analysis: Analysis dictionary from analyze_market()

        Returns:
            Trade result
        """
        try:
            if not analysis.get('should_trade'):
                return None

            signal_dict = analysis['strategy_signal']
            current_price = analysis['current_price']
            trade_type = 'BUY' if signal_dict['combined_signal'] == 'BUY' else 'SELL'

            # Get account balance for position sizing
            account_info = self.trading_engine.get_account_info()
            if account_info is None:
                logger.error("Cannot get account info")
                return None

            account_balance = account_info['balance']

            # Calculate position size based on risk
            sl_price = self.risk_manager.calculate_stop_loss(current_price, trade_type)
            position_size = self.risk_manager.calculate_position_size_by_risk(
                account_balance,
                current_price,
                sl_price,
                self.config.RISK_PERCENT_PER_TRADE
            )

            # Calculate R:R ratio
            tp_price = self.risk_manager.calculate_take_profit(current_price, trade_type)
            rr_ratio = self.risk_manager.calculate_risk_reward_ratio(
                current_price,
                sl_price,
                tp_price,
                trade_type
            )

            # Check if R:R ratio is acceptable
            if rr_ratio < self.config.MIN_RISK_REWARD_RATIO:
                logger.info(f"R:R ratio {rr_ratio:.2f} below minimum {self.config.MIN_RISK_REWARD_RATIO}")
                return None

            # Open trade
            trade_id = self.trading_engine.open_trade(
                self.config.SYMBOL,
                trade_type,
                position_size,
                current_price
            )

            if trade_id:
                # Send detailed position alert
                self.telegram_notifier.send_position_opened(
                    self.config.SYMBOL,
                    trade_type,
                    current_price,
                    position_size,
                    sl_price,
                    tp_price,
                    self.config.RISK_PERCENT_PER_TRADE
                )

                return {
                    'trade_id': trade_id,
                    'type': trade_type,
                    'entry_price': current_price,
                    'position_size': position_size,
                    'sl': sl_price,
                    'tp': tp_price,
                    'rr_ratio': rr_ratio
                }

            return None

        except Exception as e:
            logger.error(f"Error executing trade logic: {e}")
            self.telegram_notifier.send_error_alert(f"Trade execution error: {str(e)}")
            return None

    def monitor_positions(self):
        """Monitor open positions.

        Returns:
            Dictionary with monitoring results
        """
        try:
            positions = self.trading_engine.get_open_positions(self.config.SYMBOL)

            if not positions:
                return {'open_positions': 0}

            current_tick = mt5.symbol_info_tick(self.config.SYMBOL)
            if current_tick is None:
                return {'error': 'Cannot get current tick'}

            current_price = current_tick.bid
            unrealized_pnl = self.risk_manager.get_unrealized_pnl(current_price)

            logger.info(f"Monitoring {len(positions)} open positions")
            logger.info(f"Unrealized P&L: {unrealized_pnl:.2f}")

            return {
                'open_positions': len(positions),
                'current_price': current_price,
                'unrealized_pnl': unrealized_pnl
            }

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            return {'error': str(e)}

    def check_risk_alerts(self):
        """Check for risk management alerts.

        Returns:
            List of alerts
        """
        alerts = []

        # Check daily loss
        if self.risk_manager.daily_loss >= self.config.MAX_DAILY_LOSS * 0.8:
            alerts.append({
                'type': 'MAX_LOSS',
                'message': f"Daily loss limit approaching: {self.risk_manager.daily_loss:.2f}"
            })
            self.telegram_notifier.send_risk_alert(
                'MAX_LOSS',
                {
                    'daily_loss': self.risk_manager.daily_loss,
                    'limit': self.config.MAX_DAILY_LOSS
                }
            )

        # Check position size reduction
        multiplier = self.risk_manager.should_reduce_size_due_to_loss()
        if multiplier < 1.0:
            alerts.append({
                'type': 'SIZE_REDUCED',
                'message': f"Position size reduced to {multiplier*100:.0f}%"
            })

        return alerts

    def get_bot_status(self):
        """Get comprehensive bot status.

        Returns:
            Dictionary with bot status
        """
        account_info = self.trading_engine.get_account_info()
        risk_metrics = self.risk_manager.get_risk_metrics()

        return {
            'timestamp': datetime.now(),
            'account_info': account_info,
            'risk_metrics': risk_metrics,
            'mtf_enabled': self.config.MULTI_TIMEFRAME_ENABLED,
            'strategy_type': self.config.STRATEGY_TYPE,
            'open_trades': risk_metrics['open_trades'],
            'daily_pnl': -risk_metrics['daily_loss'] if risk_metrics['daily_loss'] > 0 else 0
        }

    def cleanup(self):
        """Cleanup resources."""
        if self.mtf_analyzer:
            self.mtf_analyzer.cleanup()
        logger.info("Advanced trading bot cleanup complete")

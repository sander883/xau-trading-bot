import logging
from datetime import datetime
import time

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False
    mt5 = None

logger = logging.getLogger(__name__)


class TradingEngine:
    """Main trading engine that executes trades and manages positions."""

    def __init__(self, config, data_fetcher, risk_manager, ml_model, telegram_notifier=None):
        """Initialize trading engine.

        Args:
            config: Configuration object
            data_fetcher: DataFetcher instance
            risk_manager: RiskManager instance
            ml_model: MLModel instance
            telegram_notifier: TelegramNotifier instance (optional)
        """
        self.config = config
        self.data_fetcher = data_fetcher
        self.risk_manager = risk_manager
        self.ml_model = ml_model
        self.telegram_notifier = telegram_notifier
        self.trades = {}
        self.order_counter = 0

    def should_open_trade(self, prediction, confidence, trend):
        """Determine if a trade should be opened.

        Args:
            prediction: Model prediction (0 or 1)
            confidence: Confidence score (0.0 to 1.0)
            trend: Trend direction ('UPTREND', 'DOWNTREND', 'SIDEWAYS')

        Returns:
            Tuple (should_trade, trade_type)
        """
        # Check confidence threshold
        if confidence < self.config.PREDICTION_CONFIDENCE_THRESHOLD:
            return False, None

        # Trade only when trend aligns with prediction
        if prediction == 1:  # Uptrend prediction
            if trend == 'UPTREND':
                return True, 'BUY'
        else:  # Downtrend prediction
            if trend == 'DOWNTREND':
                return True, 'SELL'

        return False, None

    def open_trade(self, symbol, trade_type, volume, entry_price):
        """Open a new trade.

        Args:
            symbol: Trading symbol
            trade_type: 'BUY' or 'SELL'
            volume: Volume in lots
            entry_price: Entry price

        Returns:
            Trade ID or None if failed
        """
        try:
            # Calculate SL and TP
            sl = self.risk_manager.calculate_stop_loss(entry_price, trade_type)
            tp = self.risk_manager.calculate_take_profit(entry_price, trade_type)

            # Validate price levels
            valid, msg = self.risk_manager.validate_price_levels(entry_price, sl, tp, trade_type)
            if not valid:
                logger.warning(f"Invalid price levels: {msg}")
                return None

            # Check if trade can be opened
            can_open, reason = self.risk_manager.can_open_trade(entry_price, trade_type)
            if not can_open:
                logger.warning(f"Cannot open trade: {reason}")
                return None

            # Prepare request
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': symbol,
                'volume': volume,
                'type': mt5.ORDER_TYPE_BUY if trade_type == 'BUY' else mt5.ORDER_TYPE_SELL,
                'price': entry_price,
                'sl': sl,
                'tp': tp,
                'deviation': 20,
                'magic': 123456,
                'comment': f'AI Trading Bot - {trade_type}',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }

            # Send order
            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order send failed: {result.comment}")
                return None

            # Record trade
            trade_id = result.order
            self.risk_manager.add_trade(
                trade_id,
                entry_price,
                trade_type,
                sl,
                tp
            )

            log_msg = f"Trade opened: ID={trade_id} Type={trade_type} Price={entry_price} SL={sl} TP={tp}"
            logger.info(log_msg)

            if self.telegram_notifier:
                self.telegram_notifier.send_trade_signal(log_msg)

            return trade_id

        except Exception as e:
            logger.error(f"Error opening trade: {e}")
            return None

    def close_trade(self, trade_id, symbol):
        """Close an open trade.

        Args:
            trade_id: Trade ID to close
            symbol: Trading symbol

        Returns:
            Exit price or None if failed
        """
        try:
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Failed to get tick: {mt5.last_error()}")
                return None

            exit_price = tick.bid

            # Prepare request
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'position': trade_id,
                'symbol': symbol,
                'volume': 0,  # Close entire position
                'type': mt5.ORDER_TYPE_SELL,
                'price': exit_price,
                'deviation': 20,
                'magic': 123456,
                'comment': 'AI Trading Bot - Close',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Close order failed: {result.comment}")
                return None

            logger.info(f"Trade closed: ID={trade_id} Exit Price={exit_price}")
            return exit_price

        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            return None

    def get_open_positions(self, symbol):
        """Get all open positions for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of open positions
        """
        try:
            positions = mt5.positions_get(symbol=symbol)
            if positions is None:
                return []
            return list(positions)
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def check_sl_tp(self, symbol, current_price):
        """Check and close trades based on SL/TP (if not using MT5 automatic).

        Args:
            symbol: Trading symbol
            current_price: Current price
        """
        try:
            positions = self.get_open_positions(symbol)

            for position in positions:
                # Check take profit
                if position.tp > 0:
                    if position.type == mt5.ORDER_TYPE_BUY and current_price >= position.tp:
                        self.close_trade(position.ticket, symbol)
                        continue

                    if position.type == mt5.ORDER_TYPE_SELL and current_price <= position.tp:
                        self.close_trade(position.ticket, symbol)
                        continue

                # Check stop loss
                if position.sl > 0:
                    if position.type == mt5.ORDER_TYPE_BUY and current_price <= position.sl:
                        self.close_trade(position.ticket, symbol)
                        continue

                    if position.type == mt5.ORDER_TYPE_SELL and current_price >= position.sl:
                        self.close_trade(position.ticket, symbol)
                        continue

        except Exception as e:
            logger.error(f"Error checking SL/TP: {e}")

    def execute_trading_cycle(self, features, ta_analysis, current_price):
        """Execute a complete trading cycle.

        Args:
            features: ML features array
            ta_analysis: TechnicalAnalysis instance
            current_price: Current market price

        Returns:
            Dictionary with cycle results
        """
        results = {
            'cycle_time': datetime.now(),
            'current_price': current_price,
            'trade_opened': False,
            'trade_id': None,
            'trend': None,
            'prediction': None,
            'confidence': None,
        }

        try:
            # Reset daily loss if needed
            self.risk_manager.check_daily_loss_reset()

            # Get trend
            trend = ta_analysis.identify_trend()
            results['trend'] = trend

            # Get ML prediction
            prediction, confidence = self.ml_model.predict_single(features)
            results['prediction'] = prediction
            results['confidence'] = confidence

            # Check if should open trade
            should_trade, trade_type = self.should_open_trade(prediction, confidence, trend)

            if should_trade:
                # Adjust volume based on risk
                size_multiplier = self.risk_manager.should_reduce_size_due_to_loss()
                volume = self.config.LOT_SIZE * size_multiplier

                trade_id = self.open_trade(self.config.SYMBOL, trade_type, volume, current_price)
                results['trade_opened'] = trade_id is not None
                results['trade_id'] = trade_id

            # Check SL/TP
            self.check_sl_tp(self.config.SYMBOL, current_price)

            return results

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            return results

    def get_account_info(self):
        """Get account information.

        Returns:
            Dictionary with account info
        """
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return None

            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'profit': account_info.profit,
                'margin': account_info.margin,
                'margin_free': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'leverage': account_info.leverage,
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def cleanup(self):
        """Cleanup and finalize."""
        logger.info("Trading engine cleanup")

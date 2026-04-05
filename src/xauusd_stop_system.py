import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DynamicStopLossCalculator:
    """Calculate dynamic stop loss based on volatility and market conditions."""

    def __init__(self, df):
        """Initialize stop loss calculator.

        Args:
            df: DataFrame with OHLC data
        """
        self.df = df.copy()

    def calculate_atr_based_sl(self, entry_price, atr, multiplier=2.0, trade_type='BUY'):
        """Calculate SL based on ATR.

        Args:
            entry_price: Entry price
            atr: Average True Range value
            multiplier: ATR multiplier (default 2.0)
            trade_type: BUY or SELL

        Returns:
            Stop loss price
        """
        try:
            sl_distance = atr * multiplier

            if trade_type == 'BUY':
                return entry_price - sl_distance
            else:
                return entry_price + sl_distance

        except Exception as e:
            logger.error(f"Error calculating ATR-based SL: {e}")
            return None

    def calculate_volatility_adjusted_sl(self, entry_price, current_atr, avg_atr, trade_type='BUY'):
        """Calculate SL adjusted for volatility level.

        Args:
            entry_price: Entry price
            current_atr: Current ATR
            avg_atr: Average ATR
            trade_type: BUY or SELL

        Returns:
            Stop loss price
        """
        try:
            atr_ratio = current_atr / avg_atr if avg_atr > 0 else 1

            # Adjust multiplier based on volatility
            if atr_ratio > 1.5:  # High volatility
                multiplier = 2.5
            elif atr_ratio > 1.2:  # Above average
                multiplier = 2.0
            elif atr_ratio > 0.8:  # Normal
                multiplier = 1.8
            else:  # Low volatility
                multiplier = 1.5

            return self.calculate_atr_based_sl(entry_price, current_atr, multiplier, trade_type)

        except Exception as e:
            logger.error(f"Error calculating volatility-adjusted SL: {e}")
            return None

    def calculate_support_resistance_sl(self, entry_price, trade_type='BUY', lookback=20):
        """Calculate SL based on recent support/resistance.

        Args:
            entry_price: Entry price
            trade_type: BUY or SELL
            lookback: Lookback period

        Returns:
            Stop loss price
        """
        try:
            if len(self.df) < lookback:
                return None

            recent = self.df.iloc[-lookback:]

            if trade_type == 'BUY':
                # For BUY, SL below nearest support
                recent_low = recent['Low'].min()
                # Add buffer (1-2 pips)
                sl = recent_low - 0.02
            else:
                # For SELL, SL above nearest resistance
                recent_high = recent['High'].max()
                # Add buffer
                sl = recent_high + 0.02

            return sl

        except Exception as e:
            logger.error(f"Error calculating support/resistance SL: {e}")
            return None

    def calculate_percentage_sl(self, entry_price, percent=2.0, trade_type='BUY'):
        """Calculate SL as percentage of entry price.

        Args:
            entry_price: Entry price
            percent: Percentage to risk (default 2%)
            trade_type: BUY or SELL

        Returns:
            Stop loss price
        """
        try:
            sl_distance = entry_price * (percent / 100)

            if trade_type == 'BUY':
                return entry_price - sl_distance
            else:
                return entry_price + sl_distance

        except Exception as e:
            logger.error(f"Error calculating percentage SL: {e}")
            return None

    def calculate_optimal_sl(self, entry_price, current_atr, avg_atr, trade_type='BUY'):
        """Calculate optimal SL considering multiple factors.

        Args:
            entry_price: Entry price
            current_atr: Current ATR
            avg_atr: Average ATR
            trade_type: BUY or SELL

        Returns:
            Dictionary with SL options
        """
        try:
            atr_based = self.calculate_atr_based_sl(entry_price, current_atr, 2.0, trade_type)
            volatility_adj = self.calculate_volatility_adjusted_sl(entry_price, current_atr, avg_atr, trade_type)
            support_res = self.calculate_support_resistance_sl(entry_price, trade_type)

            # Choose the most conservative (widest) SL
            if trade_type == 'BUY':
                valid_sls = [sl for sl in [atr_based, volatility_adj, support_res] if sl is not None]
                optimal_sl = min(valid_sls) if valid_sls else atr_based
            else:
                valid_sls = [sl for sl in [atr_based, volatility_adj, support_res] if sl is not None]
                optimal_sl = max(valid_sls) if valid_sls else atr_based

            return {
                'atr_based': atr_based,
                'volatility_adjusted': volatility_adj,
                'support_resistance': support_res,
                'recommended': optimal_sl
            }

        except Exception as e:
            logger.error(f"Error calculating optimal SL: {e}")
            return {'error': str(e)}


class TrailingStopSystem:
    """Implements trailing stop-loss mechanism."""

    def __init__(self, trailing_atr_multiplier=1.5):
        """Initialize trailing stop system.

        Args:
            trailing_atr_multiplier: ATR multiplier for trailing stop
        """
        self.trailing_atr_multiplier = trailing_atr_multiplier
        self.trades = {}  # Store active trades with trailing stops

    def add_trade_with_trailing_stop(self, trade_id, entry_price, atr, trade_type='BUY'):
        """Add trade with trailing stop.

        Args:
            trade_id: Unique trade ID
            entry_price: Entry price
            atr: Current ATR
            trade_type: BUY or SELL
        """
        try:
            initial_sl = entry_price - (atr * self.trailing_atr_multiplier) if trade_type == 'BUY' else entry_price + (atr * self.trailing_atr_multiplier)

            self.trades[trade_id] = {
                'entry_price': entry_price,
                'highest_price': entry_price if trade_type == 'BUY' else entry_price,
                'lowest_price': entry_price,
                'current_sl': initial_sl,
                'trade_type': trade_type,
                'atr': atr,
                'status': 'ACTIVE'
            }

            logger.info(f"Trade {trade_id} added with trailing stop at {initial_sl:.2f}")

        except Exception as e:
            logger.error(f"Error adding trade: {e}")

    def update_trailing_stop(self, trade_id, current_price, current_atr):
        """Update trailing stop for a trade.

        Args:
            trade_id: Trade ID
            current_price: Current market price
            current_atr: Current ATR

        Returns:
            Dictionary with trailing stop status
        """
        try:
            if trade_id not in self.trades:
                return {'error': f'Trade {trade_id} not found'}

            trade = self.trades[trade_id]

            if trade['status'] != 'ACTIVE':
                return {'status': 'INACTIVE'}

            trade_type = trade['trade_type']

            if trade_type == 'BUY':
                # Update highest price
                if current_price > trade['highest_price']:
                    trade['highest_price'] = current_price

                    # Update SL (moving only upward, never downward)
                    new_sl = current_price - (current_atr * self.trailing_atr_multiplier)

                    if new_sl > trade['current_sl']:
                        old_sl = trade['current_sl']
                        trade['current_sl'] = new_sl

                        logger.info(f"Trailing stop updated: {old_sl:.2f} → {new_sl:.2f}")

                        return {
                            'trade_id': trade_id,
                            'updated': True,
                            'old_sl': old_sl,
                            'new_sl': new_sl,
                            'price': current_price,
                            'status': 'Updated'
                        }

            else:  # SELL
                # Update lowest price
                if current_price < trade['lowest_price']:
                    trade['lowest_price'] = current_price

                    # Update SL (moving only downward, never upward)
                    new_sl = current_price + (current_atr * self.trailing_atr_multiplier)

                    if new_sl < trade['current_sl']:
                        old_sl = trade['current_sl']
                        trade['current_sl'] = new_sl

                        logger.info(f"Trailing stop updated: {old_sl:.2f} → {new_sl:.2f}")

                        return {
                            'trade_id': trade_id,
                            'updated': True,
                            'old_sl': old_sl,
                            'new_sl': new_sl,
                            'price': current_price,
                            'status': 'Updated'
                        }

            return {
                'trade_id': trade_id,
                'updated': False,
                'current_sl': trade['current_sl'],
                'status': 'No change'
            }

        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
            return {'error': str(e)}

    def check_stop_hit(self, trade_id, current_price):
        """Check if stop loss has been hit.

        Args:
            trade_id: Trade ID
            current_price: Current price

        Returns:
            Dictionary with stop status
        """
        try:
            if trade_id not in self.trades:
                return {'error': f'Trade {trade_id} not found'}

            trade = self.trades[trade_id]

            if trade['status'] != 'ACTIVE':
                return {'status': 'INACTIVE'}

            trade_type = trade['trade_type']
            current_sl = trade['current_sl']

            if trade_type == 'BUY':
                if current_price <= current_sl:
                    trade['status'] = 'STOPPED_OUT'
                    return {
                        'stopped_out': True,
                        'trade_type': trade_type,
                        'current_price': current_price,
                        'stop_level': current_sl,
                        'loss': current_price - trade['entry_price']
                    }

            else:  # SELL
                if current_price >= current_sl:
                    trade['status'] = 'STOPPED_OUT'
                    return {
                        'stopped_out': True,
                        'trade_type': trade_type,
                        'current_price': current_price,
                        'stop_level': current_sl,
                        'loss': trade['entry_price'] - current_price
                    }

            return {
                'stopped_out': False,
                'current_price': current_price,
                'stop_level': current_sl,
                'distance': abs(current_price - current_sl)
            }

        except Exception as e:
            logger.error(f"Error checking stop: {e}")
            return {'error': str(e)}

    def close_trade(self, trade_id):
        """Close a trade and remove from tracking.

        Args:
            trade_id: Trade ID

        Returns:
            Trade data
        """
        try:
            if trade_id not in self.trades:
                return {'error': f'Trade {trade_id} not found'}

            trade = self.trades[trade_id]
            trade['status'] = 'CLOSED'

            logger.info(f"Trade {trade_id} closed")

            return trade

        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            return {'error': str(e)}

    def get_all_active_trades(self):
        """Get all active trades with current stops.

        Returns:
            List of active trades
        """
        active = [
            {
                'trade_id': trade_id,
                'entry_price': trade['entry_price'],
                'current_sl': trade['current_sl'],
                'type': trade['trade_type'],
                'status': trade['status']
            }
            for trade_id, trade in self.trades.items()
            if trade['status'] == 'ACTIVE'
        ]

        return active

    def get_trade_summary(self, trade_id):
        """Get summary of a specific trade.

        Args:
            trade_id: Trade ID

        Returns:
            Trade summary
        """
        try:
            if trade_id not in self.trades:
                return {'error': f'Trade {trade_id} not found'}

            trade = self.trades[trade_id]

            return {
                'trade_id': trade_id,
                'entry_price': trade['entry_price'],
                'current_sl': trade['current_sl'],
                'trade_type': trade['trade_type'],
                'highest_price': trade.get('highest_price'),
                'lowest_price': trade.get('lowest_price'),
                'status': trade['status'],
                'trailing_distance': abs(trade['current_sl'] - trade['entry_price'])
            }

        except Exception as e:
            logger.error(f"Error getting trade summary: {e}")
            return {'error': str(e)}

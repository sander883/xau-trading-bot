import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages risk parameters for trading."""

    def __init__(self, config):
        """Initialize risk manager.

        Args:
            config: Configuration object
        """
        self.config = config
        self.daily_loss = 0.0
        self.daily_loss_reset_time = datetime.now()
        self.open_trades = []

    def can_open_trade(self, current_price, trade_type='BUY'):
        """Check if a new trade can be opened.

        Args:
            current_price: Current market price
            trade_type: 'BUY' or 'SELL'

        Returns:
            Tuple (can_open, reason)
        """
        # Check max open trades
        if len(self.open_trades) >= self.config.MAX_OPEN_TRADES:
            return False, f"Max open trades ({self.config.MAX_OPEN_TRADES}) reached"

        # Check daily loss limit
        if self.daily_loss >= self.config.MAX_DAILY_LOSS:
            return False, f"Daily loss limit ({self.config.MAX_DAILY_LOSS}) exceeded"

        # Check position size
        position_size = self.config.LOT_SIZE
        if position_size > self.config.MAX_POSITION_SIZE:
            return False, f"Position size ({position_size}) exceeds max ({self.config.MAX_POSITION_SIZE})"

        return True, "OK"

    def calculate_stop_loss(self, entry_price, trade_type='BUY'):
        """Calculate stop loss level.

        Args:
            entry_price: Entry price
            trade_type: 'BUY' or 'SELL'

        Returns:
            Stop loss price
        """
        # XAUUSD has 2 decimal places for pips
        pip_value = 0.01
        sl_distance = self.config.STOP_LOSS_PIPS * pip_value

        if trade_type == 'BUY':
            return entry_price - sl_distance
        else:
            return entry_price + sl_distance

    def calculate_take_profit(self, entry_price, trade_type='BUY'):
        """Calculate take profit level.

        Args:
            entry_price: Entry price
            trade_type: 'BUY' or 'SELL'

        Returns:
            Take profit price
        """
        pip_value = 0.01
        tp_distance = self.config.TAKE_PROFIT_PIPS * pip_value

        if trade_type == 'BUY':
            return entry_price + tp_distance
        else:
            return entry_price - tp_distance

    def add_trade(self, trade_id, entry_price, trade_type, sl, tp):
        """Record an opened trade.

        Args:
            trade_id: Unique trade identifier
            entry_price: Entry price
            trade_type: 'BUY' or 'SELL'
            sl: Stop loss price
            tp: Take profit price
        """
        trade = {
            'id': trade_id,
            'entry_price': entry_price,
            'type': trade_type,
            'stop_loss': sl,
            'take_profit': tp,
            'open_time': datetime.now(),
            'status': 'OPEN'
        }
        self.open_trades.append(trade)
        logger.info(f"Trade added: {trade_id} - {trade_type} @ {entry_price} SL:{sl} TP:{tp}")

    def close_trade(self, trade_id, exit_price, profit_loss):
        """Close a trade and update P&L.

        Args:
            trade_id: Trade identifier
            exit_price: Exit price
            profit_loss: Profit/loss amount
        """
        for trade in self.open_trades:
            if trade['id'] == trade_id:
                trade['exit_price'] = exit_price
                trade['profit_loss'] = profit_loss
                trade['close_time'] = datetime.now()
                trade['status'] = 'CLOSED'

                # Update daily loss
                if profit_loss < 0:
                    self.daily_loss += abs(profit_loss)

                logger.info(f"Trade closed: {trade_id} - Exit:{exit_price} P&L:{profit_loss}")
                break

    def check_daily_loss_reset(self):
        """Reset daily loss if new day."""
        now = datetime.now()
        if (now - self.daily_loss_reset_time).days > 0:
            self.daily_loss = 0.0
            self.daily_loss_reset_time = now
            logger.info("Daily loss reset for new trading day")

    def get_risk_metrics(self):
        """Get current risk metrics.

        Returns:
            Dictionary with risk metrics
        """
        open_count = len(self.open_trades)
        closed_trades = [t for t in self.open_trades if t['status'] == 'CLOSED']

        total_profit_loss = sum(t.get('profit_loss', 0) for t in closed_trades)
        winning_trades = sum(1 for t in closed_trades if t.get('profit_loss', 0) > 0)
        losing_trades = sum(1 for t in closed_trades if t.get('profit_loss', 0) < 0)

        win_rate = (winning_trades / len(closed_trades) * 100) if closed_trades else 0

        return {
            'open_trades': open_count,
            'total_closed_trades': len(closed_trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit_loss': total_profit_loss,
            'daily_loss': self.daily_loss,
            'daily_loss_limit': self.config.MAX_DAILY_LOSS,
            'remaining_daily_loss_limit': max(0, self.config.MAX_DAILY_LOSS - self.daily_loss)
        }

    def should_reduce_size_due_to_loss(self):
        """Determine if position size should be reduced due to losses.

        Returns:
            Multiplier for position size (0.5 for half-size, 1.0 for normal)
        """
        daily_loss_percentage = (self.daily_loss / self.config.INITIAL_BALANCE) * 100

        if daily_loss_percentage > 5:
            return 0.25  # Quarter size
        elif daily_loss_percentage > 2:
            return 0.5   # Half size
        else:
            return 1.0   # Normal size

    def validate_price_levels(self, entry, sl, tp, trade_type):
        """Validate that SL and TP are logical.

        Args:
            entry: Entry price
            sl: Stop loss price
            tp: Take profit price
            trade_type: 'BUY' or 'SELL'

        Returns:
            Tuple (is_valid, message)
        """
        if trade_type == 'BUY':
            if sl >= entry:
                return False, "SL must be below entry for BUY"
            if tp <= entry:
                return False, "TP must be above entry for BUY"
            if entry >= tp:
                return False, "Entry must be below TP for BUY"
        else:
            if sl <= entry:
                return False, "SL must be above entry for SELL"
            if tp >= entry:
                return False, "TP must be below entry for SELL"
            if entry <= tp:
                return False, "Entry must be above TP for SELL"

        return True, "Valid"

    def get_unrealized_pnl(self, current_price):
        """Calculate unrealized P&L for open trades.

        Args:
            current_price: Current market price

        Returns:
            Unrealized P&L amount
        """
        unrealized_pnl = 0.0

        for trade in self.open_trades:
            if trade['status'] == 'OPEN':
                if trade['type'] == 'BUY':
                    unrealized_pnl += (current_price - trade['entry_price']) * 100  # Simplified
                else:
                    unrealized_pnl += (trade['entry_price'] - current_price) * 100  # Simplified

        return unrealized_pnl

    def calculate_position_size_by_risk(self, account_balance, entry_price, sl_price, risk_percent=2.0):
        """Calculate position size based on risk percentage.

        Risk = (Entry - SL) * Position_Size * Pip_Value

        Args:
            account_balance: Current account balance
            entry_price: Entry price
            sl_price: Stop loss price
            risk_percent: Risk percentage of account (default 2%)

        Returns:
            Position size in lots
        """
        try:
            # Risk amount in account currency
            risk_amount = account_balance * (risk_percent / 100)

            # Distance to SL in pips (XAUUSD is 0.01 per pip)
            pip_value = 0.01
            sl_distance_pips = abs(entry_price - sl_price) / pip_value

            if sl_distance_pips == 0:
                logger.warning("SL distance is zero, cannot calculate position size")
                return self.config.LOT_SIZE

            # Position size = Risk Amount / (SL Distance in Pips * Pip Value * 100000)
            # For XAUUSD: 1 lot = 100 oz, 1 pip = 0.01
            position_size = risk_amount / (sl_distance_pips * pip_value * 100)

            # Apply max position size limit
            position_size = min(position_size, self.config.MAX_POSITION_SIZE)

            # Apply loss-based reduction
            reduction_multiplier = self.should_reduce_size_due_to_loss()
            position_size *= reduction_multiplier

            logger.info(f"Calculated position size: {position_size:.2f} lots "
                       f"(Risk: {risk_percent}%, SL: {sl_distance_pips:.2f} pips)")

            return max(0.01, position_size)  # Minimum 0.01 lots

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.config.LOT_SIZE

    def calculate_risk_reward_ratio(self, entry_price, sl_price, tp_price, trade_type='BUY'):
        """Calculate risk/reward ratio for a trade.

        Args:
            entry_price: Entry price
            sl_price: Stop loss price
            tp_price: Take profit price
            trade_type: 'BUY' or 'SELL'

        Returns:
            Risk/reward ratio (float)
        """
        try:
            pip_value = 0.01

            if trade_type == 'BUY':
                risk_pips = (entry_price - sl_price) / pip_value
                reward_pips = (tp_price - entry_price) / pip_value
            else:
                risk_pips = (sl_price - entry_price) / pip_value
                reward_pips = (entry_price - tp_price) / pip_value

            if risk_pips == 0:
                return 0

            ratio = reward_pips / risk_pips
            return max(0, ratio)

        except Exception as e:
            logger.error(f"Error calculating risk/reward ratio: {e}")
            return 0

    def get_optimal_position_size(self, account_balance, entry_price, sl_price,
                                 risk_percent=2.0, min_rr_ratio=1.5):
        """Get optimal position size with risk/reward validation.

        Args:
            account_balance: Current account balance
            entry_price: Entry price
            sl_price: Stop loss price
            risk_percent: Risk percentage (default 2%)
            min_rr_ratio: Minimum R:R ratio to accept (default 1.5:1)

        Returns:
            Tuple of (position_size, is_valid, reason)
        """
        position_size = self.calculate_position_size_by_risk(
            account_balance, entry_price, sl_price, risk_percent
        )

        return position_size, True, "Valid position size"

    def get_account_risk_metrics(self, account_balance, current_equity):
        """Get risk metrics based on account status.

        Args:
            account_balance: Account balance
            current_equity: Current equity

        Returns:
            Dictionary with risk metrics
        """
        drawdown_amount = account_balance - current_equity
        drawdown_percent = (drawdown_amount / account_balance * 100) if account_balance > 0 else 0

        daily_loss_percent = (self.daily_loss / account_balance * 100) if account_balance > 0 else 0

        return {
            'account_balance': account_balance,
            'current_equity': current_equity,
            'drawdown_amount': drawdown_amount,
            'drawdown_percent': drawdown_percent,
            'daily_loss_amount': self.daily_loss,
            'daily_loss_percent': daily_loss_percent,
            'max_daily_loss_allowed': self.config.MAX_DAILY_LOSS,
            'daily_loss_remaining': max(0, self.config.MAX_DAILY_LOSS - self.daily_loss),
            'position_size_multiplier': self.should_reduce_size_due_to_loss()
        }

    def cleanup(self):
        """Cleanup and finalize."""
        logger.info(f"Risk manager cleanup - {len(self.open_trades)} trades in memory")

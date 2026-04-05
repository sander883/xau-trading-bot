import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class XAUUSDVolatilityFilter:
    """XAUUSD-specific volatility analysis and filtering."""

    # XAUUSD typical ATR ranges (varies by instrument)
    # These should be adjusted based on your data
    ATR_RANGES = {
        'VERY_LOW': (0, 3),           # < 3 pips - too little movement
        'LOW': (3, 6),                # 3-6 pips - low volatility
        'NORMAL': (6, 15),            # 6-15 pips - optimal range
        'HIGH': (15, 30),             # 15-30 pips - high volatility
        'VERY_HIGH': (30, 100),       # > 30 pips - extreme volatility
    }

    # Volatility score for position sizing
    VOLATILITY_MULTIPLIERS = {
        'VERY_LOW': 0.5,              # Trade only with tight SL
        'LOW': 0.7,
        'NORMAL': 1.0,                # Standard sizing
        'HIGH': 1.3,                  # Can increase size (wider SL)
        'VERY_HIGH': 0.3,             # Reduce size significantly
    }

    def __init__(self, df, lookback=20):
        """Initialize volatility filter.

        Args:
            df: DataFrame with OHLC data
            lookback: Lookback period for ATR calculation
        """
        self.df = df.copy()
        self.lookback = lookback
        self.current_atr = None
        self.avg_atr = None
        self.volatility_level = None

    def calculate_atr(self, period=14):
        """Calculate ATR for the dataframe.

        Args:
            period: ATR period (default 14)

        Returns:
            Series with ATR values
        """
        try:
            high = self.df['High']
            low = self.df['Low']
            close = self.df['Close']

            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()

            self.current_atr = atr.iloc[-1]
            self.avg_atr = atr.mean()

            logger.debug(f"ATR calculated: Current={self.current_atr:.2f}, Average={self.avg_atr:.2f}")

            return atr

        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return None

    def get_volatility_level(self):
        """Get current volatility level based on ATR.

        Returns:
            Dictionary with volatility analysis
        """
        try:
            atr = self.calculate_atr()
            if atr is None or self.current_atr is None:
                return {'error': 'Cannot calculate volatility'}

            current_atr = self.current_atr

            # Determine volatility level
            for level, (min_atr, max_atr) in self.ATR_RANGES.items():
                if min_atr <= current_atr < max_atr:
                    self.volatility_level = level
                    break
            else:
                if current_atr >= 100:
                    self.volatility_level = 'VERY_HIGH'
                else:
                    self.volatility_level = 'VERY_LOW'

            # Historical context
            avg_atr = atr.iloc[-20:].mean()
            vol_percentile = (current_atr / avg_atr) if avg_atr > 0 else 1

            return {
                'current_atr': current_atr,
                'average_atr': avg_atr,
                'volatility_level': self.volatility_level,
                'atr_ratio': vol_percentile,
                'is_normal_volatility': 'NORMAL' in self.volatility_level or 'HIGH' == self.volatility_level,
                'multiplier': self.VOLATILITY_MULTIPLIERS.get(self.volatility_level, 1.0),
                'recommendation': self._get_volatility_recommendation()
            }

        except Exception as e:
            logger.error(f"Error getting volatility level: {e}")
            return {'error': str(e)}

    def _get_volatility_recommendation(self):
        """Get trading recommendation based on volatility.

        Returns:
            Recommendation string
        """
        recommendations = {
            'VERY_LOW': 'AVOID - Market too quiet, tight SL may get hit by noise',
            'LOW': 'CAUTION - Low volatility, wait for expansion',
            'NORMAL': 'OPTIMAL - Normal conditions, standard strategy',
            'HIGH': 'GOOD - High volatility, wide SL acceptable',
            'VERY_HIGH': 'RISKY - Extreme volatility, reduce size significantly',
        }

        return recommendations.get(self.volatility_level, 'UNKNOWN')

    def is_volatility_acceptable(self, min_vol='LOW', max_vol='VERY_HIGH'):
        """Check if volatility is within acceptable range.

        Args:
            min_vol: Minimum acceptable volatility
            max_vol: Maximum acceptable volatility

        Returns:
            Tuple (is_acceptable, reason)
        """
        try:
            vol_data = self.get_volatility_level()

            if 'error' in vol_data:
                return False, vol_data['error']

            current_level = vol_data['volatility_level']
            levels_order = ['VERY_LOW', 'LOW', 'NORMAL', 'HIGH', 'VERY_HIGH']

            min_idx = levels_order.index(min_vol)
            max_idx = levels_order.index(max_vol)
            current_idx = levels_order.index(current_level)

            if min_idx <= current_idx <= max_idx:
                return True, f"Volatility acceptable: {current_level}"
            else:
                return False, f"Volatility {current_level} outside range {min_vol}-{max_vol}"

        except Exception as e:
            logger.error(f"Error checking volatility range: {e}")
            return False, str(e)

    def get_position_size_multiplier(self):
        """Get position size multiplier based on volatility.

        Returns:
            Multiplier (0.1 to 1.5)
        """
        vol_data = self.get_volatility_level()
        return vol_data.get('multiplier', 1.0)

    def get_volatility_adjusted_sl(self, entry_price, base_sl, trade_type='BUY'):
        """Adjust SL based on volatility.

        Args:
            entry_price: Entry price
            base_sl: Base stop loss price
            trade_type: BUY or SELL

        Returns:
            Adjusted stop loss price
        """
        try:
            vol_data = self.get_volatility_level()
            atr = vol_data.get('current_atr', 0)

            if trade_type == 'BUY':
                # For BUY, SL is below entry
                # Widen SL in high volatility
                if self.volatility_level == 'VERY_HIGH':
                    adjusted_sl = entry_price - (atr * 1.5)
                elif self.volatility_level == 'HIGH':
                    adjusted_sl = entry_price - (atr * 1.2)
                elif self.volatility_level == 'LOW':
                    adjusted_sl = entry_price - (atr * 0.8)
                elif self.volatility_level == 'VERY_LOW':
                    # Very tight SL - use multiple of current spread
                    adjusted_sl = entry_price - 2  # 2 pips
                else:
                    adjusted_sl = base_sl
            else:
                # For SELL, SL is above entry
                if self.volatility_level == 'VERY_HIGH':
                    adjusted_sl = entry_price + (atr * 1.5)
                elif self.volatility_level == 'HIGH':
                    adjusted_sl = entry_price + (atr * 1.2)
                elif self.volatility_level == 'LOW':
                    adjusted_sl = entry_price + (atr * 0.8)
                elif self.volatility_level == 'VERY_LOW':
                    adjusted_sl = entry_price + 2  # 2 pips
                else:
                    adjusted_sl = base_sl

            return adjusted_sl

        except Exception as e:
            logger.error(f"Error adjusting SL: {e}")
            return base_sl

    def get_volatility_adjusted_tp(self, entry_price, base_tp, trade_type='BUY'):
        """Adjust TP based on volatility.

        Args:
            entry_price: Entry price
            base_tp: Base take profit price
            trade_type: BUY or SELL

        Returns:
            Adjusted take profit price
        """
        try:
            vol_data = self.get_volatility_level()
            atr = vol_data.get('current_atr', 0)

            if trade_type == 'BUY':
                # For BUY, TP is above entry
                if self.volatility_level == 'VERY_HIGH':
                    adjusted_tp = entry_price + (atr * 2.0)
                elif self.volatility_level == 'HIGH':
                    adjusted_tp = entry_price + (atr * 1.5)
                elif self.volatility_level == 'LOW':
                    adjusted_tp = entry_price + (atr * 0.8)
                elif self.volatility_level == 'VERY_LOW':
                    adjusted_tp = entry_price + 5  # 5 pips
                else:
                    adjusted_tp = base_tp
            else:
                # For SELL, TP is below entry
                if self.volatility_level == 'VERY_HIGH':
                    adjusted_tp = entry_price - (atr * 2.0)
                elif self.volatility_level == 'HIGH':
                    adjusted_tp = entry_price - (atr * 1.5)
                elif self.volatility_level == 'LOW':
                    adjusted_tp = entry_price - (atr * 0.8)
                elif self.volatility_level == 'VERY_LOW':
                    adjusted_tp = entry_price - 5  # 5 pips
                else:
                    adjusted_tp = base_tp

            return adjusted_tp

        except Exception as e:
            logger.error(f"Error adjusting TP: {e}")
            return base_tp

    def is_volatility_breakout_imminent(self):
        """Detect if volatility breakout is likely (Bollinger Bands squeezing).

        Returns:
            Dictionary with breakout analysis
        """
        try:
            if len(self.df) < 30:
                return {'is_squeeze': False}

            # Calculate Bollinger Bands
            sma = self.df['Close'].rolling(20).mean()
            std = self.df['Close'].rolling(20).std()

            bb_upper = sma + (std * 2)
            bb_lower = sma - (std * 2)
            bb_width = bb_upper - bb_lower

            current_width = bb_width.iloc[-1]
            avg_width = bb_width.iloc[-20:].mean()

            # Squeeze when width is less than average
            width_ratio = current_width / avg_width if avg_width > 0 else 1

            if width_ratio < 0.7:
                return {
                    'is_squeeze': True,
                    'bb_width_ratio': width_ratio,
                    'recommendation': 'Prepare for volatility expansion',
                    'breakout_potential': 'HIGH'
                }

            return {
                'is_squeeze': False,
                'bb_width_ratio': width_ratio,
                'recommendation': 'Normal volatility',
                'breakout_potential': 'NORMAL'
            }

        except Exception as e:
            logger.error(f"Error detecting squeeze: {e}")
            return {'error': str(e)}

    def get_volatility_profile(self):
        """Get complete volatility profile.

        Returns:
            Dictionary with full volatility analysis
        """
        vol_level = self.get_volatility_level()
        squeeze = self.is_volatility_breakout_imminent()

        return {
            'timestamp': pd.Timestamp.now(),
            'volatility_analysis': vol_level,
            'breakout_analysis': squeeze,
            'trading_recommendation': vol_level.get('recommendation'),
            'position_size_multiplier': vol_level.get('multiplier', 1.0),
            'can_trade': vol_level.get('is_normal_volatility', False) and 'is_squeeze' in squeeze
        }

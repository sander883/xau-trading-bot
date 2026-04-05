import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class LiquidityDetector:
    """Detects low liquidity, fake breakouts, and stop hunts."""

    def __init__(self, df, lookback=20):
        """Initialize liquidity detector.

        Args:
            df: DataFrame with OHLC data
            lookback: Lookback period for analysis
        """
        self.df = df.copy()
        self.lookback = lookback

    def detect_long_wicks(self, wick_threshold=2.0):
        """Detect candles with abnormally long wicks (stop hunt signals).

        Args:
            wick_threshold: Ratio of wick to body size

        Returns:
            Dictionary with wick analysis
        """
        if len(self.df) < 1:
            return None

        current = self.df.iloc[-1]
        body_size = abs(current['Close'] - current['Open'])

        if body_size == 0:
            return {'has_long_wicks': False, 'reason': 'Doji candle'}

        # Upper wick size
        upper_wick = current['High'] - max(current['Close'], current['Open'])

        # Lower wick size
        lower_wick = min(current['Close'], current['Open']) - current['Low']

        # Calculate recent average body size for context
        recent_bodies = [abs(self.df.iloc[i]['Close'] - self.df.iloc[i]['Open'])
                        for i in range(max(0, len(self.df)-self.lookback), len(self.df))]
        avg_body = np.mean(recent_bodies) if recent_bodies else body_size

        has_upper_wick = upper_wick > body_size * wick_threshold
        has_lower_wick = lower_wick > body_size * wick_threshold

        if has_upper_wick or has_lower_wick:
            return {
                'has_long_wicks': True,
                'upper_wick_size': upper_wick,
                'lower_wick_size': lower_wick,
                'upper_wick_ratio': upper_wick / body_size if body_size > 0 else 0,
                'lower_wick_ratio': lower_wick / body_size if body_size > 0 else 0,
                'stop_hunt_direction': 'UP' if has_upper_wick else 'DOWN',
                'risk_level': 'HIGH' if max(upper_wick, lower_wick) > body_size * 3 else 'MEDIUM',
                'current_high': current['High'],
                'current_low': current['Low'],
                'body_close_price': current['Close']
            }

        return {'has_long_wicks': False}

    def detect_false_breakout(self):
        """Detect false breakouts where price breaks level then reverses.

        Returns:
            Dictionary with breakout analysis
        """
        if len(self.df) < 5:
            return None

        current = self.df.iloc[-1]
        recent = self.df.iloc[-5:]

        # Calculate recent high/low
        recent_high = recent['High'].max()
        recent_low = recent['Low'].min()
        recent_high_idx = recent['High'].idxmax()
        recent_low_idx = recent['Low'].idxmin()

        # Check if current candle breaks but closes inside range
        closes_inside = (current['Close'] > recent_low) and (current['Close'] < recent_high)

        # Check if candle reverses significantly
        reversal_size = abs(current['Close'] - current['Open'])
        body_pct = reversal_size / recent['High'].iloc[-1] if recent['High'].iloc[-1] > 0 else 0

        if closes_inside and current['High'] >= recent_high:
            # Potential false breakout up
            return {
                'is_false_breakout': True,
                'direction': 'UP',
                'breakout_level': recent_high,
                'close_price': current['Close'],
                'close_inside_range': True,
                'reversal_strength': body_pct,
                'recommendation': 'AVOID - False breakout detected'
            }

        if closes_inside and current['Low'] <= recent_low:
            # Potential false breakout down
            return {
                'is_false_breakout': True,
                'direction': 'DOWN',
                'breakout_level': recent_low,
                'close_price': current['Close'],
                'close_inside_range': True,
                'reversal_strength': body_pct,
                'recommendation': 'AVOID - False breakout detected'
            }

        return {'is_false_breakout': False}

    def detect_low_volume_breakout(self):
        """Detect breakouts on low volume (likely false).

        Returns:
            Dictionary with volume analysis
        """
        if len(self.df) < 20 or 'Volume' not in self.df.columns:
            return None

        current_volume = self.df['Volume'].iloc[-1]
        avg_volume = self.df['Volume'].iloc[-20:].mean()

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        if volume_ratio < 0.6:
            return {
                'has_low_volume': True,
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'confidence': 'LOW',
                'recommendation': 'AVOID - Low volume breakout'
            }

        return {'has_low_volume': False, 'volume_ratio': volume_ratio}

    def detect_narrow_range(self):
        """Detect NR (Narrow Range) bars - potential breakout setup.

        Returns:
            Dictionary with range analysis
        """
        if len(self.df) < 20:
            return None

        current = self.df.iloc[-1]
        current_range = current['High'] - current['Low']

        # Average range of last 20 candles
        recent_ranges = [self.df.iloc[i]['High'] - self.df.iloc[i]['Low']
                        for i in range(len(self.df)-20, len(self.df))]
        avg_range = np.mean(recent_ranges)

        # NR means range is smaller than recent average
        nr_ratio = current_range / avg_range if avg_range > 0 else 1

        if nr_ratio < 0.7:
            return {
                'is_narrow_range': True,
                'current_range': current_range,
                'average_range': avg_range,
                'nr_ratio': nr_ratio,
                'potential_breakout': 'YES',
                'recommendation': 'Prepare for potential breakout'
            }

        return {
            'is_narrow_range': False,
            'nr_ratio': nr_ratio,
            'current_range': current_range,
            'average_range': avg_range
        }

    def get_liquidity_score(self):
        """Calculate overall liquidity score (0-1).

        Returns:
            Liquidity score
        """
        score = 1.0  # Start at perfect liquidity

        # Penalty for long wicks
        wicks = self.detect_long_wicks()
        if wicks and wicks.get('has_long_wicks'):
            score -= 0.3

        # Penalty for false breakouts
        breakout = self.detect_false_breakout()
        if breakout and breakout.get('is_false_breakout'):
            score -= 0.2

        # Penalty for low volume
        volume = self.detect_low_volume_breakout()
        if volume and volume.get('has_low_volume'):
            score -= 0.2

        return max(0, min(1, score))

    def is_safe_to_trade(self):
        """Check if current conditions are safe for trading.

        Returns:
            Tuple (is_safe, reason)
        """
        # Check for stop hunts
        wicks = self.detect_long_wicks()
        if wicks and wicks.get('has_long_wicks') and wicks.get('risk_level') == 'HIGH':
            return False, f"Potential stop hunt detected: {wicks['stop_hunt_direction']}"

        # Check for false breakouts
        breakout = self.detect_false_breakout()
        if breakout and breakout.get('is_false_breakout'):
            return False, f"False breakout detected: {breakout['direction']}"

        # Check for low volume
        volume = self.detect_low_volume_breakout()
        if volume and volume.get('has_low_volume'):
            return False, "Low volume - avoid entry"

        # Overall liquidity score
        liquidity = self.get_liquidity_score()
        if liquidity < 0.5:
            return False, f"Poor liquidity conditions (score: {liquidity:.2f})"

        return True, "Safe conditions for trading"

    def get_liquidity_report(self):
        """Get comprehensive liquidity analysis.

        Returns:
            Dictionary with all liquidity checks
        """
        return {
            'timestamp': pd.Timestamp.now(),
            'wicks_analysis': self.detect_long_wicks(),
            'false_breakout_analysis': self.detect_false_breakout(),
            'volume_analysis': self.detect_low_volume_breakout(),
            'narrow_range_analysis': self.detect_narrow_range(),
            'liquidity_score': self.get_liquidity_score(),
            'is_safe_to_trade': self.is_safe_to_trade()[0],
            'safety_reason': self.is_safe_to_trade()[1]
        }

    def get_entry_quality_score(self):
        """Get overall entry quality score considering all factors.

        Returns:
            Score from 0-1 (1 = perfect conditions)
        """
        score = 0.5  # Base score

        # Add points for good conditions
        liquidity_score = self.get_liquidity_score()
        score += liquidity_score * 0.3

        # Check narrow range (good for breakout)
        nr = self.detect_narrow_range()
        if nr and nr.get('is_narrow_range'):
            score += 0.2

        # Penalties already applied in liquidity_score

        return max(0, min(1, score))

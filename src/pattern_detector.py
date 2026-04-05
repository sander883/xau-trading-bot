import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detects candlestick patterns and price action signals."""

    def __init__(self, df):
        """Initialize pattern detector.

        Args:
            df: DataFrame with OHLC data
        """
        self.df = df.copy()
        self.patterns = {}

    def detect_engulfing(self, lookback=2):
        """Detect bullish and bearish engulfing patterns.

        Args:
            lookback: Number of candles to check

        Returns:
            Dictionary with pattern info
        """
        if len(self.df) < lookback + 1:
            return None

        current = self.df.iloc[-1]
        previous = self.df.iloc[-2]

        # Body size calculation
        current_body = abs(current['Close'] - current['Open'])
        prev_body = abs(previous['Close'] - previous['Open'])

        # Bullish engulfing: current closes higher than previous opens, opens lower
        bullish = (
            current['Open'] < previous['Close'] and
            current['Close'] > previous['Open'] and
            current_body > prev_body * 0.8  # At least 80% of previous body
        )

        # Bearish engulfing: opposite
        bearish = (
            current['Open'] > previous['Close'] and
            current['Close'] < previous['Open'] and
            current_body > prev_body * 0.8
        )

        if bullish:
            return {
                'pattern': 'BULLISH_ENGULFING',
                'strength': min(1.0, current_body / prev_body),
                'signal': 'BUY',
                'confidence': 0.7
            }

        if bearish:
            return {
                'pattern': 'BEARISH_ENGULFING',
                'strength': min(1.0, current_body / prev_body),
                'signal': 'SELL',
                'confidence': 0.7
            }

        return None

    def detect_pin_bar(self, wick_ratio=2.5):
        """Detect pin bar (hammer/hanging man) patterns.

        Args:
            wick_ratio: Ratio of wick to body size

        Returns:
            Dictionary with pattern info
        """
        if len(self.df) < 1:
            return None

        current = self.df.iloc[-1]

        body_size = abs(current['Close'] - current['Open'])
        if body_size == 0:
            return None

        # Lower wick (rejection from below)
        lower_wick = current['Open'] - current['Low'] if current['Open'] < current['Close'] else current['Close'] - current['Low']

        # Upper wick (rejection from above)
        upper_wick = current['High'] - current['Close'] if current['Open'] < current['Close'] else current['High'] - current['Open']

        # Bullish pin bar (hammer): long lower wick, small body at top
        if lower_wick > body_size * wick_ratio and upper_wick < body_size * 0.5:
            return {
                'pattern': 'BULLISH_PIN_BAR',
                'strength': min(1.0, lower_wick / body_size / wick_ratio),
                'signal': 'BUY',
                'confidence': 0.65
            }

        # Bearish pin bar (hanging man): long upper wick, small body at bottom
        if upper_wick > body_size * wick_ratio and lower_wick < body_size * 0.5:
            return {
                'pattern': 'BEARISH_PIN_BAR',
                'strength': min(1.0, upper_wick / body_size / wick_ratio),
                'signal': 'SELL',
                'confidence': 0.65
            }

        return None

    def detect_inside_bar(self):
        """Detect inside bar (compression/consolidation).

        Returns:
            Dictionary with pattern info
        """
        if len(self.df) < 2:
            return None

        current = self.df.iloc[-1]
        previous = self.df.iloc[-2]

        # Inside bar: High < Previous High AND Low > Previous Low
        is_inside = (
            current['High'] < previous['High'] and
            current['Low'] > previous['Low']
        )

        if is_inside:
            compression_ratio = (previous['High'] - previous['Low']) / (current['High'] - current['Low'])
            return {
                'pattern': 'INSIDE_BAR',
                'strength': min(1.0, compression_ratio),
                'signal': 'COMPRESSION',
                'confidence': 0.6,
                'breakout_potential': compression_ratio  # Higher = more potential
            }

        return None

    def detect_rejection_candles(self):
        """Detect rejection candles (wicks showing rejection).

        Returns:
            Dictionary with pattern info
        """
        if len(self.df) < 1:
            return None

        current = self.df.iloc[-1]
        body_size = abs(current['Close'] - current['Open'])

        if body_size == 0:
            return None

        # High wick rejection (at resistance)
        upper_wick = current['High'] - max(current['Close'], current['Open'])

        # Low wick rejection (at support)
        lower_wick = min(current['Close'], current['Open']) - current['Low']

        if upper_wick > body_size * 1.5:
            return {
                'pattern': 'UPPER_REJECTION',
                'strength': min(1.0, upper_wick / body_size / 2),
                'signal': 'SELL',
                'confidence': 0.6,
                'rejection_level': current['High']
            }

        if lower_wick > body_size * 1.5:
            return {
                'pattern': 'LOWER_REJECTION',
                'strength': min(1.0, lower_wick / body_size / 2),
                'signal': 'BUY',
                'confidence': 0.6,
                'rejection_level': current['Low']
            }

        return None

    def detect_pullback_to_ema(self, ema_column='EMA_FAST'):
        """Detect pullback to EMA for entry.

        Args:
            ema_column: EMA column name

        Returns:
            Dictionary with pullback info
        """
        if len(self.df) < 2 or ema_column not in self.df.columns:
            return None

        current = self.df.iloc[-1]
        previous = self.df.iloc[-2]

        ema = current[ema_column]

        # Pullback to EMA: Price touched EMA recently
        touches_ema = (
            (previous['Low'] <= ema <= previous['High']) or
            (current['Low'] <= ema <= current['High'])
        )

        if touches_ema:
            distance = abs(current['Close'] - ema)
            return {
                'pattern': 'PULLBACK_TO_EMA',
                'ema_level': ema,
                'distance_from_ema': distance,
                'signal': 'ENTRY_SETUP',
                'confidence': 0.75
            }

        return None

    def detect_all_patterns(self):
        """Detect all patterns.

        Returns:
            List of detected patterns
        """
        patterns = []

        # Engulfing
        engulfing = self.detect_engulfing()
        if engulfing:
            patterns.append(engulfing)

        # Pin bars
        pin_bar = self.detect_pin_bar()
        if pin_bar:
            patterns.append(pin_bar)

        # Inside bar
        inside = self.detect_inside_bar()
        if inside:
            patterns.append(inside)

        # Rejection
        rejection = self.detect_rejection_candles()
        if rejection:
            patterns.append(rejection)

        # Pullback
        pullback = self.detect_pullback_to_ema()
        if pullback:
            patterns.append(pullback)

        return patterns

    def get_pattern_signal(self, patterns=None):
        """Get trading signal from patterns.

        Args:
            patterns: List of patterns (default: detect all)

        Returns:
            Tuple (signal, confidence)
        """
        if patterns is None:
            patterns = self.detect_all_patterns()

        if not patterns:
            return None, 0.0

        buy_signals = []
        sell_signals = []

        for pattern in patterns:
            signal = pattern.get('signal')
            confidence = pattern.get('confidence', 0.5)

            if signal == 'BUY':
                buy_signals.append(confidence)
            elif signal == 'SELL':
                sell_signals.append(confidence)

        # Determine overall signal
        avg_buy = np.mean(buy_signals) if buy_signals else 0
        avg_sell = np.mean(sell_signals) if sell_signals else 0

        if avg_buy > avg_sell:
            return 'BUY', avg_buy
        elif avg_sell > avg_buy:
            return 'SELL', avg_sell
        else:
            return None, 0

    def is_valid_entry_setup(self, require_patterns=False):
        """Check if current setup is valid for entry.

        Args:
            require_patterns: Require specific patterns

        Returns:
            Tuple (is_valid, reason)
        """
        patterns = self.detect_all_patterns()

        if require_patterns and not patterns:
            return False, "No confirmation patterns detected"

        # Check for rejection patterns (invalid for entry)
        for pattern in patterns:
            if 'REJECTION' in pattern.get('pattern', ''):
                return False, f"Rejection pattern detected: {pattern['pattern']}"

        return True, "Valid setup"

    def get_pattern_summary(self):
        """Get summary of all detected patterns.

        Returns:
            Dictionary with pattern summary
        """
        patterns = self.detect_all_patterns()
        signal, confidence = self.get_pattern_signal(patterns)

        return {
            'patterns_detected': [p.get('pattern') for p in patterns],
            'pattern_count': len(patterns),
            'signal': signal,
            'signal_confidence': confidence,
            'is_valid_entry': self.is_valid_entry_setup()[0],
            'timestamp': pd.Timestamp.now(),
            'details': patterns
        }

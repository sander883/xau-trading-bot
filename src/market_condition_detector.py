import logging
import numpy as np
import pandas as pd
from src.technical_analysis import TechnicalAnalysis

logger = logging.getLogger(__name__)


class MarketConditionDetector:
    """Detects market conditions (trending vs ranging) and volatility."""

    def __init__(self, df, lookback=50):
        """Initialize condition detector.

        Args:
            df: DataFrame with OHLC data
            lookback: Lookback period for analysis
        """
        self.df = df.copy()
        self.lookback = lookback

    def detect_trend_strength(self):
        """Calculate trend strength using multiple methods.

        Returns:
            Dictionary with trend strength
        """
        try:
            if len(self.df) < self.lookback:
                return {'trend_strength': 0, 'reason': 'Insufficient data'}

            ta = TechnicalAnalysis(self.df.iloc[-self.lookback:])
            ta.calculate_moving_averages()
            ta.calculate_adx()

            if 'ADX' not in ta.df.columns:
                return {'trend_strength': 0}

            adx = ta.df['ADX'].iloc[-1]

            # ADX interpretation
            if adx > 40:
                trend = 'VERY_STRONG'
                strength = 1.0
            elif adx > 30:
                trend = 'STRONG'
                strength = 0.8
            elif adx > 20:
                trend = 'MODERATE'
                strength = 0.6
            else:
                trend = 'WEAK'
                strength = 0.3

            return {
                'adx': adx,
                'trend_strength': strength,
                'trend_type': trend,
                'confidence': min(adx / 50, 1.0)
            }

        except Exception as e:
            logger.error(f"Error detecting trend strength: {e}")
            return {'trend_strength': 0}

    def detect_range_condition(self):
        """Detect if market is ranging (low ADX).

        Returns:
            Dictionary with range analysis
        """
        try:
            if len(self.df) < self.lookback:
                return None

            ta = TechnicalAnalysis(self.df.iloc[-self.lookback:])
            ta.calculate_adx()

            if 'ADX' not in ta.df.columns:
                return {'is_ranging': False}

            adx = ta.df['ADX'].iloc[-1]

            # Ranging market: ADX < 20
            if adx < 20:
                return {
                    'is_ranging': True,
                    'adx': adx,
                    'condition': 'RANGE',
                    'recommendation': 'Use mean-reversion strategy'
                }

            return {
                'is_ranging': False,
                'adx': adx,
                'condition': 'TRENDING',
                'recommendation': 'Use trend-following strategy'
            }

        except Exception as e:
            logger.error(f"Error detecting range: {e}")
            return None

    def detect_volatility(self):
        """Detect current volatility level.

        Returns:
            Dictionary with volatility analysis
        """
        try:
            if len(self.df) < self.lookback:
                return None

            # Calculate ATR
            ta = TechnicalAnalysis(self.df.iloc[-self.lookback:])
            ta.calculate_atr()

            if 'ATR' not in ta.df.columns:
                return None

            current_atr = ta.df['ATR'].iloc[-1]
            avg_atr = ta.df['ATR'].mean()
            current_price = self.df['Close'].iloc[-1]

            # ATR as percentage of price
            atr_pct = (current_atr / current_price) * 100 if current_price > 0 else 0

            # Volatility level
            if current_atr > avg_atr * 1.5:
                vol_level = 'HIGH'
                vol_score = 1.0
            elif current_atr > avg_atr:
                vol_level = 'MEDIUM-HIGH'
                vol_score = 0.7
            elif current_atr > avg_atr * 0.7:
                vol_level = 'MEDIUM'
                vol_score = 0.5
            else:
                vol_level = 'LOW'
                vol_score = 0.3

            return {
                'current_atr': current_atr,
                'average_atr': avg_atr,
                'atr_ratio': current_atr / avg_atr if avg_atr > 0 else 1,
                'volatility_level': vol_level,
                'volatility_score': vol_score,
                'atr_percentage': atr_pct
            }

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None

    def detect_breakout_volatility(self):
        """Detect if volatility is expanding (potential breakout).

        Returns:
            Dictionary with expansion analysis
        """
        try:
            if len(self.df) < 30:
                return None

            ta = TechnicalAnalysis(self.df)
            ta.calculate_bollinger_bands()

            if 'BB_UPPER' not in ta.df.columns:
                return None

            # Calculate Bollinger Band width expansion
            recent_width = ta.df.iloc[-1]['BB_UPPER'] - ta.df.iloc[-1]['BB_LOWER']
            avg_width = (ta.df['BB_UPPER'] - ta.df['BB_LOWER']).iloc[-30:].mean()

            width_ratio = recent_width / avg_width if avg_width > 0 else 1

            if width_ratio > 1.3:
                return {
                    'is_expanding': True,
                    'expansion_level': 'HIGH',
                    'bb_width_ratio': width_ratio,
                    'recommendation': 'Prepare for breakout'
                }

            return {
                'is_expanding': width_ratio > 1.1,
                'bb_width_ratio': width_ratio,
                'recommendation': 'Monitor for continuation'
            }

        except Exception as e:
            logger.error(f"Error detecting volatility expansion: {e}")
            return None

    def detect_market_type(self):
        """Detect overall market type (trending, ranging, breakout).

        Returns:
            Dictionary with market type
        """
        try:
            trend_data = self.detect_trend_strength()
            range_data = self.detect_range_condition()
            volatility = self.detect_volatility()
            expansion = self.detect_breakout_volatility()

            # Determine market type
            if trend_data.get('trend_strength', 0) > 0.7:
                market_type = 'TRENDING'
            elif range_data and range_data.get('is_ranging'):
                market_type = 'RANGING'
            elif expansion and expansion.get('is_expanding'):
                market_type = 'BREAKOUT'
            else:
                market_type = 'NEUTRAL'

            return {
                'market_type': market_type,
                'trend_strength': trend_data.get('trend_strength', 0),
                'is_ranging': range_data.get('is_ranging') if range_data else None,
                'volatility_level': volatility.get('volatility_level') if volatility else None,
                'is_expanding': expansion.get('is_expanding') if expansion else None,
                'recommended_strategy': self._get_recommended_strategy(market_type),
                'timestamp': pd.Timestamp.now()
            }

        except Exception as e:
            logger.error(f"Error detecting market type: {e}")
            return {'market_type': 'UNKNOWN'}

    def _get_recommended_strategy(self, market_type):
        """Get recommended trading strategy for market type.

        Args:
            market_type: Type of market

        Returns:
            Strategy recommendation
        """
        strategies = {
            'TRENDING': {
                'name': 'Trend Following',
                'description': 'Use trend-following strategies, take breakouts',
                'entry': 'Pullback to moving average',
                'exit': 'Trailing stop or next support/resistance'
            },
            'RANGING': {
                'name': 'Mean Reversion',
                'description': 'Buy support, sell resistance',
                'entry': 'Rejection at levels',
                'exit': 'Mid-range or opposite level'
            },
            'BREAKOUT': {
                'name': 'Breakout Trading',
                'description': 'Trade the breakout',
                'entry': 'Break of highs/lows with confirmation',
                'exit': 'Take profits quickly'
            },
            'NEUTRAL': {
                'name': 'Caution',
                'description': 'No clear direction - wait for setup',
                'entry': 'Wait for clear signal',
                'exit': 'N/A'
            }
        }
        return strategies.get(market_type, strategies['NEUTRAL'])

    def get_market_condition_score(self):
        """Calculate overall market condition score (0-1).

        Returns:
            Score indicating trading favorability
        """
        score = 0.5  # Base score

        # Add trend strength
        trend = self.detect_trend_strength()
        score += trend.get('trend_strength', 0) * 0.3

        # Add volatility score (moderate volatility is best)
        volatility = self.detect_volatility()
        if volatility:
            # Best when not too low, not too high
            vol_score = volatility.get('volatility_score', 0.5)
            if vol_score > 0.7:  # Too volatile
                vol_bonus = 0.2 * (1 - (vol_score - 0.7) / 0.3)
            else:
                vol_bonus = vol_score * 0.2

            score += vol_bonus

        # Check expansion (breakout potential)
        expansion = self.detect_breakout_volatility()
        if expansion and expansion.get('is_expanding'):
            score += 0.1

        return max(0, min(1, score))

    def get_condition_report(self):
        """Get comprehensive market condition report.

        Returns:
            Dictionary with all condition analysis
        """
        return {
            'timestamp': pd.Timestamp.now(),
            'market_type': self.detect_market_type(),
            'trend_strength': self.detect_trend_strength(),
            'range_condition': self.detect_range_condition(),
            'volatility': self.detect_volatility(),
            'breakout_expansion': self.detect_breakout_volatility(),
            'overall_score': self.get_market_condition_score(),
            'trading_favorability': self._score_to_favorability(self.get_market_condition_score())
        }

    def _score_to_favorability(self, score):
        """Convert score to favorability text.

        Args:
            score: Score from 0-1

        Returns:
            Favorability text
        """
        if score > 0.75:
            return 'EXCELLENT - Ideal conditions'
        elif score > 0.6:
            return 'GOOD - Favorable conditions'
        elif score > 0.4:
            return 'FAIR - Proceed with caution'
        else:
            return 'POOR - Avoid trading or use smaller size'

    def should_trade_based_on_condition(self):
        """Determine if trading is recommended based on market condition.

        Returns:
            Tuple (should_trade, reason)
        """
        condition = self.detect_market_type()
        score = self.get_market_condition_score()

        if score < 0.3:
            return False, f"Poor market conditions (score: {score:.2f})"

        # Check if condition matches strategy
        market_type = condition.get('market_type')

        return True, f"Market type: {market_type}, Condition score: {score:.2f}"

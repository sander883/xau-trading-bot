import logging
import pandas as pd
from typing import Dict, List, Tuple
from src.technical_analysis import TechnicalAnalysis
from src.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """Analyzes price action across multiple timeframes."""

    def __init__(self, data_fetcher: DataFetcher, timeframes: List[str] = None):
        """Initialize multi-timeframe analyzer.

        Args:
            data_fetcher: DataFetcher instance
            timeframes: List of timeframes to analyze (e.g., ['M5', 'M15', 'H1'])
        """
        self.data_fetcher = data_fetcher
        self.timeframes = timeframes or ['M5', 'M15', 'H1']
        self.analyses = {}
        self.trends = {}
        self.signal_strengths = {}

    def analyze(self, symbol: str) -> bool:
        """Analyze multiple timeframes for a symbol.

        Args:
            symbol: Trading symbol (e.g., 'XAUUSD')

        Returns:
            True if analysis successful
        """
        try:
            for timeframe in self.timeframes:
                # Fetch data for timeframe
                df = self.data_fetcher.get_ohlc_data(symbol, timeframe, 500)

                if df is None or len(df) < 50:
                    logger.warning(f"Insufficient data for {timeframe}")
                    continue

                # Calculate indicators
                ta = TechnicalAnalysis(df)
                ta.calculate_moving_averages()
                ta.calculate_rsi()
                ta.calculate_bollinger_bands()
                ta.calculate_atr()
                ta.calculate_stochastic()
                ta.calculate_adx()
                ta.calculate_volume_indicators()

                # Store analysis
                self.analyses[timeframe] = ta

                # Get trend
                trend = ta.identify_trend()
                self.trends[timeframe] = trend

                # Get signal strength
                strength = ta.get_signal_strength()
                self.signal_strengths[timeframe] = strength

                logger.info(f"{timeframe}: Trend={trend}, Strength={strength}")

            return True

        except Exception as e:
            logger.error(f"Error in multi-timeframe analysis: {e}")
            return False

    def get_overall_trend(self) -> str:
        """Determine overall trend from multiple timeframes.

        Returns:
            'STRONG_UP', 'UP', 'NEUTRAL', 'DOWN', 'STRONG_DOWN'
        """
        if not self.trends:
            return 'NEUTRAL'

        # Weight trends by timeframe importance
        weights = {'M5': 1, 'M15': 2, 'H1': 3, '4H': 4, '1D': 5}
        uptrends = 0
        downtrends = 0
        total_weight = 0

        for tf, trend in self.trends.items():
            weight = weights.get(tf, 1)
            total_weight += weight

            if trend == 'UPTREND':
                uptrends += weight
            elif trend == 'DOWNTREND':
                downtrends += weight

        if uptrends == 0 and downtrends == 0:
            return 'NEUTRAL'

        uptrend_ratio = uptrends / total_weight
        downtrend_ratio = downtrends / total_weight

        if uptrend_ratio > 0.66:
            return 'STRONG_UP'
        elif uptrend_ratio > 0.33:
            return 'UP'
        elif downtrend_ratio > 0.66:
            return 'STRONG_DOWN'
        elif downtrend_ratio > 0.33:
            return 'DOWN'
        else:
            return 'NEUTRAL'

    def get_consensus_signal(self) -> Tuple[int, float]:
        """Get consensus signal from all timeframes.

        Returns:
            Tuple of (signal: 1 for UP / 0 for DOWN, confidence: 0-1)
        """
        if not self.signal_strengths:
            return 0, 0.0

        # Average signal strength across timeframes
        strengths = list(self.signal_strengths.values())
        avg_strength = sum(strengths) / len(strengths) if strengths else 0

        # Convert to signal and confidence
        if avg_strength > 10:
            signal = 1  # BUY
            confidence = min(abs(avg_strength) / 100, 1.0)
        elif avg_strength < -10:
            signal = 0  # SELL
            confidence = min(abs(avg_strength) / 100, 1.0)
        else:
            signal = 1 if avg_strength > 0 else 0
            confidence = 0.3  # Low confidence for neutral

        return signal, confidence

    def check_timeframe_alignment(self) -> bool:
        """Check if all timeframes are aligned (same direction).

        Returns:
            True if all timeframes show same trend
        """
        if not self.trends:
            return False

        trends = list(self.trends.values())
        if not trends:
            return False

        # All same trend
        return all(t == trends[0] for t in trends)

    def get_mtf_summary(self) -> Dict:
        """Get summary of multi-timeframe analysis.

        Returns:
            Dictionary with analysis summary
        """
        return {
            'timeframes_analyzed': list(self.timeframes),
            'trends': self.trends,
            'signal_strengths': self.signal_strengths,
            'overall_trend': self.get_overall_trend(),
            'consensus_signal': self.get_consensus_signal()[0],
            'consensus_confidence': self.get_consensus_signal()[1],
            'alignment': self.check_timeframe_alignment(),
            'timestamp': pd.Timestamp.now()
        }

    def get_detailed_report(self) -> Dict:
        """Get detailed report for each timeframe.

        Returns:
            Dictionary with detailed analysis
        """
        report = {}

        for timeframe, ta in self.analyses.items():
            latest = ta.get_latest_data()

            report[timeframe] = {
                'trend': self.trends.get(timeframe, 'UNKNOWN'),
                'signal_strength': self.signal_strengths.get(timeframe, 0),
                'close': latest.get('Close', 0),
                'rsi': latest.get('RSI', None),
                'macd': latest.get('MACD', None),
                'signal_line': latest.get('SIGNAL', None),
                'bb_upper': latest.get('BB_UPPER', None),
                'bb_middle': latest.get('BB_MIDDLE', None),
                'bb_lower': latest.get('BB_LOWER', None),
                'atr': latest.get('ATR', None),
                'adx': latest.get('ADX', None),
            }

        return report

    def identify_trading_opportunity(self) -> Tuple[bool, str, float]:
        """Identify if there's a trading opportunity based on MTF analysis.

        Returns:
            Tuple of (has_opportunity, trade_type, confidence)
        """
        overall_trend = self.get_overall_trend()
        aligned = self.check_timeframe_alignment()
        signal, confidence = self.get_consensus_signal()

        # Require alignment and strong trend for opportunity
        if aligned and overall_trend in ['STRONG_UP', 'STRONG_DOWN']:
            if overall_trend == 'STRONG_UP':
                return True, 'BUY', confidence
            else:
                return True, 'SELL', confidence

        # Medium opportunity with alignment
        if aligned and overall_trend in ['UP', 'DOWN']:
            if overall_trend == 'UP':
                return True, 'BUY', confidence * 0.8
            else:
                return True, 'SELL', confidence * 0.8

        return False, 'NONE', 0.0

    def get_support_resistance(self) -> Dict:
        """Get support and resistance levels from different timeframes.

        Returns:
            Dictionary with support and resistance levels
        """
        levels = {
            'support': [],
            'resistance': []
        }

        for timeframe, ta in self.analyses.items():
            if 'SUPPORT' in ta.df.columns and 'RESISTANCE' in ta.df.columns:
                support = ta.df['SUPPORT'].iloc[-1]
                resistance = ta.df['RESISTANCE'].iloc[-1]

                levels['support'].append({
                    'timeframe': timeframe,
                    'level': support
                })
                levels['resistance'].append({
                    'timeframe': timeframe,
                    'level': resistance
                })

        # Sort by timeframe importance
        tf_order = {'M5': 0, 'M15': 1, 'H1': 2, '4H': 3, '1D': 4}
        levels['support'].sort(key=lambda x: tf_order.get(x['timeframe'], 5))
        levels['resistance'].sort(key=lambda x: tf_order.get(x['timeframe'], 5))

        return levels

    def cleanup(self):
        """Cleanup resources."""
        self.analyses.clear()
        self.trends.clear()
        self.signal_strengths.clear()

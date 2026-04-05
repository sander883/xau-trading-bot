import logging
import pandas as pd
from typing import Tuple, Dict
from src.technical_analysis import TechnicalAnalysis
from src.ml_model import MLModel

logger = logging.getLogger(__name__)


class CombinedStrategy:
    """EMA + RSI + AI combined strategy for trading signals."""

    def __init__(self, config, ml_model: MLModel = None):
        """Initialize combined strategy.

        Args:
            config: Configuration object
            ml_model: Trained ML model instance
        """
        self.config = config
        self.ml_model = ml_model
        self.ema_fast_period = 12
        self.ema_slow_period = 26
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30

    def analyze_ema(self, ta: TechnicalAnalysis) -> Tuple[str, float]:
        """Analyze EMA signals.

        Args:
            ta: TechnicalAnalysis instance

        Returns:
            Tuple of (signal: 'BUY'/'SELL'/'NEUTRAL', strength: 0-1)
        """
        try:
            if 'EMA_FAST' not in ta.df.columns or 'EMA_SLOW' not in ta.df.columns:
                ta.calculate_moving_averages(fast=self.ema_fast_period,
                                            slow=self.ema_slow_period)

            latest_fast = ta.df['EMA_FAST'].iloc[-1]
            latest_slow = ta.df['EMA_SLOW'].iloc[-1]
            latest_close = ta.df['Close'].iloc[-1]

            # Golden cross / death cross
            prev_fast = ta.df['EMA_FAST'].iloc[-2]
            prev_slow = ta.df['EMA_SLOW'].iloc[-2]

            crossover = (prev_fast <= prev_slow) and (latest_fast > latest_slow)
            crossunder = (prev_fast >= prev_slow) and (latest_fast < latest_slow)

            if crossover:
                # Golden cross - strong buy signal
                strength = 0.9
                return 'BUY', strength

            if crossunder:
                # Death cross - strong sell signal
                strength = 0.9
                return 'SELL', strength

            # Price position relative to EMAs
            if latest_close > latest_fast > latest_slow:
                return 'BUY', 0.7
            elif latest_close < latest_fast < latest_slow:
                return 'SELL', 0.7
            else:
                return 'NEUTRAL', 0.3

        except Exception as e:
            logger.error(f"Error analyzing EMA: {e}")
            return 'NEUTRAL', 0.0

    def analyze_rsi(self, ta: TechnicalAnalysis) -> Tuple[str, float]:
        """Analyze RSI signals.

        Args:
            ta: TechnicalAnalysis instance

        Returns:
            Tuple of (signal: 'BUY'/'SELL'/'NEUTRAL', strength: 0-1)
        """
        try:
            if 'RSI' not in ta.df.columns:
                ta.calculate_rsi(period=self.rsi_period)

            rsi = ta.df['RSI'].iloc[-1]
            prev_rsi = ta.df['RSI'].iloc[-2]

            # RSI oversold - potential buy
            if rsi < self.rsi_oversold and prev_rsi >= self.rsi_oversold:
                return 'BUY', 0.8  # Oversold bounce

            if rsi < self.rsi_oversold:
                return 'BUY', 0.6  # Oversold condition

            # RSI overbought - potential sell
            if rsi > self.rsi_overbought and prev_rsi <= self.rsi_overbought:
                return 'SELL', 0.8  # Overbought reversal

            if rsi > self.rsi_overbought:
                return 'SELL', 0.6  # Overbought condition

            # Neutral zone (30-70)
            if 40 < rsi < 60:
                return 'NEUTRAL', 0.2

            # Mild bullish (60-70)
            if 60 <= rsi <= 70:
                return 'BUY', 0.4

            # Mild bearish (30-40)
            if 30 <= rsi < 40:
                return 'SELL', 0.4

            return 'NEUTRAL', 0.3

        except Exception as e:
            logger.error(f"Error analyzing RSI: {e}")
            return 'NEUTRAL', 0.0

    def analyze_ai(self, features) -> Tuple[int, float]:
        """Analyze AI model predictions.

        Args:
            features: Feature array for ML model

        Returns:
            Tuple of (signal: 1 for UP / 0 for DOWN, confidence: 0-1)
        """
        if self.ml_model is None:
            return 0, 0.0

        try:
            prediction, confidence = self.ml_model.predict_single(features)

            if prediction is None:
                return 0, 0.0

            return int(prediction), float(confidence)

        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return 0, 0.0

    def combine_signals(self,
                       ema_signal: str, ema_strength: float,
                       rsi_signal: str, rsi_strength: float,
                       ai_signal: int, ai_confidence: float) -> Tuple[str, float]:
        """Combine signals from EMA, RSI, and AI.

        Args:
            ema_signal: EMA signal ('BUY', 'SELL', 'NEUTRAL')
            ema_strength: EMA strength (0-1)
            rsi_signal: RSI signal ('BUY', 'SELL', 'NEUTRAL')
            rsi_strength: RSI strength (0-1)
            ai_signal: AI signal (1 for UP, 0 for DOWN)
            ai_confidence: AI confidence (0-1)

        Returns:
            Tuple of (combined_signal: 'BUY'/'SELL'/'NEUTRAL', combined_strength: 0-1)
        """
        # Convert AI signal to text
        ai_text = 'BUY' if ai_signal == 1 else 'SELL'

        # Count votes
        buy_votes = 0
        sell_votes = 0
        total_strength = 0

        if ema_signal == 'BUY':
            buy_votes += 1
            total_strength += ema_strength
        elif ema_signal == 'SELL':
            sell_votes += 1
            total_strength += ema_strength

        if rsi_signal == 'BUY':
            buy_votes += 1
            total_strength += rsi_strength
        elif rsi_signal == 'SELL':
            sell_votes += 1
            total_strength += rsi_strength

        if ai_text == 'BUY':
            buy_votes += 1
            total_strength += ai_confidence
        else:
            sell_votes += 1
            total_strength += ai_confidence

        # Determine combined signal
        if buy_votes > sell_votes:
            combined_signal = 'BUY'
        elif sell_votes > buy_votes:
            combined_signal = 'SELL'
        else:
            combined_signal = 'NEUTRAL'

        # Calculate combined strength (average of contributing factors)
        combined_strength = total_strength / 3 if combined_signal != 'NEUTRAL' else 0.3

        return combined_signal, combined_strength

    def get_signal(self, ta: TechnicalAnalysis, features=None) -> Dict:
        """Get combined trading signal.

        Args:
            ta: TechnicalAnalysis instance
            features: Feature array for ML model (optional)

        Returns:
            Dictionary with signal details
        """
        try:
            # Get individual signals
            ema_signal, ema_strength = self.analyze_ema(ta)
            rsi_signal, rsi_strength = self.analyze_rsi(ta)
            ai_signal, ai_confidence = self.analyze_ai(features) if features is not None else (0, 0.0)

            # Combine signals
            combined_signal, combined_strength = self.combine_signals(
                ema_signal, ema_strength,
                rsi_signal, rsi_strength,
                ai_signal, ai_confidence
            )

            result = {
                'combined_signal': combined_signal,
                'combined_strength': combined_strength,
                'ema_signal': ema_signal,
                'ema_strength': ema_strength,
                'rsi_signal': rsi_signal,
                'rsi_strength': rsi_strength,
                'ai_signal': 'BUY' if ai_signal == 1 else 'SELL',
                'ai_confidence': ai_confidence,
                'timestamp': pd.Timestamp.now()
            }

            return result

        except Exception as e:
            logger.error(f"Error getting combined signal: {e}")
            return {
                'combined_signal': 'NEUTRAL',
                'combined_strength': 0.0,
                'error': str(e)
            }

    def should_trade(self, signal_dict: Dict, confidence_threshold: float = 0.6) -> bool:
        """Determine if trade should be executed based on signals.

        Args:
            signal_dict: Signal dictionary from get_signal()
            confidence_threshold: Minimum confidence level

        Returns:
            True if trade should be opened
        """
        if signal_dict.get('combined_signal') == 'NEUTRAL':
            return False

        strength = signal_dict.get('combined_strength', 0)
        return strength >= confidence_threshold

    def get_signal_explanation(self, signal_dict: Dict) -> str:
        """Get human-readable explanation of the signal.

        Args:
            signal_dict: Signal dictionary from get_signal()

        Returns:
            Explanation string
        """
        signal = signal_dict.get('combined_signal', 'NEUTRAL')
        strength = signal_dict.get('combined_strength', 0)

        ema = signal_dict.get('ema_signal', 'NEUTRAL')
        rsi = signal_dict.get('rsi_signal', 'NEUTRAL')
        ai = signal_dict.get('ai_signal', 'NEUTRAL')

        explanation = f"""
Signal Analysis:
- Combined Signal: {signal} (Strength: {strength:.2f})
- EMA: {ema} ({signal_dict.get('ema_strength', 0):.2f})
- RSI: {rsi} ({signal_dict.get('rsi_strength', 0):.2f})
- AI: {ai} ({signal_dict.get('ai_confidence', 0):.2f})
        """.strip()

        return explanation

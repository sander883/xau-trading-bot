"""
Professional XAUUSD trading system with AI and risk management.

Integrates:
- Professional XGBoost model with 30+ features
- Trend confirmation with EMA crossovers
- Pattern confirmation (engulfing/rejection candles)
- Dynamic ATR-based stop loss
- 1% risk per trade with 1:2 minimum RR
- Market condition detection and adjustment
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TradeType(Enum):
    """Trade types."""
    BUY = 1
    SELL = -1
    NONE = 0


class ProfessionalTradingSystem:
    """Professional trading system with AI and risk management."""

    def __init__(self, config, data_fetcher, xgboost_model, risk_manager):
        """Initialize professional trading system.

        Args:
            config: Configuration object
            data_fetcher: Data fetcher for OHLC data
            xgboost_model: ProfessionalXGBoostModel instance
            risk_manager: Risk manager for position sizing
        """
        self.config = config
        self.data_fetcher = data_fetcher
        self.model = xgboost_model
        self.risk_manager = risk_manager

        # Trading parameters
        self.min_confidence = config.PREDICTION_CONFIDENCE_THRESHOLD  # e.g., 0.65
        self.risk_percentage = config.RISK_PERCENT_PER_TRADE  # e.g., 1.0
        self.min_rr_ratio = config.MIN_RISK_REWARD_RATIO  # e.g., 1:2
        self.max_daily_loss = config.MAX_DAILY_LOSS

        logger.info("✓ Professional Trading System initialized")

    def confirm_trend(self, df, lookback=5):
        """Confirm trend using EMA crossovers.

        Args:
            df: DataFrame with EMA values
            lookback: Number of candles to check

        Returns:
            Tuple (is_uptrend: bool, is_confirmed: bool)
        """
        try:
            if len(df) < lookback:
                return False, False

            recent = df.iloc[-lookback:].copy()

            # Check EMA 50 > EMA 200
            ema50_above_ema200 = (recent['EMA_FAST'] > recent['EMA_SLOW']).all()

            # Check price is above both EMAs
            price_above_ema = (
                (recent['Close'] > recent['EMA_FAST']).all() and
                (recent['Close'] > recent['EMA_SLOW']).all()
            )

            # Trend is confirmed if both conditions met
            is_confirmed = ema50_above_ema200 and price_above_ema

            return ema50_above_ema200, is_confirmed

        except Exception as e:
            logger.error(f"Error confirming trend: {e}")
            return False, False

    def confirm_pattern(self, df, lookback=1):
        """Confirm entry pattern (engulfing or rejection candle).

        Args:
            df: DataFrame with OHLC data
            lookback: How many candles back to check

        Returns:
            Tuple (has_pattern: bool, pattern_type: str)
        """
        try:
            if len(df) < lookback + 1:
                return False, 'NONE'

            current = df.iloc[-lookback]
            previous = df.iloc[-lookback-1]

            current_body = abs(current['Close'] - current['Open'])
            current_range = current['High'] - current['Low']
            previous_body = abs(previous['Close'] - previous['Open'])

            # Engulfing pattern: current candle body > previous candle body
            is_engulfing = current_body > previous_body * 1.2

            # Rejection candle: long wick on opposite side
            upper_wick = current['High'] - max(current['Close'], current['Open'])
            lower_wick = min(current['Close'], current['Open']) - current['Low']

            is_bullish_rejection = (
                lower_wick < upper_wick * 0.5 and
                upper_wick > current_range * 0.5
            )

            if is_engulfing:
                return True, 'ENGULFING'
            elif is_bullish_rejection:
                return True, 'REJECTION'

            return False, 'NONE'

        except Exception as e:
            logger.error(f"Error confirming pattern: {e}")
            return False, 'NONE'

    def calculate_dynamic_stops(self, entry_price, direction, df):
        """Calculate dynamic stop loss and take profit using ATR.

        Args:
            entry_price: Entry price
            direction: TradeType.BUY or TradeType.SELL
            df: DataFrame with ATR values

        Returns:
            Dictionary with SL and TP levels
        """
        try:
            if 'ATR' not in df.columns or len(df) == 0:
                # Fallback to fixed pips
                return {
                    'stop_loss': entry_price - 50 if direction == TradeType.BUY else entry_price + 50,
                    'take_profit': entry_price + 100 if direction == TradeType.BUY else entry_price - 100,
                    'stop_pips': 50,
                    'tp_pips': 100,
                    'rr_ratio': 2.0
                }

            atr = df['ATR'].iloc[-1]

            # ATR-based stops
            sl_distance = atr * 1.5  # 1.5x ATR
            tp_distance = atr * 3.0  # 3x ATR for 1:2 RR

            if direction == TradeType.BUY:
                sl = entry_price - sl_distance
                tp = entry_price + tp_distance
            else:  # SELL
                sl = entry_price + sl_distance
                tp = entry_price - tp_distance

            # Calculate pips (1 pip = 0.01 for XAUUSD)
            sl_pips = abs(entry_price - sl) / 0.01
            tp_pips = abs(entry_price - tp) / 0.01
            rr_ratio = tp_pips / sl_pips if sl_pips > 0 else 0

            return {
                'stop_loss': sl,
                'take_profit': tp,
                'stop_pips': sl_pips,
                'tp_pips': tp_pips,
                'rr_ratio': rr_ratio,
                'atr': atr,
                'method': 'ATR-based'
            }

        except Exception as e:
            logger.error(f"Error calculating stops: {e}")
            return None

    def calculate_position_size(self, entry_price, stop_loss, risk_pct=None):
        """Calculate position size based on 1% risk rule.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss level
            risk_pct: Risk percentage (default: 1%)

        Returns:
            Position size in lots
        """
        try:
            if risk_pct is None:
                risk_pct = self.risk_percentage

            # Account risk
            account_size = self.config.INITIAL_BALANCE
            risk_amount = account_size * (risk_pct / 100.0)

            # Price risk per unit
            price_risk = abs(entry_price - stop_loss)

            if price_risk <= 0:
                return self.config.LOT_SIZE

            # Position size
            position_size = risk_amount / price_risk

            # Apply max position limits
            max_position = account_size * 0.1  # Max 10% of account
            position_size = min(position_size, max_position)
            position_size = max(position_size, self.config.LOT_SIZE)

            return round(position_size, 2)

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.config.LOT_SIZE

    def analyze_entry(self, df):
        """Comprehensive entry analysis combining all signals.

        Args:
            df: DataFrame with OHLC and indicators

        Returns:
            Dictionary with trade analysis
        """
        try:
            if len(df) < 30:
                logger.warning("Insufficient data for analysis")
                return None

            # 1. Prepare features for model
            from src.professional_xgboost_model import ProfessionalXGBoostModel

            features_df = self.model.engineer_features(df)
            exclude_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'HOUR', 'DAY_OF_WEEK']
            feature_cols = [col for col in features_df.columns if col not in exclude_cols]

            recent_features = features_df[feature_cols].iloc[-1:].values

            # 2. Get AI prediction
            ai_signal = self.model.predict_signal(recent_features, self.min_confidence)

            logger.info(f"AI Signal: {ai_signal['signal_name']} (confidence: {ai_signal['confidence']:.2%})")

            # 3. Check trend confirmation
            is_uptrend, trend_confirmed = self.confirm_trend(df)
            logger.info(f"Trend: {'UPTREND' if is_uptrend else 'DOWNTREND'} (confirmed: {trend_confirmed})")

            # 4. Check pattern confirmation
            has_pattern, pattern_type = self.confirm_pattern(df)
            logger.info(f"Pattern: {pattern_type}")

            # 5. Detect market condition
            market_condition = self.model.detect_market_condition(df)
            logger.info(f"Market Condition: {market_condition.name}")

            # 6. Entry decision logic
            current_price = df['Close'].iloc[-1]
            entry_signal = TradeType.NONE

            # BUY conditions
            if (ai_signal['signal'].value >= 2 and  # BUY or STRONG_BUY
                ai_signal['meets_threshold'] and
                trend_confirmed and
                has_pattern):
                entry_signal = TradeType.BUY

            # SELL conditions
            elif (ai_signal['signal'].value <= 0 and  # SELL or STRONG_SELL
                  ai_signal['meets_threshold'] and
                  not trend_confirmed and
                  has_pattern):
                entry_signal = TradeType.SELL

            # 7. Calculate stops and position size
            stops = self.calculate_dynamic_stops(current_price, entry_signal, df)

            if stops and stops['rr_ratio'] < self.min_rr_ratio:
                logger.warning(f"RR ratio {stops['rr_ratio']:.2f} < {self.min_rr_ratio}, skipping trade")
                entry_signal = TradeType.NONE

            position_size = self.calculate_position_size(
                current_price,
                stops['stop_loss'] if stops else current_price
            ) if entry_signal != TradeType.NONE else 0

            # 8. Compile analysis
            analysis = {
                'entry_signal': entry_signal,
                'entry_price': current_price,
                'position_size': position_size,
                'ai_signal': ai_signal,
                'trend_confirmed': trend_confirmed,
                'pattern': pattern_type if has_pattern else 'NONE',
                'market_condition': market_condition.name,
                'stops': stops,
                'timestamp': datetime.now().isoformat(),
                'confidence_score': self._calculate_confidence_score(
                    ai_signal, trend_confirmed, has_pattern, market_condition
                )
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing entry: {e}", exc_info=True)
            return None

    def _calculate_confidence_score(self, ai_signal, trend_confirmed, has_pattern, market_condition):
        """Calculate overall trade confidence score (0-100).

        Args:
            ai_signal: AI signal dict
            trend_confirmed: Is trend confirmed
            has_pattern: Does pattern exist
            market_condition: Market condition enum

        Returns:
            Confidence score 0-100
        """
        score = 0.0

        # AI confidence (0-40 points)
        score += ai_signal['confidence'] * 40

        # Trend confirmation (0-30 points)
        if trend_confirmed:
            score += 30

        # Pattern confirmation (0-20 points)
        if has_pattern:
            score += 20

        # Market condition (0-10 points)
        market_value = market_condition.value if hasattr(market_condition, 'value') else 0
        score += (market_value / 3.0) * 10

        return round(score, 2)

    def get_system_status(self):
        """Get comprehensive system status.

        Returns:
            Dictionary with system information
        """
        return {
            'system_type': 'Professional XGBoost Trading System',
            'model_status': 'TRAINED' if self.model.is_trained else 'NOT TRAINED',
            'min_confidence': self.min_confidence,
            'risk_per_trade': self.risk_percentage,
            'min_rr_ratio': self.min_rr_ratio,
            'max_daily_loss': self.max_daily_loss,
            'trading_symbol': self.config.SYMBOL,
            'timeframe': self.config.TIMEFRAME,
            'timestamp': datetime.now().isoformat()
        }

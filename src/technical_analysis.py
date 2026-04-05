import logging
import numpy as np
import pandas as pd
import talib

logger = logging.getLogger(__name__)


class TechnicalAnalysis:
    """Provides technical indicators and analysis."""

    def __init__(self, df):
        """Initialize with OHLC dataframe.

        Args:
            df: DataFrame with OHLC data
        """
        self.df = df.copy()
        self.indicators = {}

    def calculate_moving_averages(self, fast=20, slow=50, signal=9):
        """Calculate moving averages and MACD.

        Args:
            fast: Fast MA period
            slow: Slow MA period
            signal: Signal line period
        """
        self.df['SMA_FAST'] = talib.SMA(self.df['Close'], timeperiod=fast)
        self.df['SMA_SLOW'] = talib.SMA(self.df['Close'], timeperiod=slow)
        self.df['EMA_FAST'] = talib.EMA(self.df['Close'], timeperiod=fast)
        self.df['EMA_SLOW'] = talib.EMA(self.df['Close'], timeperiod=slow)

        self.df['MACD'], self.df['SIGNAL'], self.df['HISTOGRAM'] = talib.MACD(
            self.df['Close'], fastperiod=12, slowperiod=26, signalperiod=signal
        )

        self.indicators['MA'] = True
        return self

    def calculate_rsi(self, period=14):
        """Calculate RSI (Relative Strength Index).

        Args:
            period: RSI period
        """
        self.df['RSI'] = talib.RSI(self.df['Close'], timeperiod=period)
        self.indicators['RSI'] = True
        return self

    def calculate_bollinger_bands(self, period=20, std_dev=2):
        """Calculate Bollinger Bands.

        Args:
            period: MA period
            std_dev: Standard deviation multiplier
        """
        self.df['BB_UPPER'], self.df['BB_MIDDLE'], self.df['BB_LOWER'] = talib.BBANDS(
            self.df['Close'], timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev
        )
        self.indicators['BB'] = True
        return self

    def calculate_atr(self, period=14):
        """Calculate Average True Range.

        Args:
            period: ATR period
        """
        self.df['ATR'] = talib.ATR(self.df['High'], self.df['Low'], self.df['Close'], timeperiod=period)
        self.indicators['ATR'] = True
        return self

    def calculate_stochastic(self, k_period=14, d_period=3):
        """Calculate Stochastic Oscillator.

        Args:
            k_period: K period
            d_period: D period (signal line)
        """
        self.df['STOCH_K'], self.df['STOCH_D'] = talib.STOCH(
            self.df['High'], self.df['Low'], self.df['Close'],
            fastk_period=k_period, slowk_period=d_period, slowd_period=d_period
        )
        self.indicators['STOCH'] = True
        return self

    def calculate_adx(self, period=14):
        """Calculate ADX (Average Directional Index).

        Args:
            period: ADX period
        """
        self.df['ADX'] = talib.ADX(self.df['High'], self.df['Low'], self.df['Close'], timeperiod=period)
        self.df['PLUS_DI'] = talib.PLUS_DI(self.df['High'], self.df['Low'], self.df['Close'], timeperiod=period)
        self.df['MINUS_DI'] = talib.MINUS_DI(self.df['High'], self.df['Low'], self.df['Close'], timeperiod=period)
        self.indicators['ADX'] = True
        return self

    def calculate_volume_indicators(self):
        """Calculate volume-based indicators."""
        self.df['SMA_VOLUME'] = self.df['Volume'].rolling(window=20).mean()
        self.df['VOLUME_RATIO'] = self.df['Volume'] / self.df['SMA_VOLUME']

        # On-Balance Volume
        self.df['OBV'] = np.where(self.df['Close'] > self.df['Close'].shift(1), self.df['Volume'],
                                   np.where(self.df['Close'] < self.df['Close'].shift(1), -self.df['Volume'], 0))
        self.df['OBV'] = self.df['OBV'].cumsum()

        # Money Flow Index
        high_low = self.df['High'] - self.df['Low']
        high_close = abs(self.df['High'] - self.df['Close'].shift(1))
        low_close = abs(self.df['Low'] - self.df['Close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        self.df['MFI'] = talib.MFI(self.df['High'], self.df['Low'], self.df['Close'], self.df['Volume'], timeperiod=14)

        self.indicators['VOLUME'] = True
        return self

    def calculate_price_patterns(self):
        """Identify price patterns and support/resistance levels."""
        # Calculate support and resistance
        self.df['SUPPORT'] = self.df['Low'].rolling(window=20).min()
        self.df['RESISTANCE'] = self.df['High'].rolling(window=20).max()

        # Pivot points
        typical_price = (self.df['High'] + self.df['Low'] + self.df['Close']) / 3
        self.df['PIVOT'] = typical_price.rolling(window=14).mean()

        # Rate of Change
        self.df['ROC'] = talib.ROC(self.df['Close'], timeperiod=12)

        self.indicators['PATTERNS'] = True
        return self

    def identify_trend(self):
        """Identify current trend direction.

        Returns:
            'UPTREND', 'DOWNTREND', or 'SIDEWAYS'
        """
        if 'SMA_FAST' not in self.df.columns or 'SMA_SLOW' not in self.df.columns:
            self.calculate_moving_averages()

        latest_fast = self.df['SMA_FAST'].iloc[-1]
        latest_slow = self.df['SMA_SLOW'].iloc[-1]
        latest_close = self.df['Close'].iloc[-1]

        if latest_close > latest_fast > latest_slow:
            return 'UPTREND'
        elif latest_close < latest_fast < latest_slow:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'

    def get_signal_strength(self):
        """Calculate overall signal strength based on multiple indicators.

        Returns:
            Score from -100 to 100
        """
        score = 0
        count = 0

        try:
            if 'RSI' in self.df.columns:
                rsi = self.df['RSI'].iloc[-1]
                if rsi < 30:
                    score += 50  # Oversold
                elif rsi > 70:
                    score -= 50  # Overbought
                count += 1

            if 'MACD' in self.df.columns and 'SIGNAL' in self.df.columns:
                if self.df['MACD'].iloc[-1] > self.df['SIGNAL'].iloc[-1]:
                    score += 25
                else:
                    score -= 25
                count += 1

            if 'SMA_FAST' in self.df.columns and 'SMA_SLOW' in self.df.columns:
                if self.df['SMA_FAST'].iloc[-1] > self.df['SMA_SLOW'].iloc[-1]:
                    score += 25
                else:
                    score -= 25
                count += 1

            if 'ADX' in self.df.columns:
                adx = self.df['ADX'].iloc[-1]
                if adx > 40:
                    score += 15  # Strong trend
                elif adx < 20:
                    score -= 15  # Weak trend
                count += 1

            return int(score / max(count, 1)) if count > 0 else 0

        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return 0

    def get_features_for_ml(self):
        """Extract features for machine learning models.

        Returns:
            DataFrame with selected features
        """
        features = self.df[['Close', 'Volume']].copy()

        # Ensure all required indicators are calculated
        if not self.indicators:
            self.calculate_moving_averages()
            self.calculate_rsi()
            self.calculate_bollinger_bands()
            self.calculate_atr()
            self.calculate_stochastic()
            self.calculate_volume_indicators()

        # Select features
        feature_cols = [col for col in self.df.columns if col not in ['Open', 'High', 'Low', 'Volume']]
        return self.df[feature_cols].dropna()

    def get_latest_data(self):
        """Get latest candle data with all calculated indicators."""
        return self.df.iloc[-1]

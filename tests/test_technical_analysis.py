import pytest
import pandas as pd
import numpy as np
from src.technical_analysis import TechnicalAnalysis


class TestTechnicalAnalysis:
    """Test suite for TechnicalAnalysis."""

    @pytest.fixture
    def sample_ohlc_data(self):
        """Create sample OHLC data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='H')
        np.random.seed(42)

        data = {
            'time': dates,
            'Open': np.random.uniform(2000, 2100, 100),
            'High': np.random.uniform(2050, 2150, 100),
            'Low': np.random.uniform(1950, 2050, 100),
            'Close': np.random.uniform(2000, 2100, 100),
            'Volume': np.random.randint(1000, 10000, 100),
        }

        df = pd.DataFrame(data)
        df.set_index('time', inplace=True)
        return df

    @pytest.fixture
    def ta(self, sample_ohlc_data):
        """Create TechnicalAnalysis instance."""
        return TechnicalAnalysis(sample_ohlc_data)

    def test_calculate_moving_averages(self, ta):
        """Test moving average calculation."""
        ta.calculate_moving_averages()

        assert 'SMA_FAST' in ta.df.columns
        assert 'SMA_SLOW' in ta.df.columns
        assert 'EMA_FAST' in ta.df.columns
        assert 'EMA_SLOW' in ta.df.columns
        assert 'MACD' in ta.df.columns
        assert ta.indicators['MA'] is True

    def test_calculate_rsi(self, ta):
        """Test RSI calculation."""
        ta.calculate_rsi()

        assert 'RSI' in ta.df.columns
        assert ta.indicators['RSI'] is True

        # RSI values should be between 0 and 100
        rsi_values = ta.df['RSI'].dropna()
        assert (rsi_values >= 0).all() and (rsi_values <= 100).all()

    def test_calculate_bollinger_bands(self, ta):
        """Test Bollinger Bands calculation."""
        ta.calculate_bollinger_bands()

        assert 'BB_UPPER' in ta.df.columns
        assert 'BB_MIDDLE' in ta.df.columns
        assert 'BB_LOWER' in ta.df.columns
        assert ta.indicators['BB'] is True

        # Upper band should be above middle, middle above lower
        bb_upper = ta.df['BB_UPPER'].dropna()
        bb_middle = ta.df['BB_MIDDLE'].dropna()
        bb_lower = ta.df['BB_LOWER'].dropna()

        assert (bb_upper >= bb_middle.iloc[:len(bb_upper)]).all()
        assert (bb_middle.iloc[:len(bb_lower)] >= bb_lower).all()

    def test_calculate_atr(self, ta):
        """Test ATR calculation."""
        ta.calculate_atr()

        assert 'ATR' in ta.df.columns
        assert ta.indicators['ATR'] is True

        # ATR should be positive
        atr_values = ta.df['ATR'].dropna()
        assert (atr_values >= 0).all()

    def test_calculate_stochastic(self, ta):
        """Test Stochastic calculation."""
        ta.calculate_stochastic()

        assert 'STOCH_K' in ta.df.columns
        assert 'STOCH_D' in ta.df.columns
        assert ta.indicators['STOCH'] is True

        # Stochastic values should be between 0 and 100
        stoch_k = ta.df['STOCH_K'].dropna()
        stoch_d = ta.df['STOCH_D'].dropna()

        assert (stoch_k >= 0).all() and (stoch_k <= 100).all()
        assert (stoch_d >= 0).all() and (stoch_d <= 100).all()

    def test_identify_trend_uptrend(self, ta):
        """Test trend identification - uptrend."""
        ta.calculate_moving_averages()

        # Create uptrend: fast MA > slow MA > close
        ta.df['SMA_FAST'] = ta.df['Close'] + 1
        ta.df['SMA_SLOW'] = ta.df['Close'] - 1

        trend = ta.identify_trend()
        assert trend == 'UPTREND'

    def test_identify_trend_downtrend(self, ta):
        """Test trend identification - downtrend."""
        ta.calculate_moving_averages()

        # Create downtrend: close < fast MA < slow MA
        ta.df['SMA_FAST'] = ta.df['Close'] - 1
        ta.df['SMA_SLOW'] = ta.df['Close'] + 1

        trend = ta.identify_trend()
        assert trend == 'DOWNTREND'

    def test_get_signal_strength(self, ta):
        """Test signal strength calculation."""
        ta.calculate_rsi()
        ta.calculate_moving_averages()

        strength = ta.get_signal_strength()

        # Should be a number between -100 and 100
        assert isinstance(strength, int)
        assert -100 <= strength <= 100

    def test_chaining_indicators(self, ta):
        """Test method chaining for indicator calculation."""
        result = (ta.calculate_moving_averages()
                    .calculate_rsi()
                    .calculate_bollinger_bands()
                    .calculate_atr())

        assert result is ta
        assert ta.indicators['MA'] is True
        assert ta.indicators['RSI'] is True
        assert ta.indicators['BB'] is True
        assert ta.indicators['ATR'] is True

    def test_get_latest_data(self, ta):
        """Test getting latest data point."""
        ta.calculate_moving_averages()

        latest = ta.get_latest_data()

        assert latest['Close'] > 0
        assert latest['Volume'] > 0

    def test_get_features_for_ml(self, ta):
        """Test extracting features for ML."""
        ta.calculate_moving_averages()
        ta.calculate_rsi()
        ta.calculate_bollinger_bands()

        features = ta.get_features_for_ml()

        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0
        assert 'RSI' in features.columns

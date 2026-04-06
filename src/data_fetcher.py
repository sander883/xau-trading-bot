import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False
    mt5 = None

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches and manages historical and real-time data from MetaTrader5."""

    def __init__(self, config):
        """Initialize data fetcher with MetaTrader5 connection.

        Args:
            config: Configuration object with MT5 credentials
        """
        self.config = config
        self.connected = False
        self.connect_to_mt5()

    def connect_to_mt5(self):
        """Establish connection to MetaTrader5."""
        try:
            if not HAS_MT5:
                logger.warning("MetaTrader5 not available - using demo mode")
                return False

            if not mt5.initialize(
                login=self.config.MT5_LOGIN,
                password=self.config.MT5_PASSWORD,
                server=self.config.MT5_SERVER
            ):
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False

            logger.info("Connected to MetaTrader5 successfully")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Error connecting to MT5: {e}")
            return False

    def disconnect_from_mt5(self):
        """Disconnect from MetaTrader5."""
        try:
            if HAS_MT5 and mt5:
                mt5.shutdown()
                logger.info("Disconnected from MetaTrader5")
            self.connected = False
        except Exception as e:
            logger.error(f"Error disconnecting from MT5: {e}")

    def get_ohlc_data(self, symbol, timeframe, count=500):
        """Fetch OHLC data from MetaTrader5.

        Args:
            symbol: Trading symbol (e.g., 'XAUUSD')
            timeframe: Timeframe string (e.g., '1H', '4H', '1D')
            count: Number of candles to fetch

        Returns:
            DataFrame with OHLC data or None if failed
        """
        if not self.connected:
            logger.error("Not connected to MT5")
            return None

        try:
            tf_map = {
                '1M': mt5.TIMEFRAME_M1,
                '5M': mt5.TIMEFRAME_M5,
                '15M': mt5.TIMEFRAME_M15,
                '30M': mt5.TIMEFRAME_M30,
                '1H': mt5.TIMEFRAME_H1,
                '4H': mt5.TIMEFRAME_H4,
                '1D': mt5.TIMEFRAME_D1
            }

            tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)

            if rates is None or len(rates) == 0:
                logger.error(f"Failed to fetch {symbol} data: {mt5.last_error()}")
                return None

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'})
            df = df[['time', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df.set_index('time', inplace=True)

            logger.info(f"Fetched {len(df)} candles for {symbol} ({timeframe})")
            return df

        except Exception as e:
            logger.error(f"Error fetching OHLC data: {e}")
            return None

    def get_historical_data(self, symbol, timeframe, start_date, end_date):
        """Fetch historical data for a date range.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            start_date: Start date (datetime or string 'YYYY-MM-DD')
            end_date: End date (datetime or string 'YYYY-MM-DD')

        Returns:
            DataFrame with historical data
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # If MT5 not available, return demo data
        if not self.connected or mt5 is None:
            logger.warning(f"MT5 not available - generating demo data for {symbol}")
            return self._generate_demo_data(symbol, start_date, end_date, timeframe)

        try:
            tf_map = {
                '1M': mt5.TIMEFRAME_M1,
                '5M': mt5.TIMEFRAME_M5,
                '15M': mt5.TIMEFRAME_M15,
                '30M': mt5.TIMEFRAME_M30,
                '1H': mt5.TIMEFRAME_H1,
                '4H': mt5.TIMEFRAME_H4,
                '1D': mt5.TIMEFRAME_D1
            }

            tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_range(symbol, tf, start_date, end_date)

            if rates is None or len(rates) == 0:
                logger.error(f"Failed to fetch historical data: {mt5.last_error()}")
                return None

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'})
            df = df[['time', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df.set_index('time', inplace=True)

            logger.info(f"Fetched {len(df)} historical candles for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

    def _generate_demo_data(self, symbol, start_date, end_date, timeframe='1H'):
        """Generate synthetic demo data for backtesting without MT5.

        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            timeframe: Timeframe string

        Returns:
            DataFrame with synthetic OHLC data
        """
        try:
            import numpy as np

            # Timeframe to frequency mapping
            freq_map = {
                '1M': 'T',
                '5M': '5T',
                '15M': '15T',
                '30M': '30T',
                '1H': 'H',
                '4H': '4H',
                '1D': 'D'
            }
            freq = freq_map.get(timeframe, 'H')

            # Generate date range
            dates = pd.date_range(start=start_date, end=end_date, freq=freq)

            # Generate synthetic price data for XAUUSD
            base_price = 2350.0 if symbol == 'XAUUSD' else 1.0

            # Create trend with some noise
            trend = np.linspace(0, 100, len(dates))
            noise = np.random.normal(0, 10, len(dates))
            close_prices = base_price + trend + noise

            # Generate OHLC from close prices
            opens = close_prices + np.random.normal(0, 2, len(dates))
            highs = np.maximum(opens, close_prices) + np.abs(np.random.normal(0, 3, len(dates)))
            lows = np.minimum(opens, close_prices) - np.abs(np.random.normal(0, 3, len(dates)))
            volumes = np.random.uniform(1000, 10000, len(dates))

            df = pd.DataFrame({
                'Open': opens,
                'High': highs,
                'Low': lows,
                'Close': close_prices,
                'Volume': volumes
            }, index=dates)

            df.index.name = 'time'

            logger.info(f"Generated {len(df)} demo candles for {symbol} ({timeframe})")
            return df

        except Exception as e:
            logger.error(f"Error generating demo data: {e}")
            return None

    def save_data_to_csv(self, df, filename):
        """Save DataFrame to CSV file.

        Args:
            df: DataFrame to save
            filename: Output filename in data/ directory
        """
        try:
            filepath = self.config.DATA_DIR / filename
            df.to_csv(filepath)
            logger.info(f"Data saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving data to CSV: {e}")

    def load_data_from_csv(self, filename):
        """Load DataFrame from CSV file.

        Args:
            filename: Filename in data/ directory

        Returns:
            DataFrame or None if file not found
        """
        try:
            filepath = self.config.DATA_DIR / filename
            if not filepath.exists():
                logger.error(f"File not found: {filepath}")
                return None

            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            logger.info(f"Data loaded from {filepath}")
            return df
        except Exception as e:
            logger.error(f"Error loading data from CSV: {e}")
            return None

    def get_symbol_info(self, symbol):
        """Get symbol information from MT5.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with symbol info or None
        """
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                logger.error(f"Symbol not found: {symbol}")
                return None

            return {
                'name': info.name,
                'description': info.description,
                'bid': info.bid,
                'ask': info.ask,
                'point': info.point,
                'digits': info.digits,
                'tick_size': info.tick_size,
                'tick_value': info.tick_value,
                'contract_size': info.contract_size,
            }
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return None

    def cleanup(self):
        """Cleanup and close connections."""
        self.disconnect_from_mt5()

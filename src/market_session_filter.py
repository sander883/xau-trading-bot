import logging
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)


class MarketSessionFilter:
    """Identifies trading sessions and liquidity conditions."""

    # Session times in UTC (adjusts for DST)
    SESSIONS = {
        'ASIA': {'start': 0, 'end': 8},          # 00:00-08:00 UTC
        'LONDON': {'start': 8, 'end': 17},       # 08:00-17:00 UTC
        'NEW_YORK': {'start': 13, 'end': 21},    # 13:00-21:00 UTC (overlaps with London)
        'SYDNEY': {'start': 22, 'end': 7},       # 22:00 prev - 07:00 next UTC
    }

    # High liquidity overlaps
    OVERLAPS = {
        'LONDON_NEWYORK': {'start': 13, 'end': 17},  # Best liquidity for XAUUSD
        'ASIA_LONDON': {'start': 8, 'end': 8},       # Minimal overlap
    }

    # Low liquidity hours (avoid)
    LOW_LIQUIDITY = {
        'start_hour': 21,  # After NY close
        'end_hour': 0,     # Before Asian open
    }

    def __init__(self):
        """Initialize session filter."""
        self.current_session = None
        self.current_time = None

    def get_current_session(self, timezone='UTC'):
        """Get current trading session.

        Args:
            timezone: Timezone (default UTC)

        Returns:
            Dictionary with session info
        """
        try:
            tz = pytz.timezone(timezone) if timezone != 'UTC' else pytz.UTC
            now = datetime.now(tz)
            self.current_time = now

            hour = now.hour

            # Determine session
            if self.SESSIONS['ASIA']['start'] <= hour < self.SESSIONS['ASIA']['end']:
                session = 'ASIA'
            elif self.SESSIONS['LONDON']['start'] <= hour < self.SESSIONS['LONDON']['end']:
                session = 'LONDON'
            elif self.SESSIONS['NEW_YORK']['start'] <= hour < self.SESSIONS['NEW_YORK']['end']:
                session = 'NEW_YORK'
            elif self.SESSIONS['SYDNEY']['start'] <= hour or hour < self.SESSIONS['SYDNEY']['end']:
                session = 'SYDNEY'
            else:
                session = 'CLOSED'

            # Check for overlaps
            overlap = self.get_session_overlap(hour)

            self.current_session = session

            return {
                'session': session,
                'hour': hour,
                'overlap': overlap,
                'timestamp': now,
                'is_high_liquidity': overlap is not None,
                'is_low_liquidity': self.is_low_liquidity_hour(hour)
            }

        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    def get_session_overlap(self, hour):
        """Check for session overlaps.

        Args:
            hour: Hour of day (0-23)

        Returns:
            Overlap name or None
        """
        # London-NY overlap (best for XAUUSD)
        if self.OVERLAPS['LONDON_NEWYORK']['start'] <= hour < self.OVERLAPS['LONDON_NEWYORK']['end']:
            return 'LONDON_NEWYORK'

        # Asia-London overlap (minimal)
        if self.OVERLAPS['ASIA_LONDON']['start'] <= hour < self.OVERLAPS['ASIA_LONDON']['end']:
            return 'ASIA_LONDON'

        return None

    def is_high_liquidity_session(self, hour=None):
        """Check if current/given hour is high liquidity.

        Args:
            hour: Hour of day (0-23), default current

        Returns:
            True if high liquidity
        """
        if hour is None:
            hour = datetime.now().hour

        # High liquidity during overlaps
        if self.OVERLAPS['LONDON_NEWYORK']['start'] <= hour < self.OVERLAPS['LONDON_NEWYORK']['end']:
            return True

        # Good liquidity during London session
        if self.SESSIONS['LONDON']['start'] <= hour < self.SESSIONS['LONDON']['end']:
            return True

        # Good liquidity during NY session
        if self.SESSIONS['NEW_YORK']['start'] <= hour < self.SESSIONS['NEW_YORK']['end']:
            return True

        return False

    def is_low_liquidity_hour(self, hour=None):
        """Check if current/given hour has low liquidity.

        Args:
            hour: Hour of day (0-23), default current

        Returns:
            True if low liquidity
        """
        if hour is None:
            hour = datetime.now().hour

        return self.LOW_LIQUIDITY['start_hour'] <= hour or hour < self.LOW_LIQUIDITY['end_hour']

    def should_trade(self, hour=None, allow_low_liquidity=False):
        """Determine if trading is allowed based on session.

        Args:
            hour: Hour of day (0-23), default current
            allow_low_liquidity: Allow trading in low liquidity hours

        Returns:
            Tuple (should_trade: bool, reason: str)
        """
        if hour is None:
            hour = datetime.now().hour

        # Always avoid market close (21:00-23:00 UTC)
        if not allow_low_liquidity and self.is_low_liquidity_hour(hour):
            return False, "Low liquidity hours (21:00-23:00 UTC)"

        # Prefer London and NY sessions
        if self.is_high_liquidity_session(hour):
            return True, "High liquidity session"

        # Allow other hours but with caution
        if self.SESSIONS['ASIA']['start'] <= hour < self.SESSIONS['ASIA']['end']:
            return True, "Asia session (lower liquidity)"

        return False, "Market closed"

    def get_session_status(self):
        """Get detailed session status.

        Returns:
            Dictionary with session details
        """
        try:
            session_info = self.get_current_session()
            if session_info is None:
                return None

            hour = session_info['hour']
            overlap = session_info['overlap']

            # Time to next major session
            if session_info['session'] == 'LONDON':
                next_session = 'NEW_YORK'
                hours_to_next = self.SESSIONS['NEW_YORK']['start'] - hour
            elif session_info['session'] == 'NEW_YORK':
                next_session = 'ASIA'
                hours_to_next = (24 - hour) + self.SESSIONS['ASIA']['start']
            elif session_info['session'] == 'ASIA':
                next_session = 'LONDON'
                hours_to_next = self.SESSIONS['LONDON']['start'] - hour
            else:
                next_session = 'LONDON'
                hours_to_next = self.SESSIONS['LONDON']['start'] - hour

            return {
                'current_session': session_info['session'],
                'current_hour': hour,
                'session_overlap': overlap,
                'is_high_liquidity': session_info['is_high_liquidity'],
                'is_low_liquidity': session_info['is_low_liquidity'],
                'next_session': next_session,
                'hours_to_next_session': hours_to_next,
                'should_trade': self.should_trade(hour)[0],
                'trade_reason': self.should_trade(hour)[1],
                'timestamp': session_info['timestamp']
            }

        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None

    def get_hours_in_session(self, session_name):
        """Get hours remaining in session.

        Args:
            session_name: Session name (LONDON, NEW_YORK, etc.)

        Returns:
            Hours remaining (float) or None
        """
        try:
            if session_name not in self.SESSIONS:
                return None

            now = datetime.now()
            hour = now.hour
            minute = now.minute
            second = now.second

            session = self.SESSIONS[session_name]
            end_hour = session['end']

            if hour >= end_hour:
                return 0

            hours_remaining = end_hour - hour - (minute / 60.0) - (second / 3600.0)
            return max(0, hours_remaining)

        except Exception as e:
            logger.error(f"Error calculating hours in session: {e}")
            return None

    def get_session_strength(self):
        """Get liquidity strength of current session (0-1).

        Returns:
            Strength score (0-1)
        """
        session_info = self.get_session_status()
        if session_info is None:
            return 0

        if session_info['session_overlap'] == 'LONDON_NEWYORK':
            return 1.0  # Best liquidity

        if session_info['is_high_liquidity']:
            return 0.8  # High liquidity

        if session_info['is_low_liquidity']:
            return 0.3  # Low liquidity

        return 0.5  # Medium liquidity

    def get_session_volatility_expectation(self):
        """Get expected volatility for current session.

        Returns:
            Dictionary with volatility info
        """
        session_info = self.get_session_status()
        if session_info is None:
            return None

        session = session_info['current_session']

        volatility_map = {
            'LONDON_NEWYORK': {
                'level': 'HIGH',
                'volatility_multiplier': 1.5,
                'recommendation': 'Tighten stops, increase position size'
            },
            'LONDON': {
                'level': 'MEDIUM-HIGH',
                'volatility_multiplier': 1.2,
                'recommendation': 'Standard settings'
            },
            'NEW_YORK': {
                'level': 'HIGH',
                'volatility_multiplier': 1.4,
                'recommendation': 'Watch for sharp moves, wider stops'
            },
            'ASIA': {
                'level': 'LOW',
                'volatility_multiplier': 0.7,
                'recommendation': 'Avoid scalping, use wider SL'
            },
            'SYDNEY': {
                'level': 'LOW',
                'volatility_multiplier': 0.7,
                'recommendation': 'Low activity, avoid trading'
            },
            'CLOSED': {
                'level': 'NONE',
                'volatility_multiplier': 0.0,
                'recommendation': 'Market closed'
            }
        }

        return volatility_map.get(session, volatility_map['ASIA'])

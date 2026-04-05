import logging
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)


class NewsEventDetector:
    """Detects and avoids high-impact economic news events."""

    # High-impact economic indicators
    HIGH_IMPACT_EVENTS = {
        # US Events (affect USD, hence XAUUSD)
        'NFP': {'country': 'US', 'impact': 'CRITICAL', 'volatility': 'EXTREME'},
        'FOMC': {'country': 'US', 'impact': 'CRITICAL', 'volatility': 'EXTREME'},
        'CPI': {'country': 'US', 'impact': 'HIGH', 'volatility': 'VERY_HIGH'},
        'PPI': {'country': 'US', 'impact': 'HIGH', 'volatility': 'VERY_HIGH'},
        'GDP': {'country': 'US', 'impact': 'CRITICAL', 'volatility': 'EXTREME'},
        'JOBLESS_CLAIMS': {'country': 'US', 'impact': 'MEDIUM', 'volatility': 'HIGH'},
        'RETAIL_SALES': {'country': 'US', 'impact': 'HIGH', 'volatility': 'VERY_HIGH'},
        'MANUFACTURING': {'country': 'US', 'impact': 'MEDIUM', 'volatility': 'HIGH'},
        'ISM': {'country': 'US', 'impact': 'MEDIUM', 'volatility': 'HIGH'},
        'PMI': {'country': 'US', 'impact': 'MEDIUM', 'volatility': 'HIGH'},
        'HOUSING': {'country': 'US', 'impact': 'MEDIUM', 'volatility': 'HIGH'},
        'DURABLE_ORDERS': {'country': 'US', 'impact': 'MEDIUM', 'volatility': 'HIGH'},

        # Fed Speakers (Janet Yellen, Jerome Powell, etc.)
        'FED_SPEAKER': {'country': 'US', 'impact': 'HIGH', 'volatility': 'VERY_HIGH'},

        # Central Bank Rate Decisions
        'RATE_DECISION': {'country': 'US', 'impact': 'CRITICAL', 'volatility': 'EXTREME'},

        # Geopolitical
        'GEOPOLITICAL': {'country': 'GLOBAL', 'impact': 'CRITICAL', 'volatility': 'EXTREME'},
    }

    # Avoidance windows (minutes before/after event)
    AVOIDANCE_WINDOWS = {
        'CRITICAL': 60,      # 60 minutes before/after
        'HIGH': 30,          # 30 minutes before/after
        'MEDIUM': 15,        # 15 minutes before/after
    }

    def __init__(self):
        """Initialize news event detector."""
        self.upcoming_events = []
        self.last_event_check = None

    def check_news_avoidance(self, minutes_ahead=120):
        """Check if any high-impact news is coming.

        Args:
            minutes_ahead: How many minutes ahead to check

        Returns:
            Dictionary with news analysis
        """
        try:
            now = datetime.now(pytz.UTC)
            check_until = now + timedelta(minutes=minutes_ahead)

            high_impact_upcoming = []

            # In production, you would fetch from economic calendar API
            # For now, return structure for integration
            # Suggested APIs: TradingView, Forex Factory, Investing.com

            return {
                'timestamp': now,
                'check_window_minutes': minutes_ahead,
                'high_impact_upcoming': high_impact_upcoming,
                'should_avoid_trading': len(high_impact_upcoming) > 0,
                'next_critical_event': None,
                'minutes_until_event': None
            }

        except Exception as e:
            logger.error(f"Error checking news: {e}")
            return {'error': str(e), 'should_avoid_trading': True}

    def add_event(self, event_name, event_time, impact_level='MEDIUM'):
        """Add a known event to the calendar.

        Args:
            event_name: Name of event
            event_time: Event time (datetime)
            impact_level: Impact level
        """
        try:
            self.upcoming_events.append({
                'name': event_name,
                'time': event_time,
                'impact_level': impact_level,
                'avoidance_window': self.AVOIDANCE_WINDOWS.get(impact_level, 15)
            })

            logger.info(f"Event added: {event_name} at {event_time}")

        except Exception as e:
            logger.error(f"Error adding event: {e}")

    def is_in_news_blackout(self, minutes_buffer=30):
        """Check if currently in news blackout period.

        Args:
            minutes_buffer: Buffer in minutes around events

        Returns:
            Tuple (is_in_blackout, event_info)
        """
        try:
            now = datetime.now(pytz.UTC)

            for event in self.upcoming_events:
                event_time = event['time']
                buffer = timedelta(minutes=event['avoidance_window'] + minutes_buffer)

                start_blackout = event_time - buffer
                end_blackout = event_time + buffer

                if start_blackout <= now <= end_blackout:
                    return True, {
                        'event': event['name'],
                        'event_time': event_time,
                        'impact': event['impact_level'],
                        'minutes_to_event': (event_time - now).total_seconds() / 60
                    }

            return False, None

        except Exception as e:
            logger.error(f"Error checking blackout: {e}")
            return True, {'error': str(e)}  # Err on side of caution

    def clear_past_events(self):
        """Remove past events from calendar.

        Returns:
            Number of events cleared
        """
        try:
            now = datetime.now(pytz.UTC)
            original_count = len(self.upcoming_events)

            # Keep only future events
            self.upcoming_events = [
                e for e in self.upcoming_events
                if e['time'] > now
            ]

            cleared = original_count - len(self.upcoming_events)
            logger.info(f"Cleared {cleared} past events")

            return cleared

        except Exception as e:
            logger.error(f"Error clearing past events: {e}")
            return 0

    def get_events_for_day(self, date=None):
        """Get all events for a specific day.

        Args:
            date: Date to check (default today)

        Returns:
            List of events
        """
        try:
            if date is None:
                date = datetime.now(pytz.UTC).date()

            day_events = [
                e for e in self.upcoming_events
                if e['time'].date() == date
            ]

            return sorted(day_events, key=lambda x: x['time'])

        except Exception as e:
            logger.error(f"Error getting day events: {e}")
            return []

    def get_event_info(self, event_name):
        """Get information about a specific event.

        Args:
            event_name: Event name

        Returns:
            Event information dictionary
        """
        if event_name not in self.HIGH_IMPACT_EVENTS:
            return None

        return self.HIGH_IMPACT_EVENTS[event_name]

    def get_trading_calendar(self, days_ahead=7):
        """Get trading calendar for upcoming days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            Dictionary with calendar data
        """
        try:
            now = datetime.now(pytz.UTC)
            end_date = now + timedelta(days=days_ahead)

            calendar = {}

            for event in self.upcoming_events:
                if event['time'] <= end_date:
                    date_str = event['time'].strftime('%Y-%m-%d')

                    if date_str not in calendar:
                        calendar[date_str] = []

                    calendar[date_str].append({
                        'time': event['time'].strftime('%H:%M:%S UTC'),
                        'name': event['name'],
                        'impact': event['impact_level']
                    })

            return calendar

        except Exception as e:
            logger.error(f"Error getting calendar: {e}")
            return {}

    def get_trading_recommendation(self):
        """Get overall trading recommendation based on news.

        Returns:
            Dictionary with recommendation
        """
        try:
            is_blackout, blackout_info = self.is_in_news_blackout()
            upcoming = self.check_news_avoidance(minutes_ahead=120)

            if is_blackout:
                return {
                    'can_trade': False,
                    'reason': f"In news blackout: {blackout_info['event']} at {blackout_info['event_time']}",
                    'recommendation': 'AVOID - High impact news coming',
                    'event_info': blackout_info
                }

            if upcoming.get('should_avoid_trading'):
                return {
                    'can_trade': False,
                    'reason': 'High impact news coming in next 2 hours',
                    'recommendation': 'CAUTION - Wait for event to pass',
                    'upcoming_events': upcoming['high_impact_upcoming']
                }

            return {
                'can_trade': True,
                'reason': 'No high-impact news in next 2 hours',
                'recommendation': 'OK to trade',
                'upcoming_events': upcoming['high_impact_upcoming']
            }

        except Exception as e:
            logger.error(f"Error getting recommendation: {e}")
            return {
                'can_trade': False,
                'reason': f"Error checking news: {str(e)}",
                'recommendation': 'AVOID - Err on side of caution'
            }

    def should_avoid_trading(self):
        """Simple boolean check for trading.

        Returns:
            True if should avoid, False if OK
        """
        recommendation = self.get_trading_recommendation()
        return not recommendation.get('can_trade', False)

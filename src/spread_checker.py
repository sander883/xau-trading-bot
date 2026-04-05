import logging

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False
    mt5 = None

logger = logging.getLogger(__name__)


class SpreadChecker:
    """Monitors and validates spreads for XAUUSD trading."""

    # Typical XAUUSD spreads (pips)
    SPREAD_THRESHOLDS = {
        'TIGHT': (0, 1),         # < 1 pip - excellent
        'NORMAL': (1, 2),        # 1-2 pips - good
        'MODERATE': (2, 3),      # 2-3 pips - acceptable
        'WIDE': (3, 5),          # 3-5 pips - high
        'VERY_WIDE': (5, 100),   # > 5 pips - too wide
    }

    # Session-based expected spreads
    SESSION_SPREADS = {
        'LONDON_NEWYORK': 0.8,   # Overlap - best spreads
        'LONDON': 1.2,
        'NEW_YORK': 1.2,
        'ASIA': 2.0,
        'SYDNEY': 2.5,
        'CLOSED': 5.0,
    }

    def __init__(self, symbol='XAUUSD'):
        """Initialize spread checker.

        Args:
            symbol: Trading symbol (default XAUUSD)
        """
        self.symbol = symbol
        self.current_spread = None
        self.current_bid = None
        self.current_ask = None

    def get_current_spread(self):
        """Get current spread in pips.

        Returns:
            Dictionary with spread information
        """
        try:
            tick = mt5.symbol_info_tick(self.symbol)

            if tick is None:
                logger.error(f"Cannot get tick for {self.symbol}")
                return {'error': 'Cannot get tick'}

            # Calculate spread in pips
            # For XAUUSD, pip = 0.01
            spread_pips = (tick.ask - tick.bid) / 0.01

            self.current_spread = spread_pips
            self.current_bid = tick.bid
            self.current_ask = tick.ask

            # Determine spread category
            spread_category = self._categorize_spread(spread_pips)

            return {
                'bid': tick.bid,
                'ask': tick.ask,
                'spread_pips': spread_pips,
                'spread_category': spread_category,
                'spread_raw': tick.ask - tick.bid,
                'is_acceptable': spread_category != 'VERY_WIDE',
                'timestamp': tick.time
            }

        except Exception as e:
            logger.error(f"Error getting spread: {e}")
            return {'error': str(e)}

    def _categorize_spread(self, spread_pips):
        """Categorize spread size.

        Args:
            spread_pips: Spread in pips

        Returns:
            Category name
        """
        for category, (min_spread, max_spread) in self.SPREAD_THRESHOLDS.items():
            if min_spread <= spread_pips < max_spread:
                return category

        return 'VERY_WIDE'

    def is_spread_acceptable(self, max_spread_pips=2.5):
        """Check if spread is acceptable for trading.

        Args:
            max_spread_pips: Maximum acceptable spread in pips

        Returns:
            Tuple (is_acceptable, spread_info)
        """
        try:
            spread_data = self.get_current_spread()

            if 'error' in spread_data:
                logger.warning("Cannot check spread - being cautious")
                return False, spread_data

            spread_pips = spread_data['spread_pips']

            if spread_pips <= max_spread_pips:
                return True, spread_data
            else:
                return False, {
                    **spread_data,
                    'reason': f"Spread {spread_pips:.1f} pips exceeds max {max_spread_pips} pips"
                }

        except Exception as e:
            logger.error(f"Error checking spread: {e}")
            return False, {'error': str(e)}

    def get_spread_impact_on_trade(self, entry_price, position_size, trade_type='BUY'):
        """Calculate spread impact on trade cost.

        Args:
            entry_price: Entry price
            position_size: Position size in lots
            trade_type: BUY or SELL

        Returns:
            Dictionary with cost analysis
        """
        try:
            spread_data = self.get_current_spread()

            if 'error' in spread_data:
                return spread_data

            spread_pips = spread_data['spread_pips']
            spread_raw = spread_data['spread_raw']

            # XAUUSD: 1 lot = 100 oz
            # Cost = spread (in dollars) × lot size × 100
            spread_cost = spread_raw * position_size * 100

            # Spread as percentage of entry price
            spread_percent = (spread_pips / entry_price) * 100 if entry_price > 0 else 0

            # Break-even distance (price must move this much to break even)
            breakeven_pips = spread_pips

            return {
                'spread_pips': spread_pips,
                'spread_cost_dollars': spread_cost,
                'spread_percent': spread_percent,
                'breakeven_pips': breakeven_pips,
                'position_size': position_size,
                'entry_price': entry_price,
                'recommendation': self._spread_impact_recommendation(spread_pips, position_size)
            }

        except Exception as e:
            logger.error(f"Error calculating spread impact: {e}")
            return {'error': str(e)}

    def _spread_impact_recommendation(self, spread_pips, position_size):
        """Get recommendation based on spread impact.

        Args:
            spread_pips: Spread in pips
            position_size: Position size

        Returns:
            Recommendation string
        """
        spread_cost = spread_pips * position_size * 100

        if spread_pips <= 1:
            return "Excellent spread - low trading cost"
        elif spread_pips <= 2:
            return "Good spread - acceptable cost"
        elif spread_pips <= 3:
            return f"Moderate spread - cost ${spread_cost:.0f} per position"
        elif spread_pips <= 5:
            return f"Wide spread - consider waiting for better price"
        else:
            return f"Very wide spread - AVOID trading (cost ${spread_cost:.0f})"

    def wait_for_tight_spread(self, max_wait_seconds=30, target_spread=2.0):
        """Wait for spread to tighten before trading.

        Args:
            max_wait_seconds: Maximum time to wait
            target_spread: Target spread in pips

        Returns:
            Dictionary with result
        """
        try:
            import time

            start_time = time.time()
            best_spread = float('inf')
            best_spread_data = None

            while time.time() - start_time < max_wait_seconds:
                spread_data = self.get_current_spread()

                if 'error' not in spread_data:
                    spread_pips = spread_data['spread_pips']

                    if spread_pips < best_spread:
                        best_spread = spread_pips
                        best_spread_data = spread_data

                    if spread_pips <= target_spread:
                        return {
                            'success': True,
                            'spread_achieved': spread_pips,
                            'wait_time_seconds': time.time() - start_time,
                            'spread_data': spread_data
                        }

                time.sleep(0.5)

            return {
                'success': False,
                'reason': f"Spread did not tighten to {target_spread} pips within {max_wait_seconds} seconds",
                'best_spread': best_spread,
                'best_spread_data': best_spread_data
            }

        except Exception as e:
            logger.error(f"Error waiting for tight spread: {e}")
            return {'error': str(e)}

    def get_spread_statistics(self, lookback_minutes=60):
        """Get spread statistics over time (requires monitoring).

        Args:
            lookback_minutes: Period to analyze

        Returns:
            Spread statistics
        """
        try:
            # In production, you would store historical spread data
            # For now, return current snapshot
            spread_data = self.get_current_spread()

            return {
                'current_spread': spread_data.get('spread_pips'),
                'timestamp': spread_data.get('timestamp'),
                'note': 'Historical spread data not available - implement with tick data logger'
            }

        except Exception as e:
            logger.error(f"Error getting spread statistics: {e}")
            return {'error': str(e)}

    def get_trading_recommendation(self):
        """Get overall spread-based trading recommendation.

        Returns:
            Dictionary with recommendation
        """
        try:
            spread_data = self.get_current_spread()

            if 'error' in spread_data:
                return {
                    'can_trade': False,
                    'recommendation': 'AVOID - Cannot get spread information'
                }

            spread_pips = spread_data['spread_pips']
            category = spread_data['spread_category']

            recommendations = {
                'TIGHT': {
                    'can_trade': True,
                    'recommendation': 'EXCELLENT - Tight spread, ideal for entry'
                },
                'NORMAL': {
                    'can_trade': True,
                    'recommendation': 'GOOD - Normal spread, OK to trade'
                },
                'MODERATE': {
                    'can_trade': True,
                    'recommendation': 'ACCEPTABLE - Moderate spread, trade with caution'
                },
                'WIDE': {
                    'can_trade': False,
                    'recommendation': 'CAUTION - Wide spread, consider waiting'
                },
                'VERY_WIDE': {
                    'can_trade': False,
                    'recommendation': 'AVOID - Very wide spread, poor entry price'
                }
            }

            rec = recommendations.get(category, {
                'can_trade': False,
                'recommendation': 'UNKNOWN - Check spread manually'
            })

            return {
                **rec,
                'spread_pips': spread_pips,
                'spread_category': category,
                'spread_data': spread_data
            }

        except Exception as e:
            logger.error(f"Error getting recommendation: {e}")
            return {
                'can_trade': False,
                'recommendation': f'ERROR - {str(e)}'
            }

    def should_enter_trade(self, max_acceptable_spread=2.5):
        """Simple boolean check for spread.

        Args:
            max_acceptable_spread: Maximum acceptable spread in pips

        Returns:
            True if spread OK, False if too wide
        """
        is_acceptable, _ = self.is_spread_acceptable(max_acceptable_spread)
        return is_acceptable

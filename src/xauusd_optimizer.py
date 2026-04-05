import logging
from datetime import datetime

from src.xauusd_volatility_filter import XAUUSDVolatilityFilter
from src.news_event_detector import NewsEventDetector
from src.spread_checker import SpreadChecker
from src.xauusd_stop_system import DynamicStopLossCalculator, TrailingStopSystem

logger = logging.getLogger(__name__)


class XAUUSDOptimizer:
    """XAUUSD-specific trading optimization system."""

    def __init__(self, df, symbol='XAUUSD'):
        """Initialize XAUUSD optimizer.

        Args:
            df: DataFrame with OHLC data
            symbol: Trading symbol (default XAUUSD)
        """
        self.symbol = symbol
        self.df = df.copy()

        # Initialize components
        self.volatility_filter = XAUUSDVolatilityFilter(df)
        self.news_detector = NewsEventDetector()
        self.spread_checker = SpreadChecker(symbol)
        self.sl_calculator = DynamicStopLossCalculator(df)
        self.trailing_stops = TrailingStopSystem()

    def pre_trade_validation(self, entry_price, max_spread=2.5, max_atr_ratio=1.5):
        """Complete pre-trade validation for XAUUSD.

        Args:
            entry_price: Planned entry price
            max_spread: Maximum acceptable spread in pips
            max_atr_ratio: Maximum acceptable ATR ratio

        Returns:
            Dictionary with validation results
        """
        try:
            validation = {
                'timestamp': datetime.now(),
                'entry_price': entry_price,
                'passed_all_checks': False,
                'checks': {}
            }

            # 1. Volatility check
            vol_data = self.volatility_filter.get_volatility_level()
            vol_acceptable, vol_reason = self.volatility_filter.is_volatility_acceptable(
                min_vol='LOW',
                max_vol='HIGH'
            )
            validation['checks']['volatility'] = {
                'passed': vol_acceptable,
                'reason': vol_reason,
                'current_atr': vol_data.get('current_atr'),
                'level': vol_data.get('volatility_level')
            }

            # 2. News check
            news_rec = self.news_detector.get_trading_recommendation()
            validation['checks']['news'] = {
                'passed': news_rec.get('can_trade', False),
                'reason': news_rec.get('recommendation'),
                'upcoming_events': news_rec.get('upcoming_events', [])
            }

            # 3. Spread check
            spread_rec = self.spread_checker.get_trading_recommendation()
            validation['checks']['spread'] = {
                'passed': spread_rec.get('can_trade', False),
                'reason': spread_rec.get('recommendation'),
                'current_spread': spread_rec.get('spread_pips'),
                'category': spread_rec.get('spread_category')
            }

            # 4. Liquidity check
            is_tight, spread_info = self.spread_checker.is_spread_acceptable(max_spread)
            validation['checks']['liquidity'] = {
                'passed': is_tight,
                'reason': spread_info.get('reason', 'Acceptable liquidity'),
                'spread_pips': spread_info.get('spread_pips')
            }

            # Calculate overall result
            all_passed = all(
                check.get('passed', False)
                for check in validation['checks'].values()
            )

            validation['passed_all_checks'] = all_passed

            if not all_passed:
                failed_checks = [
                    k for k, v in validation['checks'].items()
                    if not v.get('passed', False)
                ]
                validation['failed_checks'] = failed_checks
                validation['recommendation'] = f"AVOID - Failed checks: {', '.join(failed_checks)}"
            else:
                validation['recommendation'] = 'OK - All checks passed, ready to trade'

            return validation

        except Exception as e:
            logger.error(f"Error in pre-trade validation: {e}")
            return {
                'error': str(e),
                'passed_all_checks': False,
                'recommendation': 'AVOID - Validation error'
            }

    def calculate_optimal_entry(self, base_entry_price, trade_type='BUY'):
        """Calculate optimal entry price considering spread and volatility.

        Args:
            base_entry_price: Base entry price from analysis
            trade_type: BUY or SELL

        Returns:
            Dictionary with entry recommendations
        """
        try:
            spread_data = self.spread_checker.get_current_spread()
            atr_data = self.volatility_filter.get_volatility_level()

            if 'error' in spread_data or 'error' in atr_data:
                return {'error': 'Cannot get market data'}

            spread_pips = spread_data.get('spread_pips', 0)

            # Adjust entry for spread
            if trade_type == 'BUY':
                adjusted_entry = base_entry_price + (spread_pips * 0.01 / 2)  # Add half spread
            else:
                adjusted_entry = base_entry_price - (spread_pips * 0.01 / 2)

            return {
                'base_entry': base_entry_price,
                'adjusted_entry': adjusted_entry,
                'spread_adjustment': spread_pips * 0.01 / 2,
                'spread_pips': spread_pips,
                'recommendation': f"Use {adjusted_entry:.2f} as entry (accounts for {spread_pips:.1f} pip spread)"
            }

        except Exception as e:
            logger.error(f"Error calculating optimal entry: {e}")
            return {'error': str(e)}

    def calculate_dynamic_stops(self, entry_price, trade_type='BUY'):
        """Calculate dynamic SL and TP for XAUUSD.

        Args:
            entry_price: Entry price
            trade_type: BUY or SELL

        Returns:
            Dictionary with stop levels
        """
        try:
            atr_data = self.volatility_filter.get_volatility_level()
            current_atr = atr_data.get('current_atr')
            avg_atr = atr_data.get('average_atr')

            if current_atr is None or avg_atr is None:
                return {'error': 'Cannot calculate ATR'}

            # Calculate SL
            sl_options = self.sl_calculator.calculate_optimal_sl(
                entry_price, current_atr, avg_atr, trade_type
            )

            if 'error' in sl_options:
                return sl_options

            # Volatility-adjusted TP
            vol_level = atr_data.get('volatility_level')
            tp_multiplier = {
                'VERY_LOW': 1.5,
                'LOW': 2.0,
                'NORMAL': 2.5,
                'HIGH': 3.0,
                'VERY_HIGH': 2.0  # Reduce TP in extreme volatility
            }.get(vol_level, 2.5)

            if trade_type == 'BUY':
                tp = entry_price + (current_atr * tp_multiplier)
            else:
                tp = entry_price - (current_atr * tp_multiplier)

            # Calculate R:R ratio
            if trade_type == 'BUY':
                rr_ratio = (tp - entry_price) / (entry_price - sl_options['recommended'])
            else:
                rr_ratio = (entry_price - tp) / (sl_options['recommended'] - entry_price)

            return {
                'entry_price': entry_price,
                'stop_loss': sl_options['recommended'],
                'take_profit': tp,
                'risk_pips': abs(entry_price - sl_options['recommended']) / 0.01,
                'profit_pips': abs(tp - entry_price) / 0.01,
                'rr_ratio': rr_ratio,
                'volatility_adjusted': True,
                'atr_based': sl_options.get('atr_based'),
                'recommendation': f"R:R = 1:{rr_ratio:.2f} (SL: {sl_options['recommended']:.2f}, TP: {tp:.2f})"
            }

        except Exception as e:
            logger.error(f"Error calculating stops: {e}")
            return {'error': str(e)}

    def setup_trailing_stop(self, trade_id, entry_price, trade_type='BUY'):
        """Setup trailing stop for a trade.

        Args:
            trade_id: Trade ID
            entry_price: Entry price
            trade_type: BUY or SELL

        Returns:
            Confirmation with SL details
        """
        try:
            atr_data = self.volatility_filter.get_volatility_level()
            current_atr = atr_data.get('current_atr')

            if current_atr is None:
                return {'error': 'Cannot get ATR for trailing stop'}

            self.trailing_stops.add_trade_with_trailing_stop(
                trade_id, entry_price, current_atr, trade_type
            )

            trade_info = self.trailing_stops.get_trade_summary(trade_id)

            return {
                'trade_id': trade_id,
                'status': 'Trailing stop activated',
                'entry_price': entry_price,
                'initial_sl': trade_info.get('current_sl'),
                'trailing_atr_multiplier': self.trailing_stops.trailing_atr_multiplier,
                'recommendation': 'Stop will trail upward (BUY) or downward (SELL) with volatility'
            }

        except Exception as e:
            logger.error(f"Error setting up trailing stop: {e}")
            return {'error': str(e)}

    def update_position(self, trade_id, current_price):
        """Update position with trailing stop and checks.

        Args:
            trade_id: Trade ID
            current_price: Current market price

        Returns:
            Dictionary with position update
        """
        try:
            atr_data = self.volatility_filter.get_volatility_level()
            current_atr = atr_data.get('current_atr')

            # Update trailing stop
            trailing_update = self.trailing_stops.update_trailing_stop(
                trade_id, current_price, current_atr
            )

            # Check if stopped out
            stop_check = self.trailing_stops.check_stop_hit(trade_id, current_price)

            return {
                'trade_id': trade_id,
                'current_price': current_price,
                'trailing_update': trailing_update,
                'stop_check': stop_check,
                'should_close': stop_check.get('stopped_out', False),
                'current_sl': self.trailing_stops.get_trade_summary(trade_id).get('current_sl')
            }

        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return {'error': str(e)}

    def get_optimization_summary(self):
        """Get complete optimization summary.

        Returns:
            Dictionary with all optimization status
        """
        try:
            return {
                'timestamp': datetime.now(),
                'symbol': self.symbol,
                'volatility': self.volatility_filter.get_volatility_level(),
                'spread': self.spread_checker.get_current_spread(),
                'news': self.news_detector.get_trading_recommendation(),
                'active_trades': len(self.trailing_stops.get_all_active_trades()),
                'components_status': {
                    'volatility_filter': 'Active',
                    'news_detector': 'Active',
                    'spread_checker': 'Active',
                    'dynamic_stops': 'Active',
                    'trailing_stops': 'Active'
                }
            }

        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return {'error': str(e)}

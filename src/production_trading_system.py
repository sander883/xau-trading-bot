import logging
from datetime import datetime
import MetaTrader5 as mt5

from src.market_session_filter import MarketSessionFilter
from src.pattern_detector import PatternDetector
from src.liquidity_detector import LiquidityDetector
from src.market_condition_detector import MarketConditionDetector
from src.technical_analysis import TechnicalAnalysis
from src.advanced_ml_model import AdvancedMLModel
from src.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class ProductionTradingSystem:
    """Production-ready trading system with all advanced features."""

    def __init__(self, config, data_fetcher, ml_model, risk_manager,
                 trading_engine, telegram_notifier):
        """Initialize production trading system.

        Args:
            config: Configuration object
            data_fetcher: DataFetcher instance
            ml_model: Advanced ML model instance
            risk_manager: RiskManager instance
            trading_engine: TradingEngine instance
            telegram_notifier: TelegramNotifier instance
        """
        self.config = config
        self.data_fetcher = data_fetcher
        self.ml_model = ml_model
        self.risk_manager = risk_manager
        self.trading_engine = trading_engine
        self.telegram_notifier = telegram_notifier

        # Initialize components
        self.session_filter = MarketSessionFilter()
        self.last_analysis = {}

    def full_market_analysis(self):
        """Perform comprehensive market analysis before trading.

        Returns:
            Dictionary with complete analysis
        """
        try:
            analysis_result = {
                'timestamp': datetime.now(),
                'symbol': self.config.SYMBOL,
                'trading_allowed': False,
                'reasons': [],
                'filters_passed': 0,
                'total_filters': 0
            }

            # 1. SESSION FILTER
            analysis_result['total_filters'] += 1
            session_status = self.session_filter.get_current_session()
            analysis_result['session_status'] = session_status

            should_trade, session_reason = self.session_filter.should_trade()
            if not should_trade:
                analysis_result['reasons'].append(f"Session filter: {session_reason}")
            else:
                analysis_result['filters_passed'] += 1

            # 2. FETCH DATA
            df = self.data_fetcher.get_ohlc_data(self.config.SYMBOL, self.config.TIMEFRAME, 500)
            if df is None:
                analysis_result['reasons'].append("Failed to fetch market data")
                return analysis_result

            current_price = df['Close'].iloc[-1]
            analysis_result['current_price'] = current_price

            # 3. TECHNICAL ANALYSIS
            ta = TechnicalAnalysis(df)
            ta.calculate_moving_averages()
            ta.calculate_rsi()
            ta.calculate_bollinger_bands()
            ta.calculate_atr()
            ta.calculate_stochastic()
            ta.calculate_adx()
            ta.calculate_volume_indicators()

            analysis_result['trend'] = ta.identify_trend()
            analysis_result['signal_strength'] = ta.get_signal_strength()

            # 4. PATTERN DETECTION
            analysis_result['total_filters'] += 1
            pattern_detector = PatternDetector(df)
            patterns = pattern_detector.detect_all_patterns()
            analysis_result['patterns'] = patterns
            pattern_signal, pattern_conf = pattern_detector.get_pattern_signal(patterns)

            if pattern_signal:
                analysis_result['filters_passed'] += 1
            else:
                analysis_result['reasons'].append("No confirmation patterns detected")

            # 5. LIQUIDITY CHECK
            analysis_result['total_filters'] += 1
            liquidity_detector = LiquidityDetector(df)
            is_safe, liquidity_reason = liquidity_detector.is_safe_to_trade()
            analysis_result['liquidity_analysis'] = liquidity_detector.get_liquidity_report()

            if not is_safe:
                analysis_result['reasons'].append(f"Liquidity: {liquidity_reason}")
            else:
                analysis_result['filters_passed'] += 1

            # 6. MARKET CONDITION
            analysis_result['total_filters'] += 1
            condition_detector = MarketConditionDetector(df)
            market_condition = condition_detector.detect_market_type()
            analysis_result['market_condition'] = market_condition
            analysis_result['market_condition_score'] = condition_detector.get_market_condition_score()

            if analysis_result['market_condition_score'] > 0.3:
                analysis_result['filters_passed'] += 1
            else:
                analysis_result['reasons'].append("Poor market conditions")

            # 7. AI MODEL PREDICTION
            analysis_result['total_filters'] += 1
            features = ta.get_features_for_ml()
            if features is not None and len(features) > 0:
                ml_features = features.iloc[-1].values.reshape(1, -1)
                ai_signal, confidence, is_confident = self.ml_model.predict_with_confidence(ml_features)

                analysis_result['ai_signal'] = 'BUY' if ai_signal == 1 else 'SELL' if ai_signal == 0 else 'NEUTRAL'
                analysis_result['ai_confidence'] = confidence
                analysis_result['ai_confident'] = is_confident

                if is_confident:
                    analysis_result['filters_passed'] += 1
                else:
                    analysis_result['reasons'].append(f"Low AI confidence: {confidence:.2f}")
            else:
                analysis_result['reasons'].append("Cannot compute AI features")

            # FINAL DECISION
            analysis_result['trading_allowed'] = (
                should_trade and
                is_safe and
                analysis_result['filters_passed'] >= analysis_result['total_filters'] * 0.7
            )

            return analysis_result

        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            self.telegram_notifier.send_error_alert(f"Analysis error: {str(e)}")
            return {'error': str(e), 'trading_allowed': False}

    def generate_trade_signal(self, analysis):
        """Generate trading signal from analysis.

        Args:
            analysis: Analysis dictionary from full_market_analysis

        Returns:
            Dictionary with trade signal details
        """
        try:
            if not analysis.get('trading_allowed'):
                return {
                    'has_signal': False,
                    'reason': ', '.join(analysis.get('reasons', ['Unknown reason']))
                }

            # Determine signal direction
            trend = analysis.get('trend')
            ai_signal = analysis.get('ai_signal')
            patterns = analysis.get('patterns', [])

            # Voting system
            buy_votes = 0
            sell_votes = 0

            if trend == 'UPTREND':
                buy_votes += 2
            elif trend == 'DOWNTREND':
                sell_votes += 2

            if ai_signal == 'BUY':
                buy_votes += 2
            elif ai_signal == 'SELL':
                sell_votes += 2

            for pattern in patterns:
                if pattern.get('signal') == 'BUY':
                    buy_votes += 1
                elif pattern.get('signal') == 'SELL':
                    sell_votes += 1

            # Determine final signal
            if buy_votes > sell_votes:
                signal_type = 'BUY'
                confidence = analysis.get('ai_confidence', 0.5)
            elif sell_votes > buy_votes:
                signal_type = 'SELL'
                confidence = analysis.get('ai_confidence', 0.5)
            else:
                return {'has_signal': False, 'reason': 'Conflicting signals'}

            return {
                'has_signal': True,
                'signal_type': signal_type,
                'confidence': confidence,
                'buy_votes': buy_votes,
                'sell_votes': sell_votes,
                'market_condition': analysis.get('market_condition', {}).get('market_type'),
                'timestamp': analysis.get('timestamp')
            }

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return {'has_signal': False, 'error': str(e)}

    def execute_trade_with_advanced_risk(self, signal, analysis, account_info):
        """Execute trade with advanced risk management.

        Args:
            signal: Trade signal from generate_trade_signal
            analysis: Analysis from full_market_analysis
            account_info: Account information

        Returns:
            Trade execution result
        """
        try:
            if not signal.get('has_signal'):
                return None

            current_price = analysis.get('current_price')
            trade_type = signal.get('signal_type')

            # Calculate risk-based position size
            sl_price = self.risk_manager.calculate_stop_loss(current_price, trade_type)
            position_size = self.risk_manager.calculate_position_size_by_risk(
                account_info['balance'],
                current_price,
                sl_price,
                self.config.RISK_PERCENT_PER_TRADE
            )

            # Calculate TP
            tp_price = self.risk_manager.calculate_take_profit(current_price, trade_type)

            # Validate R:R ratio
            rr_ratio = self.risk_manager.calculate_risk_reward_ratio(
                current_price, sl_price, tp_price, trade_type
            )

            if rr_ratio < self.config.MIN_RISK_REWARD_RATIO:
                logger.info(f"R:R ratio {rr_ratio:.2f} below minimum")
                return None

            # Check daily loss
            daily_loss_check, loss_reason = self.risk_manager.can_open_trade(current_price, trade_type)
            if not daily_loss_check:
                logger.warning(f"Cannot open trade: {loss_reason}")
                return None

            # Open trade
            trade_id = self.trading_engine.open_trade(
                self.config.SYMBOL,
                trade_type,
                position_size,
                current_price
            )

            if trade_id:
                # Send detailed alert with all analysis
                self._send_trade_alert(trade_id, trade_type, signal, analysis,
                                      current_price, position_size, sl_price, tp_price, rr_ratio)

                return {
                    'trade_id': trade_id,
                    'type': trade_type,
                    'entry': current_price,
                    'sl': sl_price,
                    'tp': tp_price,
                    'size': position_size,
                    'rr_ratio': rr_ratio,
                    'confidence': signal.get('confidence')
                }

            return None

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            self.telegram_notifier.send_error_alert(f"Trade execution error: {str(e)}")
            return None

    def _send_trade_alert(self, trade_id, trade_type, signal, analysis,
                         entry_price, position_size, sl, tp, rr_ratio):
        """Send detailed trade alert.

        Args:
            trade_id: Trade ID
            trade_type: BUY or SELL
            signal: Signal data
            analysis: Analysis data
            entry_price: Entry price
            position_size: Position size
            sl: Stop loss
            tp: Take profit
            rr_ratio: Risk/reward ratio
        """
        market_condition = analysis.get('market_condition', {})

        message = f"""
<b>🎯 {trade_type} - Trade Opened</b>

<b>Price Action:</b>
Entry: {entry_price:.2f}
SL: {sl:.2f} ({abs(entry_price - sl):.2f} pips)
TP: {tp:.2f} ({abs(tp - entry_price):.2f} pips)
R:R Ratio: 1:{rr_ratio:.2f}

<b>Signal Details:</b>
AI Confidence: {analysis.get('ai_confidence', 0):.0%}
Market Trend: {analysis.get('trend')}
Market Condition: {market_condition.get('market_type')}
Session: {analysis.get('session_status', {}).get('session')}

<b>Risk Management:</b>
Position Size: {position_size:.2f} lots
Risk %: {self.config.RISK_PERCENT_PER_TRADE}%
Daily Loss: ${self.risk_manager.daily_loss:.2f}

<b>Entry Patterns:</b>
{', '.join([p.get('pattern', 'Unknown') for p in analysis.get('patterns', [])])}
        """.strip()

        self.telegram_notifier.send_message(message)

    def get_trading_system_status(self):
        """Get complete trading system status.

        Returns:
            Dictionary with system status
        """
        account_info = self.trading_engine.get_account_info()
        risk_metrics = self.risk_manager.get_risk_metrics()
        session_status = self.session_filter.get_session_status()

        return {
            'timestamp': datetime.now(),
            'account_info': account_info,
            'risk_metrics': risk_metrics,
            'session_status': session_status,
            'model_trained': self.ml_model.is_trained,
            'model_type': self.ml_model.model_type,
            'trading_allowed': session_status.get('should_trade', False) if session_status else False,
            'daily_loss_remaining': max(0, self.config.MAX_DAILY_LOSS - self.risk_manager.daily_loss)
        }

    def cleanup(self):
        """Cleanup resources."""
        logger.info("Production trading system cleanup")

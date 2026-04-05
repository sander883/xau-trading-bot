import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends trade notifications via Telegram bot."""

    def __init__(self, config):
        """Initialize Telegram notifier.

        Args:
            config: Configuration object with Telegram settings
        """
        self.config = config
        self.enabled = config.TELEGRAM_NOTIFICATIONS_ENABLED
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, message):
        """Send a message via Telegram.

        Args:
            message: Message text

        Returns:
            True if sent successfully
        """
        if not self.enabled or not self.bot_token or not self.chat_id:
            logger.debug("Telegram notifications disabled or not configured")
            return False

        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(self.api_url, json=payload, timeout=5)
            response.raise_for_status()

            logger.debug(f"Telegram message sent: {message[:50]}...")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False

    def send_trade_signal(self, message):
        """Send trade signal notification.

        Args:
            message: Trade signal message
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"🤖 <b>Trade Signal</b>\n{timestamp}\n{message}"
        self.send_message(formatted_message)

    def send_trade_opened(self, trade_id, symbol, trade_type, entry_price, sl, tp):
        """Send trade opened notification.

        Args:
            trade_id: Trade ID
            symbol: Trading symbol
            trade_type: 'BUY' or 'SELL'
            entry_price: Entry price
            sl: Stop loss
            tp: Take profit
        """
        emoji = "📈" if trade_type == "BUY" else "📉"
        message = f"""{emoji} <b>Trade Opened</b>
<b>ID:</b> {trade_id}
<b>Symbol:</b> {symbol}
<b>Type:</b> {trade_type}
<b>Entry:</b> {entry_price:.2f}
<b>SL:</b> {sl:.2f}
<b>TP:</b> {tp:.2f}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}"""
        self.send_message(message)

    def send_trade_closed(self, trade_id, symbol, profit_loss, closing_price):
        """Send trade closed notification.

        Args:
            trade_id: Trade ID
            symbol: Trading symbol
            profit_loss: Profit/Loss amount
            closing_price: Closing price
        """
        emoji = "💰" if profit_loss > 0 else "❌"
        color = "green" if profit_loss > 0 else "red"

        message = f"""{emoji} <b>Trade Closed</b>
<b>ID:</b> {trade_id}
<b>Symbol:</b> {symbol}
<b>Close Price:</b> {closing_price:.2f}
<b>P&L:</b> <code>{profit_loss:+.2f}</code>
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}"""
        self.send_message(message)

    def send_daily_report(self, risk_metrics, account_info):
        """Send daily trading report.

        Args:
            risk_metrics: Dictionary from RiskManager.get_risk_metrics()
            account_info: Dictionary from TradingEngine.get_account_info()
        """
        if account_info:
            message = f"""📊 <b>Daily Report</b>
<b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}

<b>Account:</b>
Balance: ${account_info['balance']:,.2f}
Equity: ${account_info['equity']:,.2f}
Profit: ${account_info['profit']:+,.2f}

<b>Trading:</b>
Open Trades: {risk_metrics['open_trades']}
Closed: {risk_metrics['total_closed_trades']}
Wins: {risk_metrics['winning_trades']}
Losses: {risk_metrics['losing_trades']}
Win Rate: {risk_metrics['win_rate']:.1f}%

<b>P&L:</b>
Total: ${risk_metrics['total_profit_loss']:+,.2f}
Daily Loss: ${risk_metrics['daily_loss']:,.2f}
Remaining: ${risk_metrics['remaining_daily_loss_limit']:,.2f}"""

            self.send_message(message)

    def send_error_alert(self, error_message):
        """Send error alert.

        Args:
            error_message: Error message
        """
        message = f"""⚠️ <b>Error Alert</b>
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>Message:</b> {error_message}"""
        self.send_message(message)

    def send_system_status(self, status, details=""):
        """Send system status message.

        Args:
            status: 'STARTING', 'RUNNING', 'STOPPED', 'ERROR'
            details: Additional details
        """
        emojis = {
            'STARTING': '🔄',
            'RUNNING': '✅',
            'STOPPED': '⏹️',
            'ERROR': '❌'
        }

        message = f"""{emojis.get(status, '⚠️')} <b>System Status</b>
<b>Status:</b> {status}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        if details:
            message += f"\n<b>Details:</b> {details}"

        self.send_message(message)

    def send_signal_analysis(self, symbol, signal_dict):
        """Send detailed signal analysis.

        Args:
            symbol: Trading symbol
            signal_dict: Signal analysis dictionary
        """
        signal = signal_dict.get('combined_signal', 'NEUTRAL')
        strength = signal_dict.get('combined_strength', 0)

        emoji = "🟢" if signal == 'BUY' else "🔴" if signal == 'SELL' else "🟡"

        message = f"""{emoji} <b>Signal Analysis - {symbol}</b>
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

<b>Combined Signal:</b> {signal} ({strength:.2f})
<b>EMA:</b> {signal_dict.get('ema_signal', 'N/A')} ({signal_dict.get('ema_strength', 0):.2f})
<b>RSI:</b> {signal_dict.get('rsi_signal', 'N/A')} ({signal_dict.get('rsi_strength', 0):.2f})
<b>AI:</b> {signal_dict.get('ai_signal', 'N/A')} ({signal_dict.get('ai_confidence', 0):.2f})"""

        self.send_message(message)

    def send_mtf_analysis(self, symbol, mtf_summary):
        """Send multi-timeframe analysis.

        Args:
            symbol: Trading symbol
            mtf_summary: MTF summary dictionary
        """
        overall_trend = mtf_summary.get('overall_trend', 'NEUTRAL')
        aligned = mtf_summary.get('alignment', False)
        confidence = mtf_summary.get('consensus_confidence', 0)

        emoji = "📈" if 'UP' in overall_trend else "📉" if 'DOWN' in overall_trend else "↔️"
        align_emoji = "✅" if aligned else "⚠️"

        trends_text = ""
        for tf, trend in mtf_summary.get('trends', {}).items():
            trends_text += f"\n{tf}: {trend}"

        message = f"""{emoji} <b>MTF Analysis - {symbol}</b>
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

<b>Overall Trend:</b> {overall_trend}
<b>Alignment:</b> {align_emoji} {'Aligned' if aligned else 'Not Aligned'}
<b>Confidence:</b> {confidence:.2%}

<b>Timeframes:</b>{trends_text}"""

        self.send_message(message)

    def send_position_opened(self, symbol, trade_type, entry_price, position_size, sl, tp, risk_percent):
        """Send detailed position opened alert.

        Args:
            symbol: Trading symbol
            trade_type: 'BUY' or 'SELL'
            entry_price: Entry price
            position_size: Position size in lots
            sl: Stop loss
            tp: Take profit
            risk_percent: Risk percentage
        """
        emoji = "📈" if trade_type == "BUY" else "📉"
        rr_ratio = abs((tp - entry_price) / (entry_price - sl)) if (entry_price - sl) != 0 else 0

        message = f"""{emoji} <b>Position Opened - {symbol}</b>
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

<b>Type:</b> {trade_type}
<b>Entry:</b> {entry_price:.2f}
<b>Position Size:</b> {position_size:.2f} lots
<b>Risk %:</b> {risk_percent:.2f}%

<b>Levels:</b>
SL: {sl:.2f} ({abs(entry_price - sl):.2f} pips)
TP: {tp:.2f} ({abs(tp - entry_price):.2f} pips)
R:R Ratio: 1:{rr_ratio:.2f}"""

        self.send_message(message)

    def send_risk_alert(self, alert_type, details):
        """Send risk management alert.

        Args:
            alert_type: Type of alert ('MAX_LOSS', 'DRAWDOWN', 'SIZE_REDUCED', etc.)
            details: Alert details dictionary
        """
        emojis = {
            'MAX_LOSS': '🛑',
            'DRAWDOWN': '📉',
            'SIZE_REDUCED': '⚠️',
            'RECOVERY': '📈',
            'LIMIT_REACHED': '🔒'
        }

        emoji = emojis.get(alert_type, '⚠️')

        message = f"""{emoji} <b>Risk Alert</b>
<b>Type:</b> {alert_type}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}"""

        if isinstance(details, dict):
            for key, value in details.items():
                if isinstance(value, float):
                    message += f"\n<b>{key}:</b> {value:.2f}"
                else:
                    message += f"\n<b>{key}:</b> {value}"

        self.send_message(message)

    def send_trading_summary(self, symbol, timeframe, current_price, indicators):
        """Send trading summary.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            current_price: Current price
            indicators: Dictionary with indicator values
        """
        message = f"""📊 <b>Trading Summary - {symbol}</b>
<b>Timeframe:</b> {timeframe}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

<b>Price:</b> {current_price:.2f}
<b>RSI:</b> {indicators.get('rsi', 'N/A')}
<b>MACD:</b> {indicators.get('macd', 'N/A')}
<b>BB Position:</b> {indicators.get('bb_position', 'N/A')}
<b>ATR:</b> {indicators.get('atr', 'N/A')}"""

        self.send_message(message)

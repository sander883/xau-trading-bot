# AI Trading Bot for XAUUSD (Gold)

A production-ready automated trading bot for XAUUSD (Gold) with AI-powered predictions, risk management, and backtesting capabilities.

## Features

### Core Features
- **MetaTrader5 Integration**: Direct connection to MT5 for live trading
- **AI Predictions**: XGBoost and scikit-learn models for price direction prediction
- **Technical Analysis**: 10+ technical indicators (RSI, MACD, Bollinger Bands, ATR, etc.)
- **Risk Management**: Automatic stop loss/take profit, daily loss limits, position sizing
- **Backtesting**: Full strategy backtesting with performance metrics
- **Telegram Notifications**: Real-time alerts for trades, errors, and daily reports
- **Logging System**: Comprehensive logging with rotation

### Advanced Features
- Model persistence (save/load trained models)
- Feature importance analysis
- Equity curve tracking
- Sharpe ratio and profit factor calculations
- Maximum drawdown monitoring
- Dynamic position sizing based on equity

## Project Structure

```
xau-trading-bot/
├── config/
│   ├── __init__.py
│   └── config.py              # Configuration loader and validation
├── data/
│   └── (market data CSV files)
├── logs/
│   └── (trading bot logs)
├── models/
│   └── (trained ML models)
├── src/
│   ├── __init__.py
│   ├── data_fetcher.py        # MetaTrader5 data retrieval
│   ├── technical_analysis.py  # Technical indicators
│   ├── ml_model.py            # AI model (XGBoost/sklearn)
│   ├── risk_manager.py        # Risk management logic
│   ├── trading_engine.py      # Trade execution
│   ├── telegram_notifier.py   # Notifications
│   ├── backtester.py          # Backtesting system
│   └── logger.py              # Logging setup
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## Installation

### Prerequisites
- Python 3.8+
- MetaTrader5 (installed and running)
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/xau-trading-bot.git
cd xau-trading-bot
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
nano .env
```

## Configuration

### Essential Settings (.env)

**MetaTrader5**
```
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=MetaQuotes-Demo
```

**Trading Parameters**
```
SYMBOL=XAUUSD
TIMEFRAME=1H
LOT_SIZE=0.1
INITIAL_BALANCE=10000
```

**Risk Management**
```
MAX_DAILY_LOSS=500
MAX_POSITION_SIZE=2
STOP_LOSS_PIPS=50
TAKE_PROFIT_PIPS=150
MAX_OPEN_TRADES=3
```

**AI Model**
```
MODEL_TYPE=xgboost  # or sklearn
PREDICTION_CONFIDENCE_THRESHOLD=0.65
RETRAIN_FREQUENCY=7
```

**Telegram Bot (Optional)**
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_NOTIFICATIONS_ENABLED=true
```

## Usage

### Live Trading
```bash
python main.py
```

### Backtest Strategy
```bash
python main.py backtest
```

### Check Status
```bash
tail -f logs/trading_bot.log
```

## Architecture

### Data Flow
```
MetaTrader5
    ↓
DataFetcher (OHLC data)
    ↓
TechnicalAnalysis (Indicators)
    ↓
MLModel (Predictions)
    ↓
TradingEngine (Decisions)
    ↓
RiskManager (Validation)
    ↓
Trade Execution + Notifications
```

### Risk Management Strategy
1. **Position Sizing**: Dynamically reduces lot size based on daily losses
2. **Stop Loss/Take Profit**: Automatic calculation and enforcement
3. **Daily Loss Limit**: Stops trading if daily loss exceeds threshold
4. **Max Open Trades**: Limits concurrent positions
5. **Confidence Threshold**: Only trades when model confidence is high

## Training & Backtesting

### Model Training
The bot automatically:
1. Fetches historical data (configurable date range)
2. Calculates 10+ technical indicators
3. Trains XGBoost or sklearn model
4. Saves model for future use
5. Logs accuracy metrics

### Backtest Metrics
- Total trades and win rate
- ROI and profit factor
- Maximum drawdown
- Sharpe ratio
- Trade-by-trade breakdown

## Monitoring

### Telegram Notifications
- 📈 Trade opened alerts
- 💰 Trade closed with P&L
- 📊 Daily performance reports
- ⚠️ Error alerts
- ✅ System status updates

### Log Files
- `logs/trading_bot.log`: Full trading history and debug info
- Automatic log rotation (10MB max per file, 5 backups)

## Performance Optimization

### Code Quality
- Type hints for better IDE support
- Comprehensive error handling
- Modular design for easy testing
- Clean separation of concerns

### Resource Management
- Connection pooling for MT5
- Efficient data processing with pandas
- Model caching to avoid retraining
- Smart sleep intervals based on timeframe

## Security Considerations

1. **Never commit .env file** - Use .env.example for template
2. **Validate all inputs** - Configuration is validated at startup
3. **Secure credential storage** - Use strong, unique passwords
4. **Monitor account activity** - Check MT5 logs regularly
5. **Test on demo first** - Always backtest before live trading

## Troubleshooting

### Connection Issues
```
Error: "MT5 initialization failed"
- Check MT5 is running
- Verify login credentials
- Check server name
```

### Model Training Errors
```
Error: "Failed to fetch historical data"
- Verify symbol exists in MT5
- Check date range is valid
- Ensure sufficient data points
```

### Telegram Notifications Not Working
```
- Verify bot token and chat ID
- Check internet connection
- Enable TELEGRAM_NOTIFICATIONS_ENABLED=true
```

## Development

### Adding New Indicators
Edit `src/technical_analysis.py`:
```python
def calculate_custom_indicator(self):
    self.df['CUSTOM'] = talib.INDICATOR(...)
    self.indicators['CUSTOM'] = True
    return self
```

### Custom Trading Rules
Edit `src/trading_engine.py`:
```python
def should_open_trade(self, prediction, confidence, trend):
    # Add custom logic here
    return should_trade, trade_type
```

## Testing

```bash
# Run backtests
python main.py backtest

# Check logs for errors
grep ERROR logs/trading_bot.log
```

## Performance Requirements

- **CPU**: 1+ cores
- **RAM**: 2GB minimum
- **Disk**: 1GB (for logs and models)
- **Network**: Stable internet connection
- **MT5**: Running on same machine or network

## Limitations

- Requires active MetaTrader5 installation
- Real-time trading depends on internet connectivity
- Model performance depends on market conditions
- Backtesting assumes no slippage or commissions
- Limited to XAUUSD symbol (easily customizable)

## Roadmap

- [ ] Multi-timeframe analysis
- [ ] Multiple symbol support
- [ ] Advanced backtesting with commission/slippage
- [ ] Web dashboard for monitoring
- [ ] Database integration for trade history
- [ ] Docker containerization
- [ ] Cloud deployment support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License - See LICENSE file for details

## Disclaimer

⚠️ **IMPORTANT**: This bot is for educational purposes. Trading carries risk:
- Past performance ≠ future results
- Use on demo account first
- Never risk more than you can afford to lose
- Test thoroughly before live trading
- Monitor bot performance regularly

## Support

For issues and questions:
1. Check the logs (`logs/trading_bot.log`)
2. Review this README
3. Create GitHub issue with details
4. Include relevant log excerpts

## Author

AI Trading Bot Development Team

## Changelog

### v1.0.0 (Initial Release)
- Core trading engine
- MetaTrader5 integration
- XGBoost/sklearn models
- Risk management system
- Backtesting framework
- Telegram notifications
- Comprehensive logging

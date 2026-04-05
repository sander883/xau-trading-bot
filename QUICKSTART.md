# Quick Start Guide - AI Trading Bot for XAUUSD

Get the bot running in 5 minutes!

## Prerequisites
- Python 3.8+
- MetaTrader5 installed and running on your machine
- Git

## Step 1: Setup (2 minutes)

```bash
# Clone the repository
git clone https://github.com/yourusername/xau-trading-bot.git
cd xau-trading-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure (2 minutes)

```bash
# Copy example config
cp .env.example .env

# Edit with your credentials
nano .env  # Use your preferred editor
```

**Minimum required settings:**
```
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=MetaQuotes-Demo  # or your broker server
TELEGRAM_BOT_TOKEN=your_token  # Optional
TELEGRAM_CHAT_ID=your_chat_id  # Optional
```

## Step 3: Backtest (1 minute)

Test the strategy on historical data before going live:

```bash
python main.py backtest
```

Output will show:
- Number of trades executed
- Win rate percentage
- ROI
- Maximum drawdown
- Report saved to `data/backtest_report.csv`

## Step 4: Run Live Trading

```bash
python main.py
```

Monitor the bot:
```bash
tail -f logs/trading_bot.log
```

## What The Bot Does

1. **Fetches data** from MetaTrader5 every hour (configurable)
2. **Calculates indicators**: RSI, MACD, Bollinger Bands, ATR, etc.
3. **Makes predictions** using trained AI model
4. **Opens trades** when conditions align
5. **Manages risk** with automatic stop loss/take profit
6. **Sends alerts** via Telegram (optional)

## Configuration Quick Reference

### Risk Parameters
```env
MAX_DAILY_LOSS=500           # Stop trading if loss exceeds this
MAX_OPEN_TRADES=3            # Max concurrent positions
STOP_LOSS_PIPS=50            # Stop loss distance
TAKE_PROFIT_PIPS=150         # Take profit distance
```

### AI Model
```env
MODEL_TYPE=xgboost           # xgboost or sklearn
PREDICTION_CONFIDENCE_THRESHOLD=0.65  # Only trade when confident
RETRAIN_FREQUENCY=7          # Days between retraining
```

### Trading
```env
SYMBOL=XAUUSD               # Gold/USD
TIMEFRAME=1H                # 1H, 4H, 1D, etc.
LOT_SIZE=0.1                # Position size in lots
```

## First Run Checklist

- [ ] MT5 is running and logged in
- [ ] .env file is configured with credentials
- [ ] Virtual environment is activated
- [ ] Dependencies are installed
- [ ] Backtest runs without errors
- [ ] Check logs for any issues

## Common Commands

```bash
# Run trading bot
python main.py

# Run backtest
python main.py backtest

# Show logs
tail -f logs/trading_bot.log

# Using Make (if installed)
make run        # Run bot
make backtest   # Run backtest
make logs       # Show logs
make help       # See all commands
```

## Monitoring

### Telegram Alerts (if enabled)
- 📈 Trade opened
- 💰 Trade closed with P&L
- 📊 Daily performance at midnight
- ⚠️ Errors and warnings

### Log Files
- `logs/trading_bot.log` - All trading activity
- Automatically rotates at 10MB

## Troubleshooting

### "MT5 initialization failed"
```
1. Make sure MetaTrader5 is open and logged in
2. Check login credentials in .env
3. Verify the server name is correct
```

### "Model not trained"
```
1. First run automatically trains the model
2. Fetch historical data during training
3. Check internet connection
```

### No Telegram messages
```
1. Enable: TELEGRAM_NOTIFICATIONS_ENABLED=true
2. Check bot token is correct
3. Verify chat ID is your ID (not @username)
```

## Next Steps

1. **Monitor for a week** on demo account
2. **Review the logs** and backtest results
3. **Adjust risk parameters** if needed
4. **Test on live account** with small lot size
5. **Gradually increase size** as confidence grows

## Learning Resources

- **Technical Analysis**: Check `src/technical_analysis.py`
- **Risk Management**: See `src/risk_manager.py`
- **Trading Logic**: Study `src/trading_engine.py`
- **Full docs**: Read `README.md`

## Support

If you encounter issues:
1. Check the logs: `tail -f logs/trading_bot.log`
2. Review the error message
3. See Troubleshooting section above
4. Create GitHub issue with log excerpts

---

**Remember**: Start with demo account testing. Never risk more than you can afford to lose! 📈

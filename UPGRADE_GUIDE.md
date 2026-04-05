# Upgrade Guide - Advanced Features

This document describes the new advanced features added to the AI Trading Bot.

## What's New

### 1. Multi-Timeframe Analysis 🔄

**File**: `src/multi_timeframe_analyzer.py`

Analyzes price action across multiple timeframes simultaneously (M5, M15, H1).

**Key Features**:
- **Overall Trend Detection**: Determines market direction from multiple perspectives
  - `STRONG_UP`: All/most timeframes bullish
  - `STRONG_DOWN`: All/most timeframes bearish
  - `UP`/`DOWN`: Mixed signals with bias
  - `NEUTRAL`: Conflicting signals

- **Timeframe Alignment**: Checks if all timeframes agree
  - Stronger signals when aligned
  - Caution when misaligned

- **Consensus Signals**: Combines signals from all timeframes
  - Weighted by timeframe importance
  - Returns signal + confidence score

- **Support/Resistance Levels**: Identifies key levels across timeframes

**Usage**:
```python
mtf_analyzer = MultiTimeframeAnalyzer(data_fetcher, ['M5', 'M15', 'H1'])
mtf_analyzer.analyze('XAUUSD')

# Get overall analysis
summary = mtf_analyzer.get_mtf_summary()
overall_trend = summary['overall_trend']
aligned = summary['alignment']
signal, confidence = summary['consensus_signal']

# Identify opportunities
has_opp, trade_type, conf = mtf_analyzer.identify_trading_opportunity()
```

**Configuration**:
```env
MULTI_TIMEFRAME_ENABLED=true
MULTI_TIMEFRAMES=M5,M15,H1
```

---

### 2. Combined EMA + RSI + AI Strategy 🎯

**File**: `src/combined_strategy.py`

Integrates three independent analysis methods into one unified signal.

**Components**:
1. **EMA Analysis**
   - Golden Cross: Fast EMA crosses above Slow EMA (strong buy)
   - Death Cross: Fast EMA crosses below Slow EMA (strong sell)
   - Price position relative to EMAs

2. **RSI Analysis**
   - Oversold (<30): Buy signal
   - Overbought (>70): Sell signal
   - RSI trends within bands

3. **AI Prediction**
   - ML model prediction (XGBoost/sklearn)
   - Confidence score integration

**Signal Combination**:
- Voting system: All three vote on direction
- Strength weighted by individual confidence
- Explanation generated for each signal

**Usage**:
```python
strategy = CombinedStrategy(config, ml_model)

# Get combined signal
signal_dict = strategy.get_signal(ta, features)

# Signal contains:
# - combined_signal: 'BUY', 'SELL', or 'NEUTRAL'
# - combined_strength: 0-1 confidence
# - Individual component signals
# - Explanation text

# Check if should trade
if strategy.should_trade(signal_dict, confidence_threshold=0.6):
    # Execute trade
    pass

# Get explanation
explanation = strategy.get_signal_explanation(signal_dict)
```

**Configuration**:
```env
STRATEGY_TYPE=combined  # or ema_rsi, ai_only
PREDICTION_CONFIDENCE_THRESHOLD=0.65
```

---

### 3. Risk-Based Position Sizing 💰

**File**: `src/risk_manager.py` (enhanced)

Calculate position size based on account risk percentage, not fixed lot size.

**Method**: Kelly Criterion inspired approach

```
Position Size = (Account Risk %) / (SL Distance in Pips × Pip Value)
```

**Key Functions**:

```python
# Calculate position by risk %
position_size = risk_manager.calculate_position_size_by_risk(
    account_balance=10000,
    entry_price=2050.0,
    sl_price=2040.0,
    risk_percent=2.0  # Risk 2% of account
)

# Calculate risk/reward ratio
ratio = risk_manager.calculate_risk_reward_ratio(
    entry_price=2050.0,
    sl_price=2040.0,
    tp_price=2070.0,
    trade_type='BUY'
)
# Returns: 2.0 (2:1 reward to risk)

# Get optimal position size with R:R validation
size, valid, reason = risk_manager.get_optimal_position_size(
    account_balance=10000,
    entry_price=2050.0,
    sl_price=2040.0,
    risk_percent=2.0,
    min_rr_ratio=1.5
)

# Get account risk metrics
metrics = risk_manager.get_account_risk_metrics(
    account_balance=10000,
    current_equity=9500
)
# Returns: drawdown %, daily loss %, position size multiplier
```

**Features**:
- Automatic loss-based size reduction (if daily loss >2%, reduce to 50%)
- Maximum position size limits
- Risk/reward ratio validation
- Account drawdown tracking

**Configuration**:
```env
RISK_PERCENT_PER_TRADE=2.0
MIN_RISK_REWARD_RATIO=1.5
MAX_POSITION_SIZE=2
MAX_DAILY_LOSS=500
```

---

### 4. Enhanced Telegram Alerts 📱

**File**: `src/telegram_notifier.py` (enhanced)

New notification types with detailed information.

**New Alert Methods**:

```python
# Signal analysis alert
notifier.send_signal_analysis(symbol, signal_dict)
# Shows: Combined signal, EMA/RSI/AI breakdown, confidence scores

# Multi-timeframe analysis
notifier.send_mtf_analysis(symbol, mtf_summary)
# Shows: Overall trend, alignment status, timeframe breakdown

# Position details
notifier.send_position_opened(
    symbol, trade_type, entry_price, position_size,
    sl, tp, risk_percent
)
# Shows: Full position info with risk metrics and R:R ratio

# Risk alerts
notifier.send_risk_alert(alert_type, details)
# Types: MAX_LOSS, DRAWDOWN, SIZE_REDUCED, RECOVERY, LIMIT_REACHED

# Trading summary
notifier.send_trading_summary(symbol, timeframe, price, indicators)
# Shows: Current price, RSI, MACD, Bollinger Bands, ATR
```

**Example Alert Output**:
```
🟢 Signal Analysis - XAUUSD
Time: 14:30:45

Combined Signal: BUY (0.78)
EMA: BUY (0.70)
RSI: BUY (0.65)
AI: BUY (0.92)
```

---

### 5. Advanced Backtesting Reports 📊

**File**: `src/backtester.py` (enhanced)

Generate comprehensive reports in multiple formats.

**New Report Methods**:

```python
# Generate detailed report dict
report = backtester.generate_detailed_report()
# Returns: All metrics in structured format

# Export HTML report (browser viewable)
backtester.export_html_report('backtest_report.html')

# Export text summary
backtester.export_summary_text('backtest_summary.txt')

# Export CSV (already existed)
backtester.export_backtest_report('trades.csv')
```

**Report Includes**:
- **Summary**: Total trades, wins, losses, win rate
- **Profitability**: Total profit/loss, avg win/loss, profit factor
- **Streaks**: Longest win/loss streaks
- **Performance**: ROI, max drawdown, Sharpe ratio
- **By Type**: Performance breakdown (BUY vs SELL)
- **Trades List**: Individual trade details

**Example Report Structure**:
```
BACKTEST REPORT
==============
Initial Capital: $10,000
Final Capital: $11,250

SUMMARY
Total Trades: 45
Winning: 28 (62.2%)
Losing: 17 (37.8%)

PROFITABILITY
Total Profit: $2,500
Total Loss: $1,250
Net Profit: $1,250
Profit Factor: 2.00

PERFORMANCE
ROI: 12.50%
Max Drawdown: 5.23%
Sharpe Ratio: 1.45
Avg Trade Duration: 4.2 hours
```

---

### 6. Advanced Trading Bot Orchestrator 🤖

**File**: `src/advanced_trading_bot.py` (new)

Unified interface combining all advanced features.

**Features**:

```python
bot = AdvancedTradingBot(
    config, data_fetcher, ml_model,
    risk_manager, trading_engine, telegram_notifier
)

# 1. Comprehensive market analysis
analysis = bot.analyze_market()
# Includes: MTF analysis, strategy signal, current price

# 2. Trade execution with risk sizing
trade_result = bot.execute_trade_logic(analysis)
# Returns: Trade ID, entry, SL, TP, position size, R:R ratio

# 3. Position monitoring
monitoring = bot.monitor_positions()
# Returns: Open positions count, unrealized P&L

# 4. Risk alerts
alerts = bot.check_risk_alerts()
# Returns: Daily loss, size reduction, max loss warnings

# 5. Bot status
status = bot.get_bot_status()
# Returns: Account info, risk metrics, open trades
```

**Workflow**:
```
1. Analyze market (MTF + Strategy)
2. If signal strong enough:
   - Calculate risk-based position size
   - Validate R:R ratio
   - Open position with alerts
3. Monitor positions continuously
4. Check risk alerts
5. Send daily reports
```

---

## Updated Configuration

### New .env Parameters

```env
# Multi-timeframe analysis
MULTI_TIMEFRAME_ENABLED=true
MULTI_TIMEFRAMES=M5,M15,H1

# Strategy selection
STRATEGY_TYPE=combined  # combined, ema_rsi, ai_only

# Risk-based position sizing
RISK_PERCENT_PER_TRADE=2.0      # Risk 2% of account per trade
MIN_RISK_REWARD_RATIO=1.5        # Require at least 1.5:1 R:R

# Risk management (existing, still used)
MAX_DAILY_LOSS=500
MAX_POSITION_SIZE=2
STOP_LOSS_PIPS=50
TAKE_PROFIT_PIPS=150
```

---

## Migration Guide

### From Basic Bot to Advanced Bot

**Old main.py approach**:
```python
# Single timeframe, fixed position size
df = data_fetcher.get_ohlc_data(symbol, timeframe)
ta = TechnicalAnalysis(df)
trading_engine.open_trade(symbol, 'BUY', 0.1, price)
```

**New approach with advanced bot**:
```python
bot = AdvancedTradingBot(...)

# 1. Analyze with MTF + Strategy
analysis = bot.analyze_market()

# 2. Execute with risk sizing
if analysis['should_trade']:
    trade = bot.execute_trade_logic(analysis)

# 3. Monitor and alert
bot.monitor_positions()
bot.check_risk_alerts()
```

---

## Performance Impact

**Processing Time**:
- Multi-timeframe analysis: ~2-3 seconds (3 timeframes)
- Combined strategy: ~0.1 seconds
- Risk calculations: ~0.05 seconds
- Total per cycle: ~3-4 seconds

**Memory Usage**:
- Base: ~150 MB
- With MTF (3 timeframes): ~200 MB
- Minimal increase

---

## Best Practices

### 1. Multi-Timeframe Configuration
```env
# Recommended for different trading styles
# Scalping:
MULTI_TIMEFRAMES=M1,M5,M15

# Swing:
MULTI_TIMEFRAMES=H1,H4,D1

# Hybrid:
MULTI_TIMEFRAMES=M5,M15,H1
```

### 2. Risk Percentage
```env
# Conservative: 1-2%
RISK_PERCENT_PER_TRADE=1.0

# Moderate: 2-3%
RISK_PERCENT_PER_TRADE=2.0

# Aggressive: 3-5% (not recommended for live)
RISK_PERCENT_PER_TRADE=3.0
```

### 3. Strategy Settings
```env
# Only if very confident in AI model
STRATEGY_TYPE=ai_only
PREDICTION_CONFIDENCE_THRESHOLD=0.8

# Balanced approach
STRATEGY_TYPE=combined
PREDICTION_CONFIDENCE_THRESHOLD=0.65

# Conservative, needs confirmation
STRATEGY_TYPE=ema_rsi
PREDICTION_CONFIDENCE_THRESHOLD=0.5
```

### 4. R:R Ratio
```env
# Tight stops, but riskier
MIN_RISK_REWARD_RATIO=1.0

# Balanced
MIN_RISK_REWARD_RATIO=1.5

# Conservative, larger targets
MIN_RISK_REWARD_RATIO=2.0
```

---

## Testing Recommendations

### Before Going Live

1. **Backtest thoroughly**:
   ```bash
   python main.py backtest
   # Review HTML report
   # Check win rate and Sharpe ratio
   ```

2. **Verify on demo**:
   - Run for at least 1 week
   - Monitor Telegram alerts
   - Check logs for any errors

3. **Validate configurations**:
   ```python
   Config.validate()
   # Checks all parameters are valid
   ```

4. **Test each component**:
   - MTF analyzer with different timeframes
   - Strategy signals on real data
   - Position sizing calculations

---

## Troubleshooting

### MTF Analysis
```python
# Insufficient data for some timeframes?
# Check if MT5 has data for all timeframes
# Try longer candle history (count=1000)

# Alignment always false?
# Normal when markets are consolidating
# Wait for trend confirmation
```

### Combined Strategy
```python
# Signals too conflicting?
# Increase confidence threshold
# Reduce number of timeframes
# Wait for stronger alignment

# Missing AI predictions?
# Ensure model is trained
# Check feature preparation
```

### Position Sizing
```python
# Positions too small?
# Increase RISK_PERCENT_PER_TRADE
# Decrease STOP_LOSS_PIPS (tighter stops)

# Positions too large?
# Decrease RISK_PERCENT_PER_TRADE
# Increase STOP_LOSS_PIPS (wider stops)
```

---

## Example: Complete Trading Cycle

```python
# 1. Initialize bot
bot = AdvancedTradingBot(...)

# 2. Market Analysis
analysis = bot.analyze_market()
# - Fetches 3 timeframes (M5, M15, H1)
# - Detects overall trend (STRONG_UP)
# - Analyzes EMA, RSI, AI signals
# - Determines: BUY with 0.78 confidence

# 3. Execute if qualified
if analysis['should_trade']:
    # - Calculates position size: 0.5 lots (2% risk)
    # - Validates R:R ratio: 1.8:1 (acceptable)
    # - Opens position with SL=2040, TP=2070
    # - Sends detailed Telegram alert
    trade = bot.execute_trade_logic(analysis)

# 4. Monitor
status = bot.monitor_positions()
# - 1 open position
# - Unrealized P&L: +$200

# 5. Risk check
alerts = bot.check_risk_alerts()
# - Daily loss: $50 (below limit)
# - Position multiplier: 1.0x (normal size)

# 6. Daily report
bot_status = bot.get_bot_status()
# - Account equity: $11,200
# - Open trades: 1
# - Daily P&L: +$200
```

---

## Summary of Changes

| Feature | Lines | Files |
|---------|-------|-------|
| Multi-timeframe analyzer | 250 | 1 |
| Combined strategy | 350 | 1 |
| Risk-based sizing | 200 | 1 |
| Enhanced notifications | 250 | 1 |
| Advanced backtesting | 300 | 1 |
| Advanced trading bot | 250 | 1 |
| Config updates | 50 | 1 |
| **Total** | **~1,650** | **7** |

Total project size now: **~5,950 lines** of Python code

---

**Ready to trade with advanced features!** 🚀

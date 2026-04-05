# Professional XGBoost Trading System Guide

## Overview

This guide covers the professional XGBoost-based trading system optimized for XAUUSD with advanced feature engineering, risk management, and entry logic.

## Components

### 1. ProfessionalXGBoostModel (`src/professional_xgboost_model.py`)

Advanced ML model with 30+ engineered features and 3-class classification (BUY/SELL/HOLD).

#### Features Engineered (30+)

**Trend Features:**
- EMA 50/200 crossover
- EMA distance from close
- Price position vs EMAs
- ADX trend strength
- Stochastic crossovers

**Momentum Features:**
- RSI levels and momentum
- Rate of Change (5, 10, 20 periods)
- MACD histogram and momentum
- Close momentum and direction

**Volatility Features:**
- ATR ratio (normalized to price)
- Volatility level classification
- Historical volatility (20-period)
- Bollinger Bands width and position
- Volatility trending indicator

**Price Action Features:**
- Candle body size and ratio
- Upper/lower wick ratios
- Engulfing pattern detection
- Close position in range
- Bullish/bearish candle classification

**Volume Features:**
- Volume SMA ratio
- High volume detection
- Volume trending

**Mean Reversion Features:**
- Price distance from SMA
- Oversold/overbought levels

**Sequence Features:**
- Multi-period returns (1, 3, 5 candles)
- Previous candle patterns
- Close momentum direction

#### Model Architecture

```python
from src.professional_xgboost_model import ProfessionalXGBoostModel

# Initialize
model = ProfessionalXGBoostModel(config)

# Prepare data
X, y = model.prepare_data(df_with_indicators)

# Train
metrics = model.train(X, y, test_size=0.2)

# Predict
signal = model.predict_signal(recent_features, confidence_threshold=0.65)

# Save model
model.save_model()
```

#### Prediction Output

```python
{
    'signal': TradeSignal.BUY,           # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    'signal_name': 'BUY',
    'confidence': 0.78,                  # 0-1, higher is better
    'prediction': 2,                     # 0=SELL, 1=HOLD, 2=BUY
    'probabilities': {
        'SELL': 0.12,
        'HOLD': 0.10,
        'BUY': 0.78
    },
    'meets_threshold': True              # Confidence > threshold
}
```

#### Training Metrics

The model tracks:
- Accuracy
- Precision (weighted)
- Recall (weighted)
- F1 Score
- Feature importance for top 15 features
- Training/test split sizes

### 2. ProfessionalTradingSystem (`src/professional_trading_system.py`)

Integrates the XGBoost model with professional trading logic.

#### Entry Logic (Multi-Factor Confirmation)

Trade entry requires ALL of these conditions:

**1. AI Signal (40% weight)**
- Model confidence > threshold (e.g., 0.65)
- Signal must be BUY or SELL (not HOLD)

**2. Trend Confirmation (30% weight)**
- For BUY: EMA 50 > EMA 200 AND Price > EMA 50
- For SELL: EMA 50 < EMA 200 AND Price < EMA 50
- Confirmed over last 5 candles

**3. Pattern Confirmation (20% weight)**
- Engulfing candle (larger body than previous)
- OR Rejection candle (long wick opposite to move)

**4. Market Condition (10% weight)**
- Trending market preferred (ADX > 25)
- Ranging market supported if other signals strong

#### Overall Confidence Score

```
Confidence = AI_Confidence (0-40) +
             Trend_Confirmed (0-30) +
             Pattern_Confirmed (0-20) +
             Market_Condition (0-10)
Maximum: 100
```

#### Risk Management

**Position Sizing**
```
Risk Amount = Account Size × 1% (configurable)
Position Size = Risk Amount / Price Risk
Position Size = min(Position Size, Account Size × 10%)
Position Size = max(Position Size, Min Lot Size)
```

**Stop Loss & Take Profit**
```
SL Distance = ATR × 1.5
TP Distance = ATR × 3.0 (for 1:2 RR ratio)

For BUY:
  SL = Entry - SL_Distance
  TP = Entry + TP_Distance

For SELL:
  SL = Entry + SL_Distance
  TP = Entry - TP_Distance
```

**RR Ratio Validation**
```
Min RR Ratio = 1:2 (configurable as MIN_RISK_REWARD_RATIO)
If calculated RR < Min RR: Skip trade
```

#### Usage Example

```python
from src.professional_trading_system import ProfessionalTradingSystem

# Initialize
system = ProfessionalTradingSystem(
    config=config,
    data_fetcher=data_fetcher,
    xgboost_model=model,
    risk_manager=risk_manager
)

# Analyze entry
analysis = system.analyze_entry(df_with_indicators)

# Check analysis
if analysis['entry_signal'].value > 0:  # BUY
    print(f"Entry at: {analysis['entry_price']}")
    print(f"Position Size: {analysis['position_size']}")
    print(f"SL: {analysis['stops']['stop_loss']}")
    print(f"TP: {analysis['stops']['take_profit']}")
    print(f"Confidence: {analysis['confidence_score']}/100")
```

## Configuration

### Required .env Parameters

```env
# Model
PREDICTION_CONFIDENCE_THRESHOLD=0.65    # Min confidence for trade
MIN_RISK_REWARD_RATIO=1.5              # Min RR ratio (1:1.5 means 1:1.5)

# Risk Management
RISK_PERCENT_PER_TRADE=1.0             # Risk % per trade
MAX_DAILY_LOSS=500                     # Max daily loss in USD

# Model Training
BACKTEST_START_DATE=2023-01-01
BACKTEST_END_DATE=2024-01-01
```

## Training the Model

### Step 1: Fetch Historical Data

```python
df = data_fetcher.get_historical_data(
    'XAUUSD',
    'H1',  # 1-hour timeframe recommended
    '2023-01-01',
    '2024-01-01'
)
```

### Step 2: Calculate Indicators

```python
ta = TechnicalAnalysis(df)
ta.calculate_moving_averages()
ta.calculate_rsi()
ta.calculate_bollinger_bands()
ta.calculate_atr()
ta.calculate_stochastic()
ta.calculate_volume_indicators()
```

### Step 3: Prepare Data

```python
X, y = model.prepare_data(
    ta.df,
    lookback=20,           # Feature sequence length
    prediction_horizon=1   # Predict 1 candle ahead
)
```

### Step 4: Train Model

```python
metrics = model.train(X, y, test_size=0.2)

print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"Precision: {metrics['precision_weighted']:.4f}")
print(f"Recall: {metrics['recall_weighted']:.4f}")
```

### Step 5: Save Model

```python
model.save_model('models/professional_xgboost.pkl')
```

## Feature Importance

Top 15 most important features (after training):

```python
top_features = model.get_top_features(15)
for feature, importance in top_features:
    print(f"{feature}: {importance:.4f}")
```

Typically:
- EMA distance and crossing features (20-25% importance)
- RSI levels and momentum (15-20%)
- ATR ratio and volatility (10-15%)
- Candle body and wick ratios (10-12%)
- MACD and momentum (8-10%)
- Pattern features (5-8%)

## Performance Metrics

### Model Validation

```python
# Get summary
summary = model.get_model_summary()
print(f"Trained: {summary['is_trained']}")
print(f"Features: {summary['num_features']}")
print(f"Accuracy: {summary['training_metrics']['accuracy']:.4f}")
print(f"Top Features: {summary['top_features']}")
```

### Backtesting

```python
backtester = Backtester(config)
results = backtester.run(
    df_with_signals=analysis_results,
    starting_capital=10000,
    risk_percent=1.0
)

print(f"Total Return: {results['total_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Win Rate: {results['win_rate']:.2%}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
```

## Integration with Main System

### In main_refactored.py

```python
# Initialize professional model
from src.professional_xgboost_model import ProfessionalXGBoostModel
from src.professional_trading_system import ProfessionalTradingSystem

xgb_model = ProfessionalXGBoostModel(Config)
trading_system = ProfessionalTradingSystem(
    Config, data_fetcher, xgb_model, risk_manager
)

# Main loop
while True:
    # Fetch latest data
    df = data_fetcher.get_historical_data('XAUUSD', 'H1', lookback=100)
    
    # Calculate indicators
    ta = TechnicalAnalysis(df)
    ta.calculate_all_indicators()
    
    # Analyze entry
    analysis = trading_system.analyze_entry(ta.df)
    
    if analysis and analysis['entry_signal'].value > 0:
        # Execute trade
        trading_engine.open_position(
            symbol='XAUUSD',
            type=analysis['entry_signal'],
            volume=analysis['position_size'],
            sl=analysis['stops']['stop_loss'],
            tp=analysis['stops']['take_profit'],
            reason=f"XGBoost: {analysis['ai_signal']['signal_name']}"
        )
```

## Best Practices

### 1. Model Training
- Use at least 1000 samples for training
- Recommend 1-hour or 4-hour timeframes (higher sample frequency)
- Retrain weekly or after 100+ new trades
- Use stratified split to maintain class distribution

### 2. Feature Engineering
- All features are normalized/scaled
- Missing values filled with forward/backward fill
- No data leakage (future data not used)

### 3. Confidence Thresholds
- Conservative: 0.70+ (fewer trades, higher win rate)
- Moderate: 0.65-0.70 (balanced)
- Aggressive: 0.60-0.65 (more trades, lower win rate)

### 4. Risk Management
- Always enforce 1% risk maximum per trade
- Never override RR ratio requirements
- Daily loss limits prevent over-leverage
- ATR-based stops adapt to volatility

### 5. Market Conditions
- Trending markets: Use all signals
- Ranging markets: Require higher confidence
- High volatility: Widen stops using ATR
- Low volatility: Tighten stops, require tight RR

## Troubleshooting

### Low Accuracy
- Check data quality (missing values, outliers)
- Verify indicator calculations
- Try different lookback periods
- Adjust confidence threshold

### No Trades Generated
- Lower confidence threshold (0.60 instead of 0.70)
- Check trend confirmation settings
- Verify pattern detection logic
- Review ATR-based stop calculations

### High Drawdown
- Increase confidence threshold
- Increase min RR ratio requirement
- Reduce position sizing
- Add market condition filters

## References

- XGBoost Parameters: https://xgboost.readthedocs.io
- XAUUSD Trading: Best practices for gold/USD trading
- Risk Management: Kelly Criterion, Expected Value optimization
- Machine Learning: Classification metrics, cross-validation

## Support

For issues or questions:
1. Check logs in `logs/trading.log`
2. Review feature importance with `model.get_top_features()`
3. Validate model with `model.get_model_summary()`
4. Run backtests for historical validation

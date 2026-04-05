# AI System Improvements - Complete Guide

## Overview

The AI system has been enhanced with professional-grade features for automatic model management, advanced preprocessing, comprehensive logging, and performance evaluation.

## 🎯 New Components

### 1. Model Manager (`src/model_manager.py`)

Central hub for all model management tasks.

#### ModelPreprocessor
Advanced feature preprocessing with multiple scaling methods:

```python
from src.model_manager import ModelPreprocessor, ScalingMethod

# Create preprocessor
preprocessor = ModelPreprocessor(ScalingMethod.ROBUST)

# Fit to training data
preprocessor.fit(X_train)

# Transform data
X_scaled = preprocessor.transform(X_test)

# Or fit and transform in one step
X_scaled = preprocessor.fit_transform(X_data)
```

**Scaling Methods:**
- **STANDARD**: StandardScaler (assumes normal distribution)
- **MINMAX**: MinMaxScaler (scales to [0, 1] range)
- **ROBUST**: RobustScaler (robust to outliers, default)

**Features:**
- Handles NaN and infinite values
- Tracks feature statistics (mean, std, min, max)
- Inverse transformation support

#### ModelPerformance
Real-time performance tracking with rolling window metrics:

```python
from src.model_manager import ModelPerformance

performance = ModelPerformance(window_size=100)

# Update with each prediction
performance.update(
    prediction=2,        # Model's prediction
    actual=2,           # Actual label
    confidence=0.78,    # Prediction confidence
    timestamp=datetime.now()
)

# Get metrics
metrics = performance.get_metrics()
# Returns: accuracy, precision, recall, f1, per-class metrics, confidence distribution
```

**Metrics Tracked:**
- Overall accuracy, precision, recall, F1 score
- Per-class metrics (SELL, HOLD, BUY)
- Confidence distribution (high >70%, medium 50-70%, low <50%)
- Total and per-class prediction counts

#### PredictionLogger
Comprehensive prediction logging to CSV for analysis:

```python
from src.model_manager import PredictionLogger

logger = PredictionLogger(log_dir='logs/')

# Log prediction with context
logger.log_prediction({
    'timestamp': datetime.now().isoformat(),
    'prediction': 2,          # BUY
    'signal': 'STRONG_BUY',
    'confidence': 0.82,
    'probabilities': {'SELL': 0.05, 'HOLD': 0.13, 'BUY': 0.82},
    'price': 2330.50,
    'atr': 15.2,
    'trend': 'UPTREND',
    'market_condition': 'TRENDING',
    'actual': 2,             # Optional: actual outcome
    'trade_executed': True,
    'trade_result': 25.5     # Optional: profit/loss
})

# Read recent predictions
recent = logger.get_recent_predictions(hours=24)
```

**Log File Structure:**
```
predictions_2026-04-05.csv
- Timestamp
- Prediction & Signal
- Confidence & Probabilities
- Market Context (Price, ATR, Trend)
- Actual Outcome (if available)
- Trade Results (if applicable)
```

#### ModelManager
Orchestrates all model operations:

```python
from src.model_manager import ModelManager, RetariningSchedule

manager = ModelManager(
    config=config,
    model=xgboost_model,
    schedule=RetariningSchedule.WEEKLY  # Retrain weekly
)

# Predict with logging
prediction = manager.predict_with_logging(
    features=X[-1:],
    context={
        'price': 2330.50,
        'atr': 15.2,
        'trend': 'UPTREND',
        'market_condition': 'TRENDING'
    }
)

# Get performance summary
metrics = manager.get_performance_summary()

# Manual retraining
metrics = manager.retrain_model(X_train, y_train, force=True)

# Get model status
status = manager.get_model_status()
```

**Key Features:**
- Automatic preprocessing with feature scaling
- Prediction logging with context
- Performance tracking with rolling metrics
- Model versioning with rollback support
- Performance report generation

### 2. Retraining Scheduler (`src/retraining_scheduler.py`)

Automatic background model retraining at configured intervals:

```python
from src.retraining_scheduler import RetrainingScheduler

scheduler = RetrainingScheduler(
    model_manager=manager,
    data_fetcher=data_fetcher,
    config=config
)

# Start scheduler (runs in background)
scheduler.start()

# Check status
status = scheduler.get_status()
# {
#   'is_running': True,
#   'current_status': 'idle',
#   'next_scheduled_retrain': '2026-04-12T15:30:00',
#   'last_successful_retrain': '2026-04-05T15:30:00'
# }

# Force immediate retraining
scheduler.force_retrain()

# Wait for retraining to complete
scheduler.wait_for_completion(timeout=3600)

# Stop scheduler
scheduler.stop()
```

**Retraining Schedules:**
- DAILY: Every 24 hours
- WEEKLY: Every 7 days (default)
- BIWEEKLY: Every 14 days
- MONTHLY: Every 30 days
- MANUAL: Only on demand

**Automatic Process:**
1. Fetch last 30 days of historical data
2. Calculate technical indicators
3. Prepare training data
4. Train model with preprocessed features
5. Evaluate and log metrics
6. Save model version
7. Track performance

---

## 📊 Performance Evaluation

### Metrics Provided

#### Classification Metrics
- **Accuracy**: Overall prediction correctness
  ```
  Accuracy = Correct Predictions / Total Predictions
  ```

- **Precision**: How many predicted BUY are actually BUY
  ```
  Precision = True Positives / (True Positives + False Positives)
  ```

- **Recall**: How many actual BUY did model predict
  ```
  Recall = True Positives / (True Positives + False Negatives)
  ```

- **F1 Score**: Harmonic mean of precision and recall
  ```
  F1 = 2 * (Precision * Recall) / (Precision + Recall)
  ```

#### Per-Class Metrics
- Separate precision, recall, and counts for each class:
  - SELL (0): Selling signals
  - HOLD (1): No-trade signals
  - BUY (2): Buying signals

#### Confidence Distribution
- **High Confidence** (>70%): Most reliable predictions
- **Medium Confidence** (50-70%): Moderate reliability
- **Low Confidence** (<50%): Less reliable predictions

### Getting Performance Metrics

```python
# Get real-time metrics
metrics = manager.get_performance_summary()

print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"Precision: {metrics['precision']:.4f}")
print(f"Recall: {metrics['recall']:.4f}")
print(f"F1 Score: {metrics['f1_score']:.4f}")

# Per-class metrics
for class_id, class_metrics in metrics['per_class'].items():
    print(f"Class {class_id}:")
    print(f"  Precision: {class_metrics['precision']:.4f}")
    print(f"  Recall: {class_metrics['recall']:.4f}")
    print(f"  Count: {class_metrics['count']}")

# Confidence distribution
print(f"High Confidence: {metrics['high_confidence_count']}")
print(f"Medium Confidence: {metrics['medium_confidence_count']}")
print(f"Low Confidence: {metrics['low_confidence_count']}")
```

---

## 🔄 Feature Preprocessing

### Why Preprocessing Matters

Raw features have different scales and distributions:
- EMA values: 2300-2400
- RSI values: 0-100
- ATR values: 5-50
- ROC values: -10 to +10

XGBoost trains better with normalized features!

### Preprocessing Pipeline

```python
# 1. Create preprocessor
preprocessor = ModelPreprocessor(ScalingMethod.ROBUST)

# 2. Fit on training data
preprocessor.fit(X_train)  # Learn statistics

# 3. Transform for training
X_train_scaled = preprocessor.transform(X_train)

# 4. Transform for testing
X_test_scaled = preprocessor.transform(X_test)

# 5. Transform for prediction
X_new_scaled = preprocessor.transform(X_new)

# 6. Optional: inverse transform
X_original = preprocessor.inverse_transform(X_scaled)
```

### Scaling Method Comparison

| Method | Best For | Characteristics |
|--------|----------|---|
| STANDARD | Normal distributions | Mean=0, Std=1, sensitive to outliers |
| MINMAX | Bounded ranges | Values in [0, 1], preserves 0, affected by outliers |
| ROBUST | Outlier-heavy data | Median/IQR based, ignores outliers, **recommended** |

---

## 📝 Prediction Logging

### Log Structure

Each prediction is logged with full context:

```csv
timestamp,prediction,signal,confidence,probabilities_sell,probabilities_hold,probabilities_buy,price,atr,trend,market_condition,actual,trade_executed,trade_result
2026-04-05T15:30:00,2,STRONG_BUY,0.82,0.05,0.13,0.82,2330.50,15.2,UPTREND,TRENDING,2,True,25.5
2026-04-05T15:35:00,1,HOLD,0.45,0.35,0.48,0.17,2331.20,15.1,UPTREND,TRENDING,,False,
2026-04-05T15:40:00,0,SELL,0.71,0.71,0.21,0.08,2330.80,15.3,DOWNTREND,RANGING,0,True,-12.3
```

### Analysis Examples

```python
# Load recent predictions
recent = logger.get_recent_predictions(hours=24)

# Analyze by signal
buy_signals = recent[recent['signal'].str.contains('BUY')]
print(f"BUY signals: {len(buy_signals)}")
print(f"Win rate: {(buy_signals['trade_result'] > 0).sum() / len(buy_signals):.2%}")

# Analyze by confidence
high_conf = recent[recent['confidence'] > 0.7]
print(f"High confidence trades: {len(high_conf)}")
print(f"Avg profit: ${high_conf['trade_result'].mean():.2f}")

# Analyze market conditions
trending = recent[recent['market_condition'] == 'TRENDING']
print(f"Trending market trades: {(trending['trade_result'] > 0).sum()} wins")
```

---

## ⚙️ Configuration

Add to `.env`:

```env
# Model Manager
MODEL_PREPROCESSING=robust           # Feature scaling: standard, minmax, robust
RETRAINING_SCHEDULE=weekly           # daily, weekly, biweekly, monthly

# Prediction Logging
PREDICTION_LOG_DIR=logs/predictions  # Directory for prediction logs

# Performance Tracking
PERFORMANCE_WINDOW_SIZE=100          # Predictions to track for rolling metrics
EXPORT_PERFORMANCE_REPORTS=true      # Auto-export performance reports
```

---

## 🚀 Integration with Trading System

### Step 1: Initialize Components

```python
from src.professional_xgboost_model import ProfessionalXGBoostModel
from src.model_manager import ModelManager, RetariningSchedule
from src.retraining_scheduler import RetrainingScheduler

# Initialize model
model = ProfessionalXGBoostModel(config)

# Initialize manager
manager = ModelManager(
    config=config,
    model=model,
    schedule=RetariningSchedule.WEEKLY
)

# Initialize scheduler
scheduler = RetrainingScheduler(manager, data_fetcher, config)
scheduler.start()  # Start background retraining
```

### Step 2: Use in Trading Loop

```python
# Predict with logging
prediction = manager.predict_with_logging(
    features=X[-1:],
    context={
        'price': current_price,
        'atr': atr_value,
        'trend': trend_direction,
        'market_condition': market_type
    }
)

# Check if trade should be executed
if prediction['meets_threshold']:
    # Execute trade
    position = trading_engine.open_position(...)

# Later: Update with actual result
manager.prediction_logger.log_prediction({
    **prediction,
    'actual': 2 if trade_won else 0,
    'trade_executed': True,
    'trade_result': profit_loss
})

# Update performance
manager.performance.update(
    prediction['prediction'],
    actual_label,
    prediction['confidence']
)
```

### Step 3: Monitor Performance

```python
# Get daily summary
metrics = manager.get_performance_summary()

# Export report
report_path = manager.export_performance_report()

# Check scheduler status
status = scheduler.get_status()
if status['current_status'] == 'failed':
    logger.error(f"Retraining failed: {status['recent_errors']}")
```

---

## 📈 Performance Monitoring

### Daily Metrics Report

```
================================================================================
MODEL PERFORMANCE SUMMARY
================================================================================
Accuracy: 0.6234
Precision: 0.6178
Recall: 0.6234
F1 Score: 0.6189
Total Predictions: 156
Correct Predictions: 97
Avg Confidence: 62.34%
================================================================================
```

### Weekly Analysis

```python
# Analyze weekly performance
metrics = manager.get_performance_summary()

# Check accuracy by confidence level
high_conf_acc = (
    len(manager.performance.predictions) 
    / len(manager.performance.actuals)
    if len(manager.performance.confidences) > 0 
    else 0
)

# Check trend in accuracy
recent_metrics = metrics['per_class']
sell_precision = recent_metrics[0].get('precision', 0)
hold_precision = recent_metrics[1].get('precision', 0)
buy_precision = recent_metrics[2].get('precision', 0)
```

---

## 🔧 Best Practices

### Preprocessing
1. **Always fit on training data only** - prevent data leakage
2. **Use same preprocessor for all splits** - consistency
3. **Handle outliers** - use ROBUST scaler for XAUUSD
4. **Monitor feature stats** - detect anomalies

### Retraining
1. **Schedule weekly** - balance freshness vs stability
2. **Use 30-day window** - capture recent patterns
3. **Monitor retraining success** - log errors
4. **Keep 5 model versions** - enable quick rollback

### Logging
1. **Log every prediction** - enable analysis
2. **Include context** - price, trend, volatility
3. **Update with results** - closed-loop learning
4. **Analyze logs daily** - detect issues early

### Evaluation
1. **Track 100+ predictions** - reliable metrics
2. **Monitor per-class metrics** - identify weak classes
3. **Analyze by confidence** - calibrate thresholds
4. **Review confusion matrix** - detect patterns

---

## 📚 Complete Example

```python
from config.config import Config
from src.professional_xgboost_model import ProfessionalXGBoostModel
from src.model_manager import ModelManager, RetariningSchedule
from src.retraining_scheduler import RetrainingScheduler
from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalysis
import pandas as pd

# 1. SETUP
config = Config()
config.setup_directories()

model = ProfessionalXGBoostModel(config)
manager = ModelManager(config, model, RetariningSchedule.WEEKLY)
scheduler = RetrainingScheduler(manager, data_fetcher, config)

# 2. INITIAL TRAINING
df = data_fetcher.get_historical_data(
    'XAUUSD', 'H1', '2023-01-01', '2024-01-01'
)
ta = TechnicalAnalysis(df)
ta.calculate_all_indicators()

X, y = model.prepare_data(ta.df)
manager.retrain_model(X, y, force=True)

# 3. START BACKGROUND RETRAINING
scheduler.start()

# 4. MAIN TRADING LOOP
while True:
    # Get latest data
    df = data_fetcher.get_latest_data('XAUUSD', lookback=100)
    
    # Calculate indicators
    ta.calculate_all_indicators()
    
    # Predict with logging
    prediction = manager.predict_with_logging(
        features=ta.df.iloc[-1:],
        context={
            'price': df['Close'].iloc[-1],
            'atr': ta.df['ATR'].iloc[-1],
            'trend': 'UPTREND' if ta.df['EMA_FAST'].iloc[-1] > ta.df['EMA_SLOW'].iloc[-1] else 'DOWNTREND'
        }
    )
    
    # Execute if signal
    if prediction['meets_threshold']:
        position = trading_engine.open_position(...)
    
    # Monitor performance
    if datetime.now().hour == 0:  # Daily
        metrics = manager.get_performance_summary()
        print(f"Daily Accuracy: {metrics['accuracy']:.4f}")
        
        manager.export_performance_report()
    
    time.sleep(300)  # Wait 5 minutes

# 5. CLEANUP
scheduler.stop()
```

---

## 🎯 Summary

Your AI system now has:
- ✅ **Automatic retraining** on weekly schedule
- ✅ **Advanced preprocessing** with feature scaling
- ✅ **Comprehensive logging** of all predictions
- ✅ **Performance evaluation** with detailed metrics
- ✅ **Model versioning** with rollback capability
- ✅ **Background scheduler** for hands-off operation

This creates a **self-improving trading system** that learns from market data! 🚀

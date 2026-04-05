# Advanced Backtesting System Guide

## Overview

The Advanced Backtester provides professional-grade backtesting with comprehensive metrics, automatic parameter optimization, and beautiful visualization reports.

---

## 🎯 Key Features

### 1. Comprehensive Performance Metrics

**Profitability Metrics:**
- Total Return (ROI %)
- Net Profit ($)
- Return on Risk

**Risk Metrics:**
- Maximum Drawdown (%)
- Drawdown Duration (days)
- Current Drawdown (%)

**Ratio Metrics:**
- Sharpe Ratio: Risk-adjusted returns
- Sortino Ratio: Downside risk adjusted
- Calmar Ratio: Return / Max Drawdown

**Trade Metrics:**
- Win Rate (%)
- Profit Factor (Gross Profit / Gross Loss)
- Average Win ($)
- Average Loss ($)
- Trade Expectancy (average profit per trade)
- Total/Winning/Losing Trades

### 2. Automated Visualizations

**Charts Generated:**
- Equity Curve: Account value over time
- Drawdown Chart: Peak-to-trough declines
- Trade Distribution: Win/loss histogram and pie chart

**Output Formats:**
- PNG images (100 DPI, high quality)
- Embedded in HTML reports
- Separate files for detailed analysis

### 3. Parameter Optimization

**Grid Search Engine:**
- Test multiple parameter combinations
- Automatic scoring (weighted metrics)
- Ranking by performance

**Optimization Metrics:**
- Sharpe Ratio (40% weight)
- ROI (30% weight)
- Win Rate (20% weight)
- Profit Factor (10% weight)

**Example:**
```python
results = optimizer.optimize_parameters(
    df, model, ta_func,
    param_ranges={
        'confidence_threshold': [0.60, 0.65, 0.70, 0.75],
        'position_size': [0.5, 1.0, 1.5, 2.0],
        'stop_loss_pct': [0.5, 1.0, 1.5, 2.0]
    }
)
# Tests 4 × 3 × 3 = 36 combinations
```

### 4. Professional HTML Reports

**Includes:**
- Summary metrics dashboard
- Trade statistics table
- Embedded charts (equity, drawdown, distribution)
- Recent trades detail
- Professional styling

---

## 📊 Performance Metrics Explained

### Sharpe Ratio
Measures risk-adjusted returns. Higher is better.
```
Sharpe = (Annual Return - Risk-Free Rate) / Annual Volatility
Typical: 0-2 (poor), 2-3 (good), >3 (excellent)
```

### Sortino Ratio
Like Sharpe but only penalizes downside volatility.
```
Sortino = Annual Return / Downside Volatility
Better than Sharpe for strategies with asymmetric risk
```

### Calmar Ratio
Return relative to maximum drawdown.
```
Calmar = Annual Return / Max Drawdown
Measures efficiency of returns relative to risk taken
```

### Profit Factor
Gross profit divided by gross loss.
```
Profit Factor = Sum of Wins / Sum of Losses
> 2.0 is excellent, > 1.5 is good, < 1.0 is losing
```

### Drawdown
Peak-to-trough decline from a previous peak.
```
Max Drawdown = (Trough - Peak) / Peak
Important measure of downside risk
```

---

## 🚀 Usage Examples

### Basic Backtesting

```python
from src.advanced_backtester import AdvancedBacktester

# Initialize
backtester = AdvancedBacktester(config, initial_capital=10000)

# Run backtest
metrics = backtester.run_backtest(df, ml_model, ta_func)

# Print results
print(f"ROI: {metrics['roi']:.2f}%")
print(f"Win Rate: {metrics['win_rate']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")

# Export HTML report
report_path = backtester.export_html_report('backtest_report.html')

# Export trades to CSV
trades_path = backtester.export_csv_trades('trades.csv')
```

### Parameter Optimization

```python
from src.advanced_backtester import AdvancedBacktester

backtester = AdvancedBacktester(config)

# Define parameters to optimize
param_ranges = {
    'confidence_threshold': [0.60, 0.65, 0.70],
    'position_size_pct': [0.5, 1.0, 1.5],
    'take_profit_pct': [1.0, 1.5, 2.0]
}

# Optimize
results = backtester.optimizer.optimize_parameters(
    df, ml_model, ta_func, param_ranges
)

# Get best parameters
best_params = results['best_parameters']
best_score = results['best_score']

print(f"Best Parameters: {best_params}")
print(f"Best Score: {best_score:.4f}")

# View all results
summary = backtester.optimizer.get_optimization_summary()
print(summary.head(10))
```

### Accessing All Metrics

```python
# Get all metrics at once
all_metrics = backtester.metrics.get_all_metrics()

# Profitability
print(f"Total Return: {all_metrics['total_return']:.4f}")
print(f"ROI: {all_metrics['roi']:.2f}%")
print(f"Net Profit: ${all_metrics['net_profit']:,.2f}")

# Risk
print(f"Max Drawdown: {all_metrics['max_drawdown_pct']:.2f}%")
print(f"Drawdown Duration: {all_metrics['max_drawdown_duration']} days")

# Ratios
print(f"Sharpe Ratio: {all_metrics['sharpe_ratio']:.4f}")
print(f"Sortino Ratio: {all_metrics['sortino_ratio']:.4f}")
print(f"Calmar Ratio: {all_metrics['calmar_ratio']:.4f}")

# Trade stats
print(f"Total Trades: {all_metrics['total_trades']}")
print(f"Win Rate: {all_metrics['win_rate']:.2%}")
print(f"Profit Factor: {all_metrics['profit_factor']:.2f}")
print(f"Average Trade: ${all_metrics['expectancy']:,.2f}")
```

---

## 📈 PerformanceMetrics Class

Calculate metrics on any backtest data:

```python
from src.advanced_backtester import PerformanceMetrics

# Your trades and equity curve
trades = [
    {'pnl': 100, 'type': 'BUY'},
    {'pnl': -50, 'type': 'BUY'},
    {'pnl': 150, 'type': 'SELL'},
]
equity_curve = [10000, 10100, 10050, 10200]

# Calculate metrics
metrics = PerformanceMetrics(trades, equity_curve, initial_capital=10000)

# Get all metrics
all_metrics = metrics.get_all_metrics()
```

---

## 🎨 BacktestVisualizer Class

Create publication-quality charts:

```python
from src.advanced_backtester import BacktestVisualizer

visualizer = BacktestVisualizer(output_dir='reports/')

# Plot equity curve
equity_path = visualizer.plot_equity_curve(
    equity_curve=equity_values,
    dates=date_list,
    filename='equity_curve.png'
)

# Plot drawdown
drawdown_path = visualizer.plot_drawdown(
    equity_curve=equity_values,
    dates=date_list,
    filename='drawdown.png'
)

# Plot trade distribution
dist_path = visualizer.plot_distribution(
    trades=trade_list,
    filename='distribution.png'
)
```

**Chart Features:**
- Professional styling
- Clear labels and legends
- Grid lines for readability
- Multiple file format support

---

## 🔧 ParameterOptimizer Class

Automatically find optimal parameters:

```python
from src.advanced_backtester import ParameterOptimizer

optimizer = ParameterOptimizer(backtester, config)

# Run optimization
results = optimizer.optimize_parameters(
    df, ml_model, ta_func,
    param_ranges={
        'confidence': [0.60, 0.65, 0.70],
        'position_size': [0.5, 1.0, 1.5]
    }
)

# Results structure
{
    'best_parameters': {...},
    'best_score': 2.345,
    'best_result': {...},
    'all_results': [...]
}

# Get summary DataFrame
df_results = optimizer.get_optimization_summary()
print(df_results[['parameters', 'roi', 'sharpe_ratio', 'win_rate', 'score']])
```

**Optimization Scoring:**
- **40%**: Sharpe Ratio (risk-adjusted returns)
- **30%**: ROI (absolute profitability)
- **20%**: Win Rate (consistency)
- **10%**: Profit Factor (trade quality)

---

## 📋 HTML Report Contents

Generated report includes:

**Section 1: Performance Summary**
- ROI, Net Profit, Max Drawdown
- Sharpe, Sortino, Calmar ratios
- Win Rate, Profit Factor
- Average Trade metrics

**Section 2: Trade Statistics**
- Total, winning, losing trade counts
- Average win/loss amounts
- Trade consistency metrics

**Section 3: Charts**
- Equity curve over time
- Drawdown chart
- Win/loss distribution histogram
- Win rate pie chart

**Section 4: Recent Trades Table**
- Entry/exit prices
- P&L and P&L %
- Trade type (BUY/SELL)
- Bars held and exit reason

---

## 🎯 Best Practices

### 1. Realistic Backtesting
- Use adequate historical data (6-12 months minimum)
- Include slippage and commissions
- Use realistic position sizes
- Account for gaps and limit moves

### 2. Parameter Optimization
- Use walk-forward optimization
- Test on out-of-sample data
- Avoid over-optimization
- Start with broad ranges, narrow down

### 3. Metric Interpretation
- **Sharpe > 2**: Good risk-adjusted returns
- **Win Rate > 55%**: Profitable on average
- **Profit Factor > 1.5**: Quality trade selection
- **Max Drawdown < 20%**: Acceptable risk level
- **Calmar > 0.5**: Good risk efficiency

### 4. Report Generation
- Generate reports regularly
- Compare improvements over time
- Share with team for review
- Archive for historical analysis

---

## 📊 Example Backtest Report

```
================================================================================
BACKTEST REPORT
Generated: 2026-04-05 15:30:00

PERFORMANCE METRICS
- Total Return: 25.50%
- Max Drawdown: -12.30%
- Sharpe Ratio: 1.85
- Profit Factor: 2.34
- Win Rate: 62.50%

TRADE STATISTICS
- Total Trades: 48
- Winning Trades: 30
- Losing Trades: 18
- Average Win: $125.50
- Average Loss: -$67.30

EQUITY CURVE
[Chart showing account growth from $10k to $12.55k]

RECENT TRADES
Entry Price    Exit Price    P&L      P&L %    Type    Bars    Reason
2330.50        2338.20       767.70   0.33%    BUY     24      TP
2335.80        2332.40       -340.00  -0.15%   SELL    18      SL
2337.50        2345.10       760.00   0.32%    BUY     15      TP
...
================================================================================
```

---

## 🚀 Integration with Trading System

```python
from src.advanced_backtester import AdvancedBacktester
from src.professional_xgboost_model import ProfessionalXGBoostModel

# 1. TRAINING & BACKTESTING
model = ProfessionalXGBoostModel(config)
X, y = model.prepare_data(df_train)
model.train(X, y)

backtester = AdvancedBacktester(config)
metrics = backtester.run_backtest(df_test, model, ta_func)

# 2. PARAMETER OPTIMIZATION
if metrics['sharpe_ratio'] < 1.5:
    print("Optimizing parameters...")
    results = backtester.optimizer.optimize_parameters(
        df_test, model, ta_func,
        param_ranges={
            'confidence_threshold': [0.60, 0.65, 0.70],
            'stop_loss_pct': [0.5, 1.0, 1.5]
        }
    )
    best_params = results['best_parameters']

# 3. GENERATE REPORT
backtester.export_html_report('results/backtest_final.html')
backtester.export_csv_trades('results/trades.csv')

# 4. REVIEW METRICS
print(f"Final ROI: {metrics['roi']:.2f}%")
print(f"Sharpe: {metrics['sharpe_ratio']:.4f}")
print(f"Win Rate: {metrics['win_rate']:.2%}")
```

---

## ✨ Advanced Features

### Custom Scoring
Modify optimizer scoring weights:
```python
def custom_score(metrics):
    return (
        metrics['sharpe_ratio'] * 0.5 +      # 50% - Sharpe
        metrics['roi'] / 100 * 0.3 +          # 30% - ROI
        metrics['win_rate'] * 0.2              # 20% - Win Rate
    )
```

### Walk-Forward Analysis
Test on multiple time periods:
```python
# Split data into periods
periods = [
    (df['2023-01-01':'2023-06-30'], 'H1 2023'),
    (df['2023-07-01':'2023-12-31'], 'H2 2023'),
    (df['2024-01-01':'2024-06-30'], 'H1 2024'),
]

results = []
for df_period, name in periods:
    metrics = backtester.run_backtest(df_period, model, ta_func)
    results.append((name, metrics))
```

### Monte Carlo Analysis
Test parameter sensitivity:
```python
import numpy as np

best_params = results['best_parameters']

# Vary parameters by ±10%
param_variations = {
    param: [val * 0.9, val, val * 1.1]
    for param, val in best_params.items()
}

# Run optimization with variations
variation_results = optimizer.optimize_parameters(
    df, model, ta_func, param_variations
)
```

---

## 📚 Summary

Your backtesting system now provides:
- ✅ **Comprehensive Metrics**: 15+ performance indicators
- ✅ **Professional Visualizations**: Equity curves, drawdown, distributions
- ✅ **Automatic Optimization**: Grid search with weighted scoring
- ✅ **Beautiful Reports**: HTML with embedded charts
- ✅ **CSV Export**: Detailed trade data for analysis

This enables **data-driven strategy development** and **confident parameter selection**! 🎯📈

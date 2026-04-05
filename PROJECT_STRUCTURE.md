# Project Structure Overview

Complete file structure and description of the AI Trading Bot for XAUUSD.

## Directory Tree

```
xau-trading-bot/
├── config/                      # Configuration management
│   ├── __init__.py
│   └── config.py               # Configuration loader, validation, paths
│
├── data/                        # Market data storage (auto-created)
│   └── *.csv                   # Historical data and backtest results
│
├── logs/                        # Log files (auto-created)
│   └── trading_bot.log         # Main trading log with rotation
│
├── models/                      # Trained ML models (auto-created)
│   └── model_*.pkl             # Saved model files
│
├── src/                         # Source code
│   ├── __init__.py
│   ├── backtester.py           # Backtesting engine
│   ├── data_fetcher.py         # MetaTrader5 data retrieval
│   ├── logger.py               # Logging setup
│   ├── ml_model.py             # ML model (XGBoost/sklearn)
│   ├── risk_manager.py         # Risk management logic
│   ├── technical_analysis.py   # Technical indicators (10+)
│   ├── telegram_notifier.py    # Telegram notifications
│   └── trading_engine.py       # Trade execution engine
│
├── tests/                       # Unit tests
│   ├── __init__.py
│   ├── test_risk_manager.py    # Risk manager tests
│   └── test_technical_analysis.py  # Technical analysis tests
│
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── main.py                      # Application entry point
├── Makefile                     # Convenience commands
├── PROJECT_STRUCTURE.md         # This file
├── QUICKSTART.md                # Quick start guide
├── README.md                    # Full documentation
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
└── setup.py                     # Package installation script
```

## File Descriptions

### Core Application Files

#### `main.py`
- Entry point for the entire application
- Handles initialization and cleanup
- Manages trading loop
- Supports commands: `python main.py` (live) or `python main.py backtest`
- Signal handling for graceful shutdown

#### `config/config.py`
- Loads environment variables from .env
- Validates all configuration parameters
- Defines all project paths (data, logs, models)
- Creates required directories
- Provides centralized configuration access

### Data & Fetching

#### `src/data_fetcher.py`
- **Class**: `DataFetcher`
- Connects to MetaTrader5
- Fetches OHLC data (current and historical)
- Manages data persistence (CSV export/import)
- Gets symbol information
- ~450 lines, production-ready

### Technical Analysis

#### `src/technical_analysis.py`
- **Class**: `TechnicalAnalysis`
- Calculates 10+ technical indicators:
  - Moving Averages (SMA, EMA)
  - MACD
  - RSI
  - Bollinger Bands
  - ATR
  - Stochastic
  - ADX
  - Volume indicators (OBV, MFI)
  - Price patterns
- Supports method chaining
- Identifies trend direction
- Calculates signal strength
- Extracts ML features
- ~400 lines

### Machine Learning

#### `src/ml_model.py`
- **Class**: `MLModel`
- Supports two models:
  - XGBoost (primary)
  - scikit-learn RandomForest (fallback)
- Features:
  - Data preparation with lookback windows
  - Model training with validation split
  - Prediction with confidence scores
  - Feature importance analysis
  - Model persistence (save/load)
- ~350 lines

### Risk Management

#### `src/risk_manager.py`
- **Class**: `RiskManager`
- Key features:
  - Trade opening validation
  - Stop loss/take profit calculation
  - Position tracking
  - Daily loss tracking
  - Risk metrics calculation
  - Dynamic position sizing
  - Price level validation
  - Unrealized P&L calculation
- ~300 lines

### Trading Engine

#### `src/trading_engine.py`
- **Class**: `TradingEngine`
- Orchestrates trading decisions
- Features:
  - Signal generation logic
  - Trade opening/closing execution
  - SL/TP management
  - Position monitoring
  - Account info retrieval
  - Trading cycle execution
- ~350 lines

### Notifications

#### `src/telegram_notifier.py`
- **Class**: `TelegramNotifier`
- Sends notifications:
  - Trade signals (open/close)
  - Daily reports
  - Error alerts
  - System status updates
- Graceful fallback if disabled
- ~250 lines

### Backtesting

#### `src/backtester.py`
- **Class**: `Backtester`
- Full backtest simulation
- Calculates metrics:
  - Win rate
  - ROI
  - Profit factor
  - Maximum drawdown
  - Sharpe ratio
- Generates detailed reports
- ~350 lines

### Logging

#### `src/logger.py`
- Sets up Python logging
- File handler with rotation:
  - 10MB max file size
  - 5 backup files
  - Automatic rolling
- Console output
- Timestamped messages

### Tests

#### `tests/test_risk_manager.py`
- Unit tests for RiskManager
- ~100 lines
- 10+ test cases

#### `tests/test_technical_analysis.py`
- Unit tests for TechnicalAnalysis
- ~150 lines
- 10+ test cases

### Configuration & Dependencies

#### `.env.example`
- Template for environment variables
- All configurable parameters documented
- Ready to copy and modify

#### `requirements.txt`
- Production dependencies only
- Pinned versions for stability
- Core libraries:
  - MetaTrader5
  - pandas, numpy
  - scikit-learn, xgboost
  - ta-lib
  - python-telegram-bot
  - python-dotenv

#### `requirements-dev.txt`
- Extends requirements.txt
- Development tools:
  - Testing: pytest, pytest-cov
  - Code quality: black, flake8, pylint, mypy
  - Documentation: sphinx
  - Development: ipython, jupyter

#### `Makefile`
- Convenience commands
- Targets: install, run, backtest, test, lint, format, clean
- Run with: `make help` to see all options

### Documentation

#### `README.md`
- Comprehensive documentation (500+ lines)
- Features overview
- Installation instructions
- Configuration guide
- Architecture explanation
- Troubleshooting
- Performance metrics
- Roadmap

#### `QUICKSTART.md`
- Get started in 5 minutes
- Quick setup steps
- Configuration checklist
- Common commands
- Troubleshooting quick fix

#### `setup.py`
- Python package setup script
- Enable installation with: `pip install .`
- Defines entry points and metadata

## Total Lines of Code

```
config/          ~150 lines
src/             ~2,100 lines (core logic)
tests/           ~250 lines
main.py          ~350 lines
─────────────────────────────
Total:           ~2,850 lines of production code
Plus docs:       ~1,000 lines of documentation
```

## Module Dependencies

```
main.py
├── config.Config
├── src.logger.setup_logging
├── src.data_fetcher.DataFetcher
│   └── MetaTrader5
├── src.technical_analysis.TechnicalAnalysis
│   └── talib
├── src.ml_model.MLModel
│   ├── sklearn
│   └── xgboost
├── src.risk_manager.RiskManager
├── src.trading_engine.TradingEngine
│   └── MetaTrader5
├── src.telegram_notifier.TelegramNotifier
│   └── requests
└── src.backtester.Backtester
    └── pandas, numpy
```

## Data Flow

```
1. Main Loop
   ↓
2. DataFetcher → Fetch OHLC (500 candles)
   ↓
3. TechnicalAnalysis → Calculate 10+ indicators
   ↓
4. MLModel → Generate prediction & confidence
   ↓
5. RiskManager → Check trade constraints
   ↓
6. TradingEngine → Execute decision
   ↓
7. TelegramNotifier → Send alerts
   ↓
8. Logger → Record everything
   ↓
9. Sleep → Wait for next cycle
```

## Configuration Hierarchy

```
Environment Variables (.env)
       ↓
config.py (loaded & validated)
       ↓
Config class (static access)
       ↓
All components (dependency injection)
```

## Testing Strategy

- Unit tests for core logic (risk manager, technical analysis)
- Mock data for isolated testing
- Backtesting as integration test
- Live testing on demo account

## Error Handling

- Try-catch blocks in all critical operations
- Logging of all errors
- Telegram alerts for exceptions
- Graceful degradation (fallback models)
- Signal handlers for shutdown cleanup

## Performance Characteristics

- **Memory**: ~100-200MB (model + data)
- **CPU**: Low (single-threaded)
- **Network**: Minimal (hourly data fetches)
- **Latency**: ~1-5 seconds per trading cycle
- **Scalability**: Single account, easily extendable

## Security Notes

1. .env file is .gitignored
2. Credentials never logged
3. Input validation on configuration
4. No hardcoded passwords
5. API tokens in environment only
6. SQL injection: N/A (no database)
7. XSS: N/A (no web interface)

## Extensibility Points

- Add indicators in `technical_analysis.py`
- Add entry/exit rules in `trading_engine.py`
- Add risk rules in `risk_manager.py`
- Add models in `ml_model.py`
- Add notifications in `telegram_notifier.py`
- Add metrics in `backtester.py`

---

**Total Files**: 22
**Total Directories**: 5 (auto-created: data, logs, models)
**Total Size**: ~50KB (code only, not including dependencies)

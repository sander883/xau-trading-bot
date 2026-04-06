# Dashboard Quick Start Guide

Get your real-time trading dashboard running in under 2 minutes!

## ⚡ 60-Second Setup

### 1. Ensure Dependencies are Installed
```bash
pip install flask flask-cors
```

### 2. Start the Dashboard
```bash
python run_dashboard.py
```

You should see:
```
XAUUSD Trading Bot Dashboard
Starting dashboard on 0.0.0.0:5000
✓ Open your browser and go to: http://localhost:5000/
```

### 3. Open in Browser
```
http://localhost:5000
```

## 🎯 What You'll See

### First Load (Demo Data)
The dashboard starts with **synthetic demo data**:
- Metric cards showing sample values
- Empty equity curve (will populate with real trades)
- Demo trade history
- Sample signals

### Once Your Bot Starts Trading
Real data replaces the demo:
- Live balance & equity updates
- Real trade history appears
- Actual profit/loss metrics
- Real signals from AI model
- Charts update with your data

## 📊 Key Sections

1. **Top Bar** - Bot status & last update time
2. **Metric Cards** - Balance, P&L, win rate, drawdown
3. **Charts** - Equity curve, trade distribution, daily P&L
4. **Open Positions** - Current open trades with P&L
5. **Signals** - Latest AI predictions with confidence
6. **Trade History** - Recent closed trades with details

## 🎮 Features

✅ **Real-Time Updates** - Every 3 seconds
✅ **Dark Theme** - Easy on the eyes for 24/7 monitoring  
✅ **Responsive** - Works on mobile, tablet, desktop
✅ **No Setup** - Just run `python run_dashboard.py`
✅ **No Database** - Reads from bot logs
✅ **Zero Config** - Works out of the box

## 🚀 Common Commands

### Run on Default Port (5000)
```bash
python run_dashboard.py
```

### Run on Custom Port
```bash
python run_dashboard.py --port 8000
```

### Run in Debug Mode (for development)
```bash
python run_dashboard.py --debug
```

### Run on Specific Host
```bash
python run_dashboard.py --host 192.168.1.5 --port 5000
```

### Run Both Bot and Dashboard
```bash
# Terminal 1: Start the trading bot
python main_refactored.py

# Terminal 2: Start the dashboard  
python run_dashboard.py

# Browser: Open http://localhost:5000
```

## 📡 API Endpoints

The dashboard exposes REST APIs you can query:

```bash
# Get current metrics
curl http://localhost:5000/api/metrics | python -m json.tool

# Get recent trades
curl http://localhost:5000/api/trades?limit=10 | python -m json.tool

# Get open positions
curl http://localhost:5000/api/positions | python -m json.tool

# Health check
curl http://localhost:5000/health
```

## 🔧 Customization

### Change Refresh Interval
Edit `dashboard/app.py`:
```python
@app.context_processor
def inject_config():
    return {
        "refresh_interval": 2000  # milliseconds
    }
```

### Change Colors
Edit `dashboard/static/css/style.css`:
```css
--accent-profit: #4ade80;   /* Green */
--accent-loss: #ef4444;     /* Red */
--primary-bg: #1a1a1a;      /* Dark background */
```

### Change Port
Edit `run_dashboard.py` or use `--port` flag:
```bash
python run_dashboard.py --port 3000
```

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
Install Flask:
```bash
pip install flask flask-cors
```

### "Address already in use"
Port 5000 is already in use. Try a different port:
```bash
python run_dashboard.py --port 8000
```

### No Data Shown
1. Start your trading bot first
2. Let it generate some trades
3. Check bot logs are being written
4. Refresh dashboard browser (F5)

### Metrics Not Updating
1. Check bot is running
2. Check Flask server is running (no errors)
3. Check browser console for errors (F12)
4. Verify API responds: `curl http://localhost:5000/api/metrics`

## 📚 Learn More

See **DASHBOARD_README.md** for:
- Complete feature list
- Detailed API documentation
- Configuration options
- UI customization guide
- Advanced troubleshooting
- Development guide

## 💡 Tips

1. **Multiple Monitors**: Open dashboard on one screen, trades on another
2. **Keep Running**: Dashboard works best when always visible
3. **Mobile Access**: Open `http://<your-ip>:5000` from phone
4. **Bookmark It**: Save dashboard URL to favorites for quick access
5. **Check Hourly**: Monitor dashboard every hour for trading activity

## ✅ You're Ready!

```bash
python run_dashboard.py
# Open http://localhost:5000
# Watch your bot trade in real-time!
```

## 🎓 Next Steps

1. ✅ Dashboard running
2. ⬜ Start your trading bot: `python main_refactored.py`
3. ⬜ Generate some test trades
4. ⬜ Watch dashboard update in real-time
5. ⬜ Review performance metrics & charts

**Happy Trading! 📈**

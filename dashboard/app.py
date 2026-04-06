"""
Trading Bot Dashboard - Flask Web Application

A real-time web dashboard for monitoring the XAUUSD AI trading bot.
Displays metrics, positions, trades, signals, and performance charts.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from .data_parser import TradingDataParser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure Flask application."""

    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Enable CORS for local API access
    CORS(app, resources={r"/api/*": {"origins": ["localhost:*", "127.0.0.1:*"]}})

    # Initialize data parser
    app.data_parser = TradingDataParser()

    # ========================================================================
    # Routes
    # ========================================================================

    @app.route('/')
    def index():
        """Serve main dashboard page."""
        return render_template('index.html')

    @app.route('/health')
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }), 200

    # ========================================================================
    # API Endpoints - Metrics
    # ========================================================================

    @app.route('/api/metrics', methods=['GET'])
    def get_metrics():
        """Get current trading metrics.

        Returns:
            {
                "timestamp": "2026-04-06T01:30:00",
                "balance": 10500.00,
                "equity": 10485.50,
                "initial_balance": 10000.00,
                "total_pnl": 485.50,
                "pnl_pct": 4.86,
                ...
            }
        """
        try:
            metrics = app.data_parser.get_current_metrics()
            return jsonify(metrics), 200
        except Exception as e:
            logger.error(f"Error in /api/metrics: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/trades', methods=['GET'])
    def get_trades():
        """Get recent trade history.

        Query parameters:
            - limit: Number of trades to return (default 50)

        Returns:
            {
                "trades": [
                    {
                        "id": "trade_001",
                        "type": "BUY",
                        "entry_time": "...",
                        "entry_price": 2365.50,
                        ...
                    }
                ]
            }
        """
        try:
            limit = request.args.get('limit', default=50, type=int)
            limit = min(limit, 500)  # Cap at 500

            trades = app.data_parser.get_recent_trades(limit=limit)

            return jsonify({
                "trades": trades,
                "count": len(trades),
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            logger.error(f"Error in /api/trades: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/positions', methods=['GET'])
    def get_positions():
        """Get currently open positions.

        Returns:
            {
                "positions": [
                    {
                        "id": "trade_open_001",
                        "type": "BUY",
                        "entry_price": 2348.50,
                        "current_price": 2351.20,
                        ...
                    }
                ]
            }
        """
        try:
            positions = app.data_parser.get_open_positions()

            return jsonify({
                "positions": positions,
                "count": len(positions),
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            logger.error(f"Error in /api/positions: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/equity-curve', methods=['GET'])
    def get_equity_curve():
        """Get equity curve data for charting.

        Query parameters:
            - limit: Number of data points (default 100)

        Returns:
            {
                "data": [
                    {
                        "timestamp": "2026-04-01T10:00:00",
                        "equity": 10150.50
                    },
                    ...
                ]
            }
        """
        try:
            limit = request.args.get('limit', default=100, type=int)
            curve = app.data_parser.get_equity_curve(limit=limit)

            return jsonify({
                "data": curve,
                "count": len(curve),
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            logger.error(f"Error in /api/equity-curve: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/signals', methods=['GET'])
    def get_signals():
        """Get recent trading signals.

        Query parameters:
            - limit: Number of signals (default 10)

        Returns:
            {
                "signals": [
                    {
                        "timestamp": "2026-04-06T01:25:00",
                        "direction": "BUY",
                        "confidence": 0.85,
                        "indicator": "XGBoost"
                    }
                ]
            }
        """
        try:
            limit = request.args.get('limit', default=10, type=int)
            signals = app.data_parser.get_latest_signals(limit=limit)

            return jsonify({
                "signals": signals,
                "count": len(signals),
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            logger.error(f"Error in /api/signals: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/performance', methods=['GET'])
    def get_performance():
        """Get detailed performance statistics.

        Returns:
            {
                "total_return": 4.86,
                "win_rate": 65.0,
                "profit_factor": 2.45,
                ...
            }
        """
        try:
            stats = app.data_parser.get_performance_stats()

            return jsonify(stats), 200
        except Exception as e:
            logger.error(f"Error in /api/performance: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/logs', methods=['GET'])
    def get_logs():
        """Get recent log lines for debugging.

        Query parameters:
            - lines: Number of lines (default 50)

        Returns:
            {
                "logs": "... recent log content ..."
            }
        """
        try:
            lines = request.args.get('lines', default=50, type=int)
            log_content = app.data_parser.get_log_tail(lines=lines)

            return jsonify({
                "logs": log_content,
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            logger.error(f"Error in /api/logs: {e}")
            return jsonify({"error": str(e)}), 500

    # ========================================================================
    # Error Handlers
    # ========================================================================

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        """Handle 500 errors."""
        logger.error(f"Server error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    # ========================================================================
    # Context processors for templates
    # ========================================================================

    @app.context_processor
    def inject_config():
        """Inject configuration into templates."""
        return {
            "app_version": "1.0.0",
            "dashboard_name": "XAUUSD Trading Bot Dashboard",
            "refresh_interval": 3000  # milliseconds
        }

    logger.info("Flask app created successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

#!/usr/bin/env python3
"""
Run the XAUUSD Trading Bot Dashboard

A real-time web dashboard for monitoring the AI trading bot.
Access at http://localhost:5000 after starting.

Usage:
    python run_dashboard.py              # Run on default port 5000
    python run_dashboard.py --port 8000  # Run on custom port
    python run_dashboard.py --debug      # Run in debug mode
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from dashboard.app import create_app
    logger.info("✓ Successfully imported dashboard app")
except ImportError as e:
    logger.error(f"✗ Failed to import dashboard: {e}")
    sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run XAUUSD Trading Bot Dashboard',
        epilog='Access the dashboard at http://localhost:PORT'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to run on (default: 5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode'
    )

    args = parser.parse_args()

    logger.info("="*70)
    logger.info("XAUUSD Trading Bot Dashboard")
    logger.info("="*70)
    logger.info("")
    logger.info(f"Starting dashboard on {args.host}:{args.port}")
    logger.info(f"Debug mode: {'ON' if args.debug else 'OFF'}")
    logger.info("")
    logger.info("✓ Open your browser and go to: http://localhost:{}/".format(args.port))
    logger.info("")
    logger.info("Press CTRL+C to stop the dashboard")
    logger.info("="*70)
    logger.info("")

    try:
        app = create_app()

        # Run Flask app
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True,
            use_reloader=False  # Disable reloader for simpler execution
        )

    except KeyboardInterrupt:
        logger.info("\n\nDashboard stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"✗ Error running dashboard: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
Automatic model retraining scheduler.

Features:
- Scheduled retraining at configured intervals
- Background task management
- Graceful error handling
- Retraining status tracking
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class RetrainingStatus(Enum):
    """Retraining status."""
    IDLE = 'idle'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


class RetrainingScheduler:
    """Schedule and manage automatic model retraining."""

    def __init__(self, model_manager, data_fetcher, config):
        """Initialize retraining scheduler.

        Args:
            model_manager: ModelManager instance
            data_fetcher: DataFetcher instance for historical data
            config: Configuration object
        """
        self.model_manager = model_manager
        self.data_fetcher = data_fetcher
        self.config = config

        self.is_running = False
        self.thread = None
        self.status = RetrainingStatus.IDLE
        self.last_status_update = datetime.now()
        self.last_successful_retrain = None
        self.retraining_errors = []

        logger.info("✓ Retraining Scheduler initialized")

    def start(self):
        """Start the retraining scheduler in background thread."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()

        logger.info("✓ Retraining scheduler started")

    def stop(self):
        """Stop the retraining scheduler."""
        self.is_running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)

        logger.info("✓ Retraining scheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop running in background thread."""
        try:
            while self.is_running:
                try:
                    # Check if retraining is due
                    if self.model_manager.should_retrain():
                        self._perform_retraining()

                    # Sleep for 1 hour before checking again
                    time.sleep(3600)

                except Exception as e:
                    logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                    self.retraining_errors.append({
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e)
                    })
                    time.sleep(60)  # Wait before retrying

        except Exception as e:
            logger.error(f"Fatal error in scheduler: {e}", exc_info=True)
            self.is_running = False

    def _perform_retraining(self):
        """Perform model retraining with new data."""
        try:
            self.status = RetrainingStatus.RUNNING
            self.last_status_update = datetime.now()

            logger.info("\n" + "=" * 70)
            logger.info("SCHEDULED MODEL RETRAINING")
            logger.info("=" * 70)

            # Fetch historical data for retraining
            logger.info("Fetching historical data for retraining...")
            lookback_days = 30  # Use last 30 days of data

            df = self.data_fetcher.get_historical_data(
                self.config.SYMBOL,
                self.config.TIMEFRAME,
                (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d')
            )

            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for retraining ({len(df) if df is not None else 0} candles)")
                self.status = RetrainingStatus.FAILED
                return

            logger.info(f"✓ Fetched {len(df)} candles for retraining")

            # Calculate indicators
            logger.info("Calculating technical indicators...")
            from src.technical_analysis import TechnicalAnalysis

            ta = TechnicalAnalysis(df)
            ta.calculate_moving_averages()
            ta.calculate_rsi()
            ta.calculate_bollinger_bands()
            ta.calculate_atr()
            ta.calculate_stochastic()
            ta.calculate_volume_indicators()

            logger.info("✓ Indicators calculated")

            # Prepare data
            logger.info("Preparing data for training...")
            X, y = self.model_manager.model.prepare_data(ta.df)

            if X is None or len(X) < 50:
                logger.warning(f"Insufficient prepared samples ({len(X) if X is not None else 0})")
                self.status = RetrainingStatus.FAILED
                return

            logger.info(f"✓ Data prepared: {len(X)} samples")

            # Retrain model
            logger.info("Retraining model...")
            metrics = self.model_manager.retrain_model(X, y, force=True)

            if metrics:
                self.status = RetrainingStatus.COMPLETED
                self.last_successful_retrain = datetime.now()
                self.retraining_errors = []  # Clear errors on success

                logger.info(f"✓ Retraining completed successfully")
                logger.info(f"  Accuracy: {metrics['accuracy']:.4f}")
                logger.info(f"  Precision: {metrics['precision_weighted']:.4f}")
                logger.info(f"  Recall: {metrics['recall_weighted']:.4f}")
                logger.info("=" * 70 + "\n")

            else:
                self.status = RetrainingStatus.FAILED
                logger.error("Model retraining failed")

        except Exception as e:
            logger.error(f"Error during retraining: {e}", exc_info=True)
            self.status = RetrainingStatus.FAILED
            self.retraining_errors.append({
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            })

    def get_status(self):
        """Get scheduler status.

        Returns:
            Dictionary with scheduler information
        """
        return {
            'is_running': self.is_running,
            'current_status': self.status.value,
            'last_status_update': self.last_status_update.isoformat(),
            'last_successful_retrain': self.last_successful_retrain.isoformat() if self.last_successful_retrain else None,
            'next_scheduled_retrain': self.model_manager._estimate_next_retraining(),
            'schedule': self.model_manager.schedule.value,
            'recent_errors': self.retraining_errors[-5:] if self.retraining_errors else [],
            'total_errors': len(self.retraining_errors)
        }

    def force_retrain(self):
        """Force immediate retraining regardless of schedule.

        Returns:
            True if retraining started successfully
        """
        try:
            if self.status == RetrainingStatus.RUNNING:
                logger.warning("Retraining already in progress")
                return False

            # Run retraining in background
            thread = threading.Thread(target=self._perform_retraining, daemon=True)
            thread.start()

            logger.info("✓ Forced retraining initiated")
            return True

        except Exception as e:
            logger.error(f"Error forcing retrain: {e}")
            return False

    def wait_for_completion(self, timeout=3600):
        """Wait for current retraining to complete.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            True if completed, False if timeout
        """
        start_time = datetime.now()
        while self.status == RetrainingStatus.RUNNING:
            if (datetime.now() - start_time).total_seconds() > timeout:
                logger.warning(f"Retraining timeout after {timeout}s")
                return False
            time.sleep(10)

        return True

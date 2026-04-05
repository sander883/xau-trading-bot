"""
Professional model manager with automatic retraining, preprocessing, and evaluation.

Features:
- Automatic periodic retraining (daily, weekly, monthly)
- Advanced feature scaling and preprocessing
- Prediction logging with full context
- Performance metrics tracking
- Model versioning and rollback
"""

import logging
import numpy as np
import pandas as pd
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from collections import deque

try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)


class RetariningSchedule(Enum):
    """Retraining schedule options."""
    DAILY = 'daily'
    WEEKLY = 'weekly'
    BIWEEKLY = 'biweekly'
    MONTHLY = 'monthly'
    MANUAL = 'manual'


class ScalingMethod(Enum):
    """Feature scaling methods."""
    STANDARD = 'standard'
    MINMAX = 'minmax'
    ROBUST = 'robust'


class ModelPerformance:
    """Track model performance metrics."""

    def __init__(self, window_size=100):
        """Initialize performance tracker.

        Args:
            window_size: Number of predictions to track for rolling metrics
        """
        self.window_size = window_size
        self.predictions = deque(maxlen=window_size)
        self.actuals = deque(maxlen=window_size)
        self.confidences = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)

        self.total_predictions = 0
        self.total_correct = 0
        self.by_class = {0: {'correct': 0, 'total': 0},
                        1: {'correct': 0, 'total': 0},
                        2: {'correct': 0, 'total': 0}}

    def update(self, prediction, actual, confidence, timestamp=None):
        """Update performance metrics.

        Args:
            prediction: Predicted class (0, 1, or 2)
            actual: Actual class (0, 1, or 2)
            confidence: Prediction confidence (0-1)
            timestamp: Timestamp of prediction
        """
        self.predictions.append(prediction)
        self.actuals.append(actual)
        self.confidences.append(confidence)
        self.timestamps.append(timestamp or datetime.now())

        self.total_predictions += 1
        if prediction == actual:
            self.total_correct += 1

        self.by_class[actual]['total'] += 1
        if prediction == actual:
            self.by_class[actual]['correct'] += 1

    def get_metrics(self):
        """Get comprehensive performance metrics.

        Returns:
            Dictionary with metrics
        """
        if len(self.predictions) == 0:
            return None

        predictions = list(self.predictions)
        actuals = list(self.actuals)
        confidences = list(self.confidences)

        try:
            accuracy = accuracy_score(actuals, predictions)
            precision = precision_score(actuals, predictions, average='weighted', zero_division=0)
            recall = recall_score(actuals, predictions, average='weighted', zero_division=0)
            f1 = f1_score(actuals, predictions, average='weighted', zero_division=0)

            # Per-class metrics
            per_class = {}
            for class_id in [0, 1, 2]:
                class_predictions = [p == class_id for p in predictions]
                class_actuals = [a == class_id for a in actuals]
                if any(class_actuals):
                    per_class[class_id] = {
                        'precision': precision_score(class_actuals, class_predictions, zero_division=0),
                        'recall': recall_score(class_actuals, class_predictions, zero_division=0),
                        'count': sum(class_actuals)
                    }

            # Confidence statistics
            high_conf = [c for c in confidences if c > 0.7]
            medium_conf = [c for c in confidences if 0.5 <= c <= 0.7]
            low_conf = [c for c in confidences if c < 0.5]

            return {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'per_class': per_class,
                'total_predictions': self.total_predictions,
                'total_correct': self.total_correct,
                'avg_confidence': float(np.mean(confidences)),
                'high_confidence_count': len(high_conf),
                'medium_confidence_count': len(medium_conf),
                'low_confidence_count': len(low_conf),
                'window_size': len(self.predictions),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return None


class PredictionLogger:
    """Log all model predictions for analysis and debugging."""

    def __init__(self, log_dir):
        """Initialize prediction logger.

        Args:
            log_dir: Directory to store prediction logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.current_log = []
        self.log_file = None
        self._rotate_log_file()

    def _rotate_log_file(self):
        """Create new log file for the day."""
        date_str = datetime.now().strftime('%Y-%m-%d')
        self.log_file = self.log_dir / f'predictions_{date_str}.csv'

    def log_prediction(self, prediction_data):
        """Log a prediction with full context.

        Args:
            prediction_data: Dictionary with prediction details
        """
        try:
            # Ensure date rotation
            if (datetime.now().date() !=
                datetime.fromisoformat(prediction_data['timestamp']).date()):
                self._rotate_log_file()

            # Create row
            row = {
                'timestamp': prediction_data['timestamp'],
                'prediction': prediction_data['prediction'],
                'signal': prediction_data.get('signal', 'UNKNOWN'),
                'confidence': prediction_data['confidence'],
                'probabilities_sell': prediction_data.get('probabilities', {}).get('SELL', 0),
                'probabilities_hold': prediction_data.get('probabilities', {}).get('HOLD', 0),
                'probabilities_buy': prediction_data.get('probabilities', {}).get('BUY', 0),
                'price': prediction_data.get('price', 0),
                'atr': prediction_data.get('atr', 0),
                'trend': prediction_data.get('trend', 'UNKNOWN'),
                'market_condition': prediction_data.get('market_condition', 'UNKNOWN'),
                'actual': prediction_data.get('actual', None),
                'trade_executed': prediction_data.get('trade_executed', False),
                'trade_result': prediction_data.get('trade_result', None)
            }

            self.current_log.append(row)

            # Write to CSV (append mode)
            df = pd.DataFrame([row])
            if self.log_file.exists():
                df.to_csv(self.log_file, mode='a', header=False, index=False)
            else:
                df.to_csv(self.log_file, mode='w', header=True, index=False)

        except Exception as e:
            logger.error(f"Error logging prediction: {e}")

    def get_recent_predictions(self, hours=24):
        """Get recent predictions.

        Args:
            hours: Number of hours to look back

        Returns:
            DataFrame with recent predictions
        """
        try:
            if not self.log_file.exists():
                return None

            df = pd.read_csv(self.log_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            cutoff = datetime.now() - timedelta(hours=hours)
            return df[df['timestamp'] > cutoff]
        except Exception as e:
            logger.error(f"Error reading predictions: {e}")
            return None


class ModelPreprocessor:
    """Advanced feature preprocessing and scaling."""

    def __init__(self, scaling_method=ScalingMethod.ROBUST):
        """Initialize preprocessor.

        Args:
            scaling_method: Scaling method to use
        """
        self.scaling_method = scaling_method
        self.scaler = self._create_scaler()
        self.feature_stats = {}
        self.is_fitted = False

    def _create_scaler(self):
        """Create scaler based on method.

        Returns:
            Scaler instance
        """
        if self.scaling_method == ScalingMethod.STANDARD:
            return StandardScaler()
        elif self.scaling_method == ScalingMethod.MINMAX:
            return MinMaxScaler()
        else:  # ROBUST
            return RobustScaler()

    def fit(self, X):
        """Fit scaler to data.

        Args:
            X: Feature array

        Returns:
            Self for chaining
        """
        try:
            self.scaler.fit(X)
            self.is_fitted = True

            # Calculate statistics
            self.feature_stats = {
                'mean': np.mean(X, axis=0),
                'std': np.std(X, axis=0),
                'min': np.min(X, axis=0),
                'max': np.max(X, axis=0)
            }

            logger.info("✓ Preprocessor fitted to data")
            return self
        except Exception as e:
            logger.error(f"Error fitting preprocessor: {e}")
            return self

    def transform(self, X):
        """Transform data using fitted scaler.

        Args:
            X: Feature array

        Returns:
            Scaled feature array
        """
        try:
            if not self.is_fitted:
                logger.warning("Preprocessor not fitted, returning original data")
                return X

            X_scaled = self.scaler.transform(X)

            # Handle NaN/Inf values
            X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=1e6, neginf=-1e6)

            return X_scaled
        except Exception as e:
            logger.error(f"Error transforming data: {e}")
            return X

    def fit_transform(self, X):
        """Fit and transform data.

        Args:
            X: Feature array

        Returns:
            Scaled feature array
        """
        return self.fit(X).transform(X)

    def inverse_transform(self, X_scaled):
        """Inverse transform scaled data.

        Args:
            X_scaled: Scaled feature array

        Returns:
            Original scale feature array
        """
        try:
            if not self.is_fitted:
                return X_scaled
            return self.scaler.inverse_transform(X_scaled)
        except Exception as e:
            logger.error(f"Error inverse transforming: {e}")
            return X_scaled


class ModelManager:
    """Comprehensive model management with retraining and evaluation."""

    def __init__(self, config, model, schedule=RetariningSchedule.WEEKLY):
        """Initialize model manager.

        Args:
            config: Configuration object
            model: Professional XGBoost model instance
            schedule: Retraining schedule
        """
        self.config = config
        self.model = model
        self.schedule = schedule

        # Components
        self.preprocessor = ModelPreprocessor(ScalingMethod.ROBUST)
        self.performance = ModelPerformance(window_size=100)
        self.prediction_logger = PredictionLogger(config.LOGS_DIR)

        # Retraining tracking
        self.last_training_date = None
        self.training_count = 0
        self.model_versions = []

        logger.info("✓ Model Manager initialized")

    def should_retrain(self):
        """Check if model should be retrained.

        Returns:
            True if retraining is due
        """
        if self.last_training_date is None:
            return True

        now = datetime.now()

        if self.schedule == RetariningSchedule.DAILY:
            return (now - self.last_training_date).days >= 1
        elif self.schedule == RetariningSchedule.WEEKLY:
            return (now - self.last_training_date).days >= 7
        elif self.schedule == RetariningSchedule.BIWEEKLY:
            return (now - self.last_training_date).days >= 14
        elif self.schedule == RetariningSchedule.MONTHLY:
            return (now - self.last_training_date).days >= 30

        return False

    def retrain_model(self, X, y, force=False):
        """Retrain model with new data.

        Args:
            X: Feature array
            y: Target array
            force: Force retraining regardless of schedule

        Returns:
            Training metrics or None
        """
        try:
            if not force and not self.should_retrain():
                logger.info("Retraining not due yet")
                return None

            logger.info("=" * 70)
            logger.info("AUTOMATIC MODEL RETRAINING")
            logger.info("=" * 70)

            # Preprocess features
            logger.info("Preprocessing features...")
            X_processed = self.preprocessor.fit_transform(X)

            # Train model
            logger.info("Training model with new data...")
            metrics = self.model.train(X_processed, y, test_size=0.2)

            if metrics:
                # Save model version
                self._save_model_version()

                # Log retraining
                self.last_training_date = datetime.now()
                self.training_count += 1

                logger.info(f"✓ Model retrained successfully")
                logger.info(f"  Training count: {self.training_count}")
                logger.info(f"  Accuracy: {metrics['accuracy']:.4f}")
                logger.info(f"  Precision: {metrics['precision_weighted']:.4f}")
                logger.info(f"  Recall: {metrics['recall_weighted']:.4f}")

                return metrics
            else:
                logger.error("Model training failed")
                return None

        except Exception as e:
            logger.error(f"Error during retraining: {e}", exc_info=True)
            return None

    def predict_with_logging(self, features, context=None):
        """Predict with full logging and context.

        Args:
            features: Feature array
            context: Optional context dict (price, atr, trend, etc.)

        Returns:
            Prediction dict with logging
        """
        try:
            # Preprocess
            features_processed = self.preprocessor.transform(features)

            # Predict
            signal = self.model.predict_signal(features_processed,
                                              self.config.PREDICTION_CONFIDENCE_THRESHOLD)

            # Prepare log entry
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'prediction': signal.get('prediction', -1),
                'signal': signal.get('signal_name', 'UNKNOWN'),
                'confidence': signal.get('confidence', 0),
                'probabilities': signal.get('probabilities', {}),
                'meets_threshold': signal.get('meets_threshold', False)
            }

            # Add context if provided
            if context:
                log_entry.update(context)

            # Log prediction
            self.prediction_logger.log_prediction(log_entry)

            # Update performance tracking
            if 'actual' in context and context['actual'] is not None:
                self.performance.update(
                    log_entry['prediction'],
                    context['actual'],
                    log_entry['confidence'],
                    log_entry['timestamp']
                )

            return log_entry

        except Exception as e:
            logger.error(f"Error in prediction with logging: {e}", exc_info=True)
            return None

    def get_performance_summary(self):
        """Get model performance summary.

        Returns:
            Dictionary with performance metrics
        """
        metrics = self.performance.get_metrics()

        if metrics:
            logger.info("=" * 70)
            logger.info("MODEL PERFORMANCE SUMMARY")
            logger.info("=" * 70)
            logger.info(f"Accuracy: {metrics['accuracy']:.4f}")
            logger.info(f"Precision: {metrics['precision']:.4f}")
            logger.info(f"Recall: {metrics['recall']:.4f}")
            logger.info(f"F1 Score: {metrics['f1_score']:.4f}")
            logger.info(f"Total Predictions: {metrics['total_predictions']}")
            logger.info(f"Correct Predictions: {metrics['total_correct']}")
            logger.info(f"Avg Confidence: {metrics['avg_confidence']:.2%}")
            logger.info("=" * 70)

        return metrics

    def _save_model_version(self):
        """Save current model as version."""
        try:
            version_name = f"model_v{self.training_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            version_path = self.config.MODELS_DIR / f"{version_name}.pkl"

            self.model.save_model(version_path)
            self.model_versions.append({
                'version': version_name,
                'path': str(version_path),
                'timestamp': datetime.now().isoformat(),
                'accuracy': self.performance.get_metrics()
            })

            logger.info(f"✓ Model version saved: {version_name}")

            # Keep only last 5 versions
            if len(self.model_versions) > 5:
                old_version = self.model_versions.pop(0)
                try:
                    Path(old_version['path']).unlink()
                    logger.info(f"Removed old model version: {old_version['version']}")
                except:
                    pass

        except Exception as e:
            logger.error(f"Error saving model version: {e}")

    def rollback_to_version(self, version_name):
        """Rollback to previous model version.

        Args:
            version_name: Version name to rollback to

        Returns:
            True if successful
        """
        try:
            for version in self.model_versions:
                if version['version'] == version_name:
                    self.model.load_model(version['path'])
                    logger.info(f"✓ Rolled back to {version_name}")
                    return True

            logger.warning(f"Version {version_name} not found")
            return False

        except Exception as e:
            logger.error(f"Error rolling back version: {e}")
            return False

    def get_model_status(self):
        """Get comprehensive model status.

        Returns:
            Dictionary with model information
        """
        perf = self.performance.get_metrics()

        return {
            'model_trained': self.model.is_trained,
            'training_count': self.training_count,
            'last_training': self.last_training_date.isoformat() if self.last_training_date else None,
            'next_retraining': self._estimate_next_retraining(),
            'retraining_schedule': self.schedule.value,
            'total_predictions_logged': self.performance.total_predictions,
            'performance_metrics': perf,
            'model_versions': len(self.model_versions),
            'latest_version': self.model_versions[-1] if self.model_versions else None,
            'timestamp': datetime.now().isoformat()
        }

    def _estimate_next_retraining(self):
        """Estimate next retraining time.

        Returns:
            ISO format datetime or None
        """
        if self.last_training_date is None:
            return datetime.now().isoformat()

        delta_map = {
            RetariningSchedule.DAILY: timedelta(days=1),
            RetariningSchedule.WEEKLY: timedelta(days=7),
            RetariningSchedule.BIWEEKLY: timedelta(days=14),
            RetariningSchedule.MONTHLY: timedelta(days=30)
        }

        delta = delta_map.get(self.schedule)
        if delta:
            next_time = self.last_training_date + delta
            return next_time.isoformat()

        return None

    def export_performance_report(self, filepath=None):
        """Export performance report to file.

        Args:
            filepath: Path to save report

        Returns:
            Path to saved report
        """
        try:
            if filepath is None:
                filepath = self.config.LOGS_DIR / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            with open(filepath, 'w') as f:
                f.write("=" * 70 + "\n")
                f.write("MODEL PERFORMANCE REPORT\n")
                f.write("=" * 70 + "\n\n")

                status = self.get_model_status()

                f.write(f"Generated: {status['timestamp']}\n")
                f.write(f"Model Trained: {status['model_trained']}\n")
                f.write(f"Training Count: {status['training_count']}\n")
                f.write(f"Last Training: {status['last_training']}\n")
                f.write(f"Next Retraining: {status['next_retraining']}\n")
                f.write(f"Schedule: {status['retraining_schedule']}\n\n")

                f.write("=" * 70 + "\n")
                f.write("PERFORMANCE METRICS\n")
                f.write("=" * 70 + "\n\n")

                if status['performance_metrics']:
                    metrics = status['performance_metrics']
                    f.write(f"Total Predictions: {metrics['total_predictions']}\n")
                    f.write(f"Accuracy: {metrics['accuracy']:.4f}\n")
                    f.write(f"Precision: {metrics['precision']:.4f}\n")
                    f.write(f"Recall: {metrics['recall']:.4f}\n")
                    f.write(f"F1 Score: {metrics['f1_score']:.4f}\n")
                    f.write(f"Avg Confidence: {metrics['avg_confidence']:.2%}\n\n")

                    f.write("Confidence Distribution:\n")
                    f.write(f"  High (>70%): {metrics['high_confidence_count']}\n")
                    f.write(f"  Medium (50-70%): {metrics['medium_confidence_count']}\n")
                    f.write(f"  Low (<50%): {metrics['low_confidence_count']}\n\n")

                f.write("=" * 70 + "\n")
                f.write("MODEL VERSIONS\n")
                f.write("=" * 70 + "\n\n")

                for version in self.model_versions:
                    f.write(f"Version: {version['version']}\n")
                    f.write(f"  Path: {version['path']}\n")
                    f.write(f"  Timestamp: {version['timestamp']}\n\n")

            logger.info(f"✓ Performance report saved: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return None

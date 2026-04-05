import logging
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from pathlib import Path

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
except ImportError:
    raise ImportError("scikit-learn is required. Install with: pip install scikit-learn")

try:
    import xgboost as xgb
except ImportError:
    xgb = None

logger = logging.getLogger(__name__)


class MLModel:
    """Machine learning model for price prediction."""

    def __init__(self, config, model_type='xgboost'):
        """Initialize ML model.

        Args:
            config: Configuration object
            model_type: 'xgboost' or 'sklearn'
        """
        self.config = config
        self.model_type = model_type.lower()
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
        self.last_training_date = None

        if self.model_type == 'xgboost' and xgb is None:
            logger.warning("XGBoost not installed, falling back to sklearn")
            self.model_type = 'sklearn'

    def prepare_data(self, df, lookback=20, prediction_horizon=1):
        """Prepare data for model training.

        Args:
            df: DataFrame with technical indicators
            lookback: Number of previous candles to use for features
            prediction_horizon: Candles ahead to predict

        Returns:
            X, y arrays ready for training
        """
        try:
            # Create target variable (1 for uptrend, 0 for downtrend)
            df['Target'] = (df['Close'].shift(-prediction_horizon) > df['Close']).astype(int)

            # Select features (exclude OHLC and target)
            feature_cols = [col for col in df.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume', 'Target']]
            self.feature_names = feature_cols

            # Create sequences
            X = []
            y = []

            for i in range(len(df) - lookback - prediction_horizon):
                X.append(df[feature_cols].iloc[i:i+lookback].values.flatten())
                y.append(df['Target'].iloc[i+lookback])

            X = np.array(X)
            y = np.array(y)

            # Remove NaN rows
            mask = ~np.isnan(X).any(axis=1)
            X = X[mask]
            y = y[mask]

            logger.info(f"Data prepared: {X.shape[0]} samples, {X.shape[1]} features")
            return X, y

        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return None, None

    def train(self, X, y, test_size=0.2):
        """Train the model.

        Args:
            X: Feature array
            y: Target array
            test_size: Fraction of data to use for testing
        """
        try:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            if self.model_type == 'xgboost':
                self.model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    verbose=0
                )
            else:
                self.model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=15,
                    random_state=42,
                    n_jobs=-1
                )

            self.model.fit(X_train_scaled, y_train)

            # Evaluate
            train_score = self.model.score(X_train_scaled, y_train)
            test_score = self.model.score(X_test_scaled, y_test)

            self.is_trained = True
            self.last_training_date = datetime.now()

            logger.info(f"Model trained successfully ({self.model_type})")
            logger.info(f"Train accuracy: {train_score:.4f}, Test accuracy: {test_score:.4f}")

            return {
                'train_accuracy': train_score,
                'test_accuracy': test_score
            }

        except Exception as e:
            logger.error(f"Error training model: {e}")
            return None

    def predict(self, X):
        """Make predictions on new data.

        Args:
            X: Feature array

        Returns:
            Predictions and probabilities
        """
        if self.model is None or not self.is_trained:
            logger.error("Model not trained yet")
            return None, None

        try:
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
            probabilities = self.model.predict_proba(X_scaled)

            return predictions, probabilities

        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return None, None

    def predict_single(self, features):
        """Predict for a single feature vector.

        Args:
            features: Single feature array

        Returns:
            Prediction and confidence score
        """
        try:
            features = np.array(features).reshape(1, -1)
            prediction, proba = self.predict(features)

            if prediction is None:
                return None, 0.0

            confidence = float(np.max(proba[0]))
            return int(prediction[0]), confidence

        except Exception as e:
            logger.error(f"Error in single prediction: {e}")
            return None, 0.0

    def save_model(self, filename=None):
        """Save trained model to disk.

        Args:
            filename: Output filename (default: timestamp-based)
        """
        if self.model is None:
            logger.error("No model to save")
            return False

        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"model_{self.model_type}_{timestamp}.pkl"

            filepath = self.config.MODELS_DIR / filename

            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'model_type': self.model_type,
                'training_date': self.last_training_date
            }

            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"Model saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def load_model(self, filepath):
        """Load trained model from disk.

        Args:
            filepath: Path to model file

        Returns:
            True if successful
        """
        try:
            if isinstance(filepath, str):
                filepath = Path(filepath)

            if not filepath.exists():
                logger.error(f"Model file not found: {filepath}")
                return False

            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.model_type = model_data['model_type']
            self.last_training_date = model_data['training_date']
            self.is_trained = True

            logger.info(f"Model loaded from {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def get_feature_importance(self, top_n=10):
        """Get feature importance scores.

        Args:
            top_n: Number of top features to return

        Returns:
            DataFrame with feature importance
        """
        if self.model is None:
            logger.error("Model not trained")
            return None

        try:
            if hasattr(self.model, 'feature_importances_'):
                importance = self.model.feature_importances_
                feature_importance_df = pd.DataFrame({
                    'feature': self.feature_names,
                    'importance': importance
                }).sort_values('importance', ascending=False).head(top_n)

                return feature_importance_df
            else:
                logger.warning("Model doesn't support feature importance")
                return None

        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return None

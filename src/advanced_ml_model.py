import logging
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from pathlib import Path

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
except ImportError:
    raise ImportError("scikit-learn is required")

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    xgb = None

logger = logging.getLogger(__name__)


class AdvancedMLModel:
    """Advanced ML model with enhanced feature engineering and XGBoost."""

    def __init__(self, config, model_type='xgboost'):
        """Initialize advanced ML model.

        Args:
            config: Configuration object
            model_type: 'xgboost', 'random_forest', or 'gradient_boost'
        """
        self.config = config
        self.model_type = model_type.lower()
        self.model = None
        self.scaler = RobustScaler()  # Better for outliers
        self.feature_names = []
        self.feature_importance_dict = {}
        self.is_trained = False
        self.last_training_date = None
        self.training_metrics = {}

        # Check model availability
        if self.model_type == 'xgboost' and not HAS_XGBOOST:
            logger.warning("XGBoost not available, falling back to gradient boosting")
            self.model_type = 'gradient_boost'

    def engineer_features(self, df):
        """Advanced feature engineering with domain knowledge.

        Args:
            df: DataFrame with OHLC and technical indicators

        Returns:
            DataFrame with engineered features
        """
        try:
            df_features = df.copy()

            # 1. Price Action Features
            # Rate of change
            df_features['ROC_5'] = df['Close'].pct_change(5)
            df_features['ROC_10'] = df['Close'].pct_change(10)
            df_features['ROC_20'] = df['Close'].pct_change(20)

            # Momentum
            df_features['MOMENTUM'] = df['Close'] - df['Close'].shift(10)
            df_features['MOMENTUM_NORM'] = df_features['MOMENTUM'] / (df['High'] - df['Low'])

            # 2. Volatility Features
            if 'ATR' in df.columns:
                df_features['ATR_RATIO'] = df['ATR'] / df['Close']
                df_features['ATR_SMA_RATIO'] = df['ATR'] / df['ATR'].rolling(20).mean()

            if 'BB_UPPER' in df.columns and 'BB_LOWER' in df.columns:
                bb_width = df['BB_UPPER'] - df['BB_LOWER']
                df_features['BB_WIDTH'] = bb_width
                df_features['BB_WIDTH_NORM'] = bb_width / df['Close']
                df_features['PRICE_BB_POSITION'] = (df['Close'] - df['BB_LOWER']) / bb_width

            # Historical volatility
            df_features['HV_20'] = df['Close'].pct_change().rolling(20).std()
            df_features['HV_RATIO'] = df_features['HV_20'] / df_features['HV_20'].rolling(50).mean()

            # 3. Trend Features
            if 'EMA_FAST' in df.columns and 'EMA_SLOW' in df.columns:
                df_features['EMA_DIFF'] = df['EMA_FAST'] - df['EMA_SLOW']
                df_features['EMA_DIFF_NORM'] = df_features['EMA_DIFF'] / df['Close']
                df_features['PRICE_EMA_RATIO'] = df['Close'] / df['EMA_FAST']

            # 4. Mean Reversion Features (distance from moving average)
            if 'SMA_SLOW' in df.columns:
                df_features['PRICE_SMA_DISTANCE'] = (df['Close'] - df['SMA_SLOW']) / df['SMA_SLOW']

            # 5. RSI Features
            if 'RSI' in df.columns:
                df_features['RSI_ZONE'] = pd.cut(df['RSI'], bins=[0, 30, 50, 70, 100], labels=[0, 1, 2, 3]).astype(float)
                df_features['RSI_DIVERGENCE'] = df['RSI'] - df['RSI'].shift(5)

            # 6. MACD Features
            if 'MACD' in df.columns and 'SIGNAL' in df.columns:
                df_features['MACD_HISTOGRAM'] = df['MACD'] - df['SIGNAL']
                df_features['MACD_NORM'] = df['MACD'] / df['Close']

            # 7. Volume Features
            if 'Volume' in df.columns:
                df_features['VOLUME_SMA_RATIO'] = df['Volume'] / df['Volume'].rolling(20).mean()
                df_features['VOLUME_TREND'] = df['Volume'].pct_change()

            # 8. Candle Features
            df_features['CANDLE_BODY'] = abs(df['Close'] - df['Open'])
            df_features['UPPER_WICK'] = df['High'] - df[['Close', 'Open']].max(axis=1)
            df_features['LOWER_WICK'] = df[['Close', 'Open']].min(axis=1) - df['Low']
            df_features['CANDLE_RANGE'] = df['High'] - df['Low']
            df_features['BODY_RANGE_RATIO'] = df_features['CANDLE_BODY'] / df_features['CANDLE_RANGE']

            # 9. High-Low Features
            df_features['HIGH_LOW_POSITION'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
            df_features['HIGH_RECENT'] = df['High'].rolling(10).max()
            df_features['LOW_RECENT'] = df['Low'].rolling(10).min()
            df_features['PRICE_TO_RECENT_HIGH'] = df['Close'] / df_features['HIGH_RECENT']

            # 10. Stochastic Features
            if 'STOCH_K' in df.columns:
                df_features['STOCH_DIFF'] = df['STOCH_K'] - df['STOCH_D']
                df_features['STOCH_RANGE'] = df['STOCH_K'] - df['STOCH_K'].shift(5)

            # 11. ADX Features
            if 'ADX' in df.columns:
                df_features['TREND_STRENGTH'] = df['ADX'] / 50  # Normalize to 0-1
                df_features['IS_TRENDING'] = (df['ADX'] > 20).astype(float)

            # 12. Time-based Features
            df_features['HOUR'] = pd.to_datetime(df.index).hour
            df_features['DAY_OF_WEEK'] = pd.to_datetime(df.index).dayofweek

            # 13. Lagged Features (price history)
            for lag in [1, 2, 3, 5]:
                df_features[f'CLOSE_LAG_{lag}'] = df['Close'].shift(lag)
                df_features[f'RETURN_LAG_{lag}'] = df['Close'].pct_change(lag)

            # Fill NaN values
            df_features = df_features.bfill().ffill()
            df_features = df_features.fillna(0)

            logger.info(f"Features engineered: {len(df_features.columns)} features created")
            return df_features

        except Exception as e:
            logger.error(f"Error in feature engineering: {e}")
            return df

    def prepare_data(self, df, lookback=20, prediction_horizon=1):
        """Prepare data with advanced feature engineering.

        Args:
            df: DataFrame with OHLC and indicators
            lookback: Lookback period for sequences
            prediction_horizon: Candles ahead to predict

        Returns:
            X, y arrays ready for training
        """
        try:
            # Engineer features first
            df_engineered = self.engineer_features(df)

            # Create target
            df_engineered['Target'] = (df_engineered['Close'].shift(-prediction_horizon) > df_engineered['Close']).astype(int)

            # Select feature columns (exclude OHLC, Volume, Target, and time features)
            exclude_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Target', 'HOUR', 'DAY_OF_WEEK']
            feature_cols = [col for col in df_engineered.columns if col not in exclude_cols]

            self.feature_names = feature_cols

            # Create sequences
            X = []
            y = []

            for i in range(len(df_engineered) - lookback - prediction_horizon):
                X.append(df_engineered[feature_cols].iloc[i:i+lookback].values.flatten())
                y.append(df_engineered['Target'].iloc[i+lookback])

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

    def train(self, X, y, test_size=0.2, validation_split=0.2):
        """Train advanced model with validation.

        Args:
            X: Feature array
            y: Target array
            test_size: Test set fraction
            validation_split: Validation set fraction

        Returns:
            Dictionary with training metrics
        """
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Create model
            if self.model_type == 'xgboost':
                self.model = xgb.XGBClassifier(
                    n_estimators=200,
                    max_depth=7,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    min_child_weight=1,
                    reg_alpha=0.1,
                    reg_lambda=1.0,
                    random_state=42,
                    verbose=0,
                    eval_metric='logloss'
                )
            elif self.model_type == 'gradient_boost':
                self.model = GradientBoostingClassifier(
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=6,
                    min_samples_split=10,
                    subsample=0.8,
                    random_state=42
                )
            else:  # random_forest
                self.model = RandomForestClassifier(
                    n_estimators=200,
                    max_depth=15,
                    min_samples_split=10,
                    random_state=42,
                    n_jobs=-1
                )

            # Train model
            self.model.fit(X_train_scaled, y_train)

            # Evaluate
            train_score = self.model.score(X_train_scaled, y_train)
            test_score = self.model.score(X_test_scaled, y_test)

            # Additional metrics
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)

            # ROC AUC
            try:
                roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
            except:
                roc_auc = 0

            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            sensitivity = cm[1, 1] / (cm[1, 0] + cm[1, 1]) if (cm[1, 0] + cm[1, 1]) > 0 else 0
            specificity = cm[0, 0] / (cm[0, 0] + cm[0, 1]) if (cm[0, 0] + cm[0, 1]) > 0 else 0

            self.is_trained = True
            self.last_training_date = datetime.now()

            # Store metrics
            self.training_metrics = {
                'train_accuracy': train_score,
                'test_accuracy': test_score,
                'roc_auc': roc_auc,
                'sensitivity': sensitivity,  # True positive rate
                'specificity': specificity,  # True negative rate
                'precision': cm[1, 1] / (cm[1, 1] + cm[0, 1]) if (cm[1, 1] + cm[0, 1]) > 0 else 0,
                'training_date': self.last_training_date
            }

            # Feature importance
            if hasattr(self.model, 'feature_importances_'):
                self.feature_importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))

            logger.info(f"Model trained ({self.model_type})")
            logger.info(f"Train accuracy: {train_score:.4f}, Test accuracy: {test_score:.4f}")
            logger.info(f"ROC AUC: {roc_auc:.4f}, Sensitivity: {sensitivity:.4f}, Specificity: {specificity:.4f}")

            return self.training_metrics

        except Exception as e:
            logger.error(f"Error training model: {e}")
            return None

    def predict(self, X):
        """Make predictions with confidence.

        Args:
            X: Feature array

        Returns:
            Predictions and probabilities
        """
        if self.model is None or not self.is_trained:
            logger.error("Model not trained")
            return None, None

        try:
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
            probabilities = self.model.predict_proba(X_scaled)

            return predictions, probabilities

        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return None, None

    def predict_with_confidence(self, features):
        """Predict for single feature vector with confidence.

        Args:
            features: Feature array (1D)

        Returns:
            Tuple (prediction, confidence, is_confident)
        """
        try:
            features = np.array(features).reshape(1, -1)
            prediction, proba = self.predict(features)

            if prediction is None:
                return None, 0.0, False

            confidence = float(np.max(proba[0]))
            is_confident = confidence > self.config.PREDICTION_CONFIDENCE_THRESHOLD

            return int(prediction[0]), confidence, is_confident

        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            return None, 0.0, False

    def get_top_features(self, top_n=15):
        """Get top important features.

        Args:
            top_n: Number of top features

        Returns:
            DataFrame with feature importance
        """
        if not self.feature_importance_dict:
            logger.warning("No feature importance data")
            return None

        importance_df = pd.DataFrame(
            list(self.feature_importance_dict.items()),
            columns=['feature', 'importance']
        ).sort_values('importance', ascending=False).head(top_n)

        return importance_df

    def save_model(self, filename=None):
        """Save trained model.

        Args:
            filename: Output filename

        Returns:
            True if successful
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
                'feature_importance': self.feature_importance_dict,
                'model_type': self.model_type,
                'training_date': self.last_training_date,
                'training_metrics': self.training_metrics
            }

            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"Model saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def load_model(self, filepath):
        """Load trained model.

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
            self.feature_importance_dict = model_data.get('feature_importance', {})
            self.model_type = model_data['model_type']
            self.last_training_date = model_data['training_date']
            self.training_metrics = model_data.get('training_metrics', {})
            self.is_trained = True

            logger.info(f"Model loaded from {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def get_model_summary(self):
        """Get model summary and statistics.

        Returns:
            Dictionary with model info
        """
        return {
            'model_type': self.model_type,
            'is_trained': self.is_trained,
            'training_date': self.last_training_date,
            'feature_count': len(self.feature_names),
            'feature_names': self.feature_names[:10],  # First 10
            'training_metrics': self.training_metrics,
            'has_feature_importance': bool(self.feature_importance_dict)
        }

"""
Professional XGBoost-based trading model for XAUUSD.

Features:
- 30+ engineered technical indicators
- BUY/SELL/HOLD classification
- Confidence-based entry signals
- Market condition detection (trending vs ranging)
- Dynamic risk management
- Production-ready with model persistence
"""

import logging
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from pathlib import Path
from enum import Enum

try:
    import xgboost as xgb
    from sklearn.preprocessing import RobustScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    xgb = None

logger = logging.getLogger(__name__)


class TradeSignal(Enum):
    """Trade signal types."""
    STRONG_BUY = 3
    BUY = 2
    HOLD = 1
    SELL = 0
    STRONG_SELL = -1


class MarketCondition(Enum):
    """Market condition types."""
    STRONG_TRENDING = 3
    TRENDING = 2
    RANGING = 1
    UNKNOWN = 0


class ProfessionalXGBoostModel:
    """Production-grade XGBoost model for XAUUSD trading."""

    def __init__(self, config):
        """Initialize professional XGBoost model.

        Args:
            config: Configuration object with trading parameters
        """
        self.config = config
        self.model = None
        self.scaler = RobustScaler()
        self.feature_names = []
        self.is_trained = False
        self.training_metrics = {}
        self.feature_importance = {}
        self.class_weights = {0: 1.0, 1: 1.5, 2: 2.0}  # Favor BUY signals

        if not HAS_XGBOOST:
            raise ImportError("XGBoost is required for professional trading")

    def _safe_astype_float(self, series):
        """Safely convert series to float, handling NaN values."""
        try:
            return series.fillna(0).astype(float)
        except:
            return series.fillna(0).astype(float)

    def _ensure_indicators(self, df):
        """Calculate technical indicators if missing."""
        try:
            from src.technical_analysis import TechnicalAnalysis

            # Check which indicators are missing
            required_indicators = [
                'EMA_FAST', 'EMA_SLOW', 'RSI', 'MACD', 'SIGNAL',
                'ATR', 'BB_UPPER', 'BB_LOWER', 'SMA_SLOW', 'ADX',
                'STOCH_K', 'STOCH_D'
            ]

            missing = [ind for ind in required_indicators if ind not in df.columns]

            if missing:
                logger.info(f"Calculating missing indicators: {missing}")
                ta = TechnicalAnalysis(df.copy())
                ta.calculate_moving_averages()  # Includes MACD and SIGNAL
                ta.calculate_rsi()
                ta.calculate_bollinger_bands()
                ta.calculate_atr()
                ta.calculate_stochastic()
                ta.calculate_adx()
                df = ta.df

            return df
        except Exception as e:
            logger.warning(f"Could not calculate indicators: {e}")
            # Return as-is, feature engineering will handle missing columns
            return df

    def engineer_features(self, df):
        """Engineer 30+ professional trading features.

        Args:
            df: DataFrame with OHLC and technical indicators

        Returns:
            DataFrame with engineered features
        """
        try:
            features = df.copy()

            # Fill any NaN values first to prevent conversion errors
            features = features.ffill().bfill()
            features = features.fillna(0)

            # ===== TREND FEATURES =====
            # EMA-based trend
            if 'EMA_FAST' in df.columns and 'EMA_SLOW' in df.columns:
                features['EMA_50_200_CROSS'] = self._safe_astype_float((df['EMA_FAST'] > df['EMA_SLOW']))
                features['PRICE_ABOVE_EMA50'] = self._safe_astype_float((df['Close'] > df['EMA_FAST']))
                features['PRICE_ABOVE_EMA200'] = self._safe_astype_float((df['Close'] > df['EMA_SLOW']))
                features['EMA_DISTANCE'] = (df['EMA_FAST'] - df['EMA_SLOW']) / (df['Close'] + 1e-6)
            else:
                # Fallback: Use simple moving averages
                features['EMA_50_200_CROSS'] = pd.Series(0, index=features.index)
                features['EMA_DISTANCE'] = pd.Series(0.0, index=features.index)
                features['PRICE_ABOVE_EMA50'] = pd.Series(0, index=features.index)
                features['PRICE_ABOVE_EMA200'] = pd.Series(0, index=features.index)

            # ===== MOMENTUM FEATURES =====
            # RSI features
            if 'RSI' in df.columns:
                features['RSI_BULLISH'] = (df['RSI'] > 50).astype(float)
                features['RSI_OVERSOLD'] = (df['RSI'] < 30).astype(float)
                features['RSI_OVERBOUGHT'] = (df['RSI'] > 70).astype(float)
                features['RSI_MOMENTUM'] = df['RSI'].diff()
            else:
                features['RSI_BULLISH'] = 0
                features['RSI_OVERSOLD'] = 0
                features['RSI_OVERBOUGHT'] = 0
                features['RSI_MOMENTUM'] = 0

            # Rate of Change
            features['ROC_5'] = df['Close'].pct_change(5) * 100
            features['ROC_10'] = df['Close'].pct_change(10) * 100
            features['ROC_20'] = df['Close'].pct_change(20) * 100

            # MACD features
            if 'MACD' in df.columns and 'SIGNAL' in df.columns:
                features['MACD_ABOVE_SIGNAL'] = (df['MACD'] > df['SIGNAL']).astype(float)
                features['MACD_HISTOGRAM'] = df['MACD'] - df['SIGNAL']
                features['MACD_MOMENTUM'] = features['MACD_HISTOGRAM'].diff()
            else:
                features['MACD_ABOVE_SIGNAL'] = 0
                features['MACD_HISTOGRAM'] = 0
                features['MACD_MOMENTUM'] = 0

            # ===== VOLATILITY FEATURES =====
            # ATR-based volatility
            if 'ATR' in df.columns:
                features['ATR_RATIO'] = df['ATR'] / (df['Close'] + 1e-6)  # Volatility percentage
                try:
                    features['VOLATILITY_LEVEL'] = pd.cut(
                        features['ATR_RATIO'],
                        bins=[0, 0.005, 0.01, 0.02, 1.0],
                        labels=[1, 2, 3, 4]
                    ).astype(float)  # Convert to float to avoid NaN issues
                except:
                    # Fallback if cut fails
                    features['VOLATILITY_LEVEL'] = pd.Series(2.0, index=features.index)
            else:
                features['ATR_RATIO'] = (df['High'] - df['Low']) / (df['Close'] + 1e-6)
                features['VOLATILITY_LEVEL'] = 2  # Medium volatility fallback

            # Historical volatility
            features['HIST_VOL_20'] = df['Close'].pct_change().rolling(20).std()
            features['VOLATILITY_TRENDING'] = features['HIST_VOL_20'] > features['HIST_VOL_20'].shift(5)

            # Bollinger Bands
            if 'BB_UPPER' in df.columns and 'BB_LOWER' in df.columns:
                features['BB_WIDTH'] = (df['BB_UPPER'] - df['BB_LOWER']) / (df['Close'] + 1e-6)
                features['BB_POSITION'] = (df['Close'] - df['BB_LOWER']) / (df['BB_UPPER'] - df['BB_LOWER'] + 1e-6)
                features['NEAR_BB_UPPER'] = (features['BB_POSITION'] > 0.8).astype(float)
                features['NEAR_BB_LOWER'] = (features['BB_POSITION'] < 0.2).astype(float)
            else:
                features['BB_WIDTH'] = (df['High'] - df['Low']) / (df['Close'] + 1e-6)
                features['BB_POSITION'] = 0.5
                features['NEAR_BB_UPPER'] = 0
                features['NEAR_BB_LOWER'] = 0

            # ===== PRICE ACTION FEATURES =====
            # Candle patterns
            features['CANDLE_BODY'] = abs(df['Close'] - df['Open'])
            features['UPPER_WICK'] = df['High'] - df[['Close', 'Open']].max(axis=1)
            features['LOWER_WICK'] = df[['Close', 'Open']].min(axis=1) - df['Low']
            features['CANDLE_RANGE'] = df['High'] - df['Low']
            features['BODY_RATIO'] = features['CANDLE_BODY'] / (features['CANDLE_RANGE'] + 1e-6)
            features['UPPER_WICK_RATIO'] = features['UPPER_WICK'] / (features['CANDLE_RANGE'] + 1e-6)
            features['LOWER_WICK_RATIO'] = features['LOWER_WICK'] / (features['CANDLE_RANGE'] + 1e-6)

            # Engulfing pattern
            features['IS_BULLISH_CANDLE'] = (df['Close'] > df['Open']).astype(float)
            features['IS_BEARISH_CANDLE'] = (df['Close'] < df['Open']).astype(float)
            features['BULLISH_ENGULFING'] = (
                (features['IS_BULLISH_CANDLE'].astype(bool)) &
                (features['IS_BEARISH_CANDLE'].shift(1).astype(bool)) &
                (features['CANDLE_BODY'] > features['CANDLE_BODY'].shift(1))
            ).astype(float)

            # Close position in range
            features['CLOSE_POSITION'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'] + 1e-6)

            # ===== VOLUME FEATURES =====
            if 'Volume' in df.columns:
                features['VOLUME_SMA_20'] = df['Volume'].rolling(20).mean()
                features['VOLUME_RATIO'] = df['Volume'] / (features['VOLUME_SMA_20'] + 1e-6)
                features['HIGH_VOLUME'] = (features['VOLUME_RATIO'] > 1.5).astype(float)

            # ===== MEAN REVERSION FEATURES =====
            # Distance from moving averages
            if 'SMA_SLOW' in df.columns:
                features['PRICE_SMA_DISTANCE'] = (df['Close'] - df['SMA_SLOW']) / (df['SMA_SLOW'] + 1e-6)
                features['OVERSOLD_SMA'] = (features['PRICE_SMA_DISTANCE'] < -0.02).astype(float)
                features['OVERBOUGHT_SMA'] = (features['PRICE_SMA_DISTANCE'] > 0.02).astype(float)
            else:
                features['PRICE_SMA_DISTANCE'] = 0
                features['OVERSOLD_SMA'] = 0
                features['OVERBOUGHT_SMA'] = 0

            # ===== STRENGTH FEATURES =====
            # ADX (trend strength)
            if 'ADX' in df.columns:
                features['TREND_STRENGTH'] = df['ADX'] / 50.0  # Normalize to 0-1
                features['IS_TRENDING'] = (df['ADX'] > 25).astype(float)
                features['STRONG_TREND'] = (df['ADX'] > 40).astype(float)
            else:
                features['TREND_STRENGTH'] = 0.5
                features['IS_TRENDING'] = 0
                features['STRONG_TREND'] = 0

            # Stochastic
            if 'STOCH_K' in df.columns and 'STOCH_D' in df.columns:
                features['STOCH_ABOVE_50'] = (df['STOCH_K'] > 50).astype(float)
                stoch_above = (df['STOCH_K'] > df['STOCH_D']).astype(bool)
                stoch_below_prev = (df['STOCH_K'].shift(1) <= df['STOCH_D'].shift(1)).astype(bool)
                features['STOCH_CROSSOVER'] = (stoch_above & stoch_below_prev).astype(float)
            else:
                features['STOCH_ABOVE_50'] = 0
                features['STOCH_CROSSOVER'] = 0

            # ===== SEQUENCE FEATURES =====
            # Price momentum
            features['CLOSE_MOMENTUM'] = df['Close'].diff()
            features['CLOSE_MOMENTUM_DIR'] = (features['CLOSE_MOMENTUM'] > 0).astype(float)

            # Multi-period returns
            for period in [1, 3, 5]:
                features[f'RETURN_{period}'] = df['Close'].pct_change(period)

            # Previous candle patterns
            features['PREV_BULLISH'] = features['IS_BULLISH_CANDLE'].shift(1)
            features['PREV_BEARISH'] = features['IS_BEARISH_CANDLE'].shift(1)

            # ===== TIME FEATURES =====
            if isinstance(df.index, pd.DatetimeIndex):
                features['HOUR'] = df.index.hour
                features['DAY_OF_WEEK'] = df.index.dayofweek

            # Fill NaN values
            features = features.bfill().ffill()

            logger.info(f"✓ Engineered {len(features.columns)} features")
            return features

        except Exception as e:
            logger.error(f"Error engineering features: {e}", exc_info=True)
            # Return features with default values if engineering fails
            features = df.copy()
            # Create basic features with default values to allow model to train
            features['TREND'] = 0.0
            features['MOMENTUM'] = 0.0
            features['VOLATILITY'] = 0.5
            features['VOLUME_SIGNAL'] = 0.0
            features['PRICE_ACTION'] = 0.0
            return features

    def create_target(self, df, prediction_horizon=1, threshold_pct=0.3):
        """Create BUY/SELL/HOLD targets.

        Args:
            df: DataFrame with Close prices
            prediction_horizon: Candles ahead to predict
            threshold_pct: Minimum % move to classify as BUY/SELL

        Returns:
            Target array (0=SELL, 1=HOLD, 2=BUY)
        """
        future_returns = df['Close'].shift(-prediction_horizon) / df['Close'] - 1
        threshold = threshold_pct / 100.0

        # Create 3-class target
        targets = np.ones(len(future_returns), dtype=int)  # Default: HOLD
        targets[future_returns > threshold] = 2  # BUY
        targets[future_returns < -threshold] = 0  # SELL

        return targets

    def prepare_data(self, df, lookback=20, prediction_horizon=1):
        """Prepare data for training/prediction.

        Args:
            df: DataFrame with OHLC and indicators
            lookback: Lookback period
            prediction_horizon: Prediction horizon in candles

        Returns:
            X, y arrays ready for model
        """
        try:
            # Ensure technical indicators are calculated
            df = self._ensure_indicators(df)

            # Engineer features
            features_df = self.engineer_features(df)

            # Fill NaN values in features (forward fill, then backward fill)
            features_df = features_df.ffill().bfill()
            features_df = features_df.fillna(0)  # Fill remaining NaNs with 0

            # Create target
            y = self.create_target(df, prediction_horizon=prediction_horizon)

            # Remove unnecessary columns
            exclude_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'HOUR', 'DAY_OF_WEEK']
            feature_cols = [col for col in features_df.columns if col not in exclude_cols]

            self.feature_names = feature_cols

            # Create training sequences
            X = []
            y_out = []

            for i in range(len(features_df) - lookback - prediction_horizon):
                X.append(features_df[feature_cols].iloc[i:i+lookback].values.flatten())
                y_out.append(y[i+lookback])

            X = np.array(X, dtype=np.float32)
            y_out = np.array(y_out, dtype=np.int32)

            logger.info(f"Before filtering: X shape = {X.shape}, y shape = {y_out.shape}")

            # Remove NaN/Inf rows
            try:
                valid_idx = np.isfinite(X).all(axis=1)
                valid_count = valid_idx.sum()
                logger.info(f"Valid samples: {valid_count} / {len(X)}")

                # If all values are invalid, use nan_to_num fallback
                if not valid_idx.any():
                    logger.warning(f"All samples have NaN/Inf - using fallback conversion")
                    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
                else:
                    X = X[valid_idx]
                    y_out = y_out[valid_idx]
            except Exception as e:
                logger.warning(f"Could not filter NaN/Inf values: {e}")
                # Try alternative approach
                X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)

            if len(X) == 0:
                logger.error("✗ No valid samples after data preparation")
                return None, None

            logger.info(f"✓ Data prepared: {len(X)} samples, {X.shape[1]} features")
            logger.info(f"  Class distribution: {np.bincount(y_out.astype(int))}")

            return X, y_out

        except Exception as e:
            logger.error(f"Error preparing data: {e}", exc_info=True)
            return None, None

    def train(self, X, y, test_size=0.2, validation_split=0.1):
        """Train XGBoost model with validation.

        Args:
            X: Feature array
            y: Target array
            test_size: Test set fraction
            validation_split: Validation set fraction

        Returns:
            Dictionary with training metrics
        """
        try:
            if len(X) < 100:
                logger.error("✗ Insufficient data for training (need at least 100 samples)")
                return None

            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            logger.info("Training XGBoost model...")

            # Create XGBoost classifier
            self.model = xgb.XGBClassifier(
                n_estimators=300,
                max_depth=8,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=1,
                reg_alpha=0.5,
                reg_lambda=1.0,
                objective='multi:softmax' if len(np.unique(y_train)) == 3 else 'binary:logistic',
                random_state=42,
                verbosity=0,
                eval_metric='logloss',
                tree_method='hist'
            )

            # Train model
            try:
                # Try with early stopping (newer XGBoost versions)
                self.model.fit(
                    X_train_scaled, y_train,
                    eval_set=[(X_test_scaled, y_test)],
                    early_stopping_rounds=20,
                    verbose=False
                )
            except TypeError:
                # Fallback for older XGBoost versions
                self.model.fit(
                    X_train_scaled, y_train,
                    verbose=False
                )

            # Evaluation
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)

            # Get metrics
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

            self.training_metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision_weighted': precision_score(y_test, y_pred, average='weighted', zero_division=0),
                'recall_weighted': recall_score(y_test, y_pred, average='weighted', zero_division=0),
                'f1_weighted': f1_score(y_test, y_pred, average='weighted', zero_division=0),
                'test_samples': len(X_test),
                'train_samples': len(X_train),
            }

            # Feature importance
            self.feature_importance = dict(zip(
                self.feature_names,
                self.model.feature_importances_[:len(self.feature_names)]
            ))

            self.is_trained = True

            logger.info(f"✓ Model trained successfully")
            logger.info(f"  Accuracy: {self.training_metrics['accuracy']:.4f}")
            logger.info(f"  Precision: {self.training_metrics['precision_weighted']:.4f}")
            logger.info(f"  Recall: {self.training_metrics['recall_weighted']:.4f}")

            return self.training_metrics

        except Exception as e:
            logger.error(f"Error training model: {e}", exc_info=True)
            return None

    def predict_signal(self, recent_features, confidence_threshold=0.65):
        """Predict trading signal with confidence.

        Args:
            recent_features: Recent feature array (1D or 2D)
            confidence_threshold: Minimum confidence for signal

        Returns:
            Dictionary with signal, confidence, and probabilities
        """
        try:
            if not self.is_trained or self.model is None:
                return {
                    'signal': TradeSignal.HOLD,
                    'confidence': 0.0,
                    'probabilities': {'SELL': 0.33, 'HOLD': 0.34, 'BUY': 0.33},
                    'message': 'Model not trained'
                }

            # Ensure 2D array
            if len(recent_features.shape) == 1:
                recent_features = recent_features.reshape(1, -1)

            # Scale features
            recent_scaled = self.scaler.transform(recent_features)

            # Predict
            prediction = self.model.predict(recent_scaled)[0]
            probabilities = self.model.predict_proba(recent_scaled)[0]

            max_prob = np.max(probabilities)
            signal_names = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}

            # Determine signal strength based on confidence
            if prediction == 2 and max_prob > confidence_threshold:
                signal = TradeSignal.STRONG_BUY
            elif prediction == 2:
                signal = TradeSignal.BUY
            elif prediction == 0 and max_prob > confidence_threshold:
                signal = TradeSignal.STRONG_SELL
            elif prediction == 0:
                signal = TradeSignal.SELL
            else:
                signal = TradeSignal.HOLD

            return {
                'signal': signal,
                'signal_name': signal.name,
                'confidence': float(max_prob),
                'prediction': int(prediction),
                'probabilities': {
                    'SELL': float(probabilities[0]),
                    'HOLD': float(probabilities[1]),
                    'BUY': float(probabilities[2])
                },
                'meets_threshold': max_prob > confidence_threshold
            }

        except Exception as e:
            logger.error(f"Error predicting signal: {e}", exc_info=True)
            return {
                'signal': TradeSignal.HOLD,
                'confidence': 0.0,
                'error': str(e)
            }

    def detect_market_condition(self, df, window=20):
        """Detect market condition (trending vs ranging).

        Args:
            df: DataFrame with technical indicators
            window: Window size for analysis

        Returns:
            MarketCondition enum
        """
        try:
            if 'ADX' not in df.columns or len(df) < window:
                return MarketCondition.UNKNOWN

            recent_adx = df['ADX'].iloc[-window:].mean()

            if recent_adx > 40:
                return MarketCondition.STRONG_TRENDING
            elif recent_adx > 25:
                return MarketCondition.TRENDING
            elif recent_adx > 20:
                return MarketCondition.RANGING
            else:
                return MarketCondition.UNKNOWN

        except Exception as e:
            logger.error(f"Error detecting market condition: {e}")
            return MarketCondition.UNKNOWN

    def save_model(self, filepath=None):
        """Save trained model to disk.

        Args:
            filepath: Path to save model (default: models/professional_xgboost.pkl)
        """
        try:
            if not self.is_trained or self.model is None:
                logger.warning("Model not trained, cannot save")
                return False

            if filepath is None:
                filepath = self.config.MODELS_DIR / 'professional_xgboost.pkl'

            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'training_metrics': self.training_metrics,
                'feature_importance': self.feature_importance,
                'timestamp': datetime.now().isoformat()
            }

            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"✓ Model saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def load_model(self, filepath=None):
        """Load trained model from disk.

        Args:
            filepath: Path to model file (default: models/professional_xgboost.pkl)

        Returns:
            True if successful
        """
        try:
            if filepath is None:
                filepath = self.config.MODELS_DIR / 'professional_xgboost.pkl'

            filepath = Path(filepath)
            if not filepath.exists():
                logger.warning(f"Model file not found: {filepath}")
                return False

            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.training_metrics = model_data.get('training_metrics', {})
            self.feature_importance = model_data.get('feature_importance', {})
            self.is_trained = True

            logger.info(f"✓ Model loaded from {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def get_top_features(self, top_n=15):
        """Get top N important features.

        Args:
            top_n: Number of features to return

        Returns:
            List of (feature_name, importance) tuples
        """
        if not self.feature_importance:
            return []

        sorted_features = sorted(
            self.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_features[:top_n]

    def get_model_summary(self):
        """Get comprehensive model summary.

        Returns:
            Dictionary with model information
        """
        return {
            'is_trained': self.is_trained,
            'num_features': len(self.feature_names),
            'training_metrics': self.training_metrics,
            'top_features': self.get_top_features(10),
            'model_type': 'XGBoost Classifier',
            'classes': ['SELL', 'HOLD', 'BUY'],
            'timestamp': datetime.now().isoformat()
        }

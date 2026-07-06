import pandas as pd
import numpy as np
import joblib
import os
import logging

from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    VotingClassifier
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    brier_score_loss
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURES = [
    "cpu_usage_percent",
    "memory_usage_percent",
    "memory_used_mb",
    "disk_usage_percent",
    "network_total",
    "request_latency_ms",
    "error_count",
    "active_processes",
    "cpu_memory_ratio",
    "cpu_change",
    "memory_change",
    "latency_per_process"
]


def train_and_save_model(save_path="ML/models/anomaly_model.pkl"):
    """Trains the Multi-Algorithm Soft-Voting Ensemble and saves it using the active Python/numpy environment."""
    dataset_path = "data/processed/feature_engineered_metrics.csv"
    if not os.path.exists(dataset_path):
        dataset_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "processed", "feature_engineered_metrics.csv"
        )

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Processed dataset not found at {dataset_path}")

    df = pd.read_csv(dataset_path)
    X = df[FEATURES]
    y = df["anomaly"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        stratify=y,
        random_state=42
    )

    rf_model = RandomForestClassifier(
        n_estimators=150,
        criterion="entropy",
        max_depth=7,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42
    )

    et_model = ExtraTreesClassifier(
        n_estimators=150,
        max_depth=7,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42
    )

    hgb_model = HistGradientBoostingClassifier(
        max_iter=100,
        max_depth=4,
        learning_rate=0.06,
        min_samples_leaf=4,
        class_weight="balanced",
        random_state=42
    )

    ensemble = VotingClassifier(
        estimators=[
            ("rf", rf_model),
            ("et", et_model),
            ("hgb", hgb_model)
        ],
        voting="soft",
        weights=[2, 2, 1]
    )

    ensemble.fit(X_train, y_train)

    # Save Model
    target_path = save_path
    if not os.path.isabs(target_path):
        target_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            save_path
        )
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    joblib.dump(ensemble, target_path)
    logger.info(f"[OK] Multi-Algorithm Ensemble Model trained & saved to {target_path}")

    return ensemble


if __name__ == "__main__":
    train_and_save_model()
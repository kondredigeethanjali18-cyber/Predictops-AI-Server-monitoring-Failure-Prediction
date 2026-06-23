import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)


# ----------------------------------
# Load Dataset
# ----------------------------------

df = pd.read_csv(
    "data/processed/feature_engineered_metrics.csv"
)

# ----------------------------------
# Features
# ----------------------------------

features = [
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

X = df[features]

y = df["anomaly"]

# ----------------------------------
# Split Dataset
# ----------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

# ----------------------------------
# Train Model
# ----------------------------------

model = RandomForestClassifier(
    n_estimators=500,
    max_depth=20,
    min_samples_split=3,
    min_samples_leaf=1,
    class_weight="balanced",
    random_state=42
)

model.fit(X_train, y_train)

# ----------------------------------
# Evaluate
# ----------------------------------

probabilities = model.predict_proba(X_test)

avg_confidence = (
    probabilities.max(axis=1).mean()
)

print(
    f"\nAverage Confidence: {avg_confidence * 100:.2f}%"
)

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

precision = precision_score(
    y_test,
    predictions,
    zero_division=0
)

recall = recall_score(
    y_test,
    predictions,
    zero_division=0
)

f1 = f1_score(
    y_test,
    predictions,
    zero_division=0
)

print("\n==============================")
print("MODEL EVALUATION")
print("==============================")

print(
    f"Accuracy : {accuracy * 100:.2f}%"
)

print(
    f"Precision: {precision * 100:.2f}%"
)

print(
    f"Recall   : {recall * 100:.2f}%"
)

print(
    f"F1 Score : {f1 * 100:.2f}%"
)

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions
    )
)

print("\nConfusion Matrix:")
print(
    confusion_matrix(
        y_test,
        predictions
    )
)



# ----------------------------------
# Save Model
# ----------------------------------

joblib.dump(
    model,
    "ml/models/anomaly_model.pkl"
)

print("Model Saved Successfully")
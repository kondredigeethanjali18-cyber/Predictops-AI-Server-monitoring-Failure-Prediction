import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

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
    random_state=42
)

# ----------------------------------
# Train Model
# ----------------------------------

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

# ----------------------------------
# Evaluate
# ----------------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\nAccuracy:", round(accuracy * 100, 2), "%")

# ----------------------------------
# Save Model
# ----------------------------------

joblib.dump(
    model,
    "ml/models/anomaly_model.pkl"
)

print("Model Saved Successfully")
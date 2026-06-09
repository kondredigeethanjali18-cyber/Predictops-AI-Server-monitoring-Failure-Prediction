import pandas as pd
import joblib

from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix

model = joblib.load(
    "ml/models/anomaly_model.pkl"
)

df = pd.read_csv(
    "data/processed/feature_engineered_metrics.csv"
)

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

predictions = model.predict(X)

print("\nConfusion Matrix")
print(
    confusion_matrix(y, predictions)
)

print("\nClassification Report")
print(
    classification_report(
        y,
        predictions
    )
)
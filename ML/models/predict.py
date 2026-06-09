import joblib
import pandas as pd

# Load model
model = joblib.load(
    "ml/models/anomaly_model.pkl"
)

# Load latest dataset
df = pd.read_csv(
    "data/processed/feature_engineered_metrics.csv"
)

# Same features used during training
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

# Take latest record
latest = df.iloc[-1]

X = latest[features].values.reshape(1, -1)

prediction = model.predict(X)[0]

probability = model.predict_proba(X)[0]

print("\nServer ID:", latest["server_id"])
print("Server Name:", latest["server_name"])

if prediction == 1:
    print("Status: ANOMALY DETECTED")
else:
    print("Status: NORMAL")

print(
    "Confidence:",
    round(max(probability) * 100, 2),
    "%"
)
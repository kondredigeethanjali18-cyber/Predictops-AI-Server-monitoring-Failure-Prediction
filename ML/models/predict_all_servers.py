import joblib
import pandas as pd

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

latest_servers = (
    df.groupby("server_id")
    .tail(1)
)

for _, row in latest_servers.iterrows():

    X = row[features].values.reshape(1, -1)

    prediction = model.predict(X)[0]

    print(
        f"{row['server_id']} | "
        f"{row['server_name']} | "
        f"{'ANOMALY' if prediction else 'NORMAL'}"
    )
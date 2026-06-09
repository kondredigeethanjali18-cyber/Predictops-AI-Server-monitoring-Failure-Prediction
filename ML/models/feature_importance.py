import joblib
import pandas as pd

# Load trained model
model = joblib.load(
    "ml/models/anomaly_model.pkl"
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

# Get importance scores
importance = model.feature_importances_

# Create dataframe
importance_df = pd.DataFrame({
    "Feature": features,
    "Importance": importance
})

# Sort descending
importance_df = importance_df.sort_values(
    by="Importance",
    ascending=False
)

print("\nFeature Importance:\n")
print(importance_df)

# Save for dashboard use later
importance_df.to_csv(
    "data/processed/feature_importance.csv",
    index=False
)

print(
    "\nSaved: data/processed/feature_importance.csv"
)
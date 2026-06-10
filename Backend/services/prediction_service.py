import pandas as pd
import joblib
from Backend.database.mongodb import predictions_collection
from datetime import datetime, timezone


MODEL_PATH = "ml/models/anomaly_model.pkl"

model = joblib.load(MODEL_PATH)

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



def predict_latest_server():

    df = pd.read_csv(
        "data/processed/feature_engineered_metrics.csv"
    )

    latest = df.iloc[-1]

    X = pd.DataFrame(
        [latest[FEATURES]],
        columns=FEATURES
    )

    prediction = model.predict(X)[0]

    confidence = float(
    max(model.predict_proba(X)[0])
)

    causes = []

    if latest["cpu_usage_percent"] > 90:
     causes.append("High CPU Usage")

    if latest["memory_usage_percent"] > 90:
     causes.append("High Memory Usage")

    if latest["disk_usage_percent"] > 90:
     causes.append("High Disk Usage")

    if latest["error_count"] > 10:
     causes.append("High Error Count")

    if latest["request_latency_ms"] > 500:
     causes.append("High Request Latency")

    if not causes:
     causes.append("No major issue detected")

    result = {
    "server_id": latest["server_id"],
    "server_name": latest["server_name"],

    "prediction": (
        "ANOMALY"
        if prediction == 1
        else "NORMAL"
    ),

    "confidence": round(confidence * 100, 2),

    "cpu_usage_percent": float(latest["cpu_usage_percent"]),
    "memory_usage_percent": float(latest["memory_usage_percent"]),
    "disk_usage_percent": float(latest["disk_usage_percent"]),

    "possible_causes": causes,

    "timestamp": datetime.now(timezone.utc)
}

# Save prediction to MongoDB
    predictions_collection.insert_one(result)

    return result

from Backend.services.feature_engineering import build_features


def predict_metric(metric):

    features = build_features(metric)

    X = pd.DataFrame([features])

    prediction = model.predict(X)[0]

    confidence = float(
        max(model.predict_proba(X)[0])
    )

    causes = []

    if metric["cpu_usage_percent"] > 90:
        causes.append("High CPU Usage")

    if metric["memory_usage_percent"] > 90:
        causes.append("High Memory Usage")

    if metric["disk_usage_percent"] > 90:
        causes.append("High Disk Usage")

    if not causes:
        causes.append("No major issue detected")

    result = {
        "server_name": metric["server_name"],

        "prediction":
            "ANOMALY"
            if prediction == 1
            else "NORMAL",

        "confidence":
            round(confidence * 100, 2),

        "cpu_usage_percent":
            metric["cpu_usage_percent"],

        "memory_usage_percent":
            metric["memory_usage_percent"],

        "disk_usage_percent":
            metric["disk_usage_percent"],

        "possible_causes":
            causes,

        "timestamp":
            datetime.now(timezone.utc)
    }

    predictions_collection.insert_one(result)

    return result
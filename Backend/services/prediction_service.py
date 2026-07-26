import os
import logging
import pandas as pd
import joblib
from Backend.database.mongodb import get_predictions_collection
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = "ML/models/anomaly_model.pkl"

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


def load_or_train_model():
    model_file = MODEL_PATH
    if not os.path.isabs(model_file):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_file = os.path.join(root, MODEL_PATH)

    try:
        loaded = joblib.load(model_file)
        # Probe model to verify compatibility with active numpy/sklearn runtime
        dummy = pd.DataFrame([[0.0] * len(FEATURES)], columns=FEATURES)
        loaded.predict_proba(dummy)
        logger.info(f"Model loaded successfully from {model_file}")
        return loaded
    except Exception as exc:
        logger.warning(f"Failed to load {model_file} due to version mismatch ({exc}). Retraining model with active runtime's scikit-learn & numpy...")
        try:
            from ML.models.train_model import train_and_save_model
            return train_and_save_model(model_file)
        except Exception as train_exc:
            logger.error(f"Auto-retrain failed: {train_exc}")
            raise train_exc


model = load_or_train_model()

THROUGHPUT_SAMPLE_SECONDS = 5


def calculate_network_throughput(network_total):
    return round(
        float(network_total) / THROUGHPUT_SAMPLE_SECONDS,
        2
    )



def generate_remark(prediction: str, confidence: float, cpu: float, memory: float, disk: float, causes: list) -> str:
    if prediction == "NORMAL":
        return "System operating normally within standard thresholds."
    
    cause_str = ", ".join(causes) if causes else ""
    if confidence >= 90:
        return f"CRITICAL: High failure probability ({confidence}%). Indicators: {cause_str or 'anomaly behavioral signature'}. Urgent intervention needed."
    elif confidence >= 70:
        return f"WARNING: Severe resource deviation ({confidence}%). Indicators: {cause_str or 'high utilization'}. Monitor closely."
    else:
        return f"NOTICE: Moderate variance ({confidence}%). Indicators: {cause_str or 'behavioral anomaly'}."


def predict_latest_server():

    df = pd.read_csv(
        "data/processed/feature_engineered_metrics.csv"
    )

    latest = df.iloc[-1]

    X = pd.DataFrame(
        [latest[FEATURES]],
        columns=FEATURES
    )

    prediction = int(model.predict(X)[0])
    confidence = round(float(max(model.predict_proba(X)[0])) * 100, 2)

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
     causes.append("Behavioral Telemetry Anomaly" if prediction == 1 else "Optimal Performance (Within Baseline)")

    result = {
    "server_id": latest["server_id"],
    "server_name": latest["server_name"],

    "prediction": (
        "ANOMALY"
        if prediction == 1
        else "NORMAL"
    ),

    "confidence": confidence,

    "cpu_usage_percent": float(latest["cpu_usage_percent"]),
    "memory_usage_percent": float(latest["memory_usage_percent"]),
    "disk_usage_percent": float(latest["disk_usage_percent"]),
    "network_throughput": calculate_network_throughput(
        latest["network_total"]
    ),

    "possible_causes": causes,

    "timestamp": datetime.now(timezone.utc),

    "remark": generate_remark(
        "ANOMALY" if prediction == 1 else "NORMAL",
        confidence,
        float(latest["cpu_usage_percent"]),
        float(latest["memory_usage_percent"]),
        float(latest["disk_usage_percent"]),
        causes
    )
}

    # Save prediction to MongoDB
    col = get_predictions_collection()
    if col is not None:
        col.insert_one(result)

    return result

from Backend.services.feature_engineering import build_features


def predict_metric(metric):

    features = build_features(metric)

    X = pd.DataFrame([features])

    prediction = int(model.predict(X)[0])
    confidence = round(float(max(model.predict_proba(X)[0])) * 100, 2)

    cpu = float(metric.get("cpu_usage_percent", 0))
    mem = float(metric.get("memory_usage_percent", 0))
    disk = float(metric.get("disk_usage_percent", 0))
    latency = float(metric.get("request_latency_ms", 0))
    cpu_change = float(features.get("cpu_change", 0))
    mem_change = float(features.get("memory_change", 0))

    # Multi-factor validation: Ensure high utilization, latency surges, and sudden spikes are accurately classified as ANOMALY
    is_stressed = (
        prediction == 1
        or (cpu >= 80.0 and mem >= 70.0)
        or cpu >= 85.0
        or mem >= 82.0
        or disk >= 85.0
        or latency >= 250.0
        or abs(cpu_change) >= 15.0
        or abs(mem_change) >= 15.0
    )

    if is_stressed:
        prediction = 1
        prob_anom = float(model.predict_proba(X)[0][1]) * 100
        raw_conf = float(max(model.predict_proba(X)[0])) * 100
        confidence = max(round(prob_anom, 2), round(raw_conf, 2), 88.5)

    causes = []

    if cpu >= 85 and mem >= 75:
        causes.append("Critical Resource Saturation (CPU + Memory Stress)")
    elif cpu >= 85:
        causes.append(f"High CPU Load ({cpu}%)")
    elif cpu >= 75:
        causes.append(f"Elevated CPU Usage ({cpu}%)")

    if mem >= 85:
        causes.append(f"High Memory Usage ({mem}%)")
    elif mem >= 75 and "Critical Resource Saturation (CPU + Memory Stress)" not in causes:
        causes.append(f"Elevated Memory Pressure ({mem}%)")

    if disk >= 85:
        causes.append(f"Critical Disk Utilization ({disk}%)")
    elif disk >= 75:
        causes.append(f"High Disk Usage ({disk}%)")

    if latency >= 250:
        causes.append(f"High Request Latency ({latency}ms)")

    if abs(cpu_change) >= 15:
        causes.append(f"Rapid CPU Spike (Δ{round(cpu_change, 1)}%)")
    if abs(mem_change) >= 15:
        causes.append(f"Sudden Memory Surge (Δ{round(mem_change, 1)}%)")

    if not causes:
        if prediction == 1:
            causes.append("Behavioral Telemetry Anomaly (Resource Fluctuation)")
        else:
            causes.append("Optimal Performance (Within Baseline)")

    result = {
        "server_name": metric["server_name"],

        "prediction":
            "ANOMALY"
            if prediction == 1
            else "NORMAL",

        "confidence":
            confidence,

        "cpu_usage_percent":
            metric["cpu_usage_percent"],

        "memory_usage_percent":
            metric["memory_usage_percent"],

        "disk_usage_percent":
            metric["disk_usage_percent"],

        "network_throughput":
            calculate_network_throughput(
                features["network_total"]
            ),

        "possible_causes":
            causes,

        "timestamp":
            datetime.now(timezone.utc),

        "remark": generate_remark(
            "ANOMALY" if prediction == 1 else "NORMAL",
            confidence,
            cpu,
            mem,
            disk,
            causes
        )
    }

    col = get_predictions_collection()
    if col is not None:
        col.insert_one(result)

    return result
